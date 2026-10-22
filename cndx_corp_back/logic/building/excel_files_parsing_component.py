import os
import re

import pandas as pd
from flask import abort

import cndx_corp_back.common.constants_colums as constants_colums
import cndx_corp_back.common.log as log
import cndx_corp_back.common.utils as utils
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.utils.utils import get_message

# log出力用インスタンス取得
logger = log.CorpLogger()

# ▼▼▼▼▼▼▼▼▼符号定数群▼▼▼▼▼▼▼▼▼
DOT = constants_colums.SpecialChars.DOT.value
BLANK = constants_colums.SpecialChars.BLANK.value
HYPHEN = constants_colums.SpecialChars.HYPHEN.value
SLASH = constants_colums.SpecialChars.LINUX_PATH_DELIMITER.value

# ▼▼▼▼▼▼▼▼▼識別用文字列群▼▼▼▼▼▼▼▼▼
# "事業所"
OFFICE_STRING = constants_colums.StringOfExcelFile.OFFICE.value
# "入力シート"
INPUT_SHEET_STRING = constants_colums.StringOfExcelFile.INPUT_SHEET.value
# "設定"
SETTING_STRING = constants_colums.StringOfExcelFile.SETTING.value

# システム操作時タイムスタンプ取得
current_timestamp = utils.get_current_timestamp()
# データ登録処理実行者
# creator_name = utils.get_sysuser()


