import os
import zipfile
from collections import defaultdict
from datetime import date

from psycopg2 import DatabaseError
from sqlalchemy import text

from cndx_corp_batch.common.constants import CreatedStatus
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser


class CreateZipFileService:
    def __init__(self, logger):
        """
        Parameters:
            logger: ロガー
        """
        self.logger = logger

    def execute(
        self,
        zip_users_list: list,
        target_year_month: str,
        user_power_report_file_path: str,
    ):
        """zip化実行
        Args:
            zip_users_list (list): zip化対象リスト
            target_year_month (str): 対象年月
            user_power_report_file_path (str): ZIPファイル格納パス
        """
        sales_user_dict = self.create_dict_by_sales_user_name(zip_users_list)
        # sales_user_nameごとにループ
        for sales_user_name, user_data in sales_user_dict.items():
            self.logger.info(f"顧客担当者、{sales_user_name}ごとに処理開始")

            zip_files_info = self.prepare_zip_names(
                {sales_user_name: user_data},
                target_year_month,
                user_power_report_file_path,
            )
            self.create_zip_files(zip_files_info)
            # 担当者別電力見える化レポート管理情報TBLにINSERT、電力見える化レポートを削除
            self.insert_user_power_report_and_delete_report(
                zip_files_info, target_year_month
            )

            self.logger.info(f"{sales_user_name} 処理完了")
        return

    def create_dict_by_sales_user_name(self, zip_users_list: list):
        """顧客担当者をkeyとしたdictを作成
        Args:
            zip_users_list (list): zip化顧客リスト
        Returns:
            dict: 顧客担当者別dict
        """
        sales_user_dict = {}
        for (
            supply_point_number,
            sales_user_name,
            user_org_name,
            org_id,
            syousapo_flg,
            file_name,
            file_path,
        ) in zip_users_list:
            if sales_user_name not in sales_user_dict:
                sales_user_dict[sales_user_name] = {
                    "user_org_name": user_org_name,
                    "org_id": org_id,
                    "files": [],
                }
            sales_user_dict[sales_user_name]["files"].append(
                {
                    "file_path": file_path,
                    "file_name": file_name,
                    "syousapo_flg": syousapo_flg,
                    "supply_point_number": supply_point_number,
                }
            )
        self.logger.info("顧客担当者ごとにdict作成完了")
        return sales_user_dict

    def prepare_zip_names(
        self,
        sales_user_dict: dict,
        target_year_month: str,
        user_power_report_file_path: str,
    ):
        """非省サポ・省サポユーザーで分け、ZIPファイル名を作成
        Args:
            sales_user_dict (dict): 顧客担当者別dict（単一の担当者）
            target_year_month (str): 対象年月
            user_power_report_file_path (str): ZIPファイル格納パス
        Returns:
            list: ZIP化ファイル情報
        """
        zip_files_info = []

        for sales_user, data in sales_user_dict.items():
            org_id = data.get("org_id")
            user_org_name = data.get("user_org_name")
            files = data.get("files", [])
            # syousapo_flgでグループ化
            false_files = [f for f in files if f.get("syousapo_flg") is False]
            true_files = [f for f in files if f.get("syousapo_flg") is True]
            false_zip_num = (len(false_files) + 799) // 800 if false_files else 0
            true_zip_num = (len(true_files) + 799) // 800 if true_files else 0
            # false のファイル処理
            zip_files_info.extend(
                self._create_zip_info_for_files(
                    false_files,
                    sales_user,
                    target_year_month,
                    user_power_report_file_path,
                    org_id,
                    user_org_name,
                    zip_index_offset=0,
                )
            )
            # true のファイル処理
            zip_files_info.extend(
                self._create_zip_info_for_files(
                    true_files,
                    sales_user,
                    target_year_month,
                    user_power_report_file_path,
                    org_id,
                    user_org_name,
                    zip_index_offset=false_zip_num,
                )
            )
            self.logger.info(
                f"{sales_user}: ZIP個数取得完了。非省サポ{false_zip_num}個、省サポ{true_zip_num}個"
            )

        return zip_files_info

    def _create_zip_info_for_files(
        self,
        files: list,
        sales_user: str,
        target_year_month: str,
        user_power_report_file_path: str,
        org_id: str,
        user_org_name: str,
        zip_index_offset: int = 0,
    ) -> list:
        """ファイルリストからZIP情報リストを作成
        Args:
            files (list): ファイル情報リスト
            sales_user (str): 営業担当者名
            target_year_month (str): 対象年月
            user_power_report_file_path (str): ZIPファイル格納パス
            org_id (str): 組織ID
            user_org_name (str): ユーザー組織名
            zip_index_offset (int): ZIPインデックスのオフセット
        Returns:
            list: ZIP化ファイル情報
        """
        zip_info_list = []

        for idx, file in enumerate(files):
            syousapo_flg = file.get("syousapo_flg")
            supply_point_number = file.get("supply_point_number")
            zip_index = zip_index_offset + (idx // 800) + 1
            zip_name = f"{sales_user}_{target_year_month}_{zip_index}.zip"
            zip_path = os.path.join(user_power_report_file_path, zip_name)

            zip_info_list.append(
                {
                    "zip_name": zip_name,
                    "zip_path": zip_path,
                    "info": file,
                    "org_id": org_id,
                    "user_org_name": user_org_name,
                    "sales_user_name": sales_user,
                    "syousapo_flg": syousapo_flg,
                    "supply_point_number": supply_point_number,
                }
            )

        return zip_info_list

    def create_zip_files(self, zip_files_info):
        """zip_files_infoの情報に基づいてzipファイルを作成
        Args:
            zip_files_info (list): ZIP化ファイル情報
        """
        # zip_name, zip_pathごとにファイル情報をグループ化
        zip_groups = defaultdict(list)
        for item in zip_files_info:
            key = (item["zip_name"], item["zip_path"])
            zip_groups[key].append(item["info"])
        # 各zipファイルを作成
        for (zip_name, zip_path), files in zip_groups.items():
            try:
                # zipファイルのディレクトリが存在しなければ作成
                os.makedirs(os.path.dirname(zip_path), exist_ok=True)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_info in files:
                        file_path = file_info["file_path"]
                        file_name = file_info["file_name"]
                        zf.write(file_path, arcname=file_name)
                self.logger.info(f"{zip_name} を作成完了: {zip_path}")
            except Exception as e:
                self.logger.error(f"{zip_name} の作成に失敗: {str(e)}")
                raise FileNotFoundError
        return

    def insert_user_power_report_and_delete_report(
        self,
        zip_files_info: list,
        target_year_month: str,
    ):
        """担当者別電力見える化レポート管理情報TBLにレポート情報を挿入し、ZIP化済の元ファイルを削除
        Args:
            zip_files_info (list): ZIP化ファイル情報
            target_year_month (str): 対象年月
        Raise:
            DatabaseError
        """
        current_time = get_current_time()
        processed_zips = set()
        processed_files = []
        for zip_file_item in zip_files_info:
            zip_name = zip_file_item["zip_name"]
            zip_path = zip_file_item["zip_path"]
            # zip化済フラグをTrueにする
            update_params = {
                "target_year_month": target_year_month,
                "supply_point_number": zip_file_item.get("supply_point_number"),
                "updated_by": get_sysuser(),
                "updated_at": current_time.strftime("%Y/%m/%d %H:%M:%S"),
            }
            with get_session() as session:
                try:
                    sql_query = load_sql_file("update_zip_flg.sql")
                    session.execute(text(sql_query), update_params)
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"t_power_report_mng_info Update error:{e}")
                    raise DatabaseError
                # 同じzipは1回だけDBに挿入
                zip_key = (zip_name, zip_path)
                if zip_key not in processed_zips:
                    insert_params = {
                        "file_name": zip_name,
                        "file_path": zip_path,
                        "file_created_at": date.today().strftime("%Y/%m/%d %H:%M:%S"),
                        "create_status": CreatedStatus.DONE.value,
                        "org_id": zip_file_item.get("org_id"),
                        "user_org_name": zip_file_item.get("user_org_name"),
                        "sales_user_name": zip_file_item.get("sales_user_name"),
                        "target_year_month": target_year_month,
                        "syousapo_flg": zip_file_item.get("syousapo_flg"),
                        "created_by": get_sysuser(),
                        "created_at": current_time.strftime("%Y/%m/%d %H:%M:%S"),
                        "updated_by": "",
                        "updated_at": None,
                    }
                    try:
                        sql_query = load_sql_file("insert_user_power_report.sql")
                        session.execute(text(sql_query), insert_params)
                    except Exception as e:
                        session.rollback()
                        self.logger.error(
                            f"t_user_power_report_mng_info Insert error:{e}"
                        )
                        raise DatabaseError
                    processed_zips.add(zip_key)
                # 元ファイルの削除
                file_path = zip_file_item["info"].get("file_path")
                if file_path and file_path not in processed_files:
                    try:
                        os.remove(file_path)
                        processed_files.append(file_path)
                    except Exception:
                        raise FileNotFoundError
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"commit error:{e}")
                    raise DatabaseError
        self.logger.info("TBL情報INSERT、レポート削除完了")
        return
