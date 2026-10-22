# cndx_corp_back/logic/report/backdata_report_create_component.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import base64
import io
import os
from typing import Any, Dict, List, Literal

from flask import current_app

from cndx_corp_back.common.decorators import component, log_time

# ★ 改这里：使用你新加的「バンドル」ロジック（4種CSV + ZIP 生成）
from cndx_corp_back.logic.report.cn_report_backdata_bundle_logic import (
    CnReportBackdataBundleLogic,
)


class BackdataReportCreateComponent:
    """
    レポートバックデータ（CSV/ZIP）生成コンポーネント
    - KPI用コンポーネントと同様の返却形式に揃える
    - building_id の解決（単拠点/複数拠点/グループ/企業全体）
    - request_dict の組み立て（group_items 変換を含む）
    - CnReportBackdataBundleLogic.generate_all_reports(...) を呼び出して ZIP を取得
    - return_type に応じて返却：
        - "path"   : [{"building_id": <...>, "local_path": "C:\\...\\bundle.zip"}]
        - "fileobj": [{"building_id": <...>, "fileobj": <BytesIO>, "filename": "...zip", "mimetype": "application/zip"}]
        - "base64" : [{"building_id": <...>, "filename": "...zip", "mimetype": "application/zip", "file_base64": "..."}]
    """

    def __init__(self, creation_id: str):
        # レポート作成単位のトレーサビリティ用 ID（必要なら ZIP 名などに利用）
        self.creation_id = creation_id

    # ------------------------------------------------------------------ #
    # 内部ユーティリティ
    # ------------------------------------------------------------------ #
    def _resolve_building_list(self, dto) -> List[str]:
        """処理対象の building_id 候補を決定する。"""
        if dto.building_ids_for_single and len(dto.building_ids_for_single) > 0:
            # 複数/単拠点（指定された拠点ID群）
            return list(dto.building_ids_for_single)
        if dto.is_for_multibuilding and getattr(dto, "target_type", None) == "グループ":
            return ["1"]
        # 企業全体
        return ["0"]

    def _build_request(self, dto, b_id: str) -> Dict[str, Any]:
        """
        張さんの DTO（可視化側DTO + 拡張項目）から、
        バンドルロジック用の request_dict を構築する。
        """
        req = dto.model_dump(by_alias=False).copy()
        # 生成単位ID
        req["creation_id"] = self.creation_id

        # building_id と group_items の整備
        if b_id == "1":
            req["building_id"] = "1"
            # 張DTOの group_for_multibuilding（group_no/option_no）→ 下流が期待する group_items へ変換
            req["group_items"] = [
                {"group_id": g.group_no, "location_type": g.option_no}
                for g in (dto.group_for_multibuilding or [])
            ]
        else:
            # "ALL" or 実拠点ID
            req["building_id"] = b_id

        return req

    @staticmethod
    def _guess_mimetype(filename: str) -> str:
        if filename.lower().endswith(".zip"):
            return "application/zip"
        if filename.lower().endswith(".csv"):
            return "text/csv"
        return "application/octet-stream"

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    # @log_time
    def create_files(
        self,
        df_building,
        dto,
        logger=None,
        return_type: Literal["path", "fileobj", "base64"] = "fileobj",
    ) -> List[Dict[str, Any]]:
        """
        バックデータ（複数CSV）を生成し ZIP に束ね、指定の形式で返却する。

        戻り値例：
          - path   : [{"building_id": <b_id|GROUP|ALL>, "local_path": <ZIPパス>}, ...]
          - fileobj: [{"building_id": <...>, "fileobj": <BytesIO>, "filename": <...zip>, "mimetype": "application/zip"}, ...]
          - base64 : [{"building_id": <...>, "filename": <...zip>, "mimetype": "application/zip", "file_base64": <...>}, ...]
        """
        if logger is None:
            logger = current_app.logger

        results: List[Dict[str, Any]] = []
        building_list = self._resolve_building_list(dto)

        for b_id in building_list:
            message_list: list = []
            req = self._build_request(dto, b_id)

            # グループ指定なのに要素が空ならスキップ（念のため）
            if req.get("building_id") == "1" and not req.get("group_items"):
                logger.warning(
                    "Backdata: グループ作成が指定されましたが、group_items が空のためスキップします。"
                )
                continue

            df_building_sub = df_building
            # 個別の場合
            if len(b_id) > 1:
                df_building_sub = df_building[df_building["building_id"] == b_id]

            # --- バンドルロジック呼び出し（4種CSV生成→ZIP化） ---
            zip_name, zip_bytes = CnReportBackdataBundleLogic().generate_all_reports(
                df_building_sub,
                request_dict=req,
                logger=logger,
                message_list=message_list,
            )
            if message_list:
                logger.warning(
                    f"Backdata: 生成時にエラー（building_id={b_id}）: {message_list}"
                )

            # 返却形式に応じて詰め替え
            filename = zip_name
            mimetype = "application/zip"

            results.append(
                {
                    "building_id": b_id,
                    "fileobj": io.BytesIO(zip_bytes),
                    "filename": filename,
                    "mimetype": mimetype,
                }
            )

        if not results:
            logger.info(
                "Backdata: 対象 building_list に対して生成された ZIP はありません。"
            )
        return results
