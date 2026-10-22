import pandas as pd
from flask import abort
from sqlalchemy import func
from sqlalchemy.orm import scoped_session
from werkzeug.exceptions import HTTPException

import cndx_corp_back.common.constants_colums as constants
import cndx_corp_back.common.log as log
import cndx_corp_back.common.utils as utils
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_benchmark_info_entity import MBenchmarkInfo
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.utils.utils import get_message

# ▼▼▼▼▼▼▼▼▼符号定数群▼▼▼▼▼▼▼▼▼
DOT = constants.SpecialChars.DOT.value
BLANK = constants.SpecialChars.BLANK.value
HYPHEN = constants.SpecialChars.HYPHEN.value
SLASH = constants.SpecialChars.LINUX_PATH_DELIMITER.value

# ▼▼▼▼▼▼▼▼▼識別用文字列群▼▼▼▼▼▼▼▼▼
# "事業所"
OFFICE_STRING = constants.StringOfExcelFile.OFFICE.value
# "入力シート"
INPUT_SHEET_STRING = constants.StringOfExcelFile.INPUT_SHEET.value
# "設定"
SETTING_STRING = constants.StringOfExcelFile.SETTING.value

# log出力用オブジェクト
logger = log.CorpLogger()
# システム操作時タイムスタンプ取得
current_timestamp = utils.get_current_timestamp()
# データ登録処理実行者
creator_name = utils.get_sysuser()
# 発行する建物ID格納用リスト
building_id_list = []
# エラーファイル対象格納リスト
error_filenames = {}


@log.log_writer(logger)
@component
def register_input_data(conn, dfs: dict, logger=None):
    # TDH登録処理
    try:
        # 生データ登録
        basic_df, corporate_df, building_df, energy_df = register_into_tdh(conn, dfs)
        return basic_df, corporate_df, building_df, energy_df

    except HTTPException as e:
        raise e

    except Exception as e:
        logger.error("postegreへの生データ登録が失敗しました。")
        logger.error(e)
        abort(500)


def register_into_tdh(conn_postgre, dfs: dict[pd.DataFrame]):
    """
    TDH HIVE登録
        入力基本情報
        集計情報
        ファイル処理ステータス
    params:
        conn  接続し
        register_df_dic 登録するデータ格納用辞書
    """

    # TDH登録処理
    basic_df, corporate_df, building_df, energy_df = None, None, None, None

    # dfsは辞書なので、それぞれのDataFrameに名前を付与する
    if len(dfs) > 1:

        basic_df = dfs["basic_df"]
        corporate_df = dfs["corporate_df"]
        building_df = dfs["building_df"]
        energy_df = dfs["energy_df"]

    building_df = building_df.rename(
        columns={
            "location_identifier_name": "building_name",
        }
    )
    building_df.columns = building_df.columns.str.upper()
    # 建物情報存在チェック
    building_ids = building_df["BUILDING_ID"].dropna().unique().tolist()

    existing_building_infos = (
        conn_postgre.query(MBuilding)
        .filter(
            MBuilding.building_id.in_(building_ids),
            MBuilding.corporate_number == basic_df["CORPORATE_NUMBER"].iloc[0],
            # MBuilding.agreement_org == basic_df["ORG_ID"].iloc[0],
            MBuilding.agreement_category == basic_df["AGREEMENT_CATEGORY"].iloc[0],
        )
        .all()
    )

    if len(building_ids) != len(existing_building_infos):
        abort(404, description=get_message("NOT_UPDATE", field="建物情報"))

    # SQLAlchemy結果 → DataFrame化
    existing_df = pd.DataFrame(
        [
            {col.name: getattr(row, col.name) for col in MBuilding.__table__.columns}
            for row in existing_building_infos
        ]
    )

    existing_df.columns = existing_df.columns.str.upper()

    # 重複カラムの削除
    cols_to_use = [
        col
        for col in existing_df.columns
        if col not in building_df.columns or col == "BUILDING_ID"
    ]
    # building_df に結合（BUILDING_IDでマージ）
    building_df = building_df.merge(
        existing_df[cols_to_use], on="BUILDING_ID", how="left"
    )

    # postgreへ生データ登録
    insert_input_info_postgre(
        conn_postgre, basic_df, building_df, existing_building_infos
    )

    return basic_df, corporate_df, building_df, energy_df


