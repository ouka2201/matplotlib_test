-- バッチ処理内容定義書 4：引継元の担当者情報を引継先の組織・担当者へ更新する。
UPDATE db_corp.m_staff_info
SET org_id = :handover_to_org_id,
    user_id = :handover_to_user_id
WHERE corporate_number = :corporate_number
  AND user_id = :handover_from_user_id
