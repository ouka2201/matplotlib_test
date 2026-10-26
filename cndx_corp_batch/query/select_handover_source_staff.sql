-- バッチ処理内容定義書 3：引継元担当者IDが担当者情報マスタに存在するか確認する。
SELECT 1
FROM db_corp.m_staff_info
WHERE corporate_number = :corporate_number
  AND user_id = :handover_from_user_id
LIMIT 1
