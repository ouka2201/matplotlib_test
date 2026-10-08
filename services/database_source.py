"""日別48列のテーブルから帳票用の30分データを作る。"""

import os
import math
import numpy as np
import pandas as pd
from services.data_service import bounds, validate_data

# DBの物理列名をここに集約する。
# 供給地点特定番号はお客さま番号とは別項目で、先頭の0を保持する。
POINT = "T01_KYO_CTN_TOK_NO"
DATE = "T01_GET_YMD"
# 01〜48を数値順に並べる。この列順と時刻の順番を対応させる。
SLOTS = [f"T01_30T_SYR{i:02d}" for i in range(1, 49)]
CONTRACT_POINT = "QSQB_DCIS2_SPL_PT_SPC_NO"
CONTRACT_POWER = "QSQB_DCIS2_HVPW_CTRT"


def expand_daily_rows(
    rows, report_month, supply_point, value_unit="kWh", quality_columns=()
):
    """日別48列を、1枠1行の日時・平均電力へ展開する。

    1→00:00、2→00:30、48→23:30。既定の保存値はkWhなので2倍して30分平均電力kWに変換する。
    月間電力量は平均電力×0.5時間を合計するため、元のkWh合計と一致する。

    Args:
        rows (Iterable[Mapping]): 日別レコード。物理列名は大文字・小文字どちらでもよい。
        report_month (str): 指定月を含む12か月の最終月。YYYY-MM形式。
        supply_point (str): 供給地点特定番号。先頭の0を保持する。
        value_unit (str): 保存値の単位。kW、kWh、Whのいずれか。
        quality_columns (Iterable[str]): 0件を要求する欠測・不正値件数列。指定時だけ検査する。

    Returns:
        pandas.DataFrame: 直近12か月内で実績のある期間のtimestamp・kw列。
            1年未満を許容するが、実績期間内は毎日48枠が必要。

    Raises:
        ValueError: 日付・値・単位・品質件数が不正、日別行の重複や欠損がある場合。
    """
    if not isinstance(supply_point, str) or not supply_point or len(supply_point) > 22:
        raise ValueError("供給地点特定番号は22文字以内の文字列で指定してください")
    # 保存値はkWh。30分=0.5時間なので、平均電力kWはkWh÷0.5で求める。
    # kW・Whは別の入力データ源を扱う場合の換算方法。今回の既定値はkWh。
    factors = {"kW": 1.0, "kWh": 2.0, "Wh": 0.002}
    if value_unit not in factors:
        raise ValueError("value_unitはkW、kWh、Whのいずれかです")
    # DBドライバーによる列名の大小文字の違いを吸収する。
    # 欠けている枠列を0で補わず、48列すべての存在を確認する。
    records = pd.DataFrame(
        [{str(k).upper(): v for k, v in row.items()} for row in rows]
    )
    if records.empty:
        raise ValueError("対象の直近12か月に実績データがありません")
    required = [POINT, DATE, *SLOTS, *[c.upper() for c in quality_columns]]
    missing = set(required) - set(records.columns)
    if missing:
        raise ValueError(f"日別データに必要な列がありません: {sorted(missing)}")
    if not records[POINT].map(lambda v: isinstance(v, str) and v == supply_point).all():
        raise ValueError("別の供給地点または文字列でない供給地点が含まれています")
    # 日付列はVARCHARのYYYYMMDD。8桁の形式と実在する日付の両方を検査する。
    date_strings = records[DATE].astype("string")
    if not date_strings.str.fullmatch(r"\d{8}", na=False).all():
        raise ValueError("取得年月日はYYYYMMDDの8桁文字列で指定してください")
    dates = pd.to_datetime(date_strings, format="%Y%m%d", errors="raise")
    start, end, _ = bounds(report_month)
    # 指定月を含む12か月へ絞る。終了は翌月1日で、この日付自体は含めない。
    selected = (dates >= start) & (dates < end)
    records = records.loc[selected].copy()
    dates = dates.loc[selected]
    if dates.duplicated().any():
        raise ValueError("同じ供給地点・取得年月日のレコードが重複しています")
    # 欠測・不正値の件数があれば、値が0に見えても正常なデータとして集計しない。
    for column in quality_columns:
        counts = pd.to_numeric(records[column.upper()], errors="raise")
        if counts.isna().any() or not (counts == 0).all():
            raise ValueError(f"欠測または不正値件数があるため作成できません: {column}")
    # 日別の横持ち48列を数値にする。空欄や数値以外はエラーとして扱う。
    values = records[SLOTS].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    # 日付×48枠の行列を作り、行ごとに00:00〜23:30を並べる。
    # 0〜47に30分を掛けるので、枠1は0分、枠48は1410分になる。
    timestamps = (
        dates.to_numpy()[:, None] + np.arange(48)[None, :] * np.timedelta64(30, "m")
    ).reshape(-1)
    # 日時と電力を同じ行順で平坦化する。日付や枠の対応がずれないようにする。
    # 共通検証で実績期間内の欠損・重複・負数を確認する。期間前後の不足は許容する。
    frame = pd.DataFrame(
        {"timestamp": timestamps, "kw": values.reshape(-1) * factors[value_unit]}
    )
    return validate_data(frame, report_month)