@utils.check_time
def insert_input_info_postgre(
    conn, basic_df: pd.DataFrame, building_df: pd.DataFrame, existing_building_infos
):
    """
    企業カルテ用生データ
    params:
        sheet_df   処理対象シート情報格納DataFrame
        column_list カラム情報
    return:
        energy_dic  エネルギー情報辞書
    """
    # 入力情報をTDH DWHへ登録する
    try:

        # 他社比較業種マスタ情報取得
        cimst_list = (
            conn.query(
                MBenchmarkInfo.competitor_industry_co2_avg,
                MBenchmarkInfo.energy_saving_denominator,
                # MBenchmarkInfo.industry_class_major_code,
                # MBenchmarkInfo.industry_class_middle_code,
                # MBenchmarkInfo.industry_class_minor_code,
                MBenchmarkInfo.industry_class_detail_code,
                MBenchmarkInfo.target_total_floor_area_min,
                MBenchmarkInfo.target_total_floor_area_max,
                MBenchmarkInfo.total_floor_area_flag,
            )
            .filter(MBenchmarkInfo.delete_flg.isnot(True))
            .all()
        )
        cimst = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in cimst_list
            ],
            dtype=str,
        )
        cimst.columns = cimst.columns.str.upper()

        # 他企業平均業種情報更新
        building_df = get_building_competitor_industry_co2_avg(building_df, cimst)

        # TODO 疎通のため一時的
        # 結合？
        basic_df["LOCATION_IDENTIFIER_NAME"] = None
        basic_df["ZIP_CODE"] = None
        basic_df["MUNICIPALITY_CODE"] = None
        # basic_df["ELECTRICITY_SUPPLIER_NO"] = None
        basic_df["ELECTRICITY_SUPPLIER_NAME"] = None
        # basic_df["ELECTRICITY_CONTRACT_MENU"] = None
        # basic_df["CITY_GAS_SUPPLIER_NO"] = None
        basic_df["CITY_GAS_SUPPLIER_NAME"] = None
        # basic_df["HEAT_SUPPLIER_NO"] = None
        basic_df["HEAT_SUPPLIER_NAME"] = None
        basic_df["HEAT_CONTRACT_MENU"] = None
        basic_df["TARGET_MONTH"] = None
        # basic_df = get_corprate_competitor_industry_co2_avg(basic_df, cimst)
        # basic_df["ENERGY_SAVING_DENOMINATOR"] = None
        basic_df["KPI_TARGET_ENERGY_SAVING_RATE"] = 0
        basic_df["KPI_TARGET_ELECTRIFICATION_RATE"] = 0
        basic_df["KPI_TARGET_ENERGY_CREATION"] = 0
        basic_df["KPI_TARGET_RENEWABLE_NETWORK_RATE"] = 0
        building_df = get_building_competitor_industry_co2_avg(building_df, cimst)

        # 建物情報登録
        # insert_data(conn, building_df, constants.bditbl_columns, None, input_data_table_name_BDITBL)

        m_building_info_insert(conn, building_df, basic_df)

        t_building_info_insert(conn, building_df, basic_df)

        # CN対策実施申込情報
        t_cn_application_info_insert(conn, building_df, basic_df.head(1), cimst)

    except Exception as e:
        logger.error("データ登録が失敗しました。")
        logger.error(e)
        conn.rollback()
        raise e


