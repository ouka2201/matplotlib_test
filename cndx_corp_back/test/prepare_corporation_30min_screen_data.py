"""お客さま企業マスタ照会・編集画面からAPI-04の30分値同期を試すデータを準備する。"""

import argparse
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import MetaData, Table, create_engine, func, select


MARKER = "UT_API04_30MIN"
SCHEMA = "db_corp"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    parser.add_argument("--corp-number", required=True, help="未登録の13桁法人番号")
    parser.add_argument("--supply-point", required=True, help="未登録の22桁供給地点特定番号")
    parser.add_argument("--consent-org-id", required=True, help="区分01で選ぶ金融機関の組織ID")
    parser.add_argument("--acquisition-date", default=today.strftime("%Y%m%d"), help="EPの取得日（YYYYMMDD）")
    parser.add_argument("--prefecture-code", default="13", help="企業・拠点の都道府県コード")
    parser.add_argument("--ep-office-code", default="123", help="EP事業所コード（3桁）")
    parser.add_argument("--ep-customer-number", default="0000000000123", help="EPお客さま番号（13桁）")
    parser.add_argument("--new-office", action="store_true", help="拠点を作らず、画面から新規追加する")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="検証DBに投入する")
    action.add_argument("--cleanup", action="store_true", help="このPG用の企業と関連行を削除する")
    action.add_argument("--verify", action="store_true", help="投入・画面保存後の登録条件を確認する（読取専用）")
    args = parser.parse_args(argv)
    for key, length in (("corp_number", 13), ("supply_point", 22),
                        ("ep_office_code", 3), ("ep_customer_number", 13)):
        value = getattr(args, key)
        if len(value) != length or not value.isascii() or not value.isdigit():
            parser.error(f"--{key.replace('_', '-')} は{length}桁の数字を指定してください")
    if not args.consent_org_id or len(args.consent_org_id) > 20 or args.consent_org_id == "TEP":
        parser.error("--consent-org-id はTEP以外の20文字以内の組織IDにしてください")
    try:
        day = datetime.strptime(args.acquisition_date, "%Y%m%d").date()
    except ValueError:
        parser.error("--acquisition-date は実在する日付をYYYYMMDDで指定してください")
    try:
        five_years_ago = today.replace(year=today.year - 5)
    except ValueError:
        five_years_ago = date(today.year - 5, 2, 28)
    if day.strftime("%Y%m%d") != args.acquisition_date or not five_years_ago <= day <= today:
        parser.error("--acquisition-date は直近5年以内の実在する日付にしてください")
    if len(args.prefecture_code) != 2 or not args.prefecture_code.isdigit():
        parser.error("--prefecture-code は2桁の数字にしてください")
    return args


def _tables(connection):
    metadata = MetaData()
    names = (
        "m_corporate_basic", "m_corporate_details_info", "m_user_organization_info",
        "m_building", "t_ep_electricity_data_30min", "t_arve_customer_info",
        "t_electricity_data_30min",
    )
    tables = {name: Table(name, metadata, schema=SCHEMA, autoload_with=connection) for name in names}
    tables["prefecture_mst"] = Table("prefecture_mst", metadata, schema="db_common", autoload_with=connection)
    return tables


def _one(connection, table, **key):
    return connection.execute(
        select(table).where(*(table.c[name] == value for name, value in key.items()))
    ).mappings().first()


def _insert(connection, table, values):
    missing = set(values) - set(table.c.keys())
    if missing:
        raise ValueError(f"{table.name} に必要な列がありません: {sorted(missing)}")
    connection.execute(table.insert().values(**values))


def _source_values(table, values):
    if "created_by" in table.c:
        values["created_by"] = MARKER
    if "created_at" in table.c:
        values["created_at"] = datetime.now()
    return values


def _check_available(connection, tables, args):
    if _one(connection, tables["prefecture_mst"], pref_cd=args.prefecture_code) is None:
        raise ValueError("指定した都道府県コードが共通マスタにありません")
    if _one(connection, tables["m_corporate_basic"], corporate_number=args.corp_number):
        raise ValueError("法人番号は登録済みです。別の試験用法人番号を指定してください")
    for name, column in (("t_ep_electricity_data_30min", "t01_kyo_ctn_tok_no"),
                         ("t_arve_customer_info", "cmn_supplypointspecificnum__c"),
                         ("m_building", "supply_point_number"),
                         ("t_electricity_data_30min", "supply_point_number")):
        if _one(connection, tables[name], **{column: args.supply_point}):
            raise ValueError(f"{name} に供給地点特定番号が既にあります。別の番号を指定してください")
    consent = _one(connection, tables["m_user_organization_info"], org_id=args.consent_org_id)
    if consent and (consent["business_type"] != "金融機関" or consent["delete_flg"] is not False):
        raise ValueError("同意書取得組織は区分01で選択できる有効な金融機関にしてください")
    tep = _one(connection, tables["m_user_organization_info"], org_id="TEP")
    if tep and tep["delete_flg"] is not False:
        raise ValueError("組織TEPが削除扱いです")
    return consent is None, tep is None


