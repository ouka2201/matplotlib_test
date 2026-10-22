import os
import traceback
from datetime import datetime
from typing import Dict, List

import pandas as pd
from flask import current_app
from sqlalchemy import and_, case, collate, func, literal, select
from sqlalchemy.sql import over

from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)


class SearchAgreementOrgLogic:

    @component
    def build_results(self, logger=None) -> List[Dict[str, str]]:
        """
        org_id, org_name に同意書未取得の経路で登録表示する値を返す
        """
        if logger is None:
            logger = current_app.logger

        results: List[Dict[str, str]] = []
        # 固定で値を返す
        results.append(
            {
                "org_id": "dummy",
                # "org_id": "TEP",
                "org_name": "同意書未取得",
            }
        )
        return results

    @component
    def get_agreement_org(
        self, session, request_dict, logger=None
    ) -> List[Dict[str, str]]:
        """
        利用者組織情報_検索
        """
        if logger is None:
            logger = current_app.logger

        # 同意書取得組織の小画面選択検索処理
        org_name = request_dict.get("org_name")
        category = request_dict.get("agreement_category")
        df = get_org_name(session, org_name, category, logger)

        # 結果格納用List
        results: list[dict] = []
        for _, row in df.iterrows():
            results.append(
                {
                    "org_id": row["org_id"],
                    "org_name": row["org_name"],
                }
            )

        return results


def get_org_name(session, org_name, agreement_category, logger=None) -> pd.DataFrame:
    """
    同意書取得経路ごとに 事業者区分 組織ID で絞り込む
    """
    stmt = (
        select(
            MUserOrganizationInfo.org_id,
            collate(MUserOrganizationInfo.org_name, "C").label("org_name"),
        )
        .distinct()
        .order_by(
            # MUserOrganizationInfo.org_id.asc(),
            # collate(MUserOrganizationInfo.org_name,"C").asc()
            "org_name"
        )
    )
    # Where条件リストを作る
    conditions = []
    conditions.append(MUserOrganizationInfo.delete_flg.is_(False))
    # agreement_category ごとの business_type / org_id 絞り込み
    category_map = {
        "01": (["金融機関"], None),
        "02": (["EP", "REP", "TCS"], None),
        "11": (["EP", "REP"], None),
        "12": (["可視化事業者"], "ASE"),
        "13": (["可視化事業者"], "ZRB"),
        "14": (["可視化事業者"], "JFS"),
    }
    if agreement_category in category_map:
        biz_types, org_id_filter = category_map[agreement_category]
        conditions.append(MUserOrganizationInfo.business_type.in_(biz_types))
        if org_id_filter:
            conditions.append(MUserOrganizationInfo.org_id == org_id_filter)

    # 画面から組織名が入力されている場合
    if org_name:
        conditions.append(MUserOrganizationInfo.org_name.like(f"%{org_name}%"))
    # 条件が１つ以上あればANDでまとめてfilter()
    if conditions:
        stmt = stmt.where(and_(*conditions))
    # ログ出力
    compiled = stmt.compile(
        dialect=session.connection().dialect, compile_kwargs={"literal_binds": True}
    )
    logger.info(f"SQL: {compiled}")

    # SQL実行
    try:
        df = pd.read_sql(stmt, session.connection())
    except Exception:
        raise
    return df
    try:
        df = pd.read_sql(stmt, session.connection())
    except Exception:
        raise
    return df
