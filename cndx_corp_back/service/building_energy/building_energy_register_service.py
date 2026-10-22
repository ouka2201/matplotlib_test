import base64
import traceback
from io import BytesIO

from flask import abort
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

import cndx_corp_back.common.constants_colums as constants_colums
import cndx_corp_back.logic.building.register_aggregation_Info_component as rai
import cndx_corp_back.logic.building.register_inputdata_info_component as rii
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.validation import get_message_list
from cndx_corp_back.logic.building.excel_files_parsing_component import (
    ExcelFilesParsingComponent,
)

# ▼▼▼▼▼▼▼▼▼符号定数群▼▼▼▼▼▼▼▼▼
DOT = constants_colums.SpecialChars.DOT.value
BLANK = constants_colums.SpecialChars.BLANK.value
HYPHEN = constants_colums.SpecialChars.HYPHEN.value
SLASH = constants_colums.SpecialChars.LINUX_PATH_DELIMITER.value

# ▼▼▼▼▼▼▼▼▼識別用文字列群▼▼▼▼▼▼▼▼▼
# "事業所"
OFFICE_STRING = constants_colums.StringOfExcelFile.OFFICE.value
# "入力シート"
INPUT_SHEET_STRING = constants_colums.StringOfExcelFile.INPUT_SHEET.value
# "設定"
SETTING_STRING = constants_colums.StringOfExcelFile.SETTING.value

# ▼▼▼▼▼▼▼▼▼共通オブジェクト群▼▼▼▼▼▼▼▼▼
# 実行モード
run_mode = constants_colums.RunMode.DEV.value

# 発行する建物ID格納用リスト
building_id_list = []
# エラーファイル対象格納リスト
error_filenames = {}

input_files = {}


class BuildingEnergyRegisterService:

    @service
    def save_input_data(self, dict_request_data, logger=None):
        logger.debug("------------TDH蓄積処理開始------------")

        # Excelファイル解析処理
        with get_scoped_session() as session:
            register_df_dic = {}
            # try:
            parser = ExcelFilesParsingComponent()
            input_files = [
                r"C:\step3\input_sheet\拠点・エネルギー情報入力シート(マクロなし)_Ver.3.5.xlsx"
            ]
            register_df_dic = parser.parse_excel_file(
                session, input_files, dict_request_data
            )

            # TDH登録処理
            try:
                if register_df_dic is None or len(register_df_dic) <= 0:
                    return

                # postgre生データTDH蓄積処理
                basic_df, corporate_df, building_df, energy_df, file_name = (
                    rii.register_input_data(session, register_df_dic)
                )

                # postgre集計データTDH蓄積処理
                (
                    corporation_df,
                    corporationProfileEntity_df,
                    corporationMonthlyEntity_df,
                    corporationYearlyEntity_df,
                ) = rai.register_energy_aggregation_info(
                    session, basic_df, corporate_df, building_df, energy_df
                )
                # postgre集計データTDH蓄積処理完了
                session.commit()

            except Exception as e:
                abort(500)

    @service
    def save_from_page(self, request_dict, user_context, logger=None):

        import cndx_corp_back.logic.building.register_from_page_component as rfp
        from cndx_corp_back.dto.building.energy_register_in_dto import (
            BuildingEnergyRegisterInDto as InDto,
        )

        try:
            # contextとして、entry_draft_flag insert_flag を渡さないと意図しないチェック処理になる
            checked = InDto.model_validate(
                request_dict,
                context={
                    "entry_draft_flag": request_dict["entry_draft_flag"],
                    "insert_flag": request_dict["insert_flag"],
                },
            )
        except ValidationError as e:
            logger.error(f"入力チェックエラー: {str(e)}")
            abort(400, description={"error_messages": get_message_list(e)})

        # DTOからDataFrameへ変換
        dfs = rfp.dto_to_dfs(checked, user_context)

        dfs["basic_df"]["ORG_ID"] = user_context.get("org_id")

        with get_scoped_session() as session:

            # TDH登録処理
            try:
                # postgre生データTDH蓄積処理
                basic_df, corporate_df, building_df, energy_df = (
                    rii.register_input_data(session, dfs)
                )

                rai.register_energy_aggregation_info(
                    session, basic_df, corporate_df, building_df, energy_df, checked
                )

                # postgre集計データTDH蓄積処理完了
                session.commit()

            except HTTPException as e:
                raise e
            except Exception as e:
                logger.error(e)
                abort(500)

        return basic_df["REGISTRATION_SEQ"].iloc[0]
