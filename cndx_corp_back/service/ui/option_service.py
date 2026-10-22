from collections import defaultdict

from common.db_base_handler import BaseRepository
from entity.m_consent_route_info_entity import MConsentRouteInfo
from entity.m_corp_code_info_entity import MCorpCodeInfo
from entity.m_jp_st_industry_classification_entity import MJpStIndustryClassification
from flask import current_app
from sqlalchemy import func, select

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.load_master import get_mst_data
from cndx_corp_back.constant.constants import MstTable
from cndx_corp_back.dto.ui.option_out_dto import UiOptionOutDto
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst


class UiOptionService:

    @service
    def get_pref(self, logger) -> list:
        logger = current_app.logger

        # result_list = get_mst_data(MstTable.PREFECTURE)

        with get_scoped_session() as session:
            rows = session.query(
                MPrefecture.pref_cd.label("code"),
                MPrefecture.pref_nm.label("text"),
            ).all()

        return [
            UiOptionOutDto.model_validate(row, from_attributes=True).model_dump()
            for row in rows
        ]

    @service
    def get_industry(self, logger=None) -> list | None:
        logger = current_app.logger

        from cndx_corp_back.entity.m_jp_st_industry_classification_entity import (
            MJpStIndustryClassification as Entity,
        )

        # result_list = get_mst_data(MstTable.PREFECTURE, cond=cond)

        with get_scoped_session() as session:
            # すべて取得
            stmt = select(
                Entity.division_code,
                Entity.division_name,
                Entity.major_group_code,
                Entity.major_group_name,
                Entity.group_code,
                Entity.group_name,
                Entity.industry_code,
                Entity.industry_name,
            ).where(Entity.delete_flag.isnot(True))
            rows = session.execute(stmt).all()

        # build
        hierarchy = defaultdict(lambda: {"text": "", "children": {}})

        for row in rows:
            d_code, d_name, m_code, m_name, g_code, g_name, i_code, i_name = row

            # Initialize hierarchy levels
            if d_code not in hierarchy:
                hierarchy[d_code]["text"] = d_name

            if m_code not in hierarchy[d_code]["children"]:
                hierarchy[d_code]["children"][m_code] = {"text": m_name, "children": {}}

            if g_code not in hierarchy[d_code]["children"][m_code]["children"]:
                hierarchy[d_code]["children"][m_code]["children"][g_code] = {
                    "text": g_name,
                    "children": [],
                }

            # Append industry level
            hierarchy[d_code]["children"][m_code]["children"][g_code][
                "children"
            ].append({"code": i_code, "text": i_name})

            # Build tree-like recursively
            def build_tree(level_dict: dict):
                return [
                    {
                        "code": code,
                        "text": data["text"],
                        "children": (
                            build_tree(data["children"])
                            if isinstance(data["children"], dict)
                            else data["children"]
                        ),
                    }
                    for code, data in level_dict.items()
                ]

        return build_tree(hierarchy)

    @service
    def get_consent_route(self, request_dict, logger) -> list:
        logger = current_app.logger
        from cndx_corp_back.dto.ui.option_in_consent_dto import (
            UiOptionConsentInDto as InDto,
        )
        from cndx_corp_back.entity.m_consent_route_info_entity import (
            MConsentRouteInfo as Entity,
        )

        group_cd = InDto.model_validate(request_dict).group_code

        with get_scoped_session() as session:

            query = session.query(
                Entity.agreement_category.label("code"),
                Entity.agreement_name.label("text"),
            )

            if group_cd:
                query = query.filter(Entity.agreement_category.like(f"{group_cd}%"))

            rows = query.all()

        return [
            UiOptionOutDto.model_validate(row, from_attributes=True).model_dump()
            for row in rows
        ]

    from cndx_corp_back.entity import (
        m_consent_route_info_entity,
        m_corp_code_info_entity,
        m_jp_st_industry_classification_entity,
        m_prefecture_entity,
    )

    def get_master_list(self, master_name: str, logger, filters: dict = None) -> list:
        """マスタデータ取得

        Args:
            master_name (str): _description_
            logger (_type_): _description_
            filters (dict, optional): _description_. Defaults to None.

        Raises:
            ValueError: _description_

        Returns:
            list: _description_
        """
        logger = current_app.logger

        model = MASTER_MODEL_MAP.get(master_name)
        if not model:
            raise ValueError(f"存在しないマスタ: {master_name}")

        with get_scoped_session() as session:
            repo = BaseRepository(session, model)
            rows = repo.find_all(**(filters or {}))

            return [
                {
                    "id": get_first_attr(row, "code", "pref_cd", "agreement_category"),
                    "name": get_first_attr(
                        row, "jp_code_name", "pref_nm", "agreement_name"
                    ),
                    "record": model_to_dict(row),
                }
                for row in rows
            ]


MASTER_MODEL_MAP: dict[str, BaseRepository] = {
    "prefecture": PrefectureMst,
    "consent-route": MConsentRouteInfo,
    # "industry": MJpStIndustryClassification,
    "code": MCorpCodeInfo,
}


def model_to_dict(obj):
    return {key: value for key, value in vars(obj).items() if not key.startswith("_")}


def get_first_attr(obj, *attrs):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)
    return None
