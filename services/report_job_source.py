"""管理テーブルの作成対象・状態と、ARVEの契約情報を取得する。"""

from datetime import datetime
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from sqlalchemy import MetaData, Table, bindparam, select, text, update

from services.database_source import DatabaseSource

# 管理テーブルの主キーは「供給地点特定番号＋対象年月」。
MANAGEMENT_POINT = "SUPPLY_POINT_NUMBER"
MANAGEMENT_MONTH = "TARGET_YEAR_MONTH"
STATUS = "CREATE_STATUS"
CUSTOMER_POINT = "CMN_SupplyPointSpecificNum__c"
CUSTOMER_COLUMNS = {
    "customer_number": "CMN_OldCustomerNum__c",
    "address": "CMN_DemandLocationAddress__c",
}


def normalize_report_ym(report_month):
    """対象年月を検証し、管理テーブル用のYYYYMMへ揃える。

    Args:
        report_month (str): YYYY-MMまたはYYYYMMの対象年月。

    Returns:
        str: YYYYMM形式の6桁文字列。

    Raises:
        ValueError: 年月の形式または月が不正な場合。
    """
    from services.data_service import bounds

    if not isinstance(report_month, str) or not re.fullmatch(
        r"\d{4}-?\d{2}", report_month
    ):
        raise ValueError("対象年月はYYYY-MMまたはYYYYMMで指定してください")
    report_ym = report_month.replace("-", "")
    bounds(f"{report_ym[:4]}-{report_ym[4:]}")
    return report_ym


def customer_column_mapping(table, settings):
    """ARVEの名義・住所・お客さま番号の物理列名を共通で解決する。

    Args:
        table (sqlalchemy.Table): 反映済みのARVEテーブル。
        settings (dict): customer_columnsの任意指定を持つDB設定。

    Returns:
        dict: 帳票の項目名から物理列名への対応。

    Raises:
        ValueError: 名義列を一意に特定できない場合。
    """
    mapping = {**CUSTOMER_COLUMNS, **settings.get("customer_columns", {})}
    if not mapping.get("customer_name"):
        matches = [
            column.name
            for column in table.c
            if column.name.upper().startswith("CMN_DEMANDLOCATIONFULLNAME_")
        ]
        if len(matches) != 1:
            raise ValueError(
                "customer_columns.customer_nameに名義の物理列名を指定してください"
            )
        mapping["customer_name"] = matches[0]
    return mapping


