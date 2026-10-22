from datetime import datetime

import pandas as pd

from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.decorators import log_time, service
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo


# @log_time
def insert_entity_with_info(
    bmmst,
    gross_floor_area,
    session,
    model,
    cleaned_row: dict,
    pk_info: dict,
    extra_info: dict,
    user_id: str,
) -> None:
    repo = BaseRepository(session, model=model)

    # 既存検索して、存在したら、update実行 TODO
    target_entity_list = repo.find_all_by(**pk_info)
    if target_entity_list is not None and len(target_entity_list) == 1:
        # 既にデータ登録されましたら、update実行
        target_entity = target_entity_list[0]
        bmmst_sub = bmmst[
            (
                bmmst["industry_class_detail_code"]
                == target_entity.industry_class_detail_code
            )
            & (bmmst["pulldown_code"] == target_entity.energy_benchmark_target_industry)
        ]
        if not bmmst_sub.empty:
            _set_competitor_industry_co2_avg(
                gross_floor_area, bmmst_sub=bmmst_sub, cnapp_entity=target_entity
            )

        target_entity.updated_by = user_id
        for key, value in extra_info.items():
            setattr(target_entity, key, value)
        # repo.update(target_entity, extra_info)

    else:
        # 定義されているカラムだけ許可
        allowed_fields = {c.name for c in model.__table__.columns}

        # 共通情報にユーザー、作成日時を追加
        merged_row = {**cleaned_row, **extra_info, "created_by": user_id}

        filtered_row = {k: v for k, v in merged_row.items() if k in allowed_fields}
        entity = model(**filtered_row)

        repo.session.add(entity)
        # repo.insert_entity(entity)


# @log_time
def insert_input_table_data(
    bmmst,
    gross_floor_area,
    session,
    basic_df: pd.DataFrame,
    agreement_category: str,
    org_id: str,
    user_id: str,
    fiscal_years: list[str],
    year_month_list: list[str],
    vis_company_name: str,
):
    row = basic_df.iloc[0].to_dict()
    cleaned_row = {k: v for k, v in row.items() if v is not None and not pd.isna(v)}
    corporate_number = basic_df.at[0, "corporate_number"]
    for fiscal_year in fiscal_years:
        # pk情報
        pk_info = {
            "corporate_number": corporate_number,  # PK
            "agreement_category": agreement_category,
            "org_id": org_id,
            "fiscal_year": str(fiscal_year),  # PK
            "registration_seq": 0,
        }
        corp_base_entity: MCorporateBasic = (
            session.query(MCorporateBasic)
            .filter(
                MCorporateBasic.corporate_number == corporate_number,
                MCorporateBasic.delete_flg != True,
            )
            .first()
        )
        address_prefecture = corp_base_entity.company_address_prefecture
        address_city = corp_base_entity.company_address_city

        # 開始年月
        if (
            fiscal_year + "04"
            <= min(year_month_list)
            <= str(int(fiscal_year) + 1) + "03"
        ):
            startYearMonth = min(year_month_list)
        else:
            startYearMonth = fiscal_year + "04"

        # 終了年月
        endYearMonth = str(int(fiscal_year) + 1) + "03"

        # 最大の年月と比較する
        endYearMonth = min(endYearMonth, max(year_month_list))

        # CN対策申込情報登録
        cn_info = {
            "corporate_number": corporate_number,  # PK
            "agreement_category": agreement_category,
            "org_id": org_id,
            "fiscal_year": str(fiscal_year),  # PK
            "registration_seq": 0,
            "entry_draft_flag": "0",
            "business_office_count": len(basic_df),
            "address_prefecture": address_prefecture,
            "address_city": address_city,
            "report_period_start_year_month": startYearMonth,
            "report_period_end_year_month": endYearMonth,
            "ghg_system_company_name": vis_company_name,
            "company_name": corp_base_entity.company_name,
        }

        insert_entity_with_info(
            bmmst,
            gross_floor_area,
            session=session,
            model=TCnApplicationInfo,
            cleaned_row=cleaned_row,
            pk_info=pk_info,
            extra_info=cn_info,
            user_id=user_id,
        )


def _set_competitor_industry_co2_avg(
    gross_floor_area, bmmst_sub: pd.DataFrame, cnapp_entity: TCnApplicationInfo = None
):
    if not bmmst_sub.empty:
        if gross_floor_area >= 10000:
            bmmst_sub_1 = bmmst_sub[
                (bmmst_sub["total_floor_area_flag"] == "1")
                & (bmmst_sub["target_total_floor_area_max"] == 0)
            ]
        else:
            bmmst_sub_1 = bmmst_sub[
                (bmmst_sub["total_floor_area_flag"] == "1")
                & (bmmst_sub["target_total_floor_area_min"] <= gross_floor_area)
                & (bmmst_sub["target_total_floor_area_max"] >= gross_floor_area)
            ]

        if cnapp_entity:
            if not bmmst_sub_1.empty:
                cnapp_entity.competitor_industry_co2_avg = bmmst_sub_1[
                    "competitor_industry_co2_avg"
                ].iloc[0]
                cnapp_entity.energy_saving_denominator = bmmst_sub_1[
                    "energy_saving_denominator"
                ].iloc[0]
            else:
                cnapp_entity.competitor_industry_co2_avg = bmmst_sub[
                    "competitor_industry_co2_avg"
                ].iloc[0]
                cnapp_entity.energy_saving_denominator = bmmst_sub[
                    "energy_saving_denominator"
                ].iloc[0]
