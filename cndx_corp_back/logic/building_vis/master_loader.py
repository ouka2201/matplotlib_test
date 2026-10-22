import pandas as pd
from sqlalchemy import or_, true

from cndx_corp_back.entity.activity_minor_category_mst_entity import (
    ActivityMinorCategoryMst,
)
from cndx_corp_back.entity.electric_supplier_menu_mst import ElectricSupplierMenuMst
from cndx_corp_back.entity.heat_supplier_menu_mst import HeatSupplierMenuMst
from cndx_corp_back.entity.m_benchmark_info_entity import MBenchmarkInfo
from cndx_corp_back.entity.m_calculation_logic_entity import MCalculationLogic
from cndx_corp_back.entity.m_city_gas_supplier_calorific_value_entity import (
    MCityGasSupplierCalorificValue,
)
from cndx_corp_back.entity.m_competitor_industry_entity import MCompetitorIndustry
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_electricity_conversion_entity import MElectricityConversion
from cndx_corp_back.entity.m_heat_supplier_menu_entity import MHeatSupplierMenu
from cndx_corp_back.entity.m_non_fossil_certificate_constant_entity import (
    MNonFossilCertificateConstant,
)
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.entity.m_weather_data_info_entity import MWeatherDataInfo


class MasterLoader:
    # _instance = None

    # def __new__(cls, conn, code_value = None, code_list = None):
    #     if cls._instance is None:
    #         cls._instance = super(MasterLoader, cls).__new__(cls)
    #         cls._instance._load_all(conn, code_value, code_list)
    #     return cls._instance

    def __init__(self, conn):
        self._load_all(conn)

    def _load_all(self, conn):
        # 必要に応じて省略・追加OK
        self.ccmst = self._to_df(conn.query(ActivityMinorCategoryMst).all(), upper=True)
        self.ecmst = self._to_df(conn.query(MElectricityConversion).all(), upper=True)
        self.calmst = self._to_df(
            conn.query(MCalculationLogic).filter_by(delete_flg=False).all(), upper=True
        )
        self.hsmst = self._to_df(
            conn.query(MHeatSupplierMenu).filter_by(delete_flg=False).all(), upper=True
        )
        self.ccimst = self._to_df(
            conn.query(MCorpCodeInfo).filter_by(code_type="PREF").all(), upper=True
        )
        self.wdimst = self._to_df(
            conn.query(MWeatherDataInfo).filter_by(delete_flag=False).all(), upper=True
        )
        self.nfcmst = self._to_df(
            conn.query(MNonFossilCertificateConstant).filter_by(delete_flg=False).all(),
            upper=True,
        )
        self.bmmst = self._to_df(
            conn.query(MBenchmarkInfo)
            .filter(MBenchmarkInfo.delete_flg.isnot(true()))
            .all(),
            upper=False,
        )
        self.gasmst = self._to_df(
            conn.query(MCityGasSupplierCalorificValue)
            .filter_by(delete_flg=False)
            .all(),
            upper=False,
        )

    def _load_nfcmst(self, conn):
        self.nfcmst = self._to_df(
            conn.query(MNonFossilCertificateConstant).filter_by(delete_flg=False).all(),
            upper=True,
        )

    def _to_df(self, query_result, upper=False):
        if not query_result:
            return pd.DataFrame()
        row = query_result[0]
        if hasattr(row, "_fields"):  # namedtuple形式
            df = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in query_result
                ]
            )
        else:
            df = pd.DataFrame(
                [
                    {col.name: getattr(row, col.name) for col in row.__table__.columns}
                    for row in query_result
                ]
            )
        return df.rename(columns=str.upper) if upper else df

    def get_ccmst(self):
        return self.ccmst

    def get_ecmst(self):
        return self.ecmst

    def get_calmst(self):
        return self.calmst

    def get_ccimst(self):
        return self.ccimst

    def get_hsmst(self):
        return self.hsmst

    def get_wdimst(self):
        return self.wdimst

    def get_nfcmst(self):
        return self.nfcmst

    def get_bmmst(self):
        return self.bmmst

    def get_gasmst(self):
        return self.gasmst
