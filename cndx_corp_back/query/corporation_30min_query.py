"""LMMBCS-API-04 更新仕様No.7・11。物理列名は30分値紐付けバッチと共通。"""

_energy_columns = ",\n    ".join(f"v30min_used_energy_{i}" for i in range(1, 49))
_energy_values = ",\n    ".join(
    f"CAST(e.t01_30t_syr{i:02d} AS NUMERIC)" for i in range(1, 49)
)

INSERT_CORPORATION_30MIN = f"""
INSERT INTO db_corp.t_electricity_data_30min (
    corp_number, agreement_category, org_id, building_id,
    corp_name, building_name, ep_customer_number, supply_point_number,
    company_id, missing_time_range_count, invalid_time_range_count, acquisition_date,
    {_energy_columns},
    delete_flg, created_by, created_at, updated_by, updated_at, file_update_date,
    arve_corp_name, arve_customer_number, arve_office_code
)
SELECT
    b.corporate_number, b.agreement_category, b.org_id, b.building_id,
    c.company_name, b.location_identifier_name, b.ep_customer_number,
    e.t01_kyo_ctn_tok_no, a.cmn_kigyoid_fk__c,
    CAST(e.t01_kskj_ksu AS INTEGER), CAST(e.t01_fsij_ksu AS INTEGER), e.t01_get_ymd,
    {_energy_values},
    FALSE, :user_id, :current_time, NULL, NULL, NULL,
    a.cmn_demandlocationfullname_ref__c,
    substr(a.cmn_oldcustomernum__c, 4), substr(a.cmn_oldcustomernum__c, 1, 3)
FROM db_corp.m_building AS b
INNER JOIN db_corp.m_corporate_basic AS c
    ON c.corporate_number = b.corporate_number
INNER JOIN db_corp.t_ep_electricity_data_30min AS e
    ON e.t01_kyo_ctn_tok_no = b.supply_point_number
INNER JOIN db_corp.t_arve_customer_info AS a
    ON a.cmn_supplypointspecificnum__c = b.supply_point_number
WHERE b.corporate_number = :corporate_number
    AND b.agreement_category = :agreement_category
    AND b.org_id = :org_id
    AND b.building_id = :building_id
    AND b.delete_flg = FALSE
"""
