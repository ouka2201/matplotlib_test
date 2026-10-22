import datetime
import getpass
import json
import os
import re
import subprocess
import sys
import time
from importlib.metadata import distribution
from io import BytesIO

import pandas as pd
import pytz
from flask import abort

import cndx_corp_back.common.constants_colums as constants
import cndx_corp_back.common.log as log

# プロジェクトの親ディレクトリをsys.pathに追加する
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
logger = log.CorpLogger()


def get_process_time(start_time, end_time, process_name):
    # 経過時間（秒単位）を計算
    elapsed_time = end_time - start_time

    # 時、分、秒に変換
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = elapsed_time % 60

    print(f"{process_name}の処理時間: {hours}時間 {minutes}分 {seconds:.2f}秒")


def check_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(get_process_time(start_time, end_time, func.__name__))
        return result

    return wrapper


def install_package_bk(package_name):
    # config = get_json_config()
    # proxyURL = config["k8s"]["proxyURL"]
    subprocess.check_call(["pip", "install", package_name])
    # subprocess.check_call(['pip', 'install', '--proxy', proxyURL, package_name])
    # local_dir = os.path.join(get_project_root_path(), "library")
    # package_name = f"{package_name}=={{}}".format(version)
    # command = ["pip", "install", "--no-index", f"--find-links={local_dir}", package_name]
    # subprocess.check_call(command)


@log.log_writer(logger)
def install_package(package_name):
    """
    指定されたPythonパッケージが既にインストールされているかをチェックし、インストールされていない場合はインストールを試みます。

    パラメータ:
        package_name (str): チェックおよびインストールが必要なパッケージ名。

    戻り値:
        None
    """
    try:
        # パッケージがインストールされているかどうかを確認するためにインポートを試みます
        dist = distribution(package_name)
        logger.info(
            f"{package_name} は既にインストールされています。バージョン: {dist.version}"
        )
    except Exception:
        # パッケージがインストールされていないため、pipを使ってインストールを試みます
        logger.info(
            f"{package_name} はインストールされていません。インストールを試みます..."
        )
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name]
            )
            logger.info(f"{package_name} のインストールが成功しました。")
        except Exception as e:
            logger.error(f"{package_name} のインストール中にエラーが発生しました：{e}")


@log.log_writer(logger)
def check_library():
    command = ["pip", "list"]
    subprocess.check_call(command)
    command = ["pip", "check"]
    subprocess.check_call(command)
    command = ["pip", "show", "thrift"]
    subprocess.check_call(command)
    logger.info("pipのコンフィグ設定を確認する-------------------------")
    subprocess.check_call(["pip", "config", "list"])


def get_current_date():
    # タイムゾーンが取得する
    timezone = pytz.timezone("Asia/Tokyo")
    # UTC時間が東京時間を変換する
    local_time = datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone)
    return local_time.strftime("%Y%m%d")


def get_UTC_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_current_timestamp():
    # タイムゾーンが取得する
    timezone = pytz.timezone("Asia/Tokyo")
    # UTC時間が東京時間を変換する
    local_time = datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone)
    return local_time.strftime("%Y-%m-%d %H:%M:%S")


def get_sysuser():
    """システムユーザ取得"""
    return getpass.getuser()


def hash_password(password):
    """
    パスワードを暗号化する処理

    Parameters:
    password (str):パスワード

    Returns:
    str: 暗号化済みパスワード

    復号化処理はできないみたいんで、一旦未利用
    """
    import hashlib

    # パスワードをUTF-8エンコードしてバイト列に変換
    password_bytes = password.encode("utf-8")

    # SHA-256ハッシュを計算し、16進数文字列として返す
    hashed_password = hashlib.sha256(password_bytes).hexdigest()

    # パスワードを暗号化
    # password = "LRd+Epi%y3"
    # encrypted_password = hash_password(password)
    return hashed_password


def get_relative_path(filename):
    # プロジェクトのルートディレクトリを取得　/middleフォルダ取得
    project_root_path = get_project_root_path()

    # config.jsonのパスを組み立てる
    file_path = os.path.join(project_root_path, filename)

    return file_path


def get_project_root_path():
    # プロジェクトのルートディレクトリを取得　/middleフォルダ取得
    project_root_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)
    )

    return project_root_path


# def get_json_config():
#     """
#     json設定ファイル内容取得
#     Parameters:
#         json_file_name (str):json設定ファイル名
#     Returns:
#         obj: jsonファイルの全設定値もつオブジェクト
#     """
#     run_mode = os.environ.get("MIDDLE_RUN_MODE")
#     # プラットフォームを判定して、適切なファイルパス区切り文字を使用
#     path_delimiter = constants.SpecialChars.LINUX_PATH_DELIMITER.value # "/" Linux

#     config_filename = "conf" + path_delimiter + "config_dev.json"
#     if run_mode == constants.RunMode.PROD.value:
#         config_filename = "conf" + path_delimiter + "config_prod.json"

#     if run_mode == constants.RunMode.S2_PROD.value:
#         config_filename = "conf" + path_delimiter + "config_s2_prod.json"

#     if os.name != 'posix':  # Windowsのパスdelimiterに変換する
#         config_filename = config_filename.replace(path_delimiter,
#                                 constants.SpecialChars.WINDOWS_PATH_DELIMITER.value)

#     json_file_name = get_relative_path(config_filename)
#     # 設定値格納用JSONファイルを読み込む
#     with open(json_file_name, "r", encoding='utf-8') as file:
#         config = json.load(file)
#     return config


def is_empty(obj):
    """
    文字列、整数、浮動小数点数などのオブジェクトが空かどうかをチェックします。
    空の場合はTrue、それ以外の場合はFalseを返します。
    """
    if obj is None:
        return True
    elif isinstance(obj, str):
        return not obj.strip()  # 空白文字を除去して空であるかどうかをチェック
    elif isinstance(obj, (int, float)):
        return False  # 整数や浮動小数点数は空ではない
    else:
        return True  # その他の型は空と見なす


def check_existing(content):
    """nullチェック処理"""
    if isinstance(content, list):
        # nullチェック
        for x in content:
            if isEmpty(x):
                return True
    elif isEmpty(content):
        return True


def isEmpty(arg):
    """空チェック処理"""
    return pd.isnull(arg) or (isinstance(arg, str) and arg == "")


def delete_nan_df(df):
    return df.applymap(lambda x: x.strip() if isinstance(x, str) else x)


def toDf(df):
    """
    dataframe形式変更
    params:
        df インプットデータ
    """
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame(df)
    return df