def _prepare(connection, tables, args, new_consent, new_tep):
    audit = {"delete_flg": False, "created_by": MARKER, "created_at": datetime.now()}
    org = tables["m_user_organization_info"]
    if new_tep:
        _insert(connection, org, {"org_id": "TEP", "org_name": "30分値試験用EP",
                                  "org_type_code": "01", "org_type": "EP",
                                  "business_type": "EP", **audit})
    if new_consent:
        _insert(connection, org, {"org_id": args.consent_org_id,
                                  "org_name": "30分値試験用金融機関",
                                  "org_type_code": "02", "org_type": "金融機関",
                                  "business_type": "金融機関", **audit})
    _insert(connection, tables["m_corporate_basic"], {
        "corporate_number": args.corp_number, "company_name": "30分値同期試験企業",
        "company_name_kana": "サンジュップンチドウキシケンキギョウ",
        "company_address_prefecture": args.prefecture_code,
        "company_address_city": "千代田区千代田1-1", **audit,
    })
    _insert(connection, tables["m_corporate_details_info"], {
        "corporate_number": args.corp_number, "agreement_category": "01",
        "org_id": "TEP", "business_office_count": 0 if args.new_office else 1, **audit,
    })
    if not args.new_office:
        _insert(connection, tables["m_building"], {
            "corporate_number": args.corp_number, "agreement_category": "01",
            "org_id": "TEP", "building_id": args.corp_number + "000001",
            "location_identifier_name": "30分値試験拠点", "building_name": "30分値試験拠点",
            "building_address_prefecture": args.prefecture_code,
            "building_address_city": "千代田区千代田1-1",
            "agreement_org": args.consent_org_id,
            "ep_office_code": args.ep_office_code,
            "ep_customer_number": args.ep_customer_number,
            "supply_point_number": None, **audit,
        })
    ep_values = {
        "t01_kyo_ctn_tok_no": args.supply_point, "t01_get_ymd": args.acquisition_date,
        "t01_kskj_ksu": "2", "t01_fsij_ksu": "3",
        **{f"t01_30t_syr{i:02d}": f"{i}.125" for i in range(1, 49)},
    }
    _insert(connection, tables["t_ep_electricity_data_30min"],
            _source_values(tables["t_ep_electricity_data_30min"], ep_values))
    _insert(connection, tables["t_arve_customer_info"],
            _source_values(tables["t_arve_customer_info"], {
                "cmn_supplypointspecificnum__c": args.supply_point,
                "cmn_kigyoid_fk__c": args.corp_number,
                "cmn_demandlocationfullname_ref__c": "30分値試験ARVE企業",
                "cmn_oldcustomernum__c": args.ep_office_code + args.ep_customer_number,
            }))


def _cleanup(connection, tables, args):
    basic = _one(connection, tables["m_corporate_basic"], corporate_number=args.corp_number)
    if basic is None:
        return "対象の試験用企業はありません"
    if basic["created_by"] != MARKER:
        raise ValueError("このPGが作成した企業ではないため削除できません")
    arve = tables["t_arve_customer_info"]
    source = _one(connection, arve, cmn_supplypointspecificnum__c=args.supply_point)
    if source is None or source["cmn_kigyoid_fk__c"] != args.corp_number:
        raise ValueError("企業と供給地点特定番号の対応が一致しません。削除前に確認してください")
    building = tables["m_building"]
    buildings = connection.execute(select(building).where(
        building.c.corporate_number == args.corp_number
    )).mappings().all()
    if len(buildings) > 1 or any(
           row["building_id"] != args.corp_number + "000001"
           or row["agreement_category"] != "01" or row["org_id"] != "TEP"
           or row["agreement_org"] != args.consent_org_id
           or row["supply_point_number"] not in (None, args.supply_point)
           for row in buildings):
        raise ValueError("試験用企業に想定外の拠点があります。削除前に確認してください")
    details = tables["m_corporate_details_info"]
    detail_rows = connection.execute(select(details).where(
        details.c.corporate_number == args.corp_number
    )).mappings().all()
    if (len(detail_rows) != 1 or detail_rows[0]["agreement_category"] != "01"
            or detail_rows[0]["org_id"] != "TEP"):
        raise ValueError("試験用企業に想定外の企業詳細があります。削除前に確認してください")
    raw = tables["t_electricity_data_30min"]
    if connection.execute(select(raw).where(
        raw.c.corp_number == args.corp_number,
        (raw.c.supply_point_number != args.supply_point)
        | raw.c.supply_point_number.is_(None),
    )).first():
        raise ValueError("試験用企業に想定外の30分値があります。削除前に確認してください")
    if connection.execute(select(building).where(
        building.c.corporate_number != args.corp_number,
        building.c.supply_point_number == args.supply_point,
    )).first() or connection.execute(select(raw).where(
        raw.c.corp_number != args.corp_number,
        raw.c.supply_point_number == args.supply_point,
    )).first():
        raise ValueError("供給地点特定番号が別の企業でも使われています。削除前に確認してください")
    connection.execute(raw.delete().where(raw.c.corp_number == args.corp_number,
                                          raw.c.supply_point_number == args.supply_point))
    connection.execute(building.delete().where(building.c.corporate_number == args.corp_number))
    connection.execute(details.delete().where(details.c.corporate_number == args.corp_number))
    ep = tables["t_ep_electricity_data_30min"]
    connection.execute(ep.delete().where(ep.c.t01_kyo_ctn_tok_no == args.supply_point))
    connection.execute(arve.delete().where(arve.c.cmn_supplypointspecificnum__c == args.supply_point))
    connection.execute(tables["m_corporate_basic"].delete().where(
        tables["m_corporate_basic"].c.corporate_number == args.corp_number))
    org = tables["m_user_organization_info"]
    for org_id in (args.consent_org_id, "TEP"):
        connection.execute(org.delete().where(org.c.org_id == org_id, org.c.created_by == MARKER))
    return "試験用企業と関連行を削除しました"


