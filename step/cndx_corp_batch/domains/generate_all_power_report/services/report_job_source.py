"""管理テーブルの作成対象・状態と、ARVEの契約情報を取得する。"""

# 管理テーブルの主キーは「供給地点特定番号＋対象年月」。
MANAGEMENT_POINT = "supply_point_number"
MANAGEMENT_MONTH = "target_year_month"
STATUS = "create_status"
CUSTOMER_POINT = "cmn_supplypointspecificnum__c"
CUSTOMER_COLUMNS = {
    "customer_number": "cmn_oldcustomernum__c",
    "address": "cmn_demandlocationaddress__c",
}


def customer_column_mapping(table, settings):
    """ARVEの名義・住所・お客さま番号の物理列名を共通で解決する。

    Args:
        table (sqlalchemy.Table): 反映済みのARVEテーブル。
        settings (dict): customer_columnsの任意指定を持つDB設定。

    Returns:
        dict: 帳票の項目名から物理列名への対応。

    Raises:
        ValueError: 名義列を一意に特定できない場合。
    """
    mapping = {**CUSTOMER_COLUMNS, **settings.get("customer_columns", {})}
    if not mapping.get("customer_name"):
        matches = [
            column.name
            for column in table.c
            if column.name.upper().startswith("CMN_DEMANDLOCATIONFULLNAME_")
        ]
        if len(matches) != 1:
            raise ValueError(
                "customer_columns.customer_nameに名義の物理列名を指定してください"
            )
        mapping["customer_name"] = matches[0]
    return mapping
