-- バッチ処理内容定義書 6：対象法人に引継先担当者が存在するか確認する。
-- 概要定義の、引継元・先がともに登録済みの場合の判定にも使用する。
SELECT 1
FROM db_corp.m_staff_info
WHERE corporate_number = :corporate_number
  AND user_id = :handover_to_user_id
LIMIT 1
