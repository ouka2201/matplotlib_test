# from dataclasses import dataclass, field
# import io
import os
import platform
import tempfile
from pathlib import Path

# from typing import List
from flask import current_app
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import utils

# from cndx_corp_back import db
# from cndx_corp_back.common.dag.call_dag import call_register_dag
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.common.file_save import (
    filter_target_file,
    get_next_filename,
    ls_volume,
    make_folder,
    pathjoin,
    save_file,
)

# from pandas import DataFrame, ExcelFile

# from cndx_corp_back.utils.excel_utils import get_data_frame


class FileTransferComponent:

    @component
    def excute_bk(
        self, file: FileStorage, dir_data: dict, put_dir_path: str, logger=None
    ):
        """
        ファイル転送コンポーネント
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        if dir_data is None:
            dir_data = {}

        put_base_path = current_app.config["HDFS_BASE_PATH"]
        # rootパス取得
        project_root_path = utils.get_project_root_path()

        ls_path = pathjoin(put_base_path, put_dir_path)
        exist_files = ls_volume(ls_path)
        logger.info(f"アップロード済みファイル : {exist_files}")

        new_filename = file.filename
        if not file.filename.lower().endswith(".pdf"):
            new_filename = get_next_filename(file.filename, exist_files)
        logger.info(f"new_filenameファイル名 : {new_filename}")

        # 格納先パス構築
        pathlist = []
        for val in dir_data.values():
            pathlist.append(str(val))
        to_make_dir = pathjoin(put_base_path, put_dir_path, *pathlist)

        # maprfs上で「銀行/企業/」のフォルダを作成する
        make_folder(to_make_dir)

        # 入力シートファイル格納フォルダ名取得する
        target_folder = os.path.join(project_root_path, "files/input_files")

        if os.name == "nt":
            # osがwindowsの場合、Windowsのパスdelimiterに変換する
            target_folder = target_folder.replace("/", "\\")
            local_file_path = os.path.join(target_folder, new_filename)

            # FileStorageオブジェクトを直接保存
            file.save(local_file_path)
        elif os.name == "posix":
            # 入力シート格納情報登録
            temp_dir = tempfile.gettempdir()
            temp_local_path = os.path.join(temp_dir, new_filename)

            # FileStorageオブジェクトを直接保存
            file.save(temp_local_path)

            # 保存処理
            save_file(temp_local_path, to_make_dir, new_filename)

        logger.info(f"{os.path.basename(__file__)}処理終了。")

    @component
    # @log_time
    def excute(self, input_file: FileStorage, upload_target_path: str, logger=None):
        """
        ファイル転送コンポーネント
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        system = platform.system()
        try:
            if system == "Linux":
                temp_dir = tempfile.gettempdir()
                temp_local_path = os.path.join(temp_dir, input_file.filename)

                # FileStorageオブジェクトを直接保存
                input_file.save(temp_local_path)
                # フォルダ作成
                make_folder(upload_target_path)

                # 保存処理
                logger.debug(
                    f"アップロード先：{upload_target_path} ,ローカルパス:{temp_local_path}"
                )
                save_file(temp_local_path, upload_target_path)
            elif system == "Windows":
                upload_path_name = os.path.join(upload_target_path, input_file.filename)
                # Pathオブジェクト作成（相対パス -> カレントディレクトリからのパスになる）
                target_dir = Path(upload_target_path)

                # フォルダが存在しなければ作成（親ディレクトリも再帰的に作る）
                target_dir.mkdir(parents=True, exist_ok=True)
                # FileStorageオブジェクトを直接保存
                input_file.save(upload_path_name)
        except Exception as e:
            logger.error("ファイルアップロード処理が失敗しました。")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

    # @log_time
    def get_upload_path(self, target_path_dict: dict):
        # rootパス取得
        system = platform.system()

        put_path = "corp"
        if system == "Linux":
            put_base_path = current_app.config["HDFS_BASE_PATH"]
            # フォルダ構成名取得
            dir_data = {"put_path": put_path}
            dir_data.update(target_path_dict)

            upload_target_path = pathjoin(put_base_path, *dir_data.values())
        elif system == "Windows":
            put_base_path = utils.get_project_root_path()

            # フォルダ構成名取得
            dir_data = {"put_base_path": put_base_path, "put_path": put_path}
            dir_data.update(target_path_dict)
            upload_target_path = Path(*map(str, dir_data.values()))
        elif system == "Darwin":  # macOS
            put_base_path = utils.get_project_root_path()

            # フォルダ構成名取得
            dir_data = {"put_base_path": put_base_path, "put_path": put_path}
            dir_data.update(target_path_dict)
            upload_target_path = Path(*map(str, dir_data.values()))
        else:
            # その他のOS（デフォルトはLinuxと同じ動作）
            put_base_path = current_app.config["HDFS_BASE_PATH"]
            # フォルダ構成名取得
            dir_data = {"put_path": put_path}
            dir_data.update(target_path_dict)

            upload_target_path = pathjoin(put_base_path, *dir_data.values())

        return upload_target_path
