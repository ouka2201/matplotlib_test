"""
power_report_create_service.py

「電力見える化レポート」作成サービス
  1. 受け取ったリクエスト情報をそのまま PowerReportCreateComponent に渡す
  2. PowerReportCreateComponent がローカルに PDF(空でも可) を作成し、
     t_report_storage_info.report_save_path を更新
  3. 作成先パス (report_location) をフロントへ返却
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from flask import abort, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.report.power_report_create_component import (
    PowerReportCreateComponent,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportCreateService:  # pylint: disable=too-few-public-methods
    """
    電力見える化レポート作成サービス

    Parameters
    ----------
    request_dict : dict
        フロントから受け取った JSON をそのまま渡す
    message_list : list[str]
        画面に返すメッセージ用リスト（※入力チェックはフロント側なので基本使わない）
    """

    @service
    def execute(  # noqa: D401
        self,
        request_dict: Dict[str, str],
        message_list: List[str],
        logger=None,
    ) -> Optional[str]:
        """
        Returns
        -------
        str | None
            正常時: 生成した PDF の保存パス
            失敗時: None（例外経由で 500 をフロントへ）
        """
        # ------------------------------------------------------------------
        # 0. logger 初期化
        # ------------------------------------------------------------------
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 電力レポート生成 Service 開始")

        # ------------------------------------------------------------------
        # 1. （※入力チェックはフロント実施の前提なのでここでは行わない）
        # ------------------------------------------------------------------
        # 　→ message_list を使うシーンが無い場合は空リストのまま返すだけ
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # 2. レポート生成コンポーネント呼び出し
        # ------------------------------------------------------------------
        try:
            report_location: str = PowerReportCreateComponent().execute(request_dict)

        except Exception as exc:  # pylint: disable=broad-except
            # 予期しない例外は 500
            logger.error(f"PowerReportCreateComponent 失敗: {exc}")
            abort(500, description=get_message("FAILED", data="レポート生成"))

        # ------------------------------------------------------------------
        # 3. 正常終了
        # ------------------------------------------------------------------
        logger.info(f"{os.path.basename(__file__)} 電力レポート生成 Service 終了")
        return report_location
