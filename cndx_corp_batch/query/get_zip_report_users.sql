WITH check_create_status AS (
    SELECT
    A.cmn_user_performanceaccountabilityrep__c
    FROM 
    db_corp.t_arve_customer_info AS A
    LEFT JOIN 
    db_corp.t_power_report_mng_info AS B 
        ON A.cmn_supplypointspecificnum__c = B.supply_point_number
    AND
    B.target_year_month = :target_year_month
    AND
    B.create_status IN ('3','4')
    GROUP BY
    A.cmn_user_performanceaccountabilityrep__c
    HAVING
    COUNT (A.cmn_supplypointspecificnum__c) = COUNT (B.supply_point_number)
)
SELECT
A.cmn_supplypointspecificnum__c,
A.cmn_user_performanceaccountabilityrep__c,
A.user_org_name,
A.org_id,
B.syousapo_flg,
B.file_name,
B.file_path
FROM
db_corp.t_arve_customer_info AS A
INNER JOIN
db_corp.t_power_report_mng_info AS B
    ON A.cmn_supplypointspecificnum__c = B.supply_point_number
INNER JOIN
check_create_status AS C 
    ON A.cmn_user_performanceaccountabilityrep__c = C.cmn_user_performanceaccountabilityrep__c
WHERE
B.create_status = '3'
AND
B.ZIP_FLG = FALSE
ORDER BY
A.cmn_user_performanceaccountabilityrep__c ASC,
B.syousapo_flg ASC;

