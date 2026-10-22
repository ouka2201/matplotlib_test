# cndx_corp_back/logic/report/kpi_report_create_component.py
# -*- coding: utf-8 -*-

import io
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from zoneinfo import ZoneInfo

from flask import current_app

from cndx_corp_back.common.decorators import log_time, service
from cndx_corp_back.service.report.kpi_report_create_service import (
    KpiReportCreateService,
)


class KpiReportCreateComponent:
    """
    KPI一覧（CSV）を生成して、呼び出し元が扱いやすい形で返すコンポーネント。
    - building_id の判定（単拠点/複数拠点/グループ/全体）
    - request_dict の組み立て（group_items への変換含む）
    - KpiReportCreateService の呼び出し
    - return_type に応じて以下の形式で返却する：
        - "path"   : [{"building_id": "...", "local_path": "C:\\...\\kpi.csv"}]
        - "fileobj": [{"building_id": "...", "fileobj": <BytesIO>, "filename": "...", "mimetype": "text/csv"}]
        - "base64" : [{"building_id": "...", "filename": "...", "mimetype": "text/csv", "file_base64": "..."}]
    """

    def __init__(self, creation_id: str):
        # レポート作成単位のトレーサビリティ用 ID（ファイル名やディレクトリ分けにも利用可）
        self.creation_id = creation_id

    # --------------------------------------------------------------------- #
    # 内部ユーティリティ
    # --------------------------------------------------------------------- #
    # @log_time
    def _resolve_building_list(self, dto) -> List[str]:
        """処理対象の building_id 候補を決定する。"""
        if dto.building_ids_for_single and len(dto.building_ids_for_single) > 0:
            # 単拠点/複数拠点（ID 明示指定）
            return list(dto.building_ids_for_single)

        # ★ グループ作成：仮想拠点IDがあればそれを優先
        if (
            getattr(dto, "is_for_multibuilding", False)
            and getattr(dto, "target_type", "") == "グループ"
        ):
            virt_id = getattr(dto, "virtual_group_building_id", None)
            return [virt_id or "1"]

        # 企業全体
        return ["0"]

    def _build_request(self, dto, b_id: str) -> Dict[str, Any]:
        """extended_dto から service 用 request_dict を構築する。"""
        request_dict = dto.model_dump(by_alias=False).copy()
        request_dict["creation_id"] = self.creation_id

        # ★ building_id はそのまま（ALL / 実ID / 仮想拠点ID / 旧"GROUP"）
        request_dict["building_id"] = b_id

        # ★ グループ指定時は group_items を下流へ渡す（Service 側で group1..5 へ展開して絞り込み）
        is_group_target = (
            getattr(dto, "is_for_multibuilding", False)
            and getattr(dto, "target_type", "") == "グループ"
        )
        if is_group_target:
            group_src = dto.group_for_multibuilding or []
            if not group_src:
                request_dict["_skip_reason"] = "empty_group_items"
            # 下流が扱いやすい形（group_id / option_no）に正規化
            request_dict["group_items"] = [
                {
                    "group_id": int(getattr(g, "group_no")),
                    "option_no": str(getattr(g, "option_no")),
                }
                for g in group_src
                if getattr(g, "group_no", None) is not None
                and getattr(g, "option_no", None) is not None
            ]

        return request_dict

    # --------------------------------------------------------------------- #
    # 公開 API
    # --------------------------------------------------------------------- #
    # @log_time
    def create_files(
        self,
        df_building,
        dto,
        logger=None,
        return_type: Literal["path", "fileobj", "base64"] = "path",
    ) -> List[Dict[str, Any]]:
        """
        KPI CSV を生成し、return_type に応じて返却する。

        戻り値例：
          - path   : [{"building_id": <b_id|GROUP|ALL>, "local_path": <CSVパス>}, ...]
          - fileobj: [{"building_id": <...>, "fileobj": <BytesIO>, "filename": <...>, "mimetype": "text/csv"}, ...]
          - base64 : [{"building_id": <...>, "filename": <...>, "mimetype": "text/csv", "file_base64": <...>}, ...]
        """
        if logger is None:
            logger = current_app.logger
        results: List[Dict[str, Any]] = []
        building_list = self._resolve_building_list(dto)

        for b_id in building_list:
            message_list: list = []
            req = self._build_request(dto, b_id)

            # グループ指定だが要素が空の場合はスキップ
            if req.get("_skip_reason") == "empty_group_items":
                logger.warning(
                    "KPI: グループ作成が指定されましたが、グループ要素が空のためスキップします。"
                )
                continue

            df_building_sub = df_building
            # 個別の場合
            if len(b_id) > 1:
                df_building_sub = df_building[df_building["building_id"] == b_id]

            # --- サービス呼び出し（CSV 生成） ---
            filename, csv_bytes = KpiReportCreateService().execute(
                df_building_sub,
                request_dict=req,
                logger=logger,
                message_list=message_list,
            )
            zip_name, zip_bytes = make_zip_from_named_bytes(
                [(filename, csv_bytes)], subdir="csv"
            )

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
        return results


# @log_time
def make_zip_from_named_bytes(files, subdir=None):
    """
    - filename: ZIP 内に格納するファイル名（拡張子 .csv 推奨）
    - data    : ファイル内容。bytes / bytearray / str を受け付ける。
                data が str の場合は UTF-8（BOM 付き：utf-8-sig）でエンコードして書き込む
                （Excel で文字化けしにくくするため）。
    return: (zip_filename, zip_bytes)
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        used = set()
        for name, data in files:
            if not isinstance(name, str) or not name:
                raise ValueError(f"ファイル名無効: {name!r}")

            # csv拡張子
            if not name.lower().endswith(".csv"):
                name += ".csv"

            # data 兼用処置
            if isinstance(data, str):
                data = data.encode("utf-8-sig")
            elif isinstance(data, bytearray):
                data = bytes(data)
            elif not isinstance(data, bytes):
                raise TypeError(f"{name}: bytes/bytearray/str，型 {type(data)}")

            arcname = f"{subdir}/{name}" if subdir else name
            base, ext = arcname.rsplit(".", 1)
            ext = "." + ext
            i = 1
            while arcname in used:
                arcname = f"{base}({i}){ext}"
                i += 1
            used.add(arcname)

            zf.writestr(arcname, data)

    # 時間のローカライズ
    utc_time = datetime.now(timezone.utc)
    now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
    zip_name = f"kpi_report_bundle_{now_local.strftime('%Y%m%d%H%M%S')}{now_local.microsecond // 1000:03d}.zip"

    return zip_name, buf.getvalue()
