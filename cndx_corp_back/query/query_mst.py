from enum import Enum


class QueryMst(Enum):
    """
    照会共通機能用設定
    """

    M_BUIDING_GROUP_08_04 = {
        "select": [
            "corporate_number",
            "agreement_category",
            "org_id",
            "group_id",
            "group_name",
            "select_item1",
            "select_item2",
            "select_item3",
            "select_item4",
            "select_item5",
            "select_item6",
            "select_item7",
        ],
        "from": "db_corp.m_buiding_group",
        "where": [
            {"field": "corporate_number", "op": "="},
            {"field": "delete_flg", "op": "!=", "value": True},
        ],
    }

    M_BUILDING_08_04 = """
        SELECT
            mb.corporate_number,
            mb.agreement_category,
            cri.agreement_name,
            mb.org_id,
            mb.building_id,
            mb.ep_customer_number,
            mb.supply_point_number,
            mb.building_name,
            mb.building_address_prefecture,
            mb.building_address_city,
            pm.pref_nm || mb.building_address_city as building_address,
            mb.industry_class_detail_code,
            mb.industry_class_detail_name,
            mb.benchmark_denom,
            mb.benchmark_val,
            mb.ep_office_code,
            mb.building_consent_flag,
            mb.group1,
            mb.group2,
            mb.group3,
            mb.group4,
            mb.group5,
            mb.created_at,
            mb.updated_at
        FROM
            db_corp.m_building mb
            LEFT JOIN db_common.prefecture_mst pm ON (mb.building_address_prefecture = pm.pref_cd)
            LEFT JOIN db_corp.m_consent_route_info cri ON (mb.agreement_category = cri.agreement_category)
        WHERE
            mb.corporate_number = '{corporate_number}'
            AND mb.agreement_category LIKE '{agree_cate}' 
            AND mb.delete_flg IS NOT TRUE
        ORDER BY
            mb.corporate_number,
            mb.agreement_category,
            mb.org_id,
            mb.building_id
    """

    CORP_JOIN_BLD_08_01 = """
    select
        mcb.corporate_number
        , mcb.company_name
        , mcb.company_name_kana
        , mcb.company_address_prefecture
        , mcb.company_address_city
        , pmc.pref_nm || mcb.company_address_city as company_address
        , mb.agreement_category
        , mb.building_id
        , mb.ep_customer_number
        , mb.supply_point_number
        , mb.building_name
        , mb.building_address_prefecture
        , mb.building_address_city
        , mb.ep_office_code
        , mb.agreement_org
        , pmb.pref_nm || mb.building_address_city as building_address
        , mb.group1
        , mb.group2
        , mb.group3
        , mb.group4
        , mb.group5 
    from
        db_corp.m_corporate_basic mcb
        LEFT JOIN db_corp.m_building mb ON (mcb.corporate_number = mb.corporate_number)
        LEFT JOIN db_common.prefecture_mst pmc ON (mcb.company_address_prefecture = pmc.pref_cd)
        LEFT JOIN db_common.prefecture_mst pmb ON (mb.building_address_prefecture = pmb.pref_cd)
    where
        {where} mcb.delete_flg is not True"""

    CN_KARTE_VIEW = """
SELECT
    * 
FROM
    db_corp.v_corporate_profile_report_bnk_view
WHERE
    org_id = '{org_id}'
    AND corporate_number = '{corporate_number}' 
    AND registration_seq = {registration_seq}
    {additional_condition}
"""

    # CN_KARTE_VIEW_ = """SELECT DISTINCT ON ("building_id", "energy_code", "target_year_month")
    #     *
    #     FROM v_corporate_profile_report_bnk_view
    #     WHERE 
    #         "corporate_number" = '{df_curr_year['corporate_number'].iloc[0]}'
    #         AND "org_id" = '{df_curr_year['org_id'].iloc[0]}'
    #         AND "target_year_month" IN ('{"', '".join(year_month_list)}')
    #     ORDER BY "building_id", "energy_code", "target_year_month", "registration_seq" DESC;
    # """

    ELEC_VIS = """
SELECT
    te3.*,
    bi.building_address_prefecture,
    bi.building_address_city,
    mcc.jp_code_name,
    CONCAT(jp_code_name, ' ', building_address_city) AS building_address 
FROM
    db_corp.t_electricity_data_30min te3

LEFT JOIN db_corp.m_building bi ON (
    bi.agreement_category = te3.agreement_category
    AND bi.corporate_number = te3.corp_number
    AND bi.building_id = te3.building_id
    )
    
LEFT JOIN db_corp.m_corp_code_info mcc ON (
    mcc.code_type = 'PREF'
    AND mcc.code = bi.building_address_prefecture
)
WHERE
    corp_number = '{corporate_number}' 
    AND te3.agreement_category = '{agreement_category}' 
    AND te3.building_id = '{building_id}' 
    AND te3.acquisition_date >= '{date_from}' 
    AND te3.acquisition_date <= '{date_to}'
    AND te3.org_id = '{org_id}'
"""