def m_building_info_insert(session: scoped_session, building_df, basic_df):
    """
    建物情報登録
    """
    for index, row in building_df.iterrows():
        mBuilding = (
            session.query(MBuilding)
            .filter(
                MBuilding.corporate_number == basic_df["CORPORATE_NUMBER"].iloc[0],
                MBuilding.agreement_category == basic_df["AGREEMENT_CATEGORY"].iloc[0],
                MBuilding.building_id == row["BUILDING_ID"],
            )
            .first()
        )

        mBuilding.updated_by = basic_df["CREATED_BY"].iloc[0]
        mBuilding.updated_at = basic_df["CREATED_AT"].iloc[0]

        mBuilding.industry_class_major_code = row[
            "INDUSTRY_CLASS_MAJOR_CODE"
        ]  # 日本標準産業分類（大分類）
        mBuilding.industry_class_middle_code = row[
            "INDUSTRY_CLASS_MIDDLE_CODE"
        ]  # 日本標準産業分類（中分類）
        mBuilding.industry_class_major_name = row[
            "INDUSTRY_CLASS_MAJOR_NAME"
        ]  # 日本標準産業分類名称（大分類）
        mBuilding.industry_class_middle_name = row[
            "INDUSTRY_CLASS_MIDDLE_NAME"
        ]  # 日本標準産業分類名称（中分類）
        mBuilding.industry_class_minor_code = row[
            "INDUSTRY_CLASS_MINOR_CODE"
        ]  # 日本標準産業分類（小分類）
        mBuilding.industry_class_detail_code = row[
            "INDUSTRY_CLASS_DETAIL_CODE"
        ]  # 日本標準産業分類（細分類）
        mBuilding.industry_class_minor_name = row[
            "INDUSTRY_CLASS_MINOR_NAME"
        ]  # 日本標準産業分類名称（小分類）
        mBuilding.industry_class_detail_name = row[
            "INDUSTRY_CLASS_DETAIL_NAME"
        ]  # 日本標準産業分類名称（細分類）
        mBuilding.gross_floor_area = row["GROSS_FLOOR_AREA"]  # 延床面積

    session.add(mBuilding)


