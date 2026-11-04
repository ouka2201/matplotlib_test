"""営業担当検索。検索文字列と権限条件はバインド変数で指定する。"""

SELECT_HANDOVER_MANAGERS = """
SELECT u.email_address, o.org_name AS company_name,
       u.org_id, u.user_name, u.user_id
FROM db_corp.m_user AS u
INNER JOIN db_corp.m_user_organization_info AS o ON o.org_id = u.org_id
WHERE u.delete_flg = false AND o.delete_flg = false
  AND (:is_ep_admin OR u.org_id LIKE :bank_pattern)
  AND (
    u.email_address LIKE :pattern ESCAPE '!'
    OR (:search_all AND (
      u.user_name LIKE :pattern ESCAPE '!'
      OR o.org_name LIKE :pattern ESCAPE '!'
    ))
  )
ORDER BY o.org_name ASC, u.user_name ASC, u.email_address ASC
"""
