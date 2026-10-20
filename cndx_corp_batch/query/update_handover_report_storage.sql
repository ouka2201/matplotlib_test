-- レポート保存情報の引継ぎ。
UPDATE db_corp.t_report_storage_info
SET org_id = :handover_to_org_id
WHERE corporate_number = :corporate_number
  AND org_id = :handover_from_org_id
