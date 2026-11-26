UPDATE	
db_corp.t_power_report_mng_info
SET	
zip_flg = TRUE,
updated_by = :updated_by,
updated_at = :updated_at
WHERE	
supply_point_number = :supply_point_number
AND
target_year_month = :target_year_month;