def get_vis_co2EmissionCoefficient(
    ecmst_list,
    electricPowerCorporateCode,
    electricPowerMenuNo,
    electricPowerMenuNm,
    fiscal_year,
):
    """
    電力co2排出係数取得
    params:
        electricPowerEnergyCode 電力会社コード
        electricPowerMenuNo メニュー
        fiscal_year 報告年度
    """
    # マスタデータ取得　電力会社の排出係数情報
    # 該当電量会社情報取得
    ecmst_list = ecmst_list.astype(str)
    ecmst_sub = ecmst_list[
        ecmst_list["ELECTRIC_COMPANY_REG_NO"] == str(electricPowerCorporateCode)
    ]
    ecmst_sub = ecmst_sub[ecmst_sub["MENU_NO"].str.contains(electricPowerMenuNo)]
    ecmst_sub = ecmst_sub[ecmst_sub["REPORT_TARGET_YEAR"] == str(fiscal_year)]
    if electricPowerMenuNm:
        ecmst_sub = ecmst_sub[ecmst_sub["MENU_NM"].str.contains(electricPowerMenuNm)]
    if electricPowerMenuNo:
        ecmst_sub = ecmst_sub[ecmst_sub["MENU_NO"] == (electricPowerMenuNo)]

    id_xmax_year = ecmst_sub["REPORT_TARGET_YEAR"].max()
    if int(id_xmax_year) < fiscal_year:
        ecmst_sub = ecmst_sub[ecmst_sub["REPORT_TARGET_YEAR"] == id_xmax_year]
    else:
        ecmst_sub = ecmst_sub[ecmst_sub["REPORT_TARGET_YEAR"] == str(fiscal_year)]

    if ecmst_sub.empty or ecmst_sub["ADJUSTED_EMISSION_COEF"].iloc[0] == 0:
        ecmst_sub = ecmst_list[
            ecmst_list["ELECTRIC_COMPANY_REG_NO"] == str(electricPowerCorporateCode)
        ]
        ecmst_sub = ecmst_sub[ecmst_sub["MENU_NM"].str.contains("残差")]
        ecmst_sub = ecmst_sub[ecmst_sub["REPORT_TARGET_YEAR"] == fiscal_year]
    if ecmst_sub["ADJUSTED_EMISSION_COEF"].iloc[0] == "None":
        return ecmst_sub["BASE_EMISSION_COEF"].iloc[0]

    return ecmst_sub["ADJUSTED_EMISSION_COEF"].iloc[0]


def get_co2EmissionCoefficient(
    ecmst_list,
    electricPowerCorporateCode,
    electricPowerMenuNo,
    electricPowerMenuNm,
    fiscal_year,
    nfcmst_sub,
    isBank=False,
):
    """
    電力co2排出係数取得
    params:
        electricPowerEnergyCode 電力会社コード
        electricPowerMenuNo メニュー
        fiscal_year 報告年度
    """
    # 事業者コードでまずフィルタ
    ecmst_sub_reg = ecmst_list[
        ecmst_list["ELECTRIC_COMPANY_REG_NO"] == str(electricPowerCorporateCode)
    ]

    # その事業者が存在しない → 完全にデータが無い
    if not ecmst_sub_reg.empty:
        # まず対象年度のデータを確認
        ecmst_year_match = ecmst_sub_reg[
            ecmst_sub_reg["REPORT_TARGET_YEAR"] == str(fiscal_year)
        ]

        if not ecmst_year_match.empty:
            # 対象年度のデータがある
            exist_ecmst_sub_reg = ecmst_year_match
        else:
            # REPORT_TARGET_YEAR を数値化
            ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] = ecmst_sub_reg[
                "REPORT_TARGET_YEAR"
            ].astype(int)

            # fiscal_year に最も近い年度を求める
            closest_year = ecmst_sub_reg.loc[
                (ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] - int(fiscal_year))
                .abs()
                .idxmin(),
                "REPORT_TARGET_YEAR_INT",
            ]
            # その最も近い年度を選択
            exist_ecmst_sub_reg = ecmst_sub_reg[
                ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] == closest_year
            ]

        ecmst_sub_menu = pd.DataFrame()
        if (
            not exist_ecmst_sub_reg.empty
            and bool(electricPowerMenuNm)
            and (electricPowerMenuNm in exist_ecmst_sub_reg["MENU_NM"].values)
        ):
            if isBank:
                ecmst_sub_menu = exist_ecmst_sub_reg[
                    exist_ecmst_sub_reg["MENU_NO"] == int(electricPowerMenuNo)
                ]
            else:
                ecmst_sub_menu = exist_ecmst_sub_reg[
                    exist_ecmst_sub_reg["MENU_NM"] == electricPowerMenuNm
                ]
            if not ecmst_sub_menu.empty and ecmst_sub_menu.shape[0] > 0:
                ecmst_sub_menu = ecmst_sub_menu.loc[
                    ecmst_sub_menu["PUBLICATION_COUNT"].idxmax()
                ]
                return float(ecmst_sub_menu["ADJUSTED_EMISSION_COEF"])
        else:
            ecmst_sub_reg["RESIDUAL_FLG"] = ecmst_sub_reg["RESIDUAL_FLG"].map(
                {True: True, False: False, "True": True, "False": False}
            )

            # 事業者番号 & RESIDUAL_FLG=True で絞り込み
            ecmst_sub_reg = ecmst_sub_reg.loc[
                (ecmst_sub_reg["ELECTRIC_COMPANY_REG_NO"] == electricPowerCorporateCode)
                & (ecmst_sub_reg["RESIDUAL_FLG"])
            ]

            # この時点で対象事業者のデータが1件もない場合
            if ecmst_sub_reg.empty:
                if not nfcmst_sub.empty:
                    val = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
                    val = val.iloc[0] if hasattr(val, "iloc") else val
                return float(val)
            else:
                # Step1: 対象年度のデータを探す
                ecmst_sub_menu = ecmst_sub_reg[
                    ecmst_sub_reg["REPORT_TARGET_YEAR"] == fiscal_year
                ]

                # Step2: 対象年度が無い → 一番近い年度に切り替える
                if ecmst_sub_menu.empty:
                    # 整形：文字列の年度を int に変換
                    ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] = ecmst_sub_reg[
                        "REPORT_TARGET_YEAR"
                    ].astype(int)

                    # fiscal_year に最も近い年度を計算
                    closest_year = ecmst_sub_reg.loc[
                        (ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] - int(fiscal_year))
                        .abs()
                        .idxmin(),
                        "REPORT_TARGET_YEAR_INT",
                    ]

                    # その最も近い年度を抽出
                    ecmst_sub_menu = ecmst_sub_reg[
                        ecmst_sub_reg["REPORT_TARGET_YEAR_INT"] == closest_year
                    ]

                if not ecmst_sub_menu.empty:
                    ecmst_sub_menu = ecmst_sub_menu.loc[
                        ecmst_sub_menu["PUBLICATION_COUNT"].idxmax()
                    ]
                    return float(ecmst_sub_menu["ADJUSTED_EMISSION_COEF"])

    else:
        if not nfcmst_sub.empty:
            val = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
            val = val.iloc[0] if hasattr(val, "iloc") else val
        # 新しい DataFrame を作るか、行を追加する
        return float(val)

    return float(0)


def get_cityGasHeatCoefficient(cgmst_list, cityGasRegNo, fiscal_year):
    """
    都市ガス会社係数取得
    params:
        cgmst_list エネルギーコード
        cityGasRegNo 電力会社名前
        fiscal_year エネルギーコードの換算係数情報
    """
    # マスタデータ取得　電力会社の排出係数情報
    # 該当電量会社情報取得
    cgmst_list = cgmst_list.astype(str)
    cgmst_sub = cgmst_list[cgmst_list["CITY_GAS_SUPPLIER_CODE"] == str(cityGasRegNo)]
    cgmst_sub = cgmst_sub[cgmst_sub["REPORT_YEAR"] == fiscal_year]
    cgmst_sub = cgmst_sub[cgmst_sub["CALORIFIC_VALUE_CODE"] == "1"]
    return cgmst_sub["HEAT_CONVERSION_COEFFICIENT"].iloc[0]


