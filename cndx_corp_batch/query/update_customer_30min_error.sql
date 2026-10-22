-- 更新仕様No.6：ロールバックした取得分のエラーを記録し、紐付け日時は変更しない。
UPDATE db_corp.t_30min_import_mng
SET linked_error_message = :error_message,
    updated_by = :executed_by,
    updated_at = :current_time
WHERE supply_point_number IN :supply_points
  AND target_year_month = :target_year_month
  AND create_status = '3'
  AND linked_date IS NULL
