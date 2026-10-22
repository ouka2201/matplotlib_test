import base64
import traceback
from flask import current_app
import requests
from requests.auth import HTTPBasicAuth
import os

def call_register_dag(input_sheet_file, mst_data, user_id, logger) :
    
    if logger is None:
            logger = current_app.logger

    logger.info(f"{os.path.basename(__file__)}処理開始。")
    
    try:
        # ファイルをBase64にエンコード
        input_sheet_file.seek(0)
        file_content = base64.b64encode(input_sheet_file.read()).decode('utf-8')

        # AirflowのWebサーバーURL
        AIRFLOW_URL = current_app.config["AIRFLOW_URL"]
        # 実行したいDAGのID
        DAG_ID = current_app.config["AIRFLOW_DAG_ID"] 
        # 認証情報（もし認証が必要な場合）
        USERNAME = current_app.config["AIRFLOW_USERNAME"]
        PASSWORD = current_app.config["AIRFLOW_PASSWORD"]

        # DAGをトリガーするためのエンドポイント
        trigger_endpoint = f"{AIRFLOW_URL}/dags/{DAG_ID}/dagRuns"
        # JSONデータを作成
        payload = {
            'conf': {
                'input_file_name': input_sheet_file.filename,
                'input_file_content': file_content,
                'mst_data': mst_data,
                'user_id': user_id
            }
        }

        # 同じディレクトリ内のファイルへのパスを生成
        # cert_path = os.path.join(current_dir, "airflow.crt")

        # ヘッダーと認証情報
        headers = {
            # "Authorization": "Basic Base64(hd-dev-user01:LRd+Epi%y3)",
            "Content-Type": "application/json"
        }

        response = requests.post(trigger_endpoint, 
                                json = payload,
                                headers=headers,
                                auth=HTTPBasicAuth(USERNAME, PASSWORD) ,
                                verify=False)
    except Exception as e:       
        logger.error(f"エラーが発生しました: {response.status_code}")
        logger.error(traceback.format_exc())
    
    logger.info("DAGが正常に実行されました。")
    logger.info(f"DAG Run ID: {response.json().get("dag_run_id")}")
    
    logger.info(f"{os.path.basename(__file__)}処理終了。")