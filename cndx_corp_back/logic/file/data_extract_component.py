import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from flask import abort, current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.dto.file.per30m_upload_in_dto import Per30mUploadInDto
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_electricity_data_30min_entity import (
    TElectricityData30min,
)
from cndx_corp_back.utils.dto_utils import exclude
from cndx_corp_back.utils.utils import get_message


class FileDataExtractComponent:

    def __init__(self):
        self.col_name_dict = {
            "店所": "ep_office_code",
            "電気契約番号": "ep_customer_number",
            "取得年月日": "acquisition_date",
            "欠測時間帯件数": "missing_time_range_count",
            "不正値時間帯件数": "invalid_time_range_count",
            "供給地点番号": "supply_point_number",
        }
        for i in range(48):
            self.col_name_dict[f"{i//2}:{i%2*3}0"] = f"v30min_used_energy_{i+1}"

    @component
    def get_data_from_30m_data(
        self, file: FileStorage, encoding, dto: Per30mUploadInDto, userid, logger=None
    ):
        """
        csv ファイルを解析し、30分値データを取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        message_list = []

        try:
            df = pd.read_csv(
                file,
                encoding=encoding,
                dtype={
                    "取得年月日": str,
                    "電気契約番号": str,
                    "供給地点番号": str,
                    "店所": str,
                },
            )
        except UnicodeDecodeError as e:
            return get_message("ENCODING", encoding=encoding)

        except Exception as e:
            abort(500, "csvファイル読込エラー")

        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        # お客さま番号の後ろ13桁だけを残す
        ep_customer_number = dto.ep_customer_number[-13:]
        # テーブルのカラム名を取り出す
        tbl_columns = {col.name for col in TElectricityData30min.__table__.columns}

        # フォーマット判定
        # if df.columns[0] == "店所":
        #     report_format = 1
        # elif df.columns[0] == "供給地点番号":
        #     report_format = 2
        # else:
        #     abort(400, "フォーマット不正（店所/供給地点番号）")

        errors = []
        report_format = None
        expected_columns = []
        # 0番目のカラムチェック（店所／供給地点番号）
        if len(df.columns) > 0:
            if df.columns[0] == "店所":
                report_format = 1
            elif df.columns[0] == "供給地点番号":
                report_format = 2
            else:
                errors.append("フォーマット不正（店所/供給地点番号）")

        # 1～7番目のカラムチェック（順序固定）
        if report_format == 1:
            expected_columns = [
                "電気契約番号",
                "取得年月日",
                "取得成否",
                "計器区分／計器番号",
                "欠測時間帯件数",
                "不正値時間帯件数",
            ]
        elif report_format == 2:
            expected_columns = [
                "速報確報区分",
                "取得年月日",
                "取得成否",
                "電力量仕訳コード",
                "仕訳形態コード",
                "欠測時間帯件数",
                "不正値時間帯件数",
            ]

        for idx, col_name in enumerate(expected_columns, start=1):
            if len(df.columns) <= idx:
                errors.append(f"フォーマット不正（{col_name}）")
            elif df.columns[idx] != col_name:
                errors.append(f"フォーマット不正（{col_name}）")

        # エラーが存在する場合は、まとめてエラーを返却
        if errors:
            abort(400, "\n".join(errors))

        new_df = df.copy()
        new_df["ep_office_code"] = (
            df.iloc[:, 0].astype(str) if report_format == 1 else None
        )

        # 取得成功したものだけを残す
        if "取得成否" in df.columns:
            df = df[df["取得成否"] == 0]

        # テーブルのカラム論理名にする
        df.rename(columns=self.col_name_dict, inplace=True)

        # テーブルのカラム名だけを残す
        df = df[[col for col in df.columns if col in tbl_columns]]

        # カラム追加
        df["agreement_category"] = dto.agreement_category
        df["org_id"] = "TEP"
        df["building_id"] = dto.building_id
        df["corp_number"] = dto.corp_number
        df["corp_name"] = dto.corp_name
        df["building_name"] = dto.building_name
        df["delete_flg"] = False
        df["created_by"] = userid
        df["created_at"] = now
        df["file_update_date"] = now

        # データがないセルをカラにする
        df.fillna("", inplace=True)

        # すべて対象のレコードかをチェック
        if report_format == 1:
            df["supply_point_number"] = dto.supply_point_number

            # 店所コードの行単位チェック
            office_mismatch_rows = df.index[
                new_df["ep_office_code"] != dto.ep_office_code
            ]

            # お客様番号（電気契約番号）の行単位チェック
            customer_mismatch_rows = df.index[
                df.iloc[:, 0].astype(str) != str(dto.ep_customer_number)
            ]

            # いずれかに不一致がある場合のみ、エラーメッセージを追加
            if len(office_mismatch_rows) > 0 or len(customer_mismatch_rows) > 0:
                message_list.append(
                    "店所 または 電気契約番号 が一致していない行があります"
                )

            df["ep_office_code"] = new_df["ep_office_code"]

            # df のお客さま番号は店所 + 電気契約番号 で設定する。
            # df["ep_customer_number"] = df["ep_customer_number"].apply(lambda x: x[-13:])
            df["ep_customer_number"] = df["ep_office_code"].fillna("").astype(
                str
            ) + df.iloc[:, 0].astype(str)
            df = df.drop(columns=["ep_office_code"])

            # if not (df["ep_customer_number"] == ep_customer_number).all():
            #     message_list.append(
            #         get_message("NOT_MATCH", item_name="お客さま番号")
            #     )
        elif report_format == 2:
            df["ep_customer_number"] = ep_customer_number
            with get_scoped_session() as session:
                mbuilding = (
                    session.query(MBuilding)
                    .filter(
                        MBuilding.corporate_number == dto.corp_number,
                        MBuilding.agreement_category == dto.agreement_category,
                        MBuilding.building_id == dto.building_id,
                        # MBuilding.agreement_org == dto.org_id,
                        MBuilding.delete_flg.is_not(True),
                    )
                    .first()
                )
                if not mbuilding:
                    message_list.append(get_message("NOT_FOUND", item_name="建物情報"))
                else:
                    office_code = mbuilding.ep_office_code or ""
                    df["ep_customer_number"] = office_code + df[
                        "ep_customer_number"
                    ].astype(str)
            if not (df["supply_point_number"] == dto.supply_point_number).all():
                message_list.append(get_message("NOT_MATCH", item_name="供給地点番号"))

        # 取得年月日 チェック
        if not (df["acquisition_date"].str.len() == 8).all():
            message_list.append(
                get_message("EXACT_LENGTH_ERROR", item_name="取得年月日", length=8)
            )

        if message_list:
            abort(400, "\n".join(message_list))

        new_records = [
            TElectricityData30min(**row) for row in df.to_dict(orient="records")
        ]

        # データ登録 or 更新
        try:
            with get_scoped_session() as session:
                for record in new_records:
                    rec_dict = build_dict_from_entity(record)

                    stmt = insert(TElectricityData30min).values(**rec_dict)
                    update_values = exclude(rec_dict, {"created_by", "created_at"})
                    update_values["updated_by"] = userid
                    update_values["updated_at"] = now
                    update_values["file_update_date"] = now
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[
                            "corp_number",
                            "agreement_category",
                            "org_id",
                            "building_id",
                            "acquisition_date",
                        ],
                        set_=update_values,
                    )
                    try:
                        session.execute(stmt)
                    except Exception as e:
                        logger.error(f"SQL 実行失敗: {stmt}")
                        raise e

                session.commit()
        except Exception as e:
            abort(500, "登録処理失敗。")

        return []


def build_dict_from_entity(entity, exclude_fields=None):
    from sqlalchemy.inspection import inspect

    exclude_fields = set(exclude_fields or [])
    mapper = inspect(entity.__class__)
    update_dict = {}

    for col in mapper.columns:
        if col.name in exclude_fields:
            continue
        val = getattr(entity, col.name)
        if val is None:
            continue
        update_dict[col.name] = val

    return update_dict
