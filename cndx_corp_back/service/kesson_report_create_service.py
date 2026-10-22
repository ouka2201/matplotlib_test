# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import io
import os
from typing import Any, Dict, List, Literal

import pandas as pd
from flask import current_app
from sqlalchemy import String, cast, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.service.report.kesson_report_create_service import (
    KessonReportCreateService,
)


class KessonReportCreateComponent:
    """
    欠損一覧（PDF2種のZIP）生成コンポーネント
    - BackdataReportCreateComponent と同じ返却形式に揃える
    - building_id の解決（単拠点/複数拠点/グループ/企業全体）
    - request_dict の組み立て（group_items 変換を含む）
    - KessonReportCreateService.execute(...) を呼び出して ZIP を取得
    - return_type に応じて返却：
        - "path"   : [{"building_id": <...>, "local_path": "C:\\...\\bundle.zip"}]
        - "fileobj": [{"building_id": <...>, "fileobj": <BytesIO>, "filename": "...zip", "mimetype": "application/zip"}]
        - "base64" : [{"building_id": <...>, "filename": "...zip", "mimetype": "application/zip", "file_base64": "..."}]
    """

    def __init__(self, creation_id: str):
        self.creation_id = creation_id  # トレーサビリティ用

    # ------------------------------------------------------------------ #
    # 内部ユーティリティ
    # ------------------------------------------------------------------ #
    # @log_time
    def _resolve_building_list(self, dto) -> List[str]:
        """処理対象の building_id 候補を決定する。"""
        if dto.building_ids_for_single and len(dto.building_ids_for_single) > 0:
            return list(dto.building_ids_for_single)  # 単/複数拠点
        if dto.is_for_multibuilding and getattr(dto, "target_type", None) == "グループ":
            return ["1"]
        return ["0"]  # 企業全体

    # @log_time
    def _build_request(self, dto, b_id: str) -> Dict[str, Any]:
        """
        可視化側DTO + 拡張項目 からサービス用リクエストを構築。
        グループ指定時は group_for_multibuilding を group_items に変換。
        """
        req = dto.model_dump(by_alias=False).copy()
        req["creation_id"] = self.creation_id

        if b_id == "1":
            req["building_id"] = "1"
            req["group_items"] = [
                {"group_id": g.group_no, "location_type": g.option_no}
                for g in (dto.group_for_multibuilding or [])
            ]
        else:
            req["building_id"] = b_id  # "ALL" or 実拠点ID
        return req

    @staticmethod
    def _guess_mimetype(filename: str) -> str:
        return (
            "application/zip"
            if filename.lower().endswith(".zip")
            else "application/octet-stream"
        )

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
        欠損一覧（PDF2種）を生成し ZIP に束ね、指定の形式で返却する。
        """
        if logger is None:
            logger = current_app.logger

        results: List[Dict[str, Any]] = []
        building_list = self._resolve_building_list(dto)

        # --- 【改修: DBアクセス効率化】 ループの前に全件データを一括取得 ---
        with get_scoped_session() as session:
            # 共通パラメータ
            corporate_number = dto.corporate_number
            agreement_category = dto.agreement_category
            org_id = dto.org_id
            start_ym = f"{int(dto.start_year):04d}{int(dto.start_month):02d}"
            end_ym = f"{int(dto.end_year):04d}{int(dto.end_month):02d}"

            # 企業名の取得
            cn_info = (
                session.query(TCnApplicationInfo)
                .filter_by(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    org_id=org_id,
                )
                .first()
            )
            company_name = cn_info.company_name if cn_info else ""

            # 全建物分のエネルギーデータを一括取得
            energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    cast(
                        func.round(
                            func.sum(TMonthlyBuildingEnergyAggregation.energy_quantity),
                            2,
                        ),
                        String,
                    ).label("energy_quantity"),
                    cast(
                        func.sum(
                            TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount
                        ),
                        String,
                    ).label("証書クレジット"),
                    func.count(
                        TMonthlyBuildingEnergyAggregation.target_year_month
                    ).label("件数"),
                    TMonthlyBuildingEnergyAggregation.energy_code,
                )
                .filter(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    TMonthlyBuildingEnergyAggregation.energy_quantity > 0,
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.supplier_reg_no,
                )
                .all()
            )

        # 全体用DataFrameを作成
        df_energy_all = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in energy_stmt
            ],
            dtype=str,
        )
        energy_df_by_building: dict[str, pd.DataFrame] = {
            bid: df.reset_index(drop=True)
            for bid, df in df_energy_all.groupby("building_id", sort=False)
        }

        for b_id in building_list:
            message_list: list = []
            req = self._build_request(dto, b_id)

            # グループ指定なのに要素が空ならスキップ（念のため）
            if req.get("building_id") == "1" and not req.get("group_items"):
                logger.warning(
                    "Kesson: グループ作成が指定されましたが、group_items が空のためスキップします。"
                )
                continue

            df_building_sub = df_building
            # 個別の場合
            if len(b_id) > 1:
                df_building_sub = df_building[df_building["building_id"] == b_id]

            # --- 欠損レポート（PDF2種→ZIP）サービス呼び出し ---
            zip_name, zip_bytes = KessonReportCreateService().execute(
                df_building_sub,
                request_dict=req,
                message_list=message_list,
                logger=logger,
                prefetched_data={  # 渡すデータを追加
                    "energy_df_by_building": energy_df_by_building,
                    "df_energy_all": df_energy_all,
                    "company_name": company_name,
                },
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
                "Kesson: 対象 building_list に対して生成された ZIP はありません。"
            )
        return results