class ExcelFilesParsingComponent:

    @log.log_writer(logger)
    @component
    def parse_excel_file(
        self, session, input_files: list, dict_request_data, logger=None
    ):
        logger.debug("------------入力シート解析処理開始------------")

        basic_info_df = pd.DataFrame(), pd.DataFrame()

        basic_info_df = self.get_basic_info(session)

        register_df_dic = {}
        # try:
        # Excelファイル解析
        register_df_dic = self.file_data_process_main(
            session, input_files, basic_info_df, dict_request_data
        )
        logger.debug("------------入力シート解析処理終了------------")

        return register_df_dic
        # except Exception as e:
        #     logger.error(e)
        #     abort(400, description = "ファイルETL処理失敗しました。")

    def get_basic_info(self, session):
        """
        基本情報テーブルデータ取得
        params:
            conn Hive接続し
        return:
            basic_info_df  基本情報テーブルデータ
        """
        try:
            basic_info_df = session.query(TCnApplicationInfo).all()
            # DFへ変換
            # basic_info_df = pd.DataFrame([{field: getattr(row, field) for field in row._fields} for row in basic_info_df])
            basic_info_df = pd.DataFrame(
                [
                    {
                        col.name: getattr(row, col.name)
                        for col in TCnApplicationInfo.__table__.columns
                    }
                    for row in basic_info_df
                ]
            )
            # カラム大文字にする
            if not basic_info_df.empty:
                basic_info_df.columns = basic_info_df.columns.str.upper()

            return basic_info_df

        except Exception as e:
            logger.error(e)
            abort(500)

    def file_data_process_main(
        self, session, input_files, basic_info_df, dict_request_data
    ):
        global error_filenames
        # セットになる行員向け入力シートと簡易診断入力シートを管理する辞書
        register_df_dic = {}

        # 入力シートファイル数分の処理を繰り返す
        # for input_file_path, file_io in input_files.items():
        for input_file_path in input_files:  # TODO 🔥🔥🔥🔥🔥 テスト用

            # 入力情報格納用DataFrame作成
            corporate_df = pd.DataFrame(columns=constants_colums.corporate_column)
            building_df = pd.DataFrame(columns=constants_colums.building_column)
            energy_df = pd.DataFrame(columns=constants_colums.energy_column)
            # 事業所数
            number_offices = None
            # ファイル名取得（拡張し含む）
            file_name, file_extension = os.path.splitext(
                os.path.basename(input_file_path)
            )
            input_file_name = file_name + file_extension

            # Hive登録時用辞書のkeyを構築する
            df_key = self.get_register_df_key(input_file_path, input_file_name)

            # logger.info(f"★処理対象ファイル名：{input_file_name}")

            file_io = input_file_path  # TODO 🔥🔥🔥🔥🔥テスト用
            file_df = pd.ExcelFile(file_io)
            # 処理対象シート名取得
            all_sheet_names = [
                sheet_name
                for sheet_name in (file_df.sheet_names)
                if INPUT_SHEET_STRING in sheet_name  # 記入シート
                or sheet_name.startswith(OFFICE_STRING)
            ]  # 事業所シート

            financialYear = None

            # 相関チェック項目
            correlation_check_values = {}

            for sheet_name in all_sheet_names:
                # 記入シート、事業所シートと設定シート以外はスキップする
                if (
                    INPUT_SHEET_STRING not in sheet_name
                    and not sheet_name.startswith(OFFICE_STRING)
                    and sheet_name != SETTING_STRING
                ):
                    continue

                # DataFrame加工処理
                sheet_df, value_df = self.preprocess_sheet_df(file_io, sheet_name)

                # 関連チェック
                try:
                    self.check_correlation_items(correlation_check_values)
                except Exception as e:
                    logger.error(e)
                    abort(500)
                    break

                if INPUT_SHEET_STRING in sheet_name:
                    # 「記入シート」の情報の場合
                    # 登録用df_keyに年度がない場合、記入シートの対象年度をくっ付ける
                    match = re.search(r"_(\d{4})_", input_file_name)
                    financialYear = value_df["REPORT_PERIOD_START_YEAR_MONTH"].iloc[0][
                        :4
                    ]

                    if not match:
                        df_key = df_key + financialYear
                    else:
                        df_key = re.sub(r"_(\d{4})_", f"_{financialYear}_", df_key)

                    # 記入シートデータ格納用DF設定
                    try:
                        corporate_df = self.set_corporate_df(value_df, corporate_df)
                        number_offices = int(corporate_df["BUSINESS_OFFICE_COUNT"])

                    except Exception as e:
                        logger.error(e)
                        abort(500)

                if sheet_name.startswith(OFFICE_STRING):

                    number_offices -= 1  # 当シートカウント

                    # 最大事業所数以外のシート情報読まない
                    if number_offices < 0:
                        continue

                    try:
                        # 事業所シートデータ格納用DF設定
                        building_df, energy_df = self.set_building_energy_df(
                            session,
                            sheet_df,
                            value_df,
                            corporate_df,
                            building_df,
                            energy_df,
                            dict_request_data,
                            corporate_df["FISCAL_YEAR"].iloc[0],
                            corporate_df["AREA_ID"].iloc[0],
                        )
                    except Exception as e:
                        logger.error(e)
                        abort(500)

            corporate_repeated_df = pd.concat(
                [corporate_df] * len(building_df), ignore_index=True
            )
            basic_df = pd.concat([corporate_repeated_df, building_df], axis=1)  # 列結合
            # 入力シート以外の情報設定
            basic_df = basic_df.assign(
                FILE_ID=None,
                REPORT_SAVE_PATH=None,
                REPORT_STATUS="0",
                REPORT_CLASSIFY="1",
                CREATED_AT=current_timestamp,
                CREATED_BY=dict_request_data["user_id"],
                UPDATED_AT=None,
                UPDATED_BY=None,
                DELETE_FLG=False,
                ORG_ID=dict_request_data["org_id"],
                AGREEMENT_CATEGORY=dict_request_data["agreement_category"],
                GHG_SYSTEM_COMPANY_NAME=None,
                ENERGY_BENCHMARK_TARGET_INDUSTRY=None,
                ENERGY_BENCHMARK_INDICATOR=None,
                ENERGY_BENCHMARK_YEAR=None,
                ENTRY_DRAFT_FLAG="1",
                KPI_TARGET_ENERGY_SAVING_RATE=0,
                KPI_TARGET_ELECTRIFICATION_RATE=0,
                KPI_TARGET_ENERGY_CREATION=0,
                KPI_TARGET_RENEWABLE_NETWORK_RATE=0,
            )

            # 行員向け入力シートの入力情報
            karte_dic_value = {
                input_file_name: {
                    "basic_df": basic_df,
                    "corporate_df": corporate_df,
                    "building_df": building_df,
                    "energy_df": energy_df,
                }
            }
            # 辞書にキーが存在するかどうかを確認
            if df_key in register_df_dic:
                # 既存の値に新しい値を追加
                register_df_dic[df_key].append(karte_dic_value)
            else:
                # 新しいキーに対して値を設定
                register_df_dic[df_key] = [karte_dic_value]

        return register_df_dic

    def get_register_df_key(self, input_file_path, input_file_name):
        # ファイル名からスラッシュで区切って主キー要素を取得
        global SLASH
        if os.name != "posix":
            SLASH = constants_colums.SpecialChars.WINDOWS_PATH_DELIMITER.value

        path_parts = input_file_path.split(SLASH)
        company_nm = filename_fiscal_year = BLANK
        if len(path_parts) > 5:
            company_nm = path_parts[-2]

        # ファイル名から年度を抽出
        match = re.search(r"_(\d{4})_", input_file_name)
        if match:
            filename_fiscal_year = match.group(1)

        df_key = company_nm + HYPHEN + filename_fiscal_year

        return df_key

    def preprocess_sheet_df(self, file_path, sheet_name):
        """
        入力シート(Excelファイル)の各シートごと
        のデータを整形済みのDataFrameに設定する
        params:
            file_path  入力シートファイルパス
            sheet_name エクセルファイル上シート名
        return:
            sheet_df 全体DF
            value_df データDF
        """

        # Excelファイル読み込み
        sheet_df = pd.read_excel(file_path, sheet_name)
        # 空白文字を取り除く
        utils.delete_nan_df(sheet_df)
        # 最後の行を捨てる
        sheet_df.drop(sheet_df.index[-1])
        # 日本語列名を物理名へ変換する
        sheet_df.replace(constants_colums.convert_mapping, inplace=True)
        # nanを空文字に変換
        sheet_df.fillna(BLANK, inplace=True)
        # hyphenを空文字に変換
        sheet_df.replace(HYPHEN, BLANK, inplace=True)

        # 6列目の値を列名として抽出
        if sheet_name.startswith(OFFICE_STRING):  # 拠点の場合
            sheet_column_list = sheet_df.iloc[:, 6].tolist()
            sheet_value_data_list = (
                sheet_df.iloc[:, 8:9]
                .fillna(BLANK)
                .apply(lambda row: BLANK.join(map(str, row)), axis=1)
                .tolist()
            )
        else:
            sheet_column_list = sheet_df.iloc[:, 7].tolist()
            sheet_value_data_list = (
                sheet_df.iloc[:, 9:10]
                .fillna(BLANK)
                .apply(lambda row: BLANK.join(map(str, row)), axis=1)
                .tolist()
            )
        # 8~15列の値を値として抽出

        # 新たなDataFrame作成、重複列削除
        value_df = (
            pd.DataFrame([sheet_value_data_list], columns=sheet_column_list)
            .loc[
                :,
                ~pd.DataFrame(
                    [sheet_value_data_list], columns=sheet_column_list
                ).columns.duplicated(),
            ]
            .copy()
        )

        return sheet_df, value_df

    def check_sheet(self, sheet_name, value_df, correlation_check_values):
        """
        シート毎チェック
        params:
            sheet_name チェック対象シート
            value_df 対象シートデータ格納用DF
        """
        # 必須チェック項目一覧（シート別：事業所シート）
        required_columns = None
        if INPUT_SHEET_STRING in sheet_name:
            required_columns = constants_colums.CORPORATE_REQUIRED_COLUMNS
        elif sheet_name.startswith(OFFICE_STRING):
            required_columns = constants_colums.BUILDING_REQUIRED_COLUMNS

        if required_columns is not None:
            # バリデーションチェック（必須チェック)
            correlation_check_values = self.check_required_items(
                value_df, required_columns, correlation_check_values
            )

        return correlation_check_values

    def check_required_items(self, df, required_columns, correlation_check_values):
        """
        シート毎チェック
        params:
            df 対象シートデータ格納用DF
            required_columns 必須チェック項目配列
        """
        # リスト内の各項目を検証する
        for column in required_columns:
            for index, rowdata in df.iterrows():
                if column in constants_colums.NEITHER_REQUIRED_COLUMNS:
                    correlation_check_values[column] = rowdata[column]
                    break
                if not rowdata[column]:
                    abort(400, description=get_message("REQUIRED", item_name=column))

        return correlation_check_values

    def check_correlation_items(self, correlation_check_values):
        """
        シート毎チェック
        params:
            df 対象シートデータ格納用DF
            required_columns 必須チェック項目配列
        """
        if correlation_check_values is None or len(correlation_check_values) < 3:
            return

        # 相関チェック
        company_num, ep_store_num, ep_user_num = BLANK, BLANK, BLANK
        for column, cell_value in correlation_check_values.items():
            if "CORPORATE_NUMBER" == column:
                company_num = cell_value
            if "EP_STORE_NUMBER" == column:
                ep_store_num = cell_value
            if "CUSTOMER_NUMBER_EP" == column:
                ep_user_num = cell_value

        if company_num != BLANK or (ep_store_num != BLANK and ep_user_num != BLANK):
            pass
        else:
            abort(
                400,
                description=get_message(
                    "EITHER_REQUIRED",
                    item_name1="法人番号",
                    item_name2="EPお客さま番号",
                ),
            )

    def set_corporate_df(self, value_df: pd.DataFrame, corporate_df: pd.DataFrame):

        # 業種名称(大分類、中分類)情報取得
        value_df = value_df.assign(
            INDUSTRY_CLASS_MAJOR_CODE=value_df["INDUSTRY_CLASS_MAJOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0],
            INDUSTRY_CLASS_MIDDLE_CODE=value_df["INDUSTRY_CLASS_MIDDLE_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0]
            .split("_")[1],
            INDUSTRY_CLASS_MINOR_CODE=value_df["INDUSTRY_CLASS_MINOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0]
            .split("_")[2],
            INDUSTRY_CLASS_DETAIL_CODE=value_df["INDUSTRY_DETAIL_CLASSIFICATION_MARK"]
            .iloc[0]
            .split(":")[0]
            .split("_")[3],
            INDUSTRY_CLASS_DETAIL_NAME=value_df["INDUSTRY_DETAIL_CLASSIFICATION_MARK"]
            .iloc[0]
            .split(":")[1],
        )
        value_df["INDUSTRY_CLASS_MAJOR_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MAJOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_MIDDLE_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MIDDLE_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_MINOR_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MINOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_DETAIL_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_DETAIL_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )

        # 期末を年月までの6桁の日付文字列にする
        value_df["REPORT_PERIOD_END_YEAR_MONTH"].iloc[0] = (
            value_df["REPORT_PERIOD_END_YEAR_MONTH"].iloc[0][:7].replace(HYPHEN, BLANK)
        )

        # 記入シートDataFrame構築
        corporate_df = pd.concat(
            [corporate_df, value_df], join="inner", ignore_index=True
        )

        company_code = value_df["CORPORATE_NUMBER"].iloc[0]

        # 企業はエリアIDとする
        area_id = company_code + constants_colums.NumberingStartValue.THREE_NUMBER.value
        # エリアIDと対象年度追加
        corporate_df = corporate_df.assign(
            AREA_ID=area_id,
            FISCAL_YEAR=value_df["REPORT_PERIOD_START_YEAR_MONTH"].iloc[0][:4],
        )

        return corporate_df

    def set_building_energy_df(
        self,
        session,
        sheet_df,
        value_df,
        corporate_df,
        building_df,
        energy_df,
        dict_request_data,
        financialYear,
        area_id,
    ):

        # 建物ID取得
        building_id = area_id + constants_colums.NumberingStartValue.THREE_NUMBER.value

        building_id = self.get_building_id(
            session, value_df, corporate_df, dict_request_data
        )

        value_df["BUILDING_ID"] = building_id

        # 業種名称(大分類、中分類)情報取得
        value_df = value_df.assign(
            INDUSTRY_CLASS_MAJOR_CODE=value_df["INDUSTRY_CLASS_MAJOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0],
            INDUSTRY_CLASS_MIDDLE_CODE=value_df["INDUSTRY_CLASS_MIDDLE_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0]
            .split("_")[1],
            INDUSTRY_CLASS_MINOR_CODE=value_df["INDUSTRY_CLASS_MINOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[0]
            .split("_")[2],
            INDUSTRY_CLASS_DETAIL_CODE=value_df["INDUSTRY_DETAIL_CLASSIFICATION_MARK"]
            .iloc[0]
            .split(":")[0]
            .split("_")[3],
            INDUSTRY_CLASS_DETAIL_NAME=value_df["INDUSTRY_DETAIL_CLASSIFICATION_MARK"]
            .iloc[0]
            .split(":")[1],
        )
        value_df["INDUSTRY_CLASS_MAJOR_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MAJOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_MIDDLE_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MIDDLE_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_MINOR_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_MINOR_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )
        value_df["INDUSTRY_CLASS_DETAIL_NAME"].iloc[0] = (
            value_df["INDUSTRY_CLASS_DETAIL_NAME"]
            .iloc[0]
            .split(constants_colums.SpecialChars.COLON.value)[1]
        )

        building_df = pd.concat(
            [building_df, value_df], join="inner", ignore_index=True
        )

        # エネルギー情報格納DF設定
        energy_df = self.set_energy_df_data(
            sheet_df, value_df, energy_df, financialYear
        )

        return building_df, energy_df

    def get_building_id(self, session, sheet_df, corporate_df, dict_request_data):
        """
        建物ID取得
        params:
            sheet_df
            corporate_df
            basic_info_df
        return:
            building_id  建物ID
        """
        building_id = BLANK

        # 法人番号
        corporate_number = corporate_df["CORPORATE_NUMBER"].iloc[0]
        # 組織ID
        org_id = dict_request_data["org_id"]
        # 拠点名
        building_name = sheet_df["BUILDING_NAME"].iloc[0]

        building_id = (
            session.query(MBuilding.building_id)
            .filter(
                MBuilding.location_identifier_name == building_name,
                MBuilding.corporate_number == corporate_number,
                MBuilding.org_id == org_id,
            )
            .all()
        )

        if not building_id:
            abort(400, description=get_message("NOT_UPDATE", item_name="建物情報"))

        return building_id[0]

    def set_energy_df_data(self, sheet_df, value_df, energy_df, financialYear):
        """
        エネルギー情報を格納する辞書を作成する
        params:
            sheet_df   処理対象シート情報格納DataFrame
            column_list カラム情報
        return:
            energy_dic  エネルギー情報辞書
        """
        # エネルギー辞書作成
        energy_dic = {key: [] for key in constants_colums.energy_column}
        # 隠されている列排除
        sheet_df = sheet_df.iloc[:, 4:]
        # エネルギー情報処理開始
        energy_row = sheet_df[
            sheet_df.iloc[:, 0].str.contains(
                constants_colums.StringOfExcelFile.ENERGY_INFO.value
            )
        ].index.values[0]
        # エネルギー使用情報後のデータ
        energy_value_df = sheet_df.loc[energy_row:]
        # 使っていないエネルギー排除
        energy_value_df = energy_value_df[energy_value_df.iloc[:, 20] != 0]
        # 入力シートから年月取得
        energyDateList = energy_value_df.iloc[0, 8:20].tolist()
        # 入力シートからエネルギー名称取得
        energyNameDF = pd.DataFrame(energy_value_df.iloc[1:, 2:4].values)

        for index, value in energyNameDF.iterrows():
            for dateValue in energyDateList:
                energy_value = sheet_df.iloc[
                    sheet_df[sheet_df.iloc[:, 2] == value.iloc[0]].index.values[0],
                    sheet_df.iloc[energy_row].tolist().index(dateValue),
                ]
                # if energy_value != 0 and pd.notna(energy_value) :
                # energy_dic['AREA_INFORMATION'].append(value_df['AREA_INFORMATION'].iloc[0])
                energy_dic["BUILDING_ID"].append(value_df["BUILDING_ID"].iloc[0])
                energy_dic["BUILDING_NAME"].append(value_df["BUILDING_NAME"].iloc[0])
                energy_dic["ENERGY_CODE"].append(None),
                energy_dic["CATEGORY"].append(None),
                energy_dic["ENERGY_NAME"].append(value.iloc[0])
                energy_dic["ENERGY_NAME_JP"].append(
                    constants_colums.energy_name_jp_map.get(value.iloc[0])
                )
                energy_dic["YEAR"].append(dateValue.year)
                energy_dic["MONTH"].append(dateValue.month)
                energy_dic["FISCAL_YEAR"].append(financialYear)
                energy_dic["ENERGY_QUANTITY"].append(energy_value)
                energy_dic["UNIT_ORIGIN"].append(value.iloc[1])

        # エネルギー情報DataFrame作成
        energy_df = pd.concat(
            [energy_df, pd.DataFrame(energy_dic)], join="inner", ignore_index=True
        )

        return energy_df.fillna(0)
