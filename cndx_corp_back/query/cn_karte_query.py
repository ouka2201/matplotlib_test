from enum import Enum


class CnKarteQuery(Enum):
    """
    CNカルテ作成用
    """
    

    VIS_QUERY = """
        SELECT * 
        FROM db_corp.v_corporate_profile_report_bnk 
        WHERE 
            組織ID = '{org_id}' 
            AND 法人番号 = '{corporate_number}' 
            AND 同意書取得区分 = '{agreement_category}' 
            AND 年度 = '{fisial_year}' 
            AND 登録回数 = {registration_seq}
    """

    VIS_QUERY = VIS_QUERY + """
            AND CAST(エネルギー年月 AS INT) >= {start_year_month}
            AND CAST(エネルギー年月 AS INT) <= {end_year_month}
    """
