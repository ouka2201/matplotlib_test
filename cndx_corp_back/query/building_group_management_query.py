from enum import Enum


class BuildingGroupManagementQuery(Enum):
    """
    建物グループマスタ管理画面
    """

    # ユーザー情報から建物グループマスタ取得
    BUILDING_GROUP_INFO = """
        select
            mbg.corporate_number
            , mbg.agreement_category
            , mbg.org_id
            , mbg.group_id
            , mbg.group_name
            , mbg.select_item1
            , mbg.select_item2
            , mbg.select_item3
            , mbg.select_item4
            , mbg.select_item5
            , mbg.select_item6
            , mbg.select_item7
        from db_corp.m_buiding_group mbg
        where
            mbg.delete_flg = false
            and mbg.org_id = '{param1}'
            and mbg.corporate_number = '{param2}'
    """
    # ユーザー情報から同意書取得経路取得
    CODE_INFO = """ 
        select
            cci.code
            , cci.jp_code_name
        from db_corp.m_corp_code_info cci
        where
            cci.delete_flg = false
            and code_type = 'AGREEMENT_CATEGORY'
        order by cci.jp_code_name
    """
    # TODO: 利用者組織情報取得に後で変更する
    # CODE_INFO = """


    M_BUIDING_GROUP_UPSERT = """
    INSERT INTO db_corp.m_buiding_group(
            corporate_number
			,agreement_category
			,org_id
            ,GROUP_ID
			,GROUP_NAME
			,SELECT_ITEM1
			,SELECT_ITEM2
			,SELECT_ITEM3
			,SELECT_ITEM4
			,SELECT_ITEM5
			,SELECT_ITEM6
			,SELECT_ITEM7
            ,DELETE_FLG
			,CREATED_BY
			,CREATED_AT
			,UPDATED_BY
			,UPDATED_AT
        )
        VALUES (
            '{corporate_number}'
			,'{agreement_category}'
			,'{org_id}'
            ,'{group_id}'
			,'{group_name}'
			,'{select_item1}'
			,'{select_item2}'
			,'{select_item3}'
			,'{select_item4}'
			,'{select_item5}'
			,'{select_item6}'
			,'{select_item7}'
            ,'0'
			,'{created_by}'
			,'{created_at}'
			,'{updated_by}'
			,'{updated_at}'
        )
        ON CONFLICT (corporate_number
			,agreement_category
			,org_id
            ,GROUP_ID)
        DO UPDATE SET
            corporate_number = EXCLUDED.corporate_number
			,agreement_category= EXCLUDED.agreement_category
			,org_id= EXCLUDED.org_id
            ,GROUP_ID= EXCLUDED.GROUP_ID
			,GROUP_NAME= EXCLUDED.GROUP_NAME
			,SELECT_ITEM1= EXCLUDED.SELECT_ITEM1
			,SELECT_ITEM2= EXCLUDED.SELECT_ITEM2
			,SELECT_ITEM3= EXCLUDED.SELECT_ITEM3
			,SELECT_ITEM4= EXCLUDED.SELECT_ITEM4
			,SELECT_ITEM5= EXCLUDED.SELECT_ITEM5
			,SELECT_ITEM6= EXCLUDED.SELECT_ITEM6
			,SELECT_ITEM7= EXCLUDED.SELECT_ITEM7
			,DELETE_FLG= EXCLUDED.DELETE_FLG
			,UPDATED_BY= EXCLUDED.UPDATED_BY
			,UPDATED_AT= EXCLUDED.UPDATED_AT
    """