def t_building_info_insert(session: scoped_session, building_df, basic_df):
    """
    建物情報登録
    """
    insert_flag = basic_df["INSERT_FLAG"].iloc[0]

    for index, row in building_df.iterrows():

        # フラグで、レコードを作成か照会するのを決める
        if insert_flag:
            tBuilding = TBuildingInfo()

            tBuilding.corporate_number = row["CORPORATE_NUMBER"]  # 法人番号
            tBuilding.agreement_category = row["AGREEMENT_CATEGORY"]  # 同意書取得区分
            tBuilding.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
            tBuilding.building_id = row["BUILDING_ID"]
            tBuilding.fiscal_year = basic_df["FISCAL_YEAR"].iloc[0]  # 年度
            tBuilding.registration_seq = int(
                basic_df["REGISTRATION_SEQ"].iloc[0]
            )  # 登録回数
            tBuilding.created_by = basic_df["CREATED_BY"].iloc[0]
            tBuilding.created_at = basic_df["CREATED_AT"].iloc[0]

        else:
            tBuilding = (
                session.query(TBuildingInfo)
                .filter(
                    TBuildingInfo.corporate_number
                    == basic_df["CORPORATE_NUMBER"].iloc[0],
                    TBuildingInfo.agreement_category
                    == basic_df["AGREEMENT_CATEGORY"].iloc[0],
                    TBuildingInfo.org_id == basic_df["ORG_ID"].iloc[0],
                    TBuildingInfo.building_id == row["BUILDING_ID"],
                    TBuildingInfo.fiscal_year == basic_df["FISCAL_YEAR"].iloc[0],
                    TBuildingInfo.registration_seq
                    == int(basic_df["REGISTRATION_SEQ"].iloc[0]),
                )
                .first()
            )
            tBuilding.updated_by = basic_df["CREATED_BY"].iloc[0]
            tBuilding.updated_at = basic_df["CREATED_AT"].iloc[0]

        tBuilding.entry_draft_flag = basic_df["ENTRY_DRAFT_FLAG"].iloc[
            0
        ]  # 登録下書区分
        tBuilding.location_identifier_name = row["BUILDING_NAME"]  # 拠点名
        # mBuilding.zip_code = row['ZIP_CODE']                                          # 郵便番号
        # mBuilding.municipality_code = row['MUNICIPALITY_CODE']                        # 自治体コード
        tBuilding.address_prefecture = row["BUILDING_ADDRESS_PREFECTURE"]  # 都道府県
        tBuilding.address_city = row["BUILDING_ADDRESS_CITY"]  # 市区町村以降
        tBuilding.industry_class_major_code = row[
            "INDUSTRY_CLASS_MAJOR_CODE"
        ]  # 日本標準産業分類（大分類）
        tBuilding.industry_class_middle_code = row[
            "INDUSTRY_CLASS_MIDDLE_CODE"
        ]  # 日本標準産業分類（中分類）
        tBuilding.industry_class_minor_code = row[
            "INDUSTRY_CLASS_MINOR_CODE"
        ]  # 日本標準産業分類（小分類）
        tBuilding.industry_class_detail_code = row[
            "INDUSTRY_CLASS_DETAIL_CODE"
        ]  # 日本標準産業分類（細分類）
        tBuilding.industry_class_major_name = row[
            "INDUSTRY_CLASS_MAJOR_NAME"
        ]  # 日本標準産業分類名称（大分類）
        tBuilding.industry_class_middle_name = row[
            "INDUSTRY_CLASS_MIDDLE_NAME"
        ]  # 日本標準産業分類名称（中分類）
        tBuilding.industry_class_minor_name = row[
            "INDUSTRY_CLASS_MINOR_NAME"
        ]  # 日本標準産業分類名称（小分類）
        tBuilding.industry_class_detail_name = row[
            "INDUSTRY_CLASS_DETAIL_NAME"
        ]  # 日本標準産業分類名称（細分類）
        # mBuilding.energy_benchmark_target_industry = row['org_id']                  # 省エネ法ベンチマーク対象業種
        # mBuilding.energy_benchmark_indicator = row['org_id']                        # 省エネ法ベンチマーク指標
        # mBuilding.energy_benchmark_year = row['org_id']                             # 省エネ法ベンチマーク指標年度
        tBuilding.gross_floor_area = row["GROSS_FLOOR_AREA"]  # 延床面積
        tBuilding.competitor_industry_co2_avg = row[
            "COMPETITOR_INDUSTRY_CO2_AVG"
        ]  # 他社比較業種_CO2排出源単位平均値
        tBuilding.energy_saving_denominator = row[
            "ENERGY_SAVING_DENOMINATOR"
        ]  # ベンチマーク指標
        tBuilding.electricity_supplier_no = row[
            "ELECTRICITY_SUPPLIER_NO"
        ]  # 契約先電気事業者登録番号
        tBuilding.electricity_supplier_name = row[
            "ELECTRICITY_SUPPLIER_NAME"
        ]  # 契約先電気事業者
        tBuilding.electricity_contract_menu = row[
            "ELECTRICITY_CONTRACT_MENU"
        ]  # 契約先電力メニュー
        tBuilding.ep_office_code = row["EP_OFFICE_CODE"]  # EP事業所コード
        tBuilding.ep_customer_number = row["EP_CUSTOMER_NUMBER"]  # EPお客さま番号
        tBuilding.supply_point_number = row["SUPPLY_POINT_NUMBER"]  # 供給地点特定番号
        tBuilding.city_gas_supplier_no = row[
            "CITY_GAS_SUPPLIER_NO"
        ]  # 契約先都市ガス供給事業者登録番号
        tBuilding.city_gas_supplier_name = row[
            "CITY_GAS_SUPPLIER_NAME"
        ]  # 契約先都市ガス供給事業者
        tBuilding.heat_supplier_no = row[
            "HEAT_SUPPLIER_NO"
        ]  # 契約先熱供給事業者登録番号
        tBuilding.heat_supplier_name = row["HEAT_SUPPLIER_NAME"]  # 契約先熱供給事業者
        # mBuilding.heat_contract_menu = row['ORG_ID']                                  # 契約先熱メニュー
        tBuilding.delete_flg = False  # 削除フラグ

        session.add(tBuilding)