def _verify(connection, tables, args):
    basic = tables["m_corporate_basic"]
    building = tables["m_building"]
    ep = tables["t_ep_electricity_data_30min"]
    arve = tables["t_arve_customer_info"]
    raw = tables["t_electricity_data_30min"]
    corp = _one(connection, basic, corporate_number=args.corp_number)
    office = _one(connection, building, corporate_number=args.corp_number,
                  building_id=args.corp_number + "000001")
    ep_count = connection.execute(select(func.count()).select_from(ep).where(
        ep.c.t01_kyo_ctn_tok_no == args.supply_point
    )).scalar_one()
    arve_count = connection.execute(select(func.count()).select_from(arve).where(
        arve.c.cmn_supplypointspecificnum__c == args.supply_point
    )).scalar_one()
    joined = building.join(basic, basic.c.corporate_number == building.c.corporate_number)
    joined = joined.join(ep, ep.c.t01_kyo_ctn_tok_no == building.c.supply_point_number)
    joined = joined.join(arve, arve.c.cmn_supplypointspecificnum__c == building.c.supply_point_number)
    match_count = connection.execute(select(func.count()).select_from(joined).where(
        building.c.corporate_number == args.corp_number,
        building.c.building_id == args.corp_number + "000001",
        building.c.agreement_category == "01", building.c.org_id == "TEP",
        building.c.delete_flg.is_(False),
    )).scalar_one()
    raw_count = connection.execute(select(func.count()).select_from(raw).where(
        raw.c.corp_number == args.corp_number,
        raw.c.building_id == args.corp_number + "000001",
        raw.c.supply_point_number == args.supply_point,
    )).scalar_one()
    if corp is None:
        status = "企業が見つかりません。PGを投入したDBを確認してください。"
    elif office is None:
        status = "拠点がありません。--new-officeを使った場合は画面から拠点を追加してください。"
    elif office["supply_point_number"] != args.supply_point:
        status = "拠点の供給地点特定番号が未設定または不一致です。画面で保存した値を確認してください。"
    elif raw_count:
        status = "30分値が登録されています。"
    elif match_count == 0:
        status = "APIの登録SQLで結合できる行がありません。拠点の有効状態とEP・ARVEの元データを確認してください。"
    else:
        status = ("登録条件はそろっています。画面の保存応答と、稼働中バックエンドのAPI-04実装・"
                  "接続先DBを確認してください。同じ供給地点番号を再保存しても同期は再実行されません。")
    return (f"企業基本={'あり' if corp else 'なし'}、"
            f"拠点の供給地点={office['supply_point_number'] if office else '拠点なし'}、"
            f"EP={ep_count}行、ARVE={arve_count}行、"
            f"登録対象の結合結果={match_count}行、30分値={raw_count}行\n判定: {status}")


def run(args, engine):
    with engine.begin() as connection:
        tables = _tables(connection)
        if args.verify:
            return (f"接続先: {engine.url.host or 'local'}/{engine.url.database or ''}\n"
                    + _verify(connection, tables, args))
        if args.cleanup:
            return _cleanup(connection, tables, args)
        new_consent, new_tep = _check_available(connection, tables, args)
        summary = (f"法人番号={args.corp_number}、供給地点特定番号={args.supply_point}、"
                   f"取得日={args.acquisition_date}、画面操作={'拠点を新規追加' if args.new_office else '既存拠点の供給地点を入力'}")
        if not args.apply:
            return "確認のみ（DB変更なし）: " + summary
        _prepare(connection, tables, args, new_consent, new_tep)
        return ("準備完了（30分値は未登録）: " + summary
                + "。画面で拠点を保存した後、--verifyで結果を確認してください")


def main(argv=None):
    args = parse_args(argv)
    url = os.getenv(args.database_url_env)
    if not url:
        raise SystemExit(f"環境変数 {args.database_url_env} に検証DBのURLを設定してください")
    engine = create_engine(url)
    try:
        print(run(args, engine))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
