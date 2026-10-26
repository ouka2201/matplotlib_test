-- CN申込情報の引継ぎ。
UPDATE db_corp.t_cn_application_info
SET org_id = :handover_to_org_id
WHERE corporate_number = :corporate_number
  AND org_id = :handover_from_org_id
