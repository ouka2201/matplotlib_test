-- 更新仕様No.5：生データを登録した供給地点・対象年月の紐付け完了を記録する。
UPDATE db_corp.t_30min_import_mng
SET linked_date = :current_time,
    linked_error_message = '',
    updated_by = :executed_by,
    updated_at = :current_time
WHERE supply_point_number IN :supply_points
  AND target_year_month = :target_year_month
  AND create_status = '3'
  AND linked_date IS NULL
