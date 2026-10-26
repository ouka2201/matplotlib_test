-- バッチ処理概要定義書：引継先担当者が既に登録されているか確認する。
SELECT 1
FROM db_corp.m_staff_info
WHERE corporate_number = :corporate_number
  AND user_id = :handover_to_user_id
LIMIT 1
