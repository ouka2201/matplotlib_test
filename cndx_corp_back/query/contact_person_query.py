from enum import Enum


class QueryMst(Enum):
    """
    担当者設定画面
    """

    # 企業一覧取得処理
    CORPORATE_INFO = """
        with address AS(
            select
                mb.corporate_number
                ,(pm.pref_nm || mb.company_address_city) AS company_address
            from db_corp.m_corporate_basic as mb
            left join prefecture_mst as pm
                on mb.company_address_prefecture = pm.pref_cd
        )
        select distinct
            mc.corporate_number
            , mc.company_name
            , ad.company_address
            , mc.company_name_kana
        from db_corp.m_corporate_basic mc
        left join db_corp.m_corporate_details_info as mcdi 
            on mc.corporate_number = mcdi.corporate_number
        left join db_corp.m_staff_info as si
            on mc.corporate_number = si.corporate_number
        left join db_corp.m_building mb
            on mc.corporate_number = mb.corporate_number
        inner join address ad
            on mc.corporate_number = ad.corporate_number
    """

    # 担当者LIST取得
    CONTACT_PERSON_LIST = """
    SELECT
        si.user_id
        , muoi.org_id
        , muoi.org_name
        , muoi.org_type_code
        , mu.user_name
		, mu.user_role
        , si.corporate_number
        , si.agreement_category
        , si.consent_receipt_date
    FROM db_corp.m_staff_info si
        inner join db_corp.m_user_organization_info muoi
            on si.org_id = muoi.org_id
        inner join db_corp.m_user mu
            on si.user_id = mu.user_id
    where si.delete_flg = '0' 
    """

    # お客様情報取得
    CORPORATE_INFO_DETAIL = """
        select 
            mb.company_name
            , mb.corporate_number
            , concat(pm.pref_nm, mb.company_address_city) AS company_address
        from db_corp.m_corporate_basic as mb
            left join prefecture_mst as pm
                on mb.company_address_prefecture = pm.pref_cd
    """

    # ユーザーIDに紐付く情報取得
    GET_USER = """
    SELECT mu.user_id
        , muoi2.org_name
        , muoi2.org_type_code
        , mu.user_name
		, mu.org_id
		, mu.user_role
    FROM db_corp.m_user mu
    inner join (
        select muoi.org_id, muoi.org_name, muoi.org_type_code
		from db_corp.m_user_organization_info muoi
		where muoi.delete_flg = '0'
	) as muoi2
        on muoi2.org_id = mu.org_id
	where mu.user_id = '{param2}'
	and mu.delete_flg = '0'
    """

    STAFF_INSERT = """
        INSERT INTO db_corp.M_STAFF_INFO (
            corporate_number
            , agreement_category
            , org_id
            , user_id
            , consent_receipt_date
            , delete_flg
            , created_by
            , created_at
            , updated_by
            , updated_at
        )
        VALUES (
            '{corporate_number}'
            , '{agreement_category}'
            , '{org_id}'
            , '{user_id}'
            , '{consent_receipt_date}'
            , '0'
            , '{login_user_id}'
            , '{now_datetime}'
            , '{login_user_id}'
            , '{now_datetime}'
        );
        """
    STAFF_UPDATE = """
        UPDATE db_corp.M_STAFF_INFO
        SET consent_receipt_date = '{consent_receipt_date}'
            , delete_flg = '0'
            , updated_by = '{login_user_id}'
            , updated_at = '{now_datetime}'
        WHERE
            corporate_number = '{corporate_number}'
            AND agreement_category = '{agreement_category}'
            AND org_id = '{org_id}'
            AND user_id = '{user_id}'
        ;
        """

    STAFF_DELETE = """
        UPDATE db_corp.M_STAFF_INFO
        SET delete_flg = '1'
            , updated_by = '{login_user_id}'
            , updated_at = '{now_datetime}'
        WHERE
            corporate_number = '{corporate_number}'
            AND agreement_category = '{agreement_category}'
            AND org_id = '{org_id}'
            AND user_id = '{user_id}'
        ;
        """
