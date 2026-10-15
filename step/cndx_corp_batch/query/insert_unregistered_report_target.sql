INSERT INTO db_corp.t_power_report_mng_info (
    supply_point_number,
    target_year_month,
    company_id,
    syousapo_flg,
    file_name,
    report_created_at,
    create_status,
    error_message,
    file_path,
    created_by,
    created_at
)
SELECT 
    D.supply_point_number,
    D.target_year_month,
    D.company_id,
    D.syousapo_flg,
    D.file_name,
    D.report_created_at,
    D.create_status,
    D.error_message,
    D.file_path,
    D.created_by,
    D.created_at
FROM (
 SELECT
    A.CMN_SupplyPointSpecificNum__c AS supply_point_number,
    :report_ym AS target_year_month,
    A.CMN_KigyoID_Fk__c AS company_id,
    CASE
        WHEN A.RecordTypeId = '省エネサポートサービス' THEN TRUE
        ELSE FALSE
    END AS syousapo_flg,
    '' AS file_name,
    CAST(NULL AS timestamp) AS report_created_at,
    '2' AS create_status,
    '' AS error_message,
    '' AS file_path,
    :user AS created_by,
    CAST(:created_at AS timestamp) AS created_at,
    C.supply_point_number AS is_created
FROM db_corp.t_arve_customer_info A
INNER JOIN db_corp.t_30min_import_mng B  ON A.CMN_SupplyPointSpecificNum__c = B.supply_point_number
AND B.create_status = '3'
AND B.target_year_month = :report_ym
LEFT JOIN db_corp.t_power_report_mng_info C ON A.CMN_SupplyPointSpecificNum__c = C.supply_point_number
AND C.target_year_month = :report_ym
) D
WHERE
D.is_created IS NULL;