def get_heatSupplyHeatCoefficient(
    hsmst_list,
    heat_supplier_cd,
    heatSupplyMenuNo,
    heatSupplyMenuNm,
    fiscal_year,
    nfcmst_sub,
    chiginFlg,
):
    # def get_heatSupplyHeatCoefficient(hsmst_list, heatSupplyRegNo, fiscal_year):
    """
    熱供給係数取得
    params:
        hsmst_list エネルギーコード
        heatSupplyRegNo 熱会社名前
        fiscal_year エネルギーコードの換算係数情報
    """
    # # 文字列化
    # hsmst_list = hsmst_list.astype(str)

    # # 共通関数：年度優先で探す
    # def find_by_code(code):
    #     df = hsmst_list[hsmst_list["HEAT_SUPPLIER_CD"] == code]

    #     if df.empty:
    #         return None  # 該当コードなし

    #     # まず対象年度を探す
    #     df_year = df[df["REPORT_YEAR"] == str(fiscal_year)]
    #     if not df_year.empty:
    #         return df_year

    #     # 対象年度がない → 最大年度を返す
    #     max_year = df["REPORT_YEAR"].max()
    #     df_max = df[df["REPORT_YEAR"] == max_year]
    #     if not df_max.empty:
    #         return df_max

    #     return None

    # # ① heatSupplyRegNo を探す
    # result = find_by_code(str(heatSupplyRegNo))

    # # ② heatSupplyRegNo が見つからなかったら H0999 を探す
    # if result is None:
    #     result = find_by_code("H0999")

    # # ③ それでもない場合 → hsmst_list の最大年度を返す
    # if result is None:
    #     max_year = hsmst_list["REPORT_YEAR"].max()
    #     result = hsmst_list[hsmst_list["REPORT_YEAR"] == max_year]

    # # ④ 最終的な返却
    # return (
    #     result['ADJUSTED_EMISSION_FACTOR'].iloc[0],
    #     result['MENU_NAME'].iloc[0]
    # )

    # 地銀の場合
    if chiginFlg:
        # 文字列化
        hsmst_list = hsmst_list.astype(str)

        # 共通関数：年度優先で探す
        def find_by_code(code):
            df = hsmst_list[hsmst_list["HEAT_SUPPLIER_CD"] == code]

            if df.empty:
                return None  # 該当コードなし

            # まず対象年度を探す
            df_year = df[df["REPORT_YEAR"] == str(fiscal_year)]
            if not df_year.empty:
                return df_year

            # 対象年度がない → 最大年度を返す
            max_year = df["REPORT_YEAR"].max()
            df_max = df[df["REPORT_YEAR"] == max_year]
            if not df_max.empty:
                return df_max

            return None

        # ② heat_supplier_cd が見つからなかったら H0999 を探す
        result = find_by_code("H0999")

        # ③ それでもない場合 → hsmst_list の最大年度を返す
        if result is None:
            max_year = hsmst_list["REPORT_YEAR"].max()
            result = hsmst_list[hsmst_list["REPORT_YEAR"] == max_year]

        # ④ 最終的な返却
        return result["ADJUSTED_EMISSION_FACTOR"].iloc[0]

    # 可視化の場合
    # 熱供給事業者コードでまずフィルタ
    ecmst_sub_reg = hsmst_list[hsmst_list["HEAT_SUPPLIER_CD"] == str(heat_supplier_cd)]

    # その事業者が存在しない → 完全にデータが無い
    if not ecmst_sub_reg.empty:
        # まず対象年度のデータを確認
        ecmst_year_match = ecmst_sub_reg[
            ecmst_sub_reg["REPORT_YEAR"] == str(fiscal_year)
        ]

        if not ecmst_year_match.empty:
            # 対象年度のデータがある
            exist_ecmst_sub_reg = ecmst_year_match
        else:
            # REPORT_YEAR を数値化
            ecmst_sub_reg["REPORT_YEAR_INT"] = ecmst_sub_reg["REPORT_YEAR"].astype(int)

            # fiscal_year に最も近い年度を求める
            closest_year = ecmst_sub_reg.loc[
                (ecmst_sub_reg["REPORT_YEAR_INT"] - int(fiscal_year)).abs().idxmin(),
                "REPORT_YEAR_INT",
            ]
            # その最も近い年度を選択
            exist_ecmst_sub_reg = ecmst_sub_reg[
                ecmst_sub_reg["REPORT_YEAR_INT"] == closest_year
            ]

        isBank = False
        ecmst_sub_menu = pd.DataFrame()
        if (
            not exist_ecmst_sub_reg.empty
            and bool(heatSupplyMenuNm)
            and (heatSupplyMenuNm in exist_ecmst_sub_reg["MENU_NAME"].values)
        ):
            if isBank:
                ecmst_sub_menu = exist_ecmst_sub_reg[
                    exist_ecmst_sub_reg["MENU_NO"] == int(heatSupplyMenuNo)
                ]
            else:
                ecmst_sub_menu = exist_ecmst_sub_reg[
                    exist_ecmst_sub_reg["MENU_NAME"] == heatSupplyMenuNm
                ]
            if not ecmst_sub_menu.empty and ecmst_sub_menu.shape[0] > 0:
                ecmst_sub_menu = ecmst_sub_menu.loc[
                    ecmst_sub_menu["PUBLICATION_COUNT"].idxmax()
                ]
                return float(ecmst_sub_menu["ADJUSTED_EMISSION_FACTOR"])
        else:
            ecmst_sub_reg["RESIDUAL_FLG"] = ecmst_sub_reg["RESIDUAL_FLG"].map(
                {True: True, False: False, "True": True, "False": False}
            )

            # 事業者番号 & RESIDUAL_FLG=True で絞り込み
            ecmst_sub_reg = ecmst_sub_reg.loc[
                (ecmst_sub_reg["HEAT_SUPPLIER_CD"] == heat_supplier_cd)
                & (ecmst_sub_reg["RESIDUAL_FLG"])
            ]

            # この時点で対象事業者のデータが1件もない場合
            if ecmst_sub_reg.empty:
                if not nfcmst_sub.empty:
                    val = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
                    val = val.iloc[0] if hasattr(val, "iloc") else val
                return float(val)
            else:
                # Step1: 対象年度のデータを探す
                ecmst_sub_menu = ecmst_sub_reg[
                    ecmst_sub_reg["REPORT_YEAR"] == fiscal_year
                ]

                # Step2: 対象年度が無い → 一番近い年度に切り替える
                if ecmst_sub_menu.empty:
                    # 整形：文字列の年度を int に変換
                    ecmst_sub_reg["REPORT_YEAR_INT"] = ecmst_sub_reg[
                        "REPORT_YEAR"
                    ].astype(int)

                    # fiscal_year に最も近い年度を計算
                    closest_year = ecmst_sub_reg.loc[
                        (ecmst_sub_reg["REPORT_YEAR_INT"] - int(fiscal_year))
                        .abs()
                        .idxmin(),
                        "REPORT_YEAR_INT",
                    ]

                    # その最も近い年度を抽出
                    ecmst_sub_menu = ecmst_sub_reg[
                        ecmst_sub_reg["REPORT_YEAR_INT"] == closest_year
                    ]

                if not ecmst_sub_menu.empty:
                    ecmst_sub_menu = ecmst_sub_menu.loc[
                        ecmst_sub_menu["PUBLICATION_COUNT"].idxmax()
                    ]
                    return float(ecmst_sub_menu["ADJUSTED_EMISSION_FACTOR"])

    else:
        if not nfcmst_sub.empty:
            val = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
            val = val.iloc[0] if hasattr(val, "iloc") else val
        # 新しい DataFrame を作るか、行を追加する
        return float(val)

    return float(0)


