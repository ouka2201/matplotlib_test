-- 更新仕様・Q02回答：担当者ユーザーIDだけを更新し、組織IDは保持する。
UPDATE db_corp.m_staff_info
SET user_id = :handover_to_user_id
WHERE corporate_number = :corporate_number
  AND user_id = :handover_from_user_id
