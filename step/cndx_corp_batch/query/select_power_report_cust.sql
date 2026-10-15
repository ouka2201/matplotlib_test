SELECT
 A.cmn_demandlocationfullname_ref__c as customer_name,
 A.cmn_demandlocationaddress__c as address,
 A.cmn_oldcustomernum__c as customer_number,
 B.qsqb_dcis2_hvpw_ctrt as contract_kw
FROM db_corp.t_arve_customer_info A
INNER JOIN db_corp.t_ep_contracted_power B ON A.cmn_supplypointspecificnum__c = B.qsqb_dcis2_spl_pt_spc_no
WHERE A.cmn_supplypointspecificnum__c = :supply_point_number
