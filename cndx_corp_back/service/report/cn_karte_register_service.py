import os
from datetime import datetime
from typing import Any, Dict, List

from flask import current_app

from cndx_corp_back.logic.report.cn_karte_register_logic import CnKarteRegisterLogic


class CnKarteRegisterService:
    """
    CNカルテ登録サービスクラス
    - 入力チェック（DTOで実施済み）
    - Logic 層呼び出し（パラメータ変換あり）
    """

    def execute(
        self, request_dict: Dict[str, Any], message_list: List[str], logger=None
    ) -> Dict[str, Any]:
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} – CnKarteRegisterService 開始")

        # -----------------
        # 共通パラメータ変換
        # -----------------
        base_dict = request_dict.copy()

        # 1. 期間 → report_selection_period_from（開始年月）
        start_year = request_dict["start_year"]
        start_month = str(request_dict["start_month"]).zfill(2)
        base_dict["report_selection_period_from"] = f"{start_year}{start_month}"

        # fiscal_year（主キーの一部）
        base_dict["fiscal_year"] = str(start_year)

        # 2. creation_format → format_type
        creation_format = request_dict.get("creation_format", "")
        if "簡易" in creation_format:
            base_dict["format_type"] = "CNカルテ（簡易版）"
        elif "標準" in creation_format:
            base_dict["format_type"] = "CNカルテ（標準版）"
        else:
            base_dict["format_type"] = "UNKNOWN"

        # -----------------
        # downloads に応じて複数登録
        # -----------------
        downloads = {
            "missing_data_pdf": request_dict.get("need_data_insufficiency_list", False),
            "report_back_csv": request_dict.get("need_report_backdata", False),
            "kpi_csv": request_dict.get("need_kpi_list", False),
        }

        mapping = {
            "missing_data_pdf": "3",  # データ欠損一覧
            "report_back_csv": "2",  # レポートバックデータ
            "kpi_csv": "4",  # KPI一覧
        }

        inserted_ids: List[str] = []

        # -----------------
        # 単拠点選択かどうかで分岐
        # -----------------
        is_multi = request_dict.get("is_for_multibuilding", False)
        building_ids = request_dict.get("building_ids_for_single", [])

        # === 単拠点: 選択された拠点ごとに記録 ===
        if not is_multi and building_ids:
            for b_id in building_ids:
                for key, classify in mapping.items():
                    # downloads 全 False でも CN レポート PDF (missing_data_pdf) は必須
                    if downloads.get(key, False) or key == "missing_data_pdf":
                        converted_dict = base_dict.copy()
                        converted_dict["site_selection_type"] = "個別"
                        converted_dict["building_id"] = b_id
                        converted_dict["report_classify"] = classify
                        converted_dict["report_save_path"] = (
                            f"{key}_{b_id}_{base_dict['report_selection_period_from']}.pdf"
                        )
                        converted_dict["creation_id"] = (
                            f"{converted_dict.get('user','system')}_{datetime.now().timestamp()}"
                        )
                        inserted_id = CnKarteRegisterLogic().insert_karte_condition(
                            request_dict=converted_dict, logger=logger
                        )
                        inserted_ids.append(inserted_id)

        # === 複数拠点（企業全体 or グループ）: 1件だけ ===
        else:
            converted_dict = base_dict.copy()
            if request_dict.get("group_for_multibuilding"):
                converted_dict["site_selection_type"] = "グループ"
                group_names = [
                    f"{g['group_no']}:{g['option_no']}"
                    for g in request_dict["group_for_multibuilding"]
                ]
                converted_dict["building_id"] = "1:" + ",".join(group_names)
            else:
                converted_dict["site_selection_type"] = "企業全体"
                converted_dict["building_id"] = "0"

            for key, classify in mapping.items():
                if downloads.get(key, False) or key == "missing_data_pdf":
                    dict_copy = converted_dict.copy()
                    dict_copy["report_classify"] = classify
                    dict_copy["report_save_path"] = (
                        f"{key}_{base_dict['report_selection_period_from']}.pdf"
                    )
                    dict_copy["creation_id"] = (
                        f"{dict_copy.get('user','system')}_{datetime.now().timestamp()}"
                    )
                    inserted_id = CnKarteRegisterLogic().insert_karte_condition(
                        request_dict=dict_copy, logger=logger
                    )
                    inserted_ids.append(inserted_id)

        logger.info(f"{os.path.basename(__file__)} – CnKarteRegisterService 終了")
        return {"inserted_ids": inserted_ids}
