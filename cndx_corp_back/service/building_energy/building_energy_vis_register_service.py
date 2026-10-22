import traceback

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException, InternalServerError

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import log_time, service
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.logic.building_vis.insert_vis_inputdata import (
    insert_input_table_data,
)
from cndx_corp_back.logic.building_vis.visualization_building_files_etl import (
    BuildingInputFileParser,
)
from cndx_corp_back.logic.building_vis.visualization_files_etl import InputFileParser
from cndx_corp_back.logic.building_vis.visualization_hearing_files_etl import (
    HearingInputFileParser,
)


class BuildingEnergyVisRegisterService:

    def __init__(
        self,
        *,
        input_file: FileStorage,
        logger: CorpLogger = None,
        org_id: str,
        user_id: str,
        file_type: str,
        request_dict: dict[str, any],
    ) -> None:

        self.input_file: FileStorage = input_file
        self.logger = logger
        self.org_id = org_id
        self.user_id = user_id
        self.file_type = file_type
        self.request_dict = request_dict

    @service
    # @log_time
    def execute(self, logger=None) -> list[str]:

        file_type = self.file_type
        with get_scoped_session() as session:
            # if file_type in ("energy", "hearing") and self.org_id == "TEP":
            #     agreement_category = self.request_dict.get("agreement_category")
            #     if agreement_category == "12":
            #         self.org_id = "ASE"
            #     elif agreement_category == "13":
            #         self.org_id = "ZRB"
            #     elif agreement_category == "14":
            #         self.org_id = "JFS"
            if file_type == "energy":
                # Excelファイルパーサinstance
                fileDataParser: InputFileParser = InputFileParser(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )
            if file_type == "hearing":
                # Excelファイルパーサinstance
                fileDataParser: HearingInputFileParser = HearingInputFileParser(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )
            if file_type == "buildingMaster":
                # Excelファイルパーサinstance
                fileDataParser: BuildingInputFileParser = BuildingInputFileParser(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )

            try:
                fileDataParser.main()

            except HTTPException as e:
                # Flaskの共通エラーハンドラに渡す
                error_type = type(e).__name__
                error_message = str(e.__dict__.get("orig")) or str(e)
                self.logger.error(f"【HTTPエラー】{error_type}: {error_message}")
                raise e
            except SQLAlchemyError as e:
                # SQLAlchemy関連エラー
                error_type = type(e).__name__
                # err = str(e)

                # # "DETAIL:" で分割
                # parts = err.split("DETAIL:")

                # main = parts[0].strip()  # エラーメッセージ本体

                # detail = ""
                # if len(parts) > 1:
                #     # DETAIL: のあとの最初の行だけ取得する
                #     detail_line = parts[1].strip().split("\n")[0].strip()
                #     detail = f"DETAIL: {detail_line}"

                # final_msg = f"{main}\n{detail}"

                # # traceback 情報を取得
                # tb = traceback.extract_tb(e.__traceback__)
                # last = tb[-1]  # 最後のスタックフレーム（実際にエラーが起きた場所）

                # filename = last.filename
                # lineno = last.lineno

                # メッセージ整形
                # full_message = f"{error_type}: {final_msg} ({filename}:{lineno})"
                full_message = f"{error_type}"

                raise InternalServerError(description=full_message)

            except Exception as e:
                # それ以外の一般的な例外
                error_type = type(e).__name__
                # error_msg = str(e)

                # # traceback 情報を取得
                # tb = traceback.extract_tb(e.__traceback__)
                # last = tb[-1]  # 最後のスタックフレーム（実際にエラーが起きた場所）

                # filename = last.filename
                # lineno = last.lineno

                # メッセージ整形
                # full_message = f"{error_type}: {error_msg} ({filename}:{lineno})"
                full_message = f"{error_type}"

                # 共通 errorhandler に渡したいので raise する
                raise InternalServerError(description=full_message)
