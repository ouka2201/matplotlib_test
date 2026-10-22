from typing import Any, Dict, List

from cndx_corp_back.logic.report.cn_report_backdata_dispatcher_logic import (
    CnReportBackdataDispatcherLogic,
)


class CnReportBackdataCreateService:
    """
    CNレポートバックデータ生成サービスクラス（複数CSV版）
    """

    def execute(
        self,
        request_dict: Dict[str, Any],
        message_list: List[str],
        logger,
    ) -> Dict[str, str]:
        """
        複数のCNレポートCSVを生成してパスを返す

        Args:
            request_dict (dict): リクエストボディのデータ
            message_list (list): エラーメッセージ用
            logger: ロガー

        Returns:
            dict[str, str]: 各レポート種別に対する保存先パス
        """

        # ----------- 必須パラメータ取得＆チェック -----------
        required_keys = [
            "corporate_number",
            "agreement_category",
            "org_id",
            "start_year",
            "start_month",
            "end_year",
            "end_month",
            "consent_route",  # CN特有のパラメータ
        ]

        for key in required_keys:
            if key not in request_dict or request_dict[key] is None:
                message_list.append(f"必須パラメータが不足しています：{key}")

        if message_list:
            return {}

        # ----------- ロジック呼び出し（複数CSV生成）-----------
        report_paths = CnReportBackdataDispatcherLogic().generate_multiple_csv_reports(
            request_dict=request_dict,
            logger=logger,
        )

        return report_paths
