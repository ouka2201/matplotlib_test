SELECT D.cmn_supplypointspecificnum__c
FROM(
    SELECT
    A.cmn_supplypointspecificnum__c,
    B.cmn_supplypointspecificnum__c AS last_month,
    C.supply_point_number AS import_confirmed
    FROM db_corp.t_arve_customer_info A
    LEFT JOIN db_corp.t_historical_arve_customer_info B ON A.cmn_supplypointspecificnum__c = B.cmn_supplypointspecificnum__c
    AND B.acquisition_year_month = :arve_historical_year_month
    LEFT JOIN db_corp.t_30min_import_mng C ON C.supply_point_number = A.cmn_supplypointspecificnum__c
    AND C.target_year_month = :target_year_month
    AND C.create_status = '3'
) D
WHERE
D.import_confirmed IS NULL
AND D.last_month IS NULL;