def t_cn_application_info_insert(session: scoped_session, building_df, basic_df, cimst):
    """
    CN対策実施申込情報登録
    """
    insert_flag = basic_df["INSERT_FLAG"].iloc[0]
    office_count = int(len(building_df))

    with get_scoped_session() as session:
        stmt = session.query(
            MCorporateDetailsInfo.industry_class_minor_code,
            MCorporateDetailsInfo.industry_class_detail_code,
            MCorporateDetailsInfo.industry_class_minor_name,
            MCorporateDetailsInfo.industry_class_detail_name,
        ).where(
            MCorporateDetailsInfo.corporate_number
            == basic_df["CORPORATE_NUMBER"].iloc[0],
            MCorporateDetailsInfo.agreement_category
            == basic_df["AGREEMENT_CATEGORY"].iloc[0],
            MCorporateDetailsInfo.delete_flg.is_not(True),
        )
        rows = session.execute(stmt).mappings().all()

    rows_mCorporateDetailsInfo = pd.DataFrame(rows)

    # フラグで、レコードを作成か照会するのを決める
    # for index, row in building_df.iterrows():
    if insert_flag:
        tCnApp = TCnApplicationInfo()

        # 新規の場合のみ必要なカラム
        tCnApp.corporate_number = basic_df["CORPORATE_NUMBER"].iloc[0]  # 法人番号
        tCnApp.agreement_category = basic_df["AGREEMENT_CATEGORY"].iloc[
            0
        ]  # 同意書取得区分
        tCnApp.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tCnApp.fiscal_year = basic_df["FISCAL_YEAR"].iloc[0]  # 年度
        tCnApp.registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])  # 登録回数
        tCnApp.industry_class_minor_code = rows_mCorporateDetailsInfo[
            "industry_class_minor_code"
        ].iloc[
            0
        ]  # 日本標準産業分類（小分類）
        tCnApp.industry_class_detail_code = rows_mCorporateDetailsInfo[
            "industry_class_detail_code"
        ].iloc[
            0
        ]  # 日本標準産業分類（細分類）
        tCnApp.industry_class_minor_name = rows_mCorporateDetailsInfo[
            "industry_class_minor_name"
        ].iloc[
            0
        ]  # 日本標準産業分類名称（小分類）
        tCnApp.industry_class_detail_name = rows_mCorporateDetailsInfo[
            "industry_class_detail_name"
        ].iloc[
            0
        ]  # 日本標準産業分類名称（細分類）

        tCnApp.created_by = basic_df["CREATED_BY"].iloc[0]

    else:
        tCnApp = (
            session.query(TCnApplicationInfo)
            .filter(
                TCnApplicationInfo.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],
                TCnApplicationInfo.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],
                TCnApplicationInfo.org_id == basic_df["ORG_ID"].iloc[0],
                TCnApplicationInfo.fiscal_year == basic_df["FISCAL_YEAR"].iloc[0],
                TCnApplicationInfo.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),
            )
            .first()
        )
        # 更新の場合のみ必要なカラム
        tCnApp.updated_by = basic_df["CREATED_BY"].iloc[0]
        old_entry_draft_flag = tCnApp.entry_draft_flag

    tCnApp.company_name = basic_df["COMPANY_NAME"].iloc[0]
    tCnApp.ghg_system_company_name = basic_df["GHG_SYSTEM_COMPANY_NAME"].iloc[0]
    tCnApp.entry_draft_flag = basic_df["ENTRY_DRAFT_FLAG"].iloc[0]  # 登録下書区分
    tCnApp.industry_class_major_code = basic_df["INDUSTRY_CLASS_MAJOR_CODE"].iloc[
        0
    ]  # 日本標準産業分類（大分類）
    tCnApp.industry_class_middle_code = basic_df["INDUSTRY_CLASS_MIDDLE_CODE"].iloc[
        0
    ]  # 日本標準産業分類（中分類）
    tCnApp.industry_class_major_name = basic_df["INDUSTRY_CLASS_MAJOR_NAME"].iloc[
        0
    ]  # 日本標準産業分類名称（大分類）
    tCnApp.industry_class_middle_name = basic_df["INDUSTRY_CLASS_MIDDLE_NAME"].iloc[
        0
    ]  # 日本標準産業分類名称（中分類）
    tCnApp.industry_class_minor_code = rows_mCorporateDetailsInfo[
        "industry_class_minor_code"
    ].iloc[
        0
    ]  # 日本標準産業分類（小分類）
    tCnApp.industry_class_detail_code = rows_mCorporateDetailsInfo[
        "industry_class_detail_code"
    ].iloc[
        0
    ]  # 日本標準産業分類（細分類）
    tCnApp.industry_class_minor_name = rows_mCorporateDetailsInfo[
        "industry_class_minor_name"
    ].iloc[
        0
    ]  # 日本標準産業分類名称（小分類）
    tCnApp.industry_class_detail_name = rows_mCorporateDetailsInfo[
        "industry_class_detail_name"
    ].iloc[
        0
    ]  # 日本標準産業分類名称（細分類）
    tCnApp.business_office_count = office_count
    tCnApp.energy_benchmark_target_industry = basic_df[
        "ENERGY_BENCHMARK_TARGET_INDUSTRY"
    ].iloc[0]
    tCnApp.energy_benchmark_indicator = basic_df["ENERGY_BENCHMARK_INDICATOR"].iloc[0]
    tCnApp.energy_benchmark_year = basic_df["ENERGY_BENCHMARK_YEAR"].iloc[0]
    tCnApp.address_prefecture = basic_df["ADDRESS_PREFECTURE"].iloc[0]  # 都道府県
    tCnApp.address_city = basic_df["ADDRESS_CITY"].iloc[0]  # 市区町村以降
    tCnApp.report_period_start_year_month = basic_df[
        "REPORT_PERIOD_START_YEAR_MONTH"
    ].iloc[0]
    tCnApp.report_period_end_year_month = basic_df["REPORT_PERIOD_END_YEAR_MONTH"].iloc[
        0
    ]
    # tCnApp.competitor_industry_co2_avg = float(basic_df['COMPETITOR_INDUSTRY_CO2_AVG'].iloc[0])
    # tCnApp.energy_saving_denominator = float(basic_df['ENERGY_SAVING_DENOMINATOR'].iloc[0])
    tCnApp.kpi_target_energy_saving_rate = float(
        basic_df["KPI_TARGET_ENERGY_SAVING_RATE"].iloc[0]
    )
    tCnApp.kpi_target_electrification_rate = float(
        basic_df["KPI_TARGET_ELECTRIFICATION_RATE"].iloc[0]
    )
    tCnApp.kpi_target_energy_creation = float(
        basic_df["KPI_TARGET_ENERGY_CREATION"].iloc[0]
    )
    tCnApp.kpi_target_renewable_network_rate = float(
        basic_df["KPI_TARGET_RENEWABLE_NETWORK_RATE"].iloc[0]
    )
    tCnApp.delete_flg = False  # 削除フラグ
    expunge_flg = True

    for index, row in building_df.iterrows():
        if insert_flag:
            tCnApp.industry_class_minor_code = rows_mCorporateDetailsInfo[
                "industry_class_minor_code"
            ].iloc[
                0
            ]  # 日本標準産業分類（小分類）
            tCnApp.industry_class_detail_code = rows_mCorporateDetailsInfo[
                "industry_class_detail_code"
            ].iloc[
                0
            ]  # 日本標準産業分類（細分類）
            tCnApp.industry_class_minor_name = rows_mCorporateDetailsInfo[
                "industry_class_minor_name"
            ].iloc[
                0
            ]  # 日本標準産業分類名称（小分類）
            tCnApp.industry_class_detail_name = rows_mCorporateDetailsInfo[
                "industry_class_detail_name"
            ].iloc[
                0
            ]  # 日本標準産業分類名称（細分類）
            session.add(tCnApp)
        else:
            if (
                tCnApp.entry_draft_flag == "0"
                and expunge_flg
                and old_entry_draft_flag == "0"
            ):
                expunge_flg = False
                session.expunge(tCnApp)
            else:
                tCnApp.industry_class_minor_code = rows_mCorporateDetailsInfo[
                    "industry_class_minor_code"
                ].iloc[
                    0
                ]  # 日本標準産業分類（小分類）
                tCnApp.industry_class_detail_code = rows_mCorporateDetailsInfo[
                    "industry_class_detail_code"
                ].iloc[
                    0
                ]  # 日本標準産業分類（細分類）
                tCnApp.industry_class_minor_name = rows_mCorporateDetailsInfo[
                    "industry_class_minor_name"
                ].iloc[
                    0
                ]  # 日本標準産業分類名称（小分類）
                tCnApp.industry_class_detail_name = rows_mCorporateDetailsInfo[
                    "industry_class_detail_name"
                ].iloc[
                    0
                ]  # 日本標準産業分類名称（細分類）

    basic_df = get_corprate_competitor_industry_co2_avg(
        basic_df, cimst, rows_mCorporateDetailsInfo
    )
    tCnApp.competitor_industry_co2_avg = float(
        basic_df["COMPETITOR_INDUSTRY_CO2_AVG"].iloc[0]
    )
    tCnApp.energy_saving_denominator = float(
        basic_df["ENERGY_SAVING_DENOMINATOR"].iloc[0]
    )