class ReportJobSource(DatabaseSource):
    """1プロセス専用の対象取得・状態更新・実績取得用DBサービス。"""

    def __init__(self, settings):
        """通常のDB設定に管理・ARVEテーブル設定を追加して初期化する。

        Args:
            settings (dict): DatabaseSourceの設定とmanagement_table、
                customer_table、pending_statuses、batch_user、customer_columns。

        Raises:
            ValueError: DB接続先や取得状態・更新者の設定が不正な場合。
        """
        # 上流が2で登録した対象と、前回エラー5の対象を処理する。
        self.pending_statuses = settings.get("pending_statuses", ["2", "5"])
        if (
            not isinstance(self.pending_statuses, list)
            or not self.pending_statuses
            or any(value not in ("2", "5") for value in self.pending_statuses)
        ):
            raise ValueError("pending_statusesには作成対象2・エラー5を指定してください")
        self.batch_user = settings.get("batch_user", "electricity_report_batch")
        if not isinstance(self.batch_user, str) or not 1 <= len(self.batch_user) <= 50:
            raise ValueError("batch_userは1〜50文字で指定してください")
        super().__init__(settings)
        self.management = None
        self.customer = None
        self._claim_connection = None
        self._claim_key = None
        self._lock_id = None

    def _management_table(self, connection):
        """管理テーブルを初回だけ反映する。

        Args:
            connection (sqlalchemy.Connection): 現プロセスのDB接続。

        Returns:
            sqlalchemy.Table: 作成対象と状態を保持するテーブル。
        """
        if self.management is None:
            self.management = Table(
                self.settings.get("management_table", "t_power_report_mng_info"),
                MetaData(),
                schema=self.settings.get(
                    "management_schema", self.settings.get("schema", "db_corp")
                ),
                autoload_with=connection,
            )
        return self.management

    def fetch_targets(self, report_month):
        """指定年月の状態2・5のレコードを、軽い辞書の一覧で取得する。

        実績DataFrameや画像はここで取得しない。0件なら空配列を返す。
        取得時には状態を変更せず、実際のワーカー着手時にclaimする。

        Args:
            report_month (str): YYYY-MMまたはYYYYMMの対象年月。

        Returns:
            list[dict]: supply_point、target_year_month、company_id、syousapo_flg。
        """
        report_ym = normalize_report_ym(report_month)
        with self.engine.connect() as connection:
            table = self._management_table(connection)
            point = self._column(table, MANAGEMENT_POINT)
            month = self._column(table, MANAGEMENT_MONTH)
            query = (
                select(
                    point.label("supply_point"),
                    self._column(table, "COMPANY_ID").label("company_id"),
                    self._column(table, "SYOUSAPO_FLG").label("syousapo_flg"),
                )
                .where(
                    month == bindparam("report_ym"),
                    self._column(table, STATUS).in_(self.pending_statuses),
                )
                .order_by(point)
            )
            # SELECTするのは提示SQLと同じ3列。対象月は検証済みの検索値を引き継ぐ。
            return [
                {**dict(row), "target_year_month": report_ym}
                for row in connection.execute(
                    query, {"report_ym": report_ym}
                ).mappings()
            ]

    def _key_conditions(self, table, target):
        """取得した管理レコードの複合主キーで更新条件を作る。

        Args:
            table (sqlalchemy.Table): 管理テーブル。
            target (dict): supply_pointとtarget_year_monthを持つ取得レコード。

        Returns:
            tuple: SQLAlchemyの主キー条件。値はSQLのバインド変数になる。
        """
        return (
            self._column(table, MANAGEMENT_POINT) == target["supply_point"],
            self._column(table, MANAGEMENT_MONTH) == target["target_year_month"],
        )

    def _values(self, table, values):
        """論理的な更新値を、実テーブルの大小文字に合ったColumnへ変換する。

        Args:
            table (sqlalchemy.Table): 管理テーブル。
            values (dict): 物理列名と更新値。

        Returns:
            dict: update().values()へ渡す値。
        """
        return {self._column(table, name): value for name, value in values.items()}

    @staticmethod
    def _now():
        """日本時間の日時を、仕様のTIMESTAMP用にタイムゾーンなしで返す。

        Returns:
            datetime.datetime: Asia/Tokyoの現在日時。
        """
        return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)

    def claim(self, target):
        """1件の処理権を取得し、状態2で作成を開始する。

        状態2は取得対象でもあるため、状態更新だけでは二重着手を防げない。
        PostgreSQLでは主キーごとのセッションアドバイザリロックを取得し、
        finishまで接続を保持する。状態更新は短いトランザクションで確定する。
        SQLiteのテスト実行では書込トランザクションをfinishまで保持する。

        Args:
            target (dict): fetch_targets()で取得した1件。

        Returns:
            bool: このワーカーが着手できた場合True。先に処理された場合False。

        Raises:
            RuntimeError: 複合主キーが重複し、複数行を更新した場合。
        """
        if self._claim_connection is not None:
            return False
        connection = self.engine.connect()
        self._claim_connection = connection
        self._claim_key = (target["supply_point"], target["target_year_month"])
        try:
            table = self._management_table(connection)
            if self.engine.dialect.name == "postgresql":
                # hash()はプロセスごとに変わるため、安定した64bitのキーを作る。
                identity = json.dumps(
                    ["electricity_report", table.schema, table.name, *self._claim_key]
                ).encode("utf-8")
                lock_id = int.from_bytes(
                    hashlib.sha256(identity).digest()[:8], "big", signed=True
                )
                acquired = connection.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
                ).scalar_one()
                if not acquired:
                    self.release_claim()
                    return False
                self._lock_id = lock_id
            elif self.engine.dialect.name == "sqlite":
                # SQLiteはテスト用。書込の確定までは他プロセスの着手を待たせる。
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                raise ValueError(
                    "管理バッチはPostgreSQLまたはテスト用SQLiteに対応します"
                )
            query = (
                update(table)
                .where(
                    *self._key_conditions(table, target),
                    self._column(table, STATUS).in_(self.pending_statuses),
                )
                .values(
                    self._values(
                        table,
                        {
                            STATUS: "2",
                            "ERROR_MESSAGE": None,
                            "FILE_NAME": None,
                            "FILE_PATH": None,
                            "REPORT_CREATED_AT": None,
                            "UPDATED_BY": self.batch_user,
                            "UPDATED_AT": self._now(),
                        },
                    )
                )
            )
            count = connection.execute(query).rowcount
            if count not in (0, 1):
                raise RuntimeError("管理テーブルの複合主キーまたは更新件数が不正です")
            if count == 0:
                self.release_claim()
                return False
            if self.engine.dialect.name == "postgresql":
                connection.commit()
            return True
        except BaseException:
            self.release_claim()
            raise

    def release_claim(self):
        """処理権と専用接続を解放する。未確定の更新はロールバックする。

        finish後とワーカーのfinallyから呼ぶ。解放SQLに失敗した接続は破棄し、
        ロックが残った接続をプールへ返さない。
        """
        connection = self._claim_connection
        if connection is None:
            return
        try:
            try:
                connection.rollback()
                if self._lock_id is not None:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": self._lock_id},
                    )
                    connection.commit()
            except Exception:
                connection.invalidate()
        finally:
            connection.close()
            self._claim_connection = None
            self._claim_key = None
            self._lock_id = None

    def close(self):
        """処理権を解放してから、ワーカー専用のDBプールを閉じる。"""
        try:
            self.release_claim()
        finally:
            super().close()

    def finish(self, target, output=None, error=None):
        """作成中の1件を「3:完了」または「5:エラー」へ更新する。

        Args:
            target (dict): 着手した管理レコード。
            output (pathlib.Path | None): 成功時に保存済みのPDFの絶対パス。
            error (str | None): 失敗理由。ERROR_MESSAGEの上限100文字へ切り詰める。

        Raises:
            ValueError: 成功時の保存先がない、または列の保存可能長を超える場合。
            RuntimeError: 作成中のレコードを1件更新できなかった場合。
        """
        from pathlib import Path

        succeeded = error is None
        if succeeded and output is None:
            raise ValueError("完了状態には保存済みPDFのパスが必要です")
        path = Path(output).resolve() if succeeded else None
        if path is not None and (len(path.name) > 255 or len(str(path)) > 255):
            raise ValueError("PDFのファイル名・絶対パスは255文字以内にしてください")
        now = self._now()
        values = {
            STATUS: "3" if succeeded else "5",
            "ERROR_MESSAGE": None if succeeded else str(error)[:100],
            "FILE_NAME": path.name if path else None,
            "FILE_PATH": str(path) if path else None,
            "REPORT_CREATED_AT": now if succeeded else None,
            "UPDATED_BY": self.batch_user,
            "UPDATED_AT": now,
        }
        connection = self._claim_connection
        if connection is None or self._claim_key != (
            target["supply_point"],
            target["target_year_month"],
        ):
            raise RuntimeError("処理権がないため完了・エラーを更新できませんでした")
        try:
            table = self._management_table(connection)
            query = (
                update(table)
                .where(
                    *self._key_conditions(table, target),
                    self._column(table, STATUS) == "2",
                )
                .values(self._values(table, values))
            )
            if connection.execute(query).rowcount != 1:
                raise RuntimeError(
                    "管理状態が変わり、完了・エラーを更新できませんでした"
                )
            connection.commit()
        finally:
            self.release_claim()

    def load_customer(self, supply_point):
        """ARVEテーブルからNo.0の名義・住所・お客さま番号を取得する。

        名義の物理名は画像で末尾が見えないため、customer_columnsで指定
        できる。省略時はCMN_DemandLocationFullName_で始まる唯一の列を使う。
        複数行から任意の1件を選ばず、不足・重複は顧客単位のエラーにする。

        Args:
            supply_point (str): 管理レコードの供給地点特定番号。

        Returns:
            dict: No.0のcustomer_name、address、customer_number。

        Raises:
            ValueError: 必要な列・契約情報が未登録、空欄または重複している場合。
        """
        with self.engine.connect() as connection:
            if self.customer is None:
                self.customer = Table(
                    self.settings.get("customer_table", "t_arve_customer_info"),
                    MetaData(),
                    schema=self.settings.get("schema", "db_corp"),
                    autoload_with=connection,
                )
            table = self.customer
            mapping = customer_column_mapping(table, self.settings)
            columns = [
                self._column(table, mapping[key]).label(key)
                for key in ("customer_name", "address", "customer_number")
            ]
            query = select(*columns).where(
                self._column(
                    table, self.settings.get("customer_point_column", CUSTOMER_POINT)
                )
                == supply_point
            )
            # ARVE受領時の抽出条件が既に適用されている場合は空辞書でよい。
            for name, value in self.settings.get("customer_filters", {}).items():
                query = query.where(self._column(table, name) == value)
            rows = connection.execute(query).mappings().all()
        if len(rows) != 1:
            raise ValueError("ARVEの供給地点の契約情報が未登録または重複しています")
        config = dict(rows[0])
        if any(
            not isinstance(value, str) or not value.strip() for value in config.values()
        ):
            raise ValueError(
                "ARVEの名義・住所・お客さま番号は空欄でない文字列が必要です"
            )
        return config
