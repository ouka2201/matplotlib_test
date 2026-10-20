-- バッチ処理概要定義書：引継先担当者が既に登録されている場合、引継元担当者を削除する。
DELETE FROM db_corp.m_staff_info
WHERE corporate_number = :corporate_number
  AND org_id = :handover_from_org_id
  AND user_id = :handover_from_user_id
