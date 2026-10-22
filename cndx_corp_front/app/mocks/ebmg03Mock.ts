import { EnergyBuildingDataset, ElectricityResponse } from "~/types/screen/energy-building/ebmg/ebmgType";

export const ebmg03MockData: EnergyBuildingDataset = {
  building_address_prefecture: ["東京都", "大阪府"],

  industry_class_minor: [
    { group_code: "A011", group_name: "鉄鋼" },
    { group_code: "B011", group_name: "ハウス" },
  ],

  industry_class_detail: [
    { industry_code: "A0111", industry_name: "粗鋼" },
    { industry_code: "B0111", industry_name: "トマト" },
  ],

  city_gas: [
    { city_gas_supplier_cd: "456", city_gas_supplier_nm: "東京ガス" },
    { city_gas_supplier_cd: "654", city_gas_supplier_nm: "大阪ガス" },
  ],

  heat_supplier: [
    { heat_supplier_cd: "789", heat_supplier_name: "東京熱供給" },
    { heat_supplier_cd: "987", heat_supplier_name: "大阪熱供給" },
  ],

  buildings: [
    {
      building_id: "B001",
      building_info: {
        building_name: "本社ビル",
        building_address_prefecture: "東京都",
        building_address_city: "千代田区",
        industry_class_major_code: "A",
        industry_class_major_name: "製造業",
        industry_class_middle_code: "A01",
        industry_class_middle_name: "金属",
        industry_class_minor_code: "A011",
        industry_class_minor_name: "",
        industry_class_detail_code: "A0111",
        industry_class_detail_name: "",
        gross_floor_area: "2000",
        electricity_supplier_no: "123",
        electricity_supplier_name: "東京電力",
        menu_no: "M01",
        menu_name: "高圧契約",
        ep_office_code: "EP01",
        ep_customer_number: "C12345",
        supply_point_number: "SP12345",
        city_gas_supplier_no: "456",
        city_gas_supplier_name: "東京ガス",
        heat_supplier_no: "",
        heat_supplier_name: "",
        heat_menu_number: "",
        heat_menu_name: "",
        energy_info: [
          {
            energy_code: "0100230000",
            energy_unit_original: "m3",
            energy_name_jp: "都市ガス",
            energy_quantity: [11, 22, 33, 44, 55, 66, 77, 88, 99, 100, 110, 1200],
            energy_usage_sum: 465,
          },
          {
            energy_code: "0200010011",
            energy_unit_original: "千kWh",
            energy_name_jp: "電気",
            energy_quantity: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
            energy_usage_sum: 780,
          },
        ],
        registration_seq: 1,
      },
    },
    {
      building_id: "B002",
      building_info: {
        building_name: "大阪ビル",
        building_address_prefecture: "大阪府",
        building_address_city: "大阪市",
        industry_class_major_code: "B",
        industry_class_major_name: "農業",
        industry_class_middle_code: "B01",
        industry_class_middle_name: "野菜",
        industry_class_minor_code: "B011",
        industry_class_minor_name: "",
        industry_class_detail_code: "B0111",
        industry_class_detail_name: "",
        gross_floor_area: "1500",
        electricity_supplier_no: "321",
        electricity_supplier_name: "大阪電力",
        menu_no: "M02",
        menu_name: "低圧契約",
        ep_office_code: "EP02",
        ep_customer_number: "C67890",
        supply_point_number: "SP67890",
        city_gas_supplier_no: "654",
        city_gas_supplier_name: "大阪ガス",
        heat_supplier_no: "987",
        heat_supplier_name: "大阪熱供給",
        heat_menu_number: "H02",
        heat_menu_name: "特別契約",
        energy_info: [],
        registration_seq: 1,
      },
    },
  ],
};

export const ebmg03AutoFillElectricityMockData = {
  electricity_data: [
    { sum: 9875.0, year_month: "202404" },
    { sum: 10020.5, year_month: "202405" },
    { sum: 10150.3, year_month: "202406" },
    { sum: 10425.0, year_month: "202407" },
    { sum: 10890.75, year_month: "202408" },
    { sum: 11010.2, year_month: "202409" },
    { sum: 10650.0, year_month: "202410" },
    { sum: 10230.8, year_month: "202411" },
    { sum: 9950.6, year_month: "202412" },
    { sum: 10045.9, year_month: "202501" },
    { sum: 10320.7, year_month: "202502" },
    { sum: 10510.4, year_month: "202503" },
  ],
  unit: "千kWh",
};