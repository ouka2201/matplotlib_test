import io
import os
import time
import traceback
from copy import deepcopy
from datetime import datetime

import fitz  # PyMuPDF
import pandas as pd
import tableauserverclient as TSC
from flask import abort, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from tableauserverclient.server.endpoint.exceptions import TableauError

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.file_save import pathjoin
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto as VisInDto,
)
from cndx_corp_back.dto.report.create_cn_karte_in_dto import CreateCnKarteInDto as InDto
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent
from cndx_corp_back.utils.utils import get_message


class ReportPdfCreateComponent:

    site_name = ""

    def __init__(self):
        # Tableau Server の認証情報
        self.server_url = current_app.config["TABLEAU_SERVER_URL"]
        self.username = current_app.config["TABLEAU_USERNAME"]
        self.password = current_app.config["TABLEAU_PASSWORD"]
        self.workbook_name = current_app.config["TABLEAU_WORKBOOK_NAME"]

    @component
    def excute(self, dto: InDto | VisInDto, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        from sqlalchemy.exc import SQLAlchemyError
        from werkzeug.exceptions import HTTPException

        from cndx_corp_back.common.database_manager import get_scoped_session
        from cndx_corp_back.entity.t_report_storage_info_entity import (
            TReportStorageInfo,
        )

        report_location = "path//test.pdf"

        creation_id_dict = {
            "report_created_at": func.now(),
            "report_created_by": _get_user_id(),
        }

        try:
            with get_scoped_session() as session:
                #
                if isinstance(dto, InDto):
                    pattern = "1"  # 地銀
                else:
                    pattern = "2"  # 可視化側

                db_filter_dict = {"report_classify": "01"}  # CNカルテを表す
                if pattern == "1":
                    db_filter_dict = dto.model_dump()
                elif pattern == "2":
                    db_filter_dict["org_id"] = dto.org_id
                    db_filter_dict["corporate_number"] = dto.corporate_number
                    db_filter_dict["fiscal_year"] = dto.start_year
                    db_filter_dict["registration_seq"] = 1

                rp_info = (
                    session.query(TReportStorageInfo)
                    .filter_by(**db_filter_dict)
                    .first()
                )

                if not rp_info:
                    logger.info("該当レコードなし、作成失敗。")
                    abort(
                        404,
                        description=get_message("NOT_FOUND", item_name="該当レコード"),
                    )

                logger.info(f"取得した rp_info: {rp_info}")

                # ==== Tableau 関連処理は全てコメントアウト ====
                # # Tableau サーバーログイン & データ更新 & PDF生成 (注释)
                # tableau_auth = TSC.TableauAuth(self.username, self.password, self.site_name)
                # server = TSC.Server(self.server_url)
                # server.version = "3.21"
                # with server.auth.sign_in(tableau_auth):
                #     ...

                # ==== PDF ====
                # pdf_stream = io.BytesIO()
                pdf_doc = fitz.open()
                page = pdf_doc.new_page(width=595, height=842)  # A4
                page.insert_text((72, 72), "Test PDF for local run", fontsize=20)
                # pdf_doc.save(pdf_stream)
                pdf_bytes = pdf_doc.tobytes()
                pdf_doc.close()

                # 保存 PDF 文件
                pdf_file_name = (
                    f"企業カルテ_{dto.corporate_number}_{dto.start_year}.pdf"
                )
                output_dir = os.path.join(os.getcwd(), "output")
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.join(output_dir, pdf_file_name)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)

                report_location = file_path
                logger.info(f"PDFファイルを保存しました: {report_location}")

                # 更新 DB
                rp_info.report_save_path = report_location
                rp_info.report_created_at = creation_id_dict["report_created_at"]
                rp_info.report_created_by = creation_id_dict["report_created_by"]
                session.commit()

        except HTTPException as e:
            raise e
        except SQLAlchemyError as e:
            logger.error(f"データベース接続エラー：{e}")
            abort(500)
        except Exception as e:
            logger.info(f"予想外のエラーにより生成失敗：{e}\n{traceback.format_exc()}")
            abort(500)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return report_location

    def report_info_trans(
        self,
        server: TSC.Server,
        view_filter_dict: dict,
        creation_id: str,
        hyper_name: str,
        logger: CorpLogger,
    ) -> str:
        """
        レポート情報変換
            :param server: Tableau Server インスタンス
            :param db_filter_dict: DB フィルタ条件
            :param hyper_name: Hyper ファイル名
            :param logger: ロガー
        """
        from cndx_corp_back.common.database_manager import get_db_engine
        from cndx_corp_back.common.db_base_handler import BaseRepository
        from cndx_corp_back.common.hyper_manager import HyperManager

        # hyper 生成開始 timestamp
        ts_ms_0 = int(time.time() * 1000)

        # Hyper マネージャ
        hmgr = HyperManager()

        # 当年度 ビュー DataFrame
        code_repo = BaseRepository(self.session, model=None)
        results = code_repo.find_all(**view_filter_dict)
        # DFに変換
        records = [
            {k: v for k, v in obj.__dict__.items() if not k.startswith("_sa_")}
            for obj in results
        ]
        df = pd.DataFrame(records)
        #        df = hmgr.fetch_table_data(query, get_db_engine())
        df["対象年度フラグ"] = "1"

        # DataFrame が空の場合はエラー
        if df is None or df.empty:
            if logger:
                logger.error("企業カルテ作成データが見つかりませんでした。")
            abort(500, description="レポートの生成が失敗しました。")

        # 前年度 ビュー DataFrame
        df_past_year = _get_past_year_data(df, get_db_engine())
        if not df_past_year.empty:
            df_past_year["対象年度フラグ"] = "2"

            df = pd.concat([df, df_past_year], ignore_index=True)

        df["グループ１"] = None
        df["グループ２"] = None
        df["グループ３"] = None
        df["グループ４"] = None
        df["グループ５"] = None

        # 作成用データ特定用情報
        df["creation_id"] = creation_id

        if df.empty:
            if logger:
                logger.error("企業カルテ作成データが見つかりませんでした。")
            abort(500, description=get_message("FAILED", data="レポートの生成"))

        table_def = hmgr.fetch_table_def(df)

        # Hyper ファイルに変換
        hp_file_path = hmgr.create_hyper_file(
            dataframe=df, table_def=table_def, hyper_file_loc=hyper_name
        )

        # サーバにある全部のデータソースを取得し、必要なものを特定
        all_datasources, pag = server.datasources.get()
        target_datasource = next(
            (ds for ds in all_datasources if ds.name == hmgr.ds_name),
            None,
        )
        # hyper 生成終了 timestamp
        ts_ms_1 = int(time.time() * 1000)

        # 拠点数を取得
        number_offices = int(df.iat[0, df.columns.get_loc("拠点数")])

        logger.info(f"hyper生成時間: {ts_ms_1 - ts_ms_0} ms")

        if target_datasource:

            # Hyper で データソースを overwrite
            updated_datasource = server.datasources.publish(
                target_datasource,
                hp_file_path,
                # TSC.Server.PublishMode.Append,
                TSC.Server.PublishMode.Overwrite,
            )
            # hyperアップロード完了 timestamp
            ts_ms_2 = int(time.time() * 1000)
            if logger:
                logger.info(f"hyperアップロード時間: {ts_ms_2 - ts_ms_1} ms")
                logger.info(f"「{hp_file_path}」でデータソースを更新しました。")
            return number_offices
        else:
            if logger:
                logger.error("データソースが見つかりませんでした。")
            abort(500, description=get_message("FAILED", data="レポートの生成"))


def adjust_margin(binary_pdf):
    """PDF余白調整"""

    pdf_stream = io.BytesIO(binary_pdf)

    doc = fitz.open("pdf", pdf_stream)

    for page in doc:
        rect = page.cropbox  # 現在のページのトリミング領域

        # 左：右へ10 下：上へ20 右：右へ-50 上：上へ-20
        new_rect = fitz.Rect(rect.x0 + 10, rect.y0 + 20, rect.x1 - 45, rect.y1 - 20)

        page.set_cropbox(new_rect)

    # バイナリデータとして保存
    output_stream = io.BytesIO()
    doc.save(output_stream)
    doc.close()

    # return output_stream
    return output_stream.getvalue()


def pdf_to_img(pdf_stream):
    """プレビュー画像を生成"""

    pdf_doc = fitz.open("pdf", pdf_stream)

    page = pdf_doc.load_page(0)

    # 画像レンダリング
    # pix0 = page._makePixmap()
    # pix0.save("page1.png")

    pix = page.get_pixmap()
    pix.save("page1.png")

    # return output_stream
    return


@component
def create_cn_karte(self, request_dict: dict, logger=None):

    if logger is None:
        logger = current_app.logger

    logger.info(f"{os.path.basename(__file__)}処理開始。")

    # from http.client import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    from werkzeug.exceptions import HTTPException

    from cndx_corp_back.common.database_manager import get_scoped_session
    from cndx_corp_back.entity.t_report_storage_info_entity import (
        TReportStorageInfo,
    )

    # データ抽出

    # hyperへ変換

    # Tableau Serverへアップロード

    # PDF生成

    # PDF調整

    # PDF保存

    return


def _get_user_id():
    """
    ユーザーIDを取得するヘルパー関数
    """
    try:
        user_id = get_jwt_identity()
    except Exception as e:
        # ログにエラーを記録 TODO 一時的
        current_app.logger.error(f"JWTからユーザーIDの取得に失敗: {str(e)}")
        user_id = None
    if not user_id:
        return "test"  # デフォルト値を返す
    return user_id


def _get_past_year_data(df_curr_year: pd.DataFrame, session):

    # 月度変換dict
    month_flag_dict = {}

    year_month_list: list = df_curr_year["エネルギー年月"].unique()
    for i in range(len(year_month_list)):
        year_month = year_month_list[i]
        # 年度に1を減らす
        year = int(year_month[:4])
        month = year_month[4:6]

        year_month_list[i] = str(year - 1) + month
        month_flag_dict[month] = i

    # TODO:sqlalchemyを使用したSQLに、下記を変更する必要がある
    query = f"""SELECT DISTINCT ON ("拠点名", "エネルギーコード", "エネルギー年月")
        *
        FROM v_corporate_profile_report_bnk
        WHERE 
            "法人番号" = '{df_curr_year['法人番号'].iloc[0]}'
            AND "組織id" = '{df_curr_year['組織id'].iloc[0]}'
            AND "エネルギー年月" IN ('{"', '".join(year_month_list)}')
        ORDER BY "拠点名", "エネルギーコード", "エネルギー年月", "登録回数" DESC;
        """
    past_year_df = pd.read_sql(query, session.connection())

    # DataFrameの行に対して、エネルギー年度の月度を抽出して月度dictで変換してカラム"月度フラグ"に設定
    past_year_df["月度フラグ"] = (
        past_year_df["エネルギー年月"].str[4:6].map(month_flag_dict)
    )
    df_curr_year["月度フラグ"] = (
        df_curr_year["エネルギー年月"].str[4:6].map(month_flag_dict)
    )

    return past_year_df
