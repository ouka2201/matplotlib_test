-- バッチ処理内容定義書 5：引継元担当者が存在しない対象の引継情報を削除する。
DELETE FROM db_corp.t_sales_user_handover_info
WHERE corporate_number = :corporate_number
  AND handover_from_org_id = :handover_from_org_id
  AND handover_from_user_id = :handover_from_user_id
  AND handover_to_org_id = :handover_to_org_id
  AND handover_to_user_id = :handover_to_user_id
  AND handover_status = '1'
  AND handover_schedule_date = :batch_date