def registration_seq(conn, basic_df):
    """
    登録回数取得
    """
    # result_df = select_data(conn, condition_list, None, "DB_CORP.T_CN_APPLICATION_INFO")
    max_registration_seq = (
        conn.query(func.max(TCnApplicationInfo.registration_seq))
        .filter(
            TCnApplicationInfo.fiscal_year == basic_df["FISCAL_YEAR"].iloc[0],
            TCnApplicationInfo.corporate_number == basic_df["CORPORATE_NUMBER"].iloc[0],
            # TCnApplicationInfo.org_id == basic_df["ORG_ID"].iloc[0],
            TCnApplicationInfo.agreement_category
            == basic_df["AGREEMENT_CATEGORY"].iloc[0],
        )
        .all()
    )

    insert_registration_seq = None
    if not max_registration_seq or max_registration_seq[0][0] is None:
        insert_registration_seq = 1
    else:
        insert_registration_seq = max_registration_seq[0][0] + 1
    # 年度のインデスク取得
    col_index = basic_df.columns.get_loc("FISCAL_YEAR")
    # 登録回数の項目と値の差込
    basic_df.insert(col_index + 1, "REGISTRATION_SEQ", insert_registration_seq)


def get_corprate_competitor_industry_co2_avg(
    basic_df, cimst, rows_mCorporateDetailsInfo
):
    """
    企業業種平均CO2排出量原単位情報取得
    """
    cimst_sub = cimst[
        (
            cimst["INDUSTRY_CLASS_DETAIL_CODE"]
            == rows_mCorporateDetailsInfo["industry_class_detail_code"].iloc[0]
        )
        & (cimst["TOTAL_FLOOR_AREA_FLAG"] == "0")
    ]

    basic_df = basic_df.assign(
        COMPETITOR_INDUSTRY_CO2_AVG=0, ENERGY_SAVING_DENOMINATOR=0
    )

    if not cimst_sub.empty:
        # 企業単位の他社比較業種_CO2排出源単位平均値と省エネ率分母設定
        basic_df["COMPETITOR_INDUSTRY_CO2_AVG"] = (
            cimst_sub["COMPETITOR_INDUSTRY_CO2_AVG"].fillna(0).iloc[0]
        )
        basic_df["ENERGY_SAVING_DENOMINATOR"] = (
            cimst_sub["ENERGY_SAVING_DENOMINATOR"].fillna(0).iloc[0]
        )

    return basic_df


