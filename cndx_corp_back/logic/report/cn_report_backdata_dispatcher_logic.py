import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

from cndx_corp_back.logic.report.cn_energy_ranking_report_logic import (
    CnEnergyRankingReportLogic,
)
from cndx_corp_back.logic.report.cn_raw_data_report_logic import CnRawDataReportLogic
from cndx_corp_back.logic.report.cn_report_backdata_create_logic import (
    CnReportBackdataCreateLogic,
)
from cndx_corp_back.logic.report.cn_site_ranking_report_logic import (
    CnSiteRankingReportLogic,
)


class CnReportBackdataDispatcherLogic:
    """
    複数のCNレポートCSVを作成する調整用ロジッククラス
    """

    def generate_multiple_csv_reports(
        self, request_dict: Dict[str, Any], logger
    ) -> Dict[str, str]:
        result_paths = {}

        # 1. CNバックデータレポート
        result_paths[
            "cn_report_backdata"
        ] = CnReportBackdataCreateLogic().generate_csv_report(
            request_dict=request_dict, logger=logger
        )

        # 2. 生データレポート
        result_paths["raw_data_report"] = CnRawDataReportLogic().generate_raw_data_csv(
            request_dict=request_dict, logger=logger
        )

        # 3. 拠点ランキングレポート
        result_paths[
            "site_ranking_report"
        ] = CnSiteRankingReportLogic().generate_site_ranking_csv(
            request_dict=request_dict, logger=logger
        )

        # 4. エネルギーランキングレポート
        result_paths[
            "energy_ranking_report"
        ] = CnEnergyRankingReportLogic().generate_energy_ranking_csv(
            request_dict=request_dict, logger=logger
        )

        # === 追加: ZIP ファイル作成 ===
        zip_file_path = self._create_zip(result_paths, logger)
        result_paths["zip_path"] = zip_file_path

        return result_paths

    def _create_zip(self, file_paths: Dict[str, str], logger) -> str:
        """
        指定された複数ファイルを ZIP にまとめる
        """
        output_dir = r"C:\\HZY\\FILE DOWNLOAD\\2_レポートバックデータ(csv)"
        os.makedirs(output_dir, exist_ok=True)

        # 時間のローカライズ
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        zip_name = f"cn_report_bundle_{now_local .strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = os.path.join(output_dir, zip_name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for name, path in file_paths.items():
                if not path or not os.path.exists(path):
                    logger.warning(f"ファイルが存在しないためスキップ: {name}={path}")
                    continue
                arcname = os.path.basename(path)
                zipf.write(path, arcname)
                logger.info(f"ZIPに追加: {path} → {arcname}")

        logger.info(f"ZIPファイル作成完了: {zip_path}")
        return zip_path
