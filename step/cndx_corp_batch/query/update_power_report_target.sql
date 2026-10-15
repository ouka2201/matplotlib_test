UPDATE db_corp.t_power_report_mng_info
SET
file_name = :file_name,
report_created_at = :report_created_at,
create_status = :create_status,
file_path = :file_path,
error_message = :error_message,
updated_by = :updated_by,
updated_at = :updated_at
WHERE supply_point_number = :supply_point_number
AND target_year_month = :target_year_month