def get_building_competitor_industry_co2_avg(building_df, cimst):
    """
    拠点業種平均CO2排出量原単位情報取得
    """
    # 可視化ヒアリングシート情報事前登録の場合
    industry_class_code = ""

    for index, buildingRowData in building_df.iterrows():

        # industry_class_code = ""
        # #省エネ法ベンチマーク対象業種取得
        # if 'ENERGY_BENCHMARK_TARGET_INDUSTRY' in building_df.columns:
        #     industry_class_code = buildingRowData["ENERGY_BENCHMARK_TARGET_INDUSTRY"]

        # 省エネ法ベンチマーク対象業種空ではない場合
        buildingRowData = set_competitor_industry_info(
            buildingRowData, cimst, buildingRowData["INDUSTRY_CLASS_DETAIL_CODE"]
        )

        competitor_industry_co2_avg = buildingRowData["COMPETITOR_INDUSTRY_CO2_AVG"]
        energy_saving_denominator = buildingRowData["ENERGY_SAVING_DENOMINATOR"]

        building_df.at[index, "ENERGY_SAVING_DENOMINATOR"] = energy_saving_denominator
        building_df.at[index, "COMPETITOR_INDUSTRY_CO2_AVG"] = (
            competitor_industry_co2_avg
        )

    return building_df


