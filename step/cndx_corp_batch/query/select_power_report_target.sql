SELECT
  supply_point_number,
  company_id,
  syousapo_flg
FROM db_corp.t_power_report_mng_info as a
WHERE
  target_year_month = :report_ym
AND
  create_status in ('2','5')
ORDER BY a.created_at ASC;
