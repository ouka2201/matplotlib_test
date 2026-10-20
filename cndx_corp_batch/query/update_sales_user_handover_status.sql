-- バッチ処理内容定義書 10・12：引継実施ステータスと引継実施日時を更新する。
UPDATE db_corp.t_sales_user_handover_info
SET handover_status = :handover_status,
    handovered_at = CURRENT_TIMESTAMP
WHERE corporate_number = :corporate_number
  AND handover_from_org_id = :handover_from_org_id
  AND handover_from_user_id = :handover_from_user_id
  AND handover_to_org_id = :handover_to_org_id
  AND handover_to_user_id = :handover_to_user_id
  AND handover_status = :planned_status
  AND handover_schedule_date = :batch_date
