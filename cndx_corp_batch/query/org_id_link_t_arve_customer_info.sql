UPDATE db_corp.t_arve_customer_info AS A
SET org_id = (
    SELECT B.org_id
    FROM db_corp.m_user_organization_info AS B 
    WHERE A.user_org_name LIKE B.org_name || '%'  
    ORDER BY B.org_id 
    LIMIT 1
)
WHERE A.org_id IS NULL;