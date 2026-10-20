-- 建物マスタの同意書取得組織を引継ぎ先へ変更する。
UPDATE db_corp.m_building
SET agreement_org = :handover_to_org_id
WHERE corporate_number = :corporate_number
  AND agreement_org = :handover_from_org_id