def set_competitor_industry_info(buildingRowData, cimst, industry_class_detail_code):
    """
    CO2排出源単位平均値と省エネ率分母取得
    params:
        buildingRowData   拠点情報
        cimst 他社比較業種マスタ
        industry_class_major_code　大分類
        industry_class_middle_code　中分類
        industry_class_minor_code　小分類
        industry_class_detail_code　細分類
    return:
        無し
    """
    cimst_sub = cimst[
        (cimst["INDUSTRY_CLASS_DETAIL_CODE"] == industry_class_detail_code)
    ]

    # デフォルト値設定
    buildingRowData["COMPETITOR_INDUSTRY_CO2_AVG"] = "0"
    buildingRowData["ENERGY_SAVING_DENOMINATOR"] = "0"

    # 平均業種マスタに情報ない場合
    if cimst_sub.empty:
        return buildingRowData

    # 延床面積別フラグは1がある場合
    cimst_sub_1 = cimst_sub[
        (cimst_sub["TOTAL_FLOOR_AREA_FLAG"] == "1")
        & (
            cimst_sub["TARGET_TOTAL_FLOOR_AREA_MIN"]
            >= str(buildingRowData["GROSS_FLOOR_AREA"])
        )
        & (
            cimst_sub["TARGET_TOTAL_FLOOR_AREA_MAX"]
            <= str(buildingRowData["GROSS_FLOOR_AREA"])
        )
    ]

    cimst_sub_0 = cimst_sub[cimst_sub["TOTAL_FLOOR_AREA_FLAG"] == "0"]

    # 面積フラグ0がある場合、先に設定
    if not cimst_sub_0.empty:

        buildingRowData["COMPETITOR_INDUSTRY_CO2_AVG"] = cimst_sub_0[
            "COMPETITOR_INDUSTRY_CO2_AVG"
        ].iloc[0]
        buildingRowData["ENERGY_SAVING_DENOMINATOR"] = cimst_sub_0[
            "ENERGY_SAVING_DENOMINATOR"
        ].iloc[0]

    # 面積フラグ1がある場合、優先設定
    if not cimst_sub_1.empty:
        buildingRowData["COMPETITOR_INDUSTRY_CO2_AVG"] = cimst_sub_1[
            "COMPETITOR_INDUSTRY_CO2_AVG"
        ].iloc[0]
        buildingRowData["ENERGY_SAVING_DENOMINATOR"] = cimst_sub_1[
            "ENERGY_SAVING_DENOMINATOR"
        ].iloc[0]

    return buildingRowData