def tocsv(data_list, folder_dic, table_name):
    """
    登録するデータをcsvファイルへ出力する
    params:
        data_list   登録データリスト
        column_list カラム情報
    """

    new_df = None
    if isinstance(data_list, pd.DataFrame):
        new_df = data_list

    # プロジェクトのルートディレクトリを取得　/middleフォルダ取得
    project_root_path = get_project_root_path()
    output_dir = get_json_config()["filesDir"]["outputfiles"]

    # config.jsonのパスを組み立てる
    output_dir = os.path.join(
        project_root_path,
        output_dir,
        folder_dic["BANK_CODE"],
        folder_dic["CORPORATE_NUMBER"],
    )

    # フォルダ構成を作成
    os.makedirs(output_dir, exist_ok=True)

    # 連番を追加した新しいファイル名を生成する
    output_filename = None
    counter = 1
    while True:
        output_filename = os.path.join(output_dir, f"{table_name}_{counter}.csv")
        if not os.path.exists(output_filename):
            break
        counter += 1

    # dfをcsvへ変換する
    new_df.columns = new_df.columns.str.lower()
    new_df.to_csv(
        f"{output_filename}",
        index=False,
        encoding=constants.EncodingMethod.UTF8BOM.value,
    )


def validate_varchar(value, max_length):
    return isinstance(value, str) and len(value) <= max_length


def set_log_level(run_mode):
    """
    AirflowのVariableから実行モードに応じてログレベルを設定する。
    - 開発環境、ステージング環境ではDEBUGレベル
    - 本番環境ではINFOレベル

    パラメータ:
        run_mode (str): 実行モード

    戻り値:
        なし
    """
    if run_mode == constants.RunMode.DEV.value:
        os.environ["LOG_LEVEL"] = "DEBUG"
    elif run_mode == constants.RunMode.STG.value:
        os.environ["LOG_LEVEL"] = "DEBUG"
    elif run_mode == constants.RunMode.PROD.value:
        os.environ["LOG_LEVEL"] = "INFO"


@log.log_writer(logger)
def get_file_from_hadoop(base_path, sub_path, key):
    files_io = {}

    # Hadoop対象フォルダを取得
    target_paths = get_target_paths(base_path, sub_path, key)
    logger.debug(f"target_paths {target_paths}")

    for target_path in target_paths:
        # Hadoop対象ファイルパスを取得
        file_paths = get_hadoop_file_paths(target_path)

        if not file_paths:
            logger.warn(
                f"Hadoop対象フォルダ:{target_path}がありません、または、フォルダにファイルがありません。"
            )
            continue

        for file_path in file_paths:
            if not file_path.endswith(
                (
                    constants.ExcelExtension.XLSX.value,
                    constants.ExcelExtension.XLS.value,
                    constants.ExcelExtension.XLSM.value,
                    constants.ExcelExtension.CSV.value,
                )
            ):
                logger.warn(f"{file_path}がExcelファイルではありません。")
                continue

            # HadoopからファイルのBytesIOを取得
            file_io = get_hadoop_file_io(file_path)

            if not file_io:
                logger.warn(f"{file_path}のBytesIOを取得できません。")
                continue

            files_io[file_path] = file_io

    return files_io


@log.log_writer(logger)
def get_target_paths(base_path, sub_path, key):
    target_paths = []
    edited_path = get_joined_path(base_path, sub_path)
    if key is not None:
        edited_path = get_joined_path(edited_path, key)
    target_paths.append(edited_path)

    return target_paths


@log.log_writer(logger)
def get_joined_path(*path_list):
    path_list = [path.strip("/") for path in path_list]
    return "/".join(path_list)


