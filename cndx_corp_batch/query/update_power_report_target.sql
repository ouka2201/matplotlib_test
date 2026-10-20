-- 処理20・22・25／データ項目更新仕様説明書No.7～9：供給地点特定番号と対象年月で管理情報を更新する。
-- 状態は3（完了）・4（完了（警告））・5（エラー）。ファイル情報・エラー文言は呼び出し側で設定する。
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
