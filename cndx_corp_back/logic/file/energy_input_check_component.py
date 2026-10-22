import os

import pandas as pd
from flask import current_app
from pandas import DataFrame, ExcelFile

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.load_master import mst_data
from cndx_corp_back.common.validation import (
    decimal_digits_check,
    integer_format_check,
    length_check,
    newline_check,
    numeric_range_check,
    required_check,
)
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.utils.excel_utils import (
    exists_sheet,
    exists_sheet_like,
    get_data_frame,
)
from cndx_corp_back.utils.utils import get_message


class EnergyInputCheckComponent:

    def __init__(self):
        self.sheet_nm = ""
        self.item_nm = ""

    def item_name(self):
        return "シート「" + self.sheet_nm + "」にある「" + self.item_nm + "」"

    @component
    def excute(self, input: ExcelFile, message_list: list, logger=None):
        """
        入力チェック
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # input = ExcelFile(input)
        self.sheet_nm = exists_sheet_like(input, "記入シート")
        if not self.sheet_nm:
            message_list.append(get_message("SHEET_NOT_EXIST", sheet_name="記入シート"))
            return
        df: DataFrame = get_data_frame(input, self.sheet_nm)
        df.fillna("", inplace=True)

        # チェック処理
        self.item_nm = "金融機関名"
        bank_name = df.iat[4, 10]
        if required_check(bank_name, self.item_name(), message_list):
            length_check(bank_name, self.item_name(), message_list, None, 100)
            newline_check(bank_name, self.item_name(), message_list)

        self.item_nm = "金融機関コード"
        bank_code = df.iat[5, 10]
        if required_check(bank_code, self.item_name(), message_list):
            length_check(bank_code, self.item_name(), message_list, 4, 4)
            integer_format_check(bank_code, self.item_name(), message_list)
            newline_check(bank_code, self.item_name(), message_list)

        self.item_nm = "支店名"
        staff_branch_name = df.iat[7, 10]
        if required_check(staff_branch_name, self.item_name(), message_list):
            length_check(staff_branch_name, self.item_name(), message_list, None, 100)
            newline_check(staff_branch_name, self.item_name(), message_list)

        self.item_nm = "支店コード"
        staff_branch_code = df.iat[8, 10]
        if required_check(staff_branch_code, self.item_name(), message_list):
            length_check(staff_branch_code, self.item_name(), message_list, 3, 3)
            integer_format_check(staff_branch_code, self.item_name(), message_list)
            newline_check(staff_branch_code, self.item_name(), message_list)

        self.item_nm = "氏名"
        corp_staff_name = df.iat[9, 10]
        if required_check(corp_staff_name, self.item_name(), message_list):
            length_check(corp_staff_name, self.item_name(), message_list, None, 50)
            newline_check(corp_staff_name, self.item_name(), message_list)

        self.item_nm = "企業名"
        company_name = df.iat[13, 10]
        if required_check(company_name, self.item_name(), message_list):
            length_check(company_name, self.item_name(), message_list, None, 100)
            newline_check(company_name, self.item_name(), message_list)
        self.item_nm = "法人番号"
        corporate_number = df.iat[14, 10]
        logger.info(f"対象法人番号:{corporate_number})")
        if required_check(corporate_number, self.item_name(), message_list):
            length_check(corporate_number, self.item_name(), message_list, 13, 13)
            integer_format_check(corporate_number, self.item_name(), message_list)
            newline_check(corporate_number, self.item_name(), message_list)

        # 複数金融機関利用チェック
        self.multiple_bank_check(corporate_number, bank_code, message_list)

        self.item_nm = "本社住所"
        office_address = df.iat[15, 10]
        if required_check(office_address, self.item_name(), message_list):
            length_check(office_address, self.item_name(), message_list, None, 100)
            newline_check(office_address, self.item_name(), message_list)

        # マスタチェック
        # self.check_cate_large(message_list, input.industry_cate_large)
        # self.check_cate_middle(message_list, input.industry_cate_large)

        self.item_nm = "対象年度"
        reporting_year = df.iat[19, 10]
        if required_check(reporting_year, self.item_name(), message_list):
            length_check(reporting_year, self.item_name(), message_list, 4, 4)
            integer_format_check(reporting_year, self.item_name(), message_list)
            newline_check(reporting_year, self.item_name(), message_list)

        self.item_nm = "期初"
        start_period = df.iat[20, 10]
        if required_check(start_period, self.item_name(), message_list):
            length_check(start_period, self.item_name(), message_list, 6, 6)
            integer_format_check(start_period, self.item_name(), message_list)

        self.item_nm = "事業所数"
        number_offices = df.iat[16, 10]
        if required_check(number_offices, self.item_name(), message_list):
            length_check(number_offices, self.item_name(), message_list, None, 2)
            if not integer_format_check(number_offices, self.item_name(), message_list):
                return
            if not numeric_range_check(
                number_offices, self.item_name(), message_list, max_value=5
            ):
                return
            newline_check(number_offices, self.item_name(), message_list)

            for i in range(1, number_offices + 1):

                self.sheet_nm = f"事業所{i}"
                if not exists_sheet(input, self.sheet_nm):
                    message_list.append(
                        get_message("SHEET_NOT_EXIST", sheet_name=self.sheet_nm)
                    )
                    continue
                df: DataFrame = get_data_frame(input, self.sheet_nm)
                df.fillna("", inplace=True)

                self.item_nm = "事業所名"
                branch_name = df.iat[3, 10]
                if required_check(branch_name, self.item_name(), message_list):
                    length_check(branch_name, self.item_name(), message_list, None, 100)
                    newline_check(branch_name, self.item_name(), message_list)

                self.item_nm = "建物名"
                building_name = df.iat[4, 10]
                length_check(building_name, self.item_name(), message_list, None, 100)
                newline_check(building_name, self.item_name(), message_list)

                self.item_nm = "住所"
                address = df.iat[5, 10]
                length_check(address, self.item_name(), message_list, None, 100)
                newline_check(address, self.item_name(), message_list)

                # マスタチェック
                self.item_nm = "産業分類"
                division_code = df.iat[6, 10].split(":")[0]  # 産業分類符号（大分類)
                major_group_code = (
                    df.iat[7, 10].split(":")[0].replace(division_code, "")
                )  # 産業分類符号（中分類)
                group_code = df.iat[9, 10]  # 産業分類符号（小分類)
                self.check_industry_classification(
                    division_code, major_group_code, group_code, message_list
                )

                self.item_nm = "延床面積"
                branch_code = df.iat[10, 10]
                if required_check(branch_code, self.item_name(), message_list):
                    decimal_digits_check(
                        branch_code, self.item_name(), message_list, 10, 2
                    )
                    newline_check(branch_code, self.item_name(), message_list)

                # 契約先電気事業者
                self.item_nm = "契約先電気事業者"
                electricity_provider = df.iat[11, 10]
                length_check(
                    electricity_provider, self.item_name(), message_list, None, 100
                )
                newline_check(electricity_provider, self.item_name(), message_list)

                self.item_nm = "事業所コード"
                branch_code = df.iat[13, 10]
                if required_check(branch_code, self.item_name(), message_list):
                    length_check(branch_code, self.item_name(), message_list, 3, 3)
                    integer_format_check(branch_code, self.item_name(), message_list)
                    newline_check(branch_code, self.item_name(), message_list)

                self.item_nm = "お客さま番号"
                branch_code = df.iat[14, 10]
                if required_check(branch_code, self.item_name(), message_list):
                    length_check(branch_code, self.item_name(), message_list, 13, 13)
                    integer_format_check(branch_code, self.item_name(), message_list)
                    newline_check(branch_code, self.item_name(), message_list)

                self.item_nm = "供給地点特定番号"
                branch_code = df.iat[15, 10]
                if required_check(branch_code, self.item_name(), message_list):
                    length_check(branch_code, self.item_name(), message_list, 22, 22)
                    integer_format_check(branch_code, self.item_name(), message_list)
                    newline_check(branch_code, self.item_name(), message_list)

                self.item_nm = "契約電力"
                branch_code = df.iat[16, 10]
                if required_check(branch_code, self.item_name(), message_list):
                    decimal_digits_check(
                        branch_code, self.item_name(), message_list, 10
                    )
                    newline_check(branch_code, self.item_name(), message_list)

                # 電気の年度合計変数
                total_energy = 0.0

                for i in range(18, 53):

                    energy_name = df.iat[i, 8]

                    for j in range(14, 26):

                        energy = df.iat[i, j]

                        # try:
                        #     energy = float(energy)
                        # except (TypeError, ValueError):
                        #     continue

                        # TODO 暫定対応
                        if not isinstance(energy, (float, int, str)):
                            continue

                        if energy:
                            energy_month = df.iat[17, j].strftime("%Y/%m")
                            self.item_nm = f"{energy_name}の{energy_month}分"
                            is_valid = decimal_digits_check(
                                energy,
                                self.item_name(),
                                message_list,
                                10,
                                4,
                            )
                            newline_check(energy, self.item_name(), message_list)

                            if i == 52 and is_valid:
                                total_energy += energy

                self.item_nm = "電気"
                numeric_range_check(
                    total_energy,
                    self.item_name(),
                    message_list,
                    0.0001,
                    None,
                    msg_id="AT_LEAST_ONE_VALID_VALUE",
                )

        logger.info(f"{os.path.basename(__file__)}処理終了。")

    def check_industry_classification(
        self, division_code: str, major_group_code: str, group_code: str, err_list: list
    ):
        """
        産業分類存在チェック
        マスタに存在しない場合、エラーメッセージを返す
        """

        jimst = pd.read_json(mst_data["M_JP_ST_INDUSTRY_CLASSIFICATION"], dtype=str)

        filtered_df = jimst[
            (jimst["division_code"] == division_code)
            & (jimst["major_group_code"] == major_group_code)
            & (jimst["group_code"] == group_code)
        ]

        if filtered_df.empty:
            err_list.append(get_message("INDUSTRY_NOT_FOUND"))
            return False
        return True

    def multiple_bank_check(self, corporate_number, bank_code, message_list: list):

        with get_scoped_session() as session:

            cnap_infos = session.query(TCnApplicationInfo).filter_by(
                corporate_number=corporate_number
            )
            cnap_info = cnap_infos.first()
            if cnap_info is not None and not cnap_info.bank_code == str(bank_code):
                message_list.append(get_message("MULTIPLE_BANK_ERROR"))
                return False
            else:
                return True