@log.log_writer(logger)
def get_hadoop_file_paths(_path):
    result = subprocess.run(
        ["hadoop", "fs", "-ls", _path],
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # command = ["hadoop", "fs", "-ls", path]
    # result = subprocess.run(
    #     command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    # )
    if result.returncode != 0:
        logger.error(f"Error listing files in {_path}: {result.stderr}")
        return []
    lines = result.stdout.splitlines()
    # files = [line.split()[-1] for line in lines[1:]]

    files = []
    for line in lines[1:]:
        parts = line.split()
        # ファイルまたはディレクトリのパス
        file_or_dir_path = parts[-1]

        # ディレクトリかどうかを判定
        is_dir = parts[0][0] == "d"

        # フォルダだった場合は再帰的にその中身を取得
        if is_dir:
            files_in_dir = get_hadoop_file_paths(file_or_dir_path)
            files.extend(files_in_dir)
        else:
            files.append(file_or_dir_path)

    return files


@log.log_writer(logger)
def get_hadoop_file_io(file_path):
    command = ["hadoop", "fs", "-cat", file_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logger.error(f"Error reading file {file_path}: {result.stderr}")
        return None

    return BytesIO(result.stdout)


# Hadoopコマンドを使ってファイルに書き込む
def put_file_to_hadoop(csv_string, file_path):
    # with BytesIO(file.encode("utf-8")) as file_io:
    command = ["hadoop", "fs", "-put", "-", file_path]

    result = subprocess.run(
        command,
        # input=file_io.read(),
        input=csv_string.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        logger.error(
            f"Error writing file to Hadoop "
            f"{file_path}: {result.stderr.decode('utf-8')}"
        )

    logger.info(f"CSV file successfully written to Hadoop {file_path}")


# def load_data_to_csv(base_path, output_path, target_df, csv_filename):
#     base_path = Variable.get("middle_download_put_base_path")
#     output_path = Variable.get("middle_output_csv_path")
#     formatted_time = re.sub(r'[-: ]', '_', get_current_timestamp())
#     basic_csv_path = get_joined_path(base_path, output_path, csv_filename)
#     put_file_to_hadoop(target_df.to_csv(index=False), basic_csv_path)


def delete_mapr_file(_paths):
    out = None
    for _full_path in _paths:
        out = subprocess.run(
            ["hdfs", "dfs", "-rm", "-r", _full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    # return out


def get_max_branch_number(filenames):
    branch_numbers = [extract_branch_number(filename) for filename in filenames]
    branch_numbers = [num for num in branch_numbers if num is not None]
    if branch_numbers:
        return max(branch_numbers)
    return 0


def extract_branch_number(filename):
    # ファイル名の末尾から枝番を抽出
    match = re.search(r"_(\d+)\.csv$", filename)
    if match:
        return int(match.group(1))
    return None


def make_folder(_full_path):
    out = subprocess.run(
        ["hdfs", "dfs", "-mkdir", "-p", _full_path], capture_output=True
    )
    return out


""" 登録するデータをcsvファイル形でmaprfsに格納する"""


@check_time
# def make_csv_to_maprfs(_target_df, _csv_prefix, _report_type):
#     base_path = Variable.get("middle_download_put_base_path")
#     output_path = Variable.get("middle_output_csv_path")
#     current_date = get_current_date()
#     target_csv_folder = pathjoin(_target_df["BANK_CODE"].iloc[0], _report_type, current_date)
#     output_files = get_file_from_hadoop(base_path, output_path, target_csv_folder)

#     csv_filename_list = []
#     for output_file_path, file_io in output_files.items():
#         #ファイル名取得（拡張し含む）
#         file_name, file_extension = os.path.splitext(os.path.basename(output_file_path))
#         # 企業カルテ以外のファイルはスキップする
#         if not _csv_prefix in output_file_path: continue
#         csv_filename_list.append(file_name + file_extension)

#     numbering_num = get_max_branch_number(csv_filename_list) + 1
#     to_make_dir = pathjoin(base_path, output_path, target_csv_folder)
#     # maprfs上で「銀行/企業/」のフォルダを作成する
#     make_folder(to_make_dir)
#     basic_csv_path = get_joined_path(to_make_dir, f"{_csv_prefix}{numbering_num}.csv")
#     # カラム名を小文字に変換
#     _target_df.columns = _target_df.columns.str.lower()
#     put_file_to_hadoop(_target_df.to_csv(index=False), basic_csv_path)


def get_originalConsumptionUnitYaxisEnd(ecdmst_list, buideUseKbn):
    """
    消費原単位基準線Y軸座標END取得
    params:
        buideUseKbn 建物用途区分
    """
    ecdmst_maxyear = ecdmst_list["FISCAL_YEAR"].max()
    for index, item in ecdmst_list.iterrows():
        # if str(item['BUILDING_USAGE']) == buideUseKbn and \
        if item["ENERGY_CATEGORY_DIV"] == "B01":
            # item['FISCAL_YEAR'] == ecdmst_maxyear:
            return item["VALUE"]


def get_calculate_grade(hq_17, hr_17, hq_15, ij_18):
    """
    象限取得
    params:
        hq_17 一次エネルギー消費量
        hr_17 一次エネルギー原単位
        hq_15 一次エネルギー消費量中央値
        ij_18 消費原単位基準線Y軸座標
    """
    if hq_17 <= hq_15:
        if hr_17 <= ij_18:
            return "C"
        else:
            return "B-1"
    else:
        if hr_17 <= ij_18:
            return "B-2"
        else:
            return "A"


def get_scatter_plot_label(quadrant, office_name):
    """
    散布図ラベル取得
    params:
        quadrant 象限
        office_name 建物名称
    """
    if quadrant == "C":
        return ""
    else:
        return office_name


def get_consumptionQuantityYaxisEnd(max, yaxis):
    """
    一次エネルギー原単位消費量基準線Y軸座標END取得
    params:
        max 一次エネルギー原単位最大値
        yaxis 基準線一次エネルギー消費原単位Y軸座標
    """
    if max < yaxis:
        return yaxis + 500
    else:
        return max


def get_menu(
    buideUseKbn,
    energyConsumptionCategory,
    correctionCategoryUsage,
    baseEnergyConsumptionRate,
    ecdmst_list,
):
    """
    params:
        buideUseKbn 建物用途区分
        energyConsumptionCategory   エネルギー消費先区分
        correctionCategoryUsage   補正区分用途
        baseEnergyConsumptionRate  ベース省エネ率
        ecdmst_list
    """

    value_c04 = ecdmst_list.loc[
        ecdmst_list["ENERGY_CATEGORY_DIV"] == "C04", "VALUE"
    ].values
    value_c05 = ecdmst_list.loc[
        ecdmst_list["ENERGY_CATEGORY_DIV"] == "C05", "VALUE"
    ].values

    value_subname = ecdmst_list.loc[
        ecdmst_list["ENERGY_SUB_NAME"] == energyConsumptionCategory, "VALUE"
    ].values
    value_category = ecdmst_list.loc[
        ecdmst_list["ENERGY_CATEGORY_NAME"] == correctionCategoryUsage, "VALUE"
    ].values
    value_subname = convert_to_float(value_subname[0]) if len(value_subname) > 0 else 0
    value_category = (
        convert_to_float(value_category[0]) if len(value_category) > 0 else 0
    )

    value_c04 = convert_to_float(value_c04[0]) if len(value_c04) > 0 else 0
    value_c05 = convert_to_float(value_c05[0]) if len(value_c05) > 0 else 0
    baseEnergyConsumptionRate = (
        0
        if baseEnergyConsumptionRate is None
        else convert_to_float(baseEnergyConsumptionRate)
    )

    ret = (
        value_subname
        * value_category
        * value_c04
        * value_c05
        * baseEnergyConsumptionRate
    )
    return ret
    # for index,item in ecdmst_list.iterrows():
    #     a = item['VALUE'] if item['ENERGY_SUB_NAME'] == energyConsumptionCategory else 0
    #     b = item['VALUE'] if item['ENERGY_CATEGORY_NAME'] == correctionCategoryUsage else 0
    #     a = convert_to_float(a)
    #     b = convert_to_float(b)

    #     pasanta = a * b * value_c04 * value_c05 * baseEnergyConsumptionRate
    #     return pasanta


def convert_to_float(value):
    if value is None:
        return 1
    if isinstance(value, str):
        value = value.strip()
        if value.endswith("%"):
            value = value[:-1]
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Could not convert string to float: '{value}'")
    return float(value)


def get_menuvalues(buideUseKbn, buildingUseValues, cmst, menu_max_num):
    """
    params:
        menuNum
        buideUseKbn 建物用途区分
        cmst
    """
    countList = []
    value_list = []
    for index, item in cmst.iterrows():
        # if item['MENU_NUM'] == menuNum:
        values1 = 1 - buildingUseValues * item["COUNTERMEASURE_FLAG"]
        value_list.append(values1)
        menu_num = item["MENU_NUM"]
        menu_dic = {
            "menu": item["COUNTERMEASURE_MENU"],
            "num": menu_num,
            "value": values1,
        }
        countList.append(menu_dic)

    # countMeasureDict = {}
    # for menu_dic in countList:
    #     # 建物全体
    #     allBuild_value = 1 - np.product(menu_dic['value'])
    #     #照明高効率化全体省エネ率に対する比率
    #     ratio_value = (1 - menu_dic['value'] ) / (menu_max_num - sum(value_list))
    #     key = f"{buideUseKbn}-{menu_dic['menu']}"
    #     countMeasureDict[key] = {'allBuildValue':allBuild_value, 'ratioValue': ratio_value}
    return countList


# def get_followUpvalues(corporation_df,kesu):
#     #フォローアップ／一次エネルギー
#     """
#     params:
#         corporation_df      年一次エネルギー
#         kesu   系数list
#     """
#     #フォローアップ／一次エネルギー
#     targetYear = list(range(2013, 2051))
#     countFollowUpList=[]
#     #oneFollowUpList=[]
#     oneFollowUpDict=[]

#     for year in targetYear.iterrows():
#         for item1, item2 in zip(corporation_df, kesu):
#             if year == item1['FISCAL_YEAR']:
#                  a = item1['ENERGY_CONSUMPTION'] if item1['ENERGY_NAME'] =='電力' else 0
#                  b = item1['ENERGY_CONSUMPTION'] if item1['ENERGY_NAME'] =='都市ガス' else 0
#                  x = item2['PRIMARY_EMISSION_COEFFICIENT'] if item2['ENERGY_NAME'] =='電力' else 0
#                  y = item2['PRIMARY_EMISSION_COEFFICIENT'] if item2['ENERGY_NAME'] =='都市ガス' else 0
#                  c = item1['ENERGY_CONSUMPTION']*item2['PRIMARY_EMISSION_COEFFICIENT']  if item1['燃料種別'] == item2['ENERGY_NAME'] and item2['ENERGY_NAME'] =='重油' or '灯油' else 0
#                  d = ( a * x + b * y + c ) /1000
#             else:
#                  d = 0
#             countFollowUpdata = [{'year':year},{'officename':item1['OFFICE_NAME']},{'FollowUpvalue':d}]
#             countFollowUpList.extend(countFollowUpdata)

#     countFollowUpList.sort(key=lambda x: x['year'])
#     for year, group in groupby(countFollowUpList, key=lambda x: x['year']):
#         total_value1 = sum(item['FollowUpvalue'] for item in group)
#         #oneFollowUpList.append({'year': year, 'total_value1': total_value1})
#         key = f"{year}"
#         oneFollowUpDict[key] = {'total_value1':total_value1}

#     return oneFollowUpDict
# def get_followUpCo2values(corporation_df,co2EmissionCoefficientlist):
#     #フォローアップ／CO2
#     """
#     params:
#         corporation_df      年一次エネルギー
#         co2EmissionCoefficientlist   CO2系数list
#     """
#     #フォローアップ／一次エネルギー
#     targetYear = list(range(2013, 2051))
#     countFollowUpCo2List=[]
#     oneFollowUpCo2List=[]
#     oneFollowUpCo2Dict=[]

#     for year in targetYear.iterrows():
#         for item1, item2 in zip(corporation_df, co2EmissionCoefficientlist):
#             if year == item1['FISCAL_YEAR']:
#                  a = item1['ENERGY_CONSUMPTION'] if item1['ENERGY_NAME'] =='電力' else 0
#                  b = item1['ENERGY_CONSUMPTION'] if item1['ENERGY_NAME'] =='都市ガス' else 0
#                  c = item1['ENERGY_CONSUMPTION'] if item1['燃料種別'] =='重油' or '灯油' else 0
#                  x = item2['電力']
#                  y = item2['都市ガス']
#                  u = item2['重油']
#                  v = item2['灯油']
#                  validate_varchar
#                  d = ( a * x + b * y + c * u + c * v) /1000
#             else:
#                  d = 0
#             countFollowUpCo2data = [{'year':year},{'officename':item1['OFFICE_NAME']},{'FollowUpvalue':d}]

#             countFollowUpCo2List.extend(countFollowUpCo2data)
#     countFollowUpCo2List.sort(key=lambda x: x['year'])
#     for year, group in np.groupby(countFollowUpCo2List, key=lambda x: x['year']):
#         total_value1 = sum(item['FollowUpvalue'] for item in group)
#         #oneFollowUpCo2List.append({'year': year, 'total_value1': total_value1})
#         key = f"{year}"
#         oneFollowUpCo2Dict[key] = {'total_value1':total_value1}
#     return oneFollowUpCo2Dict


def get_electricPowerCoefficient(ecemst_list):
    # 電気CO2排出量換算係数パターン
    """
    params:
        ecemst_list      電気CO2排出量換算系数master
    """
    targetYear = list(range(2013, 2051))
    elecDict = {}
    (
        FIXED_PATTERN,
        ELECTRIC_POWER_2030_PATTERN,
        CUSTOM_SETTING_PATTERN,
        NATIONAL_AVERAGE_PATTERN,
    ) = ("", "", "", "")
    for index, ecemst_row in ecemst_list.iterrows():
        fiscal_year = ecemst_row["FISCAL_YEAR"]
        if fiscal_year != "FISC" and int(fiscal_year) in targetYear:
            # if item1 == item2['FISCAL_YEAR']:
            FIXED_PATTERN = ecemst_row["FIXED_PATTERN"]  #
            ELECTRIC_POWER_2030_PATTERN = ecemst_row["ELECTRIC_POWER_2030_PATTERN"]
            CUSTOM_SETTING_PATTERN = ecemst_row["CUSTOM_SETTING_PATTERN"]
            NATIONAL_AVERAGE_PATTERN = ecemst_row["NATIONAL_AVERAGE_PATTERN"]
            # elecdata = [{'year':item1},{'FIXED_PATTERN':item1['FIXED_PATTERN']},{'ELECTRIC_POWER_2030_PATTERN':item1['ELECTRIC_POWER_2030_PATTERN']},{'CUSTOM_SETTING_PATTERN':item1['CUSTOM_SETTING_PATTERN']},{'NATIONAL_AVERAGE_PATTERN':item1['NATIONAL_AVERAGE_PATTERN']}]
            # else:
            # elecdata = [{'year':item1},{'FIXED_PATTERN':FIXED_PATTERN},{'ELECTRIC_POWER_2030_PATTERN':ELECTRIC_POWER_2030_PATTERN},{'CUSTOM_SETTING_PATTERN':CUSTOM_SETTING_PATTERN},{'NATIONAL_AVERAGE_PATTERN':NATIONAL_AVERAGE_PATTERN}]
            # key = f"{item1}"
            elecDict[fiscal_year] = {
                "FIXED_PATTERN": FIXED_PATTERN,
                "ELECTRIC_POWER_2030_PATTERN": ELECTRIC_POWER_2030_PATTERN,
                "CUSTOM_SETTING_PATTERN": CUSTOM_SETTING_PATTERN,
                "NATIONAL_AVERAGE_PATTERN": NATIONAL_AVERAGE_PATTERN,
            }

    return elecDict


def get_co2EmissionCoefficientlist(ccmst, electricPowerCoefficientlist):
    # CO2排出量換算係数
    """
    params:
        ccmst_list      換算系数master
        electricPowerCoefficientlist 電気CO2排出量換算係数パターン
    """
    # 換算係数マスタから処理中エネルギーデータを取得する(DataFrame型)
    co2_ret_dict = {}
    targetYear = list(range(2013, 2051))
    for year in targetYear:
        co2_dict = {}
        for index, officeUsedEnergyInfo in ccmst.iterrows():
            if officeUsedEnergyInfo["ENERGY_NAME"] in ["都市ガス", "A重油", "灯油"]:
                co2_dict[officeUsedEnergyInfo["ENERGY_NAME"]] = round(
                    officeUsedEnergyInfo["UNIT_HEAT_GENERATION"]
                    * officeUsedEnergyInfo["EMISSION_COEFFICIENT"]
                    * 44
                    / 12,
                    4,
                )
            co2_ret_dict[year] = co2_dict
    for key, value in electricPowerCoefficientlist.items():
        if key != "FISC" and int(key) in co2_ret_dict:
            co2_ret_dict[int(key)]["電力"] = value["FIXED_PATTERN"]  # 電力

    return co2_ret_dict


def co2EmissionGJCoefficientlist(co2cientlist, ccmst_list):
    # CO2排出量換算係数 GJ→t-CO2
    """
    params:
        co2cientlist  CO2排出量換算係数
        ccmst_list      換算系数master
    """
    # targetYear = list(range(2013, 2051))
    # co2GJList=[]
    co2GJDict = {}
    # for item1, item2 in zip(co2cientlist, ccmst_list):
    for key, submap in co2cientlist.items():
        submap_keys = list(submap.keys())
        row_dic = {}
        for sub_key in submap_keys:
            for index, ccmst_row in ccmst_list.iterrows():
                energy_name = ccmst_row["ENERGY_NAME"]
                if sub_key == energy_name:
                    ccmst_row["PRIMARY_EMISSION_COEFFICIENT"] = (
                        1
                        if ccmst_row["PRIMARY_EMISSION_COEFFICIENT"] is None
                        else ccmst_row["PRIMARY_EMISSION_COEFFICIENT"]
                    )
                    ret = float(submap[sub_key]) / float(
                        ccmst_row["PRIMARY_EMISSION_COEFFICIENT"]
                    )
                    row_dic[ccmst_row["ENERGY_NAME"]] = ret
                    break
        co2GJDict[key] = row_dic
    return co2GJDict


def get_files(file_type):
    """
    企業カルテ用生データと集計データ
    params:
        conn
        corporate_df   処理対象シート情報格納DataFrame
        building_df カラム情報
        energy_df
        file_name
    return:
        energy_dic  エネルギー情報辞書
    """
    json_config = get_json_config()
    # rootパス取得
    project_root_path = get_project_root_path()
    # 入力シートファイル格納フォルダ名取得する
    target_folder = os.path.join(project_root_path, json_config["filesDir"][file_type])

    # osがwindowsの場合、Windowsのパスdelimiterに変換する
    if os.name != "posix":
        target_folder = target_folder.replace(
            constants.SpecialChars.LINUX_PATH_DELIMITER.value,
            constants.SpecialChars.WINDOWS_PATH_DELIMITER.value,
        )

    # files/inputfiles配下各銀行の入力シートファイルを取得する
    excel_files = []
    for root, dirs, files in os.walk(target_folder):
        # 除外するフォルダ
        dirs[:] = [d for d in dirs if d not in ["processed_files", "error_files"]]
        for file in files:
            # ファイルのフルパスを取得します
            file_path = os.path.join(root, file)
            # ファイルのフルパスをリストに追加します
            if file.endswith(
                (
                    constants.ExcelExtension.XLS.value,
                    constants.ExcelExtension.XLSM.value,
                    constants.ExcelExtension.XLSX.value,
                )
            ):
                excel_files.append(file_path)
    # 指定フォルダーに存在する全Excelファイルを取得
    # excel_files = [f for f in os.listdir(target_folder)
    #                if f.endswith((constants.ExcelExtension.XLS.value,
    #                             constants.ExcelExtension.XLSM.value,
    #                             constants.ExcelExtension.XLSX.value))]

    if excel_files is None or len(excel_files) == 0:
        logger.info("処理する入力シートファイルが存在しません。")
        # TODO 異常内容とタイプ確認
        raise Exception("処理する入力シートファイルが存在しません。")

    return excel_files


def get_input_files():
    """
    企業カルテ用生データと集計データ
    params:
        conn
        corporate_df   処理対象シート情報格納DataFrame
        building_df カラム情報
        energy_df
        file_name
    return:
        energy_dic  エネルギー情報辞書
    """
    json_config = get_json_config()
    # rootパス取得
    project_root_path = get_project_root_path()
    # 入力シートファイル格納フォルダ名取得する
    target_folder = os.path.join(
        project_root_path, json_config["filesDir"]["inputfiles"]
    )

    # osがwindowsの場合、Windowsのパスdelimiterに変換する
    if os.name != "posix":
        target_folder = target_folder.replace(
            constants.SpecialChars.LINUX_PATH_DELIMITER.value,
            constants.SpecialChars.WINDOWS_PATH_DELIMITER.value,
        )

    # files/inputfiles配下各銀行の入力シートファイルを取得する
    excel_files = []
    for root, dirs, files in os.walk(target_folder):
        # 除外するフォルダ
        dirs[:] = [d for d in dirs if d not in ["processed_files", "error_files"]]
        for file in files:
            # ファイルのフルパスを取得します
            file_path = os.path.join(root, file)
            # ファイルのフルパスをリストに追加します
            if file.endswith(
                (
                    constants.ExcelExtension.XLS.value,
                    constants.ExcelExtension.XLSM.value,
                    constants.ExcelExtension.XLSX.value,
                )
            ):
                excel_files.append(file_path)
    # 指定フォルダーに存在する全Excelファイルを取得
    # excel_files = [f for f in os.listdir(target_folder)
    #                if f.endswith((constants.ExcelExtension.XLS.value,
    #                             constants.ExcelExtension.XLSM.value,
    #                             constants.ExcelExtension.XLSX.value))]

    if excel_files is None or len(excel_files) == 0:
        logger.info("処理する入力シートファイルが存在しません。")
        # TODO 異常内容とタイプ確認
        raise Exception("処理する入力シートファイルが存在しません。")

    return excel_files


def print_progress_bar(
    iteration,
    total,
    prefix="Progress:",
    suffix="Complete",
    decimals=1,
    length=50,
    fill="█",
):
    """
    プロセスの進行状況をグラフィカルに表示する関数。
    - 進行状況のパーセンテージとバーで現在の進捗を表示する。
    - ロガーを使用してAirflowのログに情報を記録する。

    パラメータ:
        iteration (int): 現在のイテレーション数
        total (int): 総イテレーション数
        prefix (str): プログレスバーの前に表示するテキスト
        suffix (str): プログレスバーの後に表示するテキスト
        decimals (int): 進行状況のパーセンテージ表示における小数点以下の桁数
        length (int): プログレスバーの長さ
        fill (str): プログレスバーの充填に使用する文字

    戻り値:
        なし
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    logger.info(f"{prefix} |{bar}| {percent}% {suffix} 【{iteration}/{total}】")


@log.log_writer(logger)
def ls_volume(_path):
    ls_out = subprocess.run(
        ["hdfs", "dfs", "-ls", "-R", _path],
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ls_out.returncode != 0:
        msg = f"hdfs dfs -ls command is failed. path is {_path}. stdout is {ls_out.stdout}. stderr is {ls_out.stderr}"
        logger.error(msg)
        raise Exception(msg)
    exist_files = [_line.split() for _line in ls_out.stdout.splitlines()[0:]]
    exist_files = [basename(_line[-1]) for _line in exist_files]
    return exist_files


# ステータスコードが400,500番台の時raiseする
@log.log_writer(logger)
def check_status(code):
    code = int(code)
    if code >= 500:
        msg = "Check webdav service status. code was " + str(code)
        logger.error(msg)
        raise Exception(msg)

    elif code >= 400:
        msg = "something wrong to connect webdav target. code was " + str(code)
        logger.error(msg)
        raise Exception(msg)


@log.log_writer(logger)
def get_list(_url, _auth):
    import requests
    from requests.auth import HTTPBasicAuth

    headers = {"Depth": "1", "Content-Type": "application/x-www-form-urlencoded"}
    data = "<D:propfind xmlns:D='DAV:' xmlns:Z='http://www.northgrid.co.jp/proself/'><D:prop></D:prop></D:propfind>"
    response = requests.request(
        "PROPFIND",
        _url,
        headers=headers,
        data=data,
        verify=False,
        auth=HTTPBasicAuth(_auth["user"], _auth["password"]),
    )
    check_status(response.status_code)

    return response.content


# xml形式のresponceからファイルパスのリストを取得
@log.log_writer(logger)
def xml_to_list(content, _get_path):
    import re
    from urllib.parse import unquote

    path_pattern = "<D:href>(.*)</D:href>"
    sentence = unquote(content)
    _file_list = [find_str for find_str in re.findall(path_pattern, sentence)]
    # 1番目はcurrent dirなので捨てる
    _folder_list = [_item for _item in _file_list if not isfile(_item)][1:]
    _file_list = [_file for _file in _file_list if isfile(_file)]

    return _file_list, _folder_list


@log.log_writer(logger)
def recursive_get_list(_base_url, _get_path, _auth, _files=None):
    if _files is None:
        _files = []

    url = make_proself_url(_base_url, _get_path)
    content = get_list(url, _auth)

    file_list, folder_list = xml_to_list(content.decode(), _get_path)
    _files += file_list

    for folder in folder_list:
        folder = folder.split("/")[-2]
        if folder == "old":
            continue
        _files = recursive_get_list(
            _base_url, pathjoin(_get_path, folder), _auth, _files
        )

    return _files


@log.log_writer(logger)
def make_proself_url(_base_url, _file_path):
    from urllib.parse import quote

    _file_path = quote(_file_path)
    return pathjoin(_base_url, _file_path)


@log.log_writer(logger)
def get_file(_url, _local_path, _auth):
    from io import BytesIO

    import requests
    from requests.auth import HTTPBasicAuth

    # 未格納ファイルをダウンロード
    response = requests.get(
        _url, auth=HTTPBasicAuth(_auth["user"], _auth["password"]), verify=False
    )
    check_status(response.status_code)

    # ローカルにダウンロードしたファイルを書き出し
    with open(_local_path, "wb") as f:
        f.write(response.content)

    return _local_path


# 引数のファイルがVariables"middle_download_filter_taget_files"に含まれているか確認する
@log.log_writer(logger)
def filter_target_file(file_name):
    import json
    import re

    from airflow.models import Variable

    filter_str = Variable.get("middle_download_filter_taget_files")
    filter_list = _load_json_to_list(filter_str)
    try:
        for filter_str in filter_list:
            if file_name.lower().startswith(filter_str.lower()):
                return True
    except Exception as e:
        logger.error(f"error in filter list area. error message : {e}")
        raise e

    return False


@log.log_writer(logger)
def put_file(_local_path, _put_path):
    out = subprocess.run(
        ["hdfs", "dfs", "-put", _local_path, _put_path], capture_output=True
    )
    return out


@log.log_writer(logger)
def remove_local_file(_local_path):
    from pathlib import Path

    Path(_local_path).unlink(missing_ok=True)
    is_exist = Path(_local_path).exists()
    return not is_exist


def move_to_old(in_process_path, to_path):

    # 新しいパスのディレクトリが存在しない場合、作成
    to_path.parent.mkdir(parents=True, exist_ok=True)

    # ファイルをリネーム（移動）
    in_process_path.rename(to_path)


# VariablesのJson文字列からlistに変換する
def _load_json_to_list(_json_file):
    import json

    try:
        target_list = json.loads(_json_file)
    except Exception as e:
        logger.error(f"error in target list area. error message : {e}")
        raise e

    return target_list


def _splittext(_path):
    return os.path.splitext(_path)


def basename(_path):
    return os.path.basename(_path)


def pathjoin(*_path_list):
    _path_list = [_path[1:] if _path[0] == "/" else _path for _path in _path_list]
    _path_list = [
        _path[:-1] if ((_path[-1] == "/") and (_path[-3:] != "://")) else _path
        for _path in _path_list
    ]
    return os.path.join(*_path_list)


def isfile(_path):
    return bool(_splittext(_path)[1])


def get_filtered_df(_target_df, _condition_dic):
    """
    条件に沿って対象DFをフィルタする

    params:
        _target_df, _condition_dic

    return
        フィルタ済DF
    """
    # フィルタリング条件を作成
    if _target_df is None or len(_condition_dic) <= 0:
        return

    # filter条件タプル取得
    conditions = []
    for key, value in _condition_dic.items():
        _condition = _target_df[key] == value
        conditions.append(_condition)

    # 条件を全て結合する
    if conditions:
        combined_conditions = conditions[0]
        for condition in conditions:
            combined_conditions &= condition

        # フィルタリングして新しい DataFrame を作成
        filtered_df = _target_df[combined_conditions]
    else:
        # 条件がない場合のデフォルトの処理
        filtered_df = _target_df

    return filtered_df


def get_relative_path(file_name):
    """
    指定されたファイル名に対して、プロジェクトルートディレクトリからの相対パスを取得する。

    パラメータ:
        file_name (str): 相対パスを取得したいファイルの名前。

    戻り値:
        str: プロジェクトルートディレクトリからの相対パス。
    """
    # 現在のファイルが存在するディレクトリのパスを取得
    current_dir_path = os.path.dirname(os.path.abspath(__file__))

    # 現在のディレクトリの親ディレクトリのパスを取得
    parent_dir_path = os.path.dirname(current_dir_path)

    # 相対パスを組み立て
    return os.path.join(parent_dir_path, file_name)


def nan_to_zero(value):
    import math

    if value is None:
        return 0
    if isinstance(value, float) and math.isnan(value):
        return 0
    return value


def prepare_file_download_response(response, encoded_filename):
    """
    ファイルダウンロード用のレスポンスを準備する共通関数
    304レスポンス対策とContent-Dispositionヘッダーの設定を行う

    パラメータ:
        response: FlaskのResponseオブジェクト（send_fileの戻り値）
        encoded_filename: URLエンコード済みのファイル名

    戻り値:
        FlaskのResponseオブジェクト（ヘッダー設定済み）
    """
    # 304レスポンスの場合は200に変更（ブラウザがキャッシュを使用しないようにする）
    if response.status_code == 304:
        response.status_code = 200

    # Content-Dispositionヘッダーを明示的に設定（RFC 5987形式）
    content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"
    response.headers["Content-Disposition"] = content_disposition

    # 304レスポンスを防ぐため、キャッシュ関連ヘッダーを無効化
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    # ETagとLast-Modifiedを削除して304レスポンスを防ぐ
    if "ETag" in response.headers:
        del response.headers["ETag"]
    if "Last-Modified" in response.headers:
        del response.headers["Last-Modified"]

    return response