class DatabaseSource:
    """1ワーカー専用のSQLAlchemy接続。親プロセスの接続を共有しない。"""

    def __init__(self, settings):
        """接続先の環境変数とテーブル設定からEngineを作る。

        Args:
            settings (dict): url_env、schema、daily_table、contract_table、
                value_unit、quality_columns。接続URLを直接設定ファイルに保存しない。

        Raises:
            ValueError: 接続先環境変数がない場合。
        """
        from sqlalchemy import create_engine

        # 接続先と認証情報は環境変数から読む。顧客ジョブや設定JSONには書かない。
        variable = settings.get("url_env", "REPORT_DATABASE_URL")
        url = os.environ.get(variable)
        if not url:
            raise ValueError(f"DB接続先を環境変数{variable}に設定してください")
        self.settings = settings
        # Engineはワーカー内で作る。接続の利用前確認を有効にし、SQLの値をログへ表示しない。
        self.engine = create_engine(url, pool_pre_ping=True, hide_parameters=True)
        self.daily = None
        self.contract = None

    def _tables(self, connection):
        """実DBの列を一度だけ反映する。

        Args:
            connection (sqlalchemy.Connection): 現ワーカー内の接続。
        """
        # 列の定義は最初の取得時だけ実DBから読み、同じワーカー内で再利用する。
        if self.daily is None or self.contract is None:
            from sqlalchemy import MetaData, Table

            metadata = MetaData()
            schema = self.settings.get("schema", "db_corp")
            self.daily = Table(
                self.settings.get("daily_table", "t_ep_electricity_data_30min"),
                metadata,
                schema=schema,
                autoload_with=connection,
            )
            self.contract = Table(
                self.settings.get("contract_table", "t_ep_contracted_power"),
                metadata,
                schema=schema,
                autoload_with=connection,
            )

    @staticmethod
    def _column(table, name):
        """大文字・小文字を区別せず、物理列を取得する。

        Args:
            table (sqlalchemy.Table): 反映済みテーブル。
            name (str): 物理列名。

        Returns:
            sqlalchemy.Column: 対応する列。

        Raises:
            ValueError: 指定列が存在しない場合。
        """
        for column in table.c:
            if column.name.upper() == name.upper():
                return column
        raise ValueError(f"テーブルに必要な列がありません: {name}")

    def load(self, supply_point, report_month):
        """供給地点と期間を指定し、日別データと契約電力を取得する。

        接続は取得中だけ使い、PDF描画前にプールへ返す。WHERE条件の値は
        バインド変数を使用する。取得年月日はVARCHARのYYYYMMDDとして比較する。

        Args:
            supply_point (str): 22文字以内の供給地点特定番号。
            report_month (str): 最終対象月。指定月を含む12か月。

        Returns:
            tuple[pandas.DataFrame, float]: 30分平均電力と契約電力(kW)。

        Raises:
            ValueError: 契約電力が未登録・重複・不正、または30分データが不完全な場合。
        """
        from sqlalchemy import select, bindparam

        if (
            not isinstance(supply_point, str)
            or not supply_point
            or len(supply_point) > 22
        ):
            raise ValueError("供給地点特定番号は22文字以内の文字列で指定してください")
        start, end, _ = bounds(report_month)
        quality = self.settings.get("quality_columns", [])
        with self.engine.connect() as connection:
            self._tables(connection)
            # 必要な48枠と日付・供給地点・品質件数だけをSELECTする。
            columns = [
                self._column(self.daily, name).label(name)
                for name in [POINT, DATE, *SLOTS, *quality]
            ]
            date = self._column(self.daily, DATE)
            # 供給地点と日付はSQL文字列へ連結せず、値としてバインドする。
            # YYYYMMDDの8桁文字列は辞書順と日付順が一致するため、範囲条件で取得できる。
            query = (
                select(*columns)
                .where(
                    self._column(self.daily, POINT) == bindparam("point"),
                    date >= bindparam("start"),
                    date < bindparam("end"),
                )
                .order_by(date)
            )
            rows = (
                connection.execute(
                    query,
                    {
                        "point": supply_point,
                        "start": start.strftime("%Y%m%d"),
                        "end": end.strftime("%Y%m%d"),
                    },
                )
                .mappings()
                .all()
            )
            # 同じ供給地点の契約電力を参照する。1年分の履歴を持つテーブルではないため、
            # 参照時点の登録値を使用する。複数行から任意の1件を選ぶことはしない。
            contract_query = select(self._column(self.contract, CONTRACT_POWER)).where(
                self._column(self.contract, CONTRACT_POINT) == bindparam("point")
            )
            contracts = (
                connection.execute(contract_query, {"point": supply_point})
                .scalars()
                .all()
            )
        # この位置ではwithを抜け、DB接続はプールに返っている。
        # 以降のデータ展開・画像描画中はDB接続を占有しない。
        if len(contracts) != 1:
            raise ValueError("供給地点の契約電力が未登録または重複しています")
        contract = float(contracts[0])
        if not math.isfinite(contract) or contract <= 0:
            raise ValueError("契約電力は正の有限数である必要があります")
        return (
            expand_daily_rows(
                rows,
                report_month,
                supply_point,
                self.settings.get("value_unit", "kWh"),
                quality,
            ),
            contract,
        )

    def close(self):
        """ワーカー終了時にDB接続プールを解放する。"""
        self.engine.dispose()
