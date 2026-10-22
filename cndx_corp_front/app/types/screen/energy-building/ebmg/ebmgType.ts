// 拠点エネルギー情報用IF

// 拠点エネルギー情報照会登録更新

export type EnergyInfo = {
  energy_code: string;
  energy_unit_original: string;
  energy_name_jp:string;
  energy_quantity: number[];
  energy_usage_sum: number;
};

export type BuildingInfo = {
  building_name: string; //建物名[拠点名]
  building_address_prefecture: string; //建物所在地(都道府県)[所在地]
  building_address_city: string; //建物所在地(市区町村)[所在地]
  industry_class_major_code: string; //日本標準産業分類（大分類）[産業分類(大分類)]
  industry_class_major_name: string; //日本標準産業分類名称（大分類）[産業分類(大分類)]
  industry_class_middle_code: string; //日本標準産業分類（中分類）[産業分類(中分類)]
  industry_class_middle_name: string; //日本標準産業分類名称（大分類）[産業分類(大分類)]
  industry_class_minor_code: string; //日本標準産業分類（小分類）[産業分類(小分類)]
  industry_class_minor_name: string;
  industry_class_detail_code: string; //日本標準産業分類（細分類）[産業分類(細分類)]
  industry_class_detail_name: string;
  gross_floor_area: string; //延床面積
  electricity_supplier_no: string; //電気事業者登録番号[契約先電気事業者]
  electricity_supplier_name: string; //電気事業者名[契約先電気事業者] (仮)
  menu_no: string | undefined; //メニュー番号[契約先電気料金メニュー]
  menu_name: string; //メニュー名称[契約先電気料金メニュー]
  ep_office_code: string; //EP事業者コード[事業者コード]
  ep_customer_number: string; //EPお客さま番号
  supply_point_number: string; //供給地点特定番号
  city_gas_supplier_no: string; //契約先都市ガス供給事業者登録番号[契約先都市ガス供給事業者](仮)
  city_gas_supplier_name: string; //都市ガス供給事業者名[契約先都市ガス供給事業者] (仮)
  heat_supplier_no: string; //契約先熱供給事業者登録番号[契約先熱供給事業者]
  heat_supplier_name: string; //熱供給事業者名[契約先熱供給事業者] (仮)
  heat_menu_number: string; //メニュー番号[熱供給料金メニュー]
  heat_menu_name: string; //メニュー名称[熱供給料金メニュー]
  energy_info: EnergyInfo[];
  registration_seq: number; //登録回数
};

export type Building = {
  building_id: string;
  building_info: BuildingInfo;
};

export type ElectricCompanyMenu = {
  menu_no: string;
  menu_nm: string;
};

export type IndustryClassDetail = {
  industry_code: string;
  industry_name: string;
};

export type IndustryClassMinor = {
  group_code: string;
  group_name: string;
};

export type CityGasSupplier = {
  city_gas_supplier_cd: string;
  city_gas_supplier_nm: string;
};

export type HeatSupplier = {
  heat_supplier_cd: string;
  heat_supplier_name: string;
};

export type MasterData = {
  building_address_prefecture: string[];
  industry_class_minor: IndustryClassMinor[];
  industry_class_detail: IndustryClassDetail[];
  city_gas: CityGasSupplier[];
  heat_supplier: HeatSupplier[];
};

export type EnergyBuildingDataset = MasterData & {
  buildings: Building[];
};

export type BuildingInfoFormValues = {
  building_name: string; 
  building_address_prefecture: string;
  building_address_city: string; 
  industry_class_major_code: string; 
  industry_class_major_name: string; 
  industry_class_middle_code: string; 
  industry_class_middle_name: string; 
  industry_class_minor_code: string; 
  industry_class_detail_code: string; 
  gross_floor_area: string; 
  electricity_supplier_no: string; 
  electricity_supplier_name: string; 
  menu_no: string | undefined; 
  menu_name: string; 
  ep_office_code: string; 
  ep_customer_number: string; 
  supply_point_number: string; 
  city_gas_supplier_no: string; 
  city_gas_supplier_name: string; 
  heat_supplier_no: string; 
  heat_supplier_name: string;
  heat_menu_number: string; 
  heat_menu_name: string; 
  energy_info: EnergyInfo[];
  registration_seq: number; 
};

export type BuildingInfoWithMenu = BuildingInfo & {
  select_menu?: {
    menu_no: string;
    menu_nm: string;
  }[];
};

export type ElectricCompanyList = {
  electric_company_reg_no: string; //企業コード
  electric_co_name: string; //
  select_menu: ElectricCompanyMenu[];
}

export  type EnergyRegisterRequest = {
  entry_draft_flag: string;
  corporate_number: string;
  agreement_category: string;
  org_id: string;
  start_year_month: string;
  end_year_month: string;
  fiscal_year: string;
  updated_building_info: any[];
};

export type ElectricityDataItem = {
  sum: number;
  year_month: string;
};

export type ElectricityResponse = {
    electricity_data: ElectricityDataItem[];
    unit: string; 
};

export type Option = {
  id : string;
  name :string;
};


export type Encoding = "utf-8" | "sjis" | "utf-8-sig";
