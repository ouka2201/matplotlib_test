-- バッチ処理内容定義書 8：法人番号と引継元組織IDで過去データ8表の存在を確認する。
SELECT
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_monthly_building_energy_aggregation
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS monthly_building,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_annual_building_energy_aggregation
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS annual_building,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_monthly_corporate_energy_aggregation
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS monthly_corporate,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_annual_corporate_energy_aggregation
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS annual_corporate,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_report_storage_info
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS report_storage,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.m_building
        WHERE corporate_number = :corporate_number AND agreement_org = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS building,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_cn_application_info
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS cn_application,
    CASE WHEN EXISTS (
        SELECT 1 FROM db_corp.t_building_info
        WHERE corporate_number = :corporate_number AND org_id = :handover_from_org_id
    ) THEN 1 ELSE 0 END AS building_info
