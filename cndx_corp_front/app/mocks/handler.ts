import { http, HttpResponse } from "msw";
import {
  BuildingGroup,
  AgreementCategoryMaster,
} from "~/types/screen/master/msmg/msmgType";
import {
  EnergyRegisterRequest,
} from "~/types/screen/energy-building/ebmg/ebmgType";
import { ebmg03MockData, ebmg03AutoFillElectricityMockData } from "~/mocks/ebmg03Mock";

//const BASE_URL = process.env.VITE_API_URL

// モックデータの型定義
type CustomerResponseItem = {
  bank_code: string; //拠点情報
  bank_name: string; //金融機関名
  branch_code: string; //支店コード
  branch_name: string; //支店名
  user_cd: string; //担当者コード
  user_name: string; //担当名
  corporate_number: string; //法人番号
  corporation_name: string; //企業名
  building_id: string; //建物ID
  fiscal_year: string; //対象年度
  registration_seq: number; //登録回数
  report_status: string; //ステータス
  report_location: string; //PDF格納先
  creation_datetime: string; //作成日時
  creator: string; //作成者
  delete_flg: string; //削除フラグ
  file_id: string; //ファイルID
  report_type: string; //レポート区分
  update_datetime: string; //更新日時
  updateor: string; //更新者
};

// POSTリクエストのパラメータ用型
type PostRequestData = {
  task_id: string;
  creation_info: {
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    fiscal_year: string;
    registration_seq: string;
    current_status: string;
  };
};

// モックデータ
const mockData: CustomerResponseItem[] = [
  {
    bank_code: "001",
    bank_name: "A銀行",
    branch_code: "101",
    branch_name: "A本店",
    user_cd: "U001",
    user_name: "山田 太郎",
    corporate_number: "1234567890123",
    corporation_name: "ABC株式会社",
    building_id: "B001",
    fiscal_year: "2024",
    registration_seq: 2,
    report_status: "2",
    report_location: "/storage/pdf/abc_2024.pdf",
    creation_datetime: "2024-01-10 10:00:00",
    creator: "admin",
    delete_flg: "0",
    file_id: "F001",
    report_type: "1",
    update_datetime: "2024-01-15 12:00:00",
    updateor: "user123",
  },
  {
    bank_code: "002",
    bank_name: "B金庫",
    branch_code: "202",
    branch_name: "B支店",
    user_cd: "U002",
    user_name: "佐藤 次郎",
    corporate_number: "9876543210987",
    corporation_name: "XYZ合同会社",
    building_id: "B002",
    fiscal_year: "2024",
    registration_seq: 1,
    report_status: "0",
    report_location: "/storage/pdf/xyz_2023.pdf",
    creation_datetime: "2020-12-20 15:30:00",
    creator: "user456",
    delete_flg: "0",
    file_id: "F002",
    report_type: "収支報告",
    update_datetime: "2024-01-05 09:45:00",
    updateor: "admin",
  },
  {
    bank_code: "003",
    bank_name: "C銀行",
    branch_code: "303",
    branch_name: "C支店",
    user_cd: "U003",
    user_name: "高橋 花子",
    corporate_number: "4561237890456",
    corporation_name: "DEF株式会社",
    building_id: "B003",
    fiscal_year: "2022",
    registration_seq: 3,
    report_status: "1",
    report_location: "/storage/pdf/def_2022.pdf",
    creation_datetime: "2022-11-15 08:20:00",
    creator: "user789",
    delete_flg: "1",
    file_id: "F003",
    report_type: "監査報告",
    update_datetime: "2023-01-10 14:10:00",
    updateor: "admin",
  },
  {
    bank_code: "004",
    bank_name: "D銀行",
    branch_code: "404",
    branch_name: "D支店",
    user_cd: "U004",
    user_name: "田中 一郎",
    corporate_number: "7890123456789",
    corporation_name: "GHI株式会社",
    building_id: "B004",
    fiscal_year: "2021",
    registration_seq: 5,
    report_status: "9",
    report_location: "/storage/pdf/ghi_2021.pdf",
    creation_datetime: "2022-11-15 19:50:00",
    creator: "user999",
    delete_flg: "0",
    file_id: "F004",
    report_type: "財務諸表",
    update_datetime: "2022-12-30 16:30:00",
    updateor: "admin",
  },
];

// GETリクエストのモックハンドラー
const getHandler = http.get(
  "http://localhost:5173/api/report/status/inquiry",
  async ({ request }) => {
    try {
      // リクエストのクエリパラメータを取得
      const url = new URL(request.url);
      const params = Object.fromEntries(url.searchParams.entries());

      console.log("受け取った検索パラメータ:", params);

      // 入力された検索条件の数をカウント（どの項目が検索対象になっているか）
      const activeSearchFields = Object.keys(params).filter(
        (key) => params[key] !== "" && params[key] !== undefined
      ).length;

      // 条件に一致するデータを取得（AND 条件）
      const filteredData = mockData.filter((item) => {
        let matchCount = 0;

        if (params.bank_code && item.bank_code.includes(params.bank_code))
          matchCount++;
        if (params.bank_name && item.bank_name.includes(params.bank_name))
          matchCount++;
        if (
          params.corporation_name &&
          item.corporation_name.includes(params.corporation_name)
        )
          matchCount++;
        if (params.fiscal_year && item.fiscal_year.includes(params.fiscal_year))
          matchCount++;
        if (
          params.creation_date_from &&
          new Date(item.creation_datetime) >=
            new Date(params.creation_date_from)
        )
          matchCount++;
        if (
          params.creation_date_to &&
          new Date(item.creation_datetime) <= new Date(params.creation_date_to)
        )
          matchCount++;
        if (
          params.input_sheet_name &&
          item.report_type.includes(params.input_sheet_name)
        )
          matchCount++;
        if (params.report_status && item.report_status === params.report_status)
          matchCount++;

        // 全ての入力条件に一致する場合のみ表示（AND 条件）
        return matchCount === activeSearchFields;
      });

      console.log("フィルタリング後のデータ:", filteredData);

      return HttpResponse.json(
        { report_info_list: filteredData },
        { status: 200 }
      );
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

// POSTリクエストをモック
const postHandler = http.post(
  "http://localhost:5173/api/report/pdf/create",
  async ({ request }) => {
    try {
      // フロントから送られるJSONデータを解析
      const data = (await request.json()) as PostRequestData; // 型アサーションを追加
      console.log("受け取ったデータ:", data);

      const {
        task_id,
        creation_info: {
          bank_code,
          branch_code,
          corporate_number,
          fiscal_year,
          registration_seq,
          current_status,
        },
      } = data;

      // 必要なパラメーターが全て存在するかをチェック
      if (
        !task_id ||
        !bank_code ||
        !branch_code ||
        !corporate_number ||
        !fiscal_year ||
        !registration_seq ||
        !current_status
      ) {
        return HttpResponse.json(
          { error_message_list: "必須パラメーターが不足しています。" },
          { status: 400 }
        );
      }

      // データが正常に送信されている場合
      console.log("受信したデータ:", data);

      // task_id を数値に変換
      const task_id_num = Number(task_id);

      // 数値に変換できない場合はエラー
      if (isNaN(task_id_num)) {
        return HttpResponse.json(
          { error_message_list: "task_id は数値である必要があります。" },
          { status: 400 }
        );
      }

      if (task_id_num === 0) {
        // **成功時**
        return HttpResponse.json(
          {
            message: "PDF作成のリクエストが正常に処理されました。",
            report_location: `/storage/pdf/${corporate_number}_${fiscal_year}.pdf`,
          },
          { status: 200 }
        );
      } else if (task_id_num >= 1) {
        // **処理待ち**
        return HttpResponse.json(
          {
            message: "処理中",
            task_id: 1,
            pending_task_seq: 2,
          },
          { status: 200 }
        );
      } else {
        // **失敗時**
        return HttpResponse.json(
          { error_message_list: "無効な順番が割り振られました" },
          { status: 400 }
        );
      }
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

// POSTリクエストでPDFを生成
const postPdfHandler = http.post(
  "http://localhost:5173/api/report/pdf/output", // ここはPOST先のエンドポイント
  async ({ request }) => {
    try {
      // フロントから送られるJSONデータを解析
      const data = await request.json();
      console.log("受け取ったデータ:", data);

      // モック用のPDFファイルのURLを指定
      const pdfUrl = "/mock-data/dashboard.pdf"; // 正しいURLに合わせてください

      // PDFをバイナリで取得
      const pdfResponse = await fetch(pdfUrl);

      if (!pdfResponse.ok) {
        throw new Error("PDFファイルの取得に失敗しました");
      }

      const pdfArrayBuffer = await pdfResponse.arrayBuffer();

      // PDFレスポンスを返す
      return new HttpResponse(pdfArrayBuffer, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": `attachment; filename="mock-report.pdf"`,
        },
      });
    } catch (error) {
      console.error("PDF生成エラー:", error);
      return new HttpResponse("PDFの生成に失敗しました", { status: 500 });
    }
  }
);

//ここからinput_dataのモック

const inputMockData = [
  {
    basic_info: {
      //department_branch_name: "東京事業所",
      area_information: "東京事業所",
      building_name: "東京ビル",
      industry_category_small: "1234",
      address: "東京都千代田区",
      gross_floor_area: "1000",
      electric_power_corporate_name: "東京",
      ep_store_number: "TOKYO-001",
      customer_number_ep: "123456789",
      supply_point_number: "987654321",
      contracted_power: "500",
      start_year: "2024",
      start_month: "4",
    },
    energy_usage_info: {
      import_raw_charcoal: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
      coking_coal: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60],
      pci_coal: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36],
      jet_fuel: [37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48],
      city_gas: [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200],
      electric_power: [
        100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210,
      ],
    },
  },
  {
    basic_info: {
      //department_branch_name: "大阪事業所",
      area_information: "大阪事業所",
      building_name: "大阪ビル",
      industry_category_small: "5678",
      address: "大阪府大阪市",
      gross_floor_area: "1200",
      electric_power_corporate_name: "関西",
      ep_store_number: "KANSAI-001",
      customer_number_ep: "987654321",
      supply_point_number: "123456789",
      contracted_power: "600",
      start_year: "2024",
      start_month: "1",
    },
    energy_usage_info: {
      import_ordinary_charcoal: [
        15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125,
      ],
      domestic_standard_coal: [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
      import_smokeless_coal: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      kerosene: [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61],
      industrial_steam: [
        200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750,
      ],
      electric_power: [
        150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260,
      ],
    },
  },
  {
    basic_info: {
      //department_branch_name: "名古屋事業所",
      area_information: "名古屋事業所",
      building_name: "名古屋ビル",
      industry_category_small: "9101",
      address: "愛知県名古屋市",
      gross_floor_area: "1300",
      electric_power_corporate_name: "名古屋",
      ep_store_number: "NAGOYA-001",
      customer_number_ep: "117114311",
      supply_point_number: "122422722",
      contracted_power: "700",
      start_year: "2024",
      start_month: "9",
    },
    energy_usage_info: {
      import_raw_charcoal: [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61],
      import_ordinary_charcoal: [
        18, 23, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125,
      ],
      import_smokeless_coal: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      petroleum_coke: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      fcc_coke: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      coal_tar: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      petroleum_asphalt: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      crude_oil_condensate: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
      crude_oil_condensate_except: [
        30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
      ],
      city_gas: [200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750],
      cold_water: [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
      electric_power: [
        150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260,
      ],
    },
  },
];

// GETリクエストのモックハンドラー
export const getInputDataHandler = http.get(
  "http://localhost:5173/api/input",
  async () => {
    try {
      // 期待されるデータ形式で返す
      return HttpResponse.json(inputMockData, { status: 200 });
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

// POSTリクエストをモック

const postExcelMockHandler = http.post(
  "http://localhost:5173/api/file/check-transfer",
  async ({ request }) => {
    try {
      const formData = await request.formData();
      const file = formData.get("file");

      // ファイルが送信されていない場合の処理
      if (!file || !(file instanceof File)) {
        console.error("不正なファイルデータが送信されました:", file);
        return HttpResponse.json(
          {
            error_message_list:
              "送信されたデータに有効なファイルが含まれていません。",
          },
          { status: 400 }
        );
      }

      // ファイル拡張子のチェック
      const fileExtension = file.name.slice(file.name.lastIndexOf("."));
      const allowedExtensions = [".tsx", ".csv", ".xlsx"];
      if (!allowedExtensions.includes(fileExtension)) {
        console.error("許可されていないファイル形式:", file.name);
        return HttpResponse.json(
          { error_message_list: "許可されていないファイル形式です。" },
          { status: 400 }
        );
      }

      // 正常レスポンス
      console.log("アップロードされたファイル:", file.name);
      return HttpResponse.json(
        { success_message: "ファイルが正常にアップロードされました。" },
        { status: 200 }
      );
    } catch (error) {
      console.error("エラー発生:", error);
      // エラーが発生した場合は500エラーを返す
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

const buildingListMockData = {
  building_info_list: [
    {
      agreement_category: "0A0A001",
      building_address_prefecture: "東京都",
      building_address_city: "台東区",
      building_id: "101",
      building_name: "A本店",
      corporate_number: "0000000000001",
      created_at: "2024-01-10T10:00:00Z",
      ep_customer_number: "1234512345001",
      group1: "1",
      group2: "1",
      group3: "1",
      group4: "2",
      group5: "2",
      supply_point_number: "1111222233334444555501",
      updated_at: "2024-01-15T12:00:00Z",
      industry_code: "111",
      industry_name: "製造業",
      ep_office_code: "EP001",
      benchmark_denom: "1000",
      benchmark_val: "50",
      building_consent_flag: "有",
    },
    {
      agreement_category: "0A0A002",
      building_address_prefecture: "大阪府",
      building_address_city: "堺市",
      building_id: "102",
      building_name: "B工場",
      corporate_number: "0000000000002",
      created_at: "2023-12-05T09:00:00Z",
      ep_customer_number: "1234512345002",
      group1: "2",
      group2: "2",
      group3: "2",
      group4: "3",
      group5: "1",
      supply_point_number: "1111222233334444555502",
      updated_at: "2024-02-01T14:30:00Z",
      industry_code: "112",
      industry_name: "建設業",
      ep_office_code: "EP002",
      benchmark_denom: "2000",
      benchmark_val: "30",
      building_consent_flag: "無",
    },
    {
      agreement_category: "0A0A001",
      building_address_prefecture: "北海道",
      building_address_city: "札幌市",
      building_id: "103",
      building_name: "C倉庫",
      corporate_number: "0000000000003",
      created_at: "2024-03-20T11:15:00Z",
      ep_customer_number: "1234512345003",
      group1: "3",
      group2: "3",
      group3: "3",
      group4: "1",
      group5: "3",
      supply_point_number: "1111222233334444555503",
      updated_at: "2024-04-01T10:45:00Z",
      industry_code: "113",
      industry_name: "物流業",
      ep_office_code: "EP003",
      benchmark_denom: "3000",
      benchmark_val: "40",
      building_consent_flag: "有",
    },
  ],
  group_setting_info: [
    {
      agreement_category: "0A0A001",
      group_id: "1",
      group_name: "エリア大",
      group_options: ["関東", "関西", "北海道", "中部"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A001",
      group_id: "2",
      group_name: "建物種別",
      group_options: ["事務所", "工場", "倉庫", "店舗"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A001",
      group_id: "3",
      group_name: "使用目的",
      group_options: ["自社利用", "賃貸", "未使用"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A001",
      group_id: "4",
      group_name: "築年数区分",
      group_options: ["10年未満", "10～20年", "20年以上"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A002",
      group_id: "1",
      group_name: "確認",
      group_options: ["確認１", "確認２", "確認３"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A002",
      group_id: "4",
      group_name: "対象年",
      group_options: ["~2000年", "2001~2010年", "2011~2020年", "2021~2030年"],
      org_id: "777",
      corporate_number: "0001",
    },
    {
      agreement_category: "0A0A001",
      group_id: "5",
      group_name: "耐震等級",
      group_options: ["等級1", "等級2", "等級3"],
      org_id: "777",
      corporate_number: "0001",
    },
  ],
};
const getBuildingListHandler = http.get(
  "http://localhost:5173/api/building/info",
  async () => {
    try {
      return HttpResponse.json(
        {
          building_info_list: buildingListMockData.building_info_list,
          group_setting_info: buildingListMockData.group_setting_info,
        },
        { status: 200 }
      );
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

type ebmv02ResponseItem = {
  agreement_category: string;
  org_id: string;
  org_name: string;
  user_id: string;
  user_name: string;
  company_name: string;
  corporate_number: string;
  company_address_prefecture: string;
  company_address_city: string;
  building_id: string;
  building_name: string;
  building_address_prefecture: string;
  building_address_city: string;
  ep_customer_number: string;
};

// モックデータ
const ebmv02MockData: ebmv02ResponseItem[] = [
  {
    agreement_category: "9",
    org_id: "ORG001",
    org_name: "第一組織",
    user_id: "U001",
    user_name: "佐藤 太郎",
    company_name: "株式会社A",
    corporate_number: "1234567890123",
    company_address_prefecture: "東京都",
    company_address_city: "新宿区",
    building_id: "B001",
    building_name: "え新宿ビルA",
    building_address_prefecture: "東京都",
    building_address_city: "新宿区",
    ep_customer_number: "EP123456",
  },
  {
    agreement_category: "1BNK0142",
    org_id: "BNK0142101",
    org_name: "地銀名",
    user_id: "U002",
    user_name: "鈴木 次郎",
    company_name: "合同会社B",
    corporate_number: "9876543210987",
    company_address_prefecture: "大阪府",
    company_address_city: "大阪市",
    building_id: "B002",
    building_name: "い大阪ビルB",
    building_address_prefecture: "大阪府",
    building_address_city: "大阪市",
    ep_customer_number: "EP987654",
  },
  {
    agreement_category: "1TEP",
    org_id: "TEP",
    org_name: "EP",
    user_id: "U003",
    user_name: "高橋 花子",
    company_name: "株式会社C",
    corporate_number: "4561237890456",
    company_address_prefecture: "愛知県",
    company_address_city: "名古屋市",
    building_id: "B003",
    building_name: "う名古屋ビルC",
    building_address_prefecture: "愛知県",
    building_address_city: "名古屋市",
    ep_customer_number: "EP456789",
  },
  {
    agreement_category: "1REP002",
    org_id: "REP002",
    org_name: "REP会社名",
    user_id: "U002",
    user_name: "花山 花子",
    company_name: "株式会社D",
    corporate_number: "9876543210444",
    company_address_prefecture: "大阪府",
    company_address_city: "大阪市北区",
    building_id: "D002",
    building_name: "あ梅田ビルD",
    building_address_prefecture: "大阪府",
    building_address_city: "大阪市北区",
    ep_customer_number: "EP654444",
  },
];

// モックハンドラー
const ebmv02Handler = http.get(
  "http://localhost:5173/api/corp/building/list",
  async ({ request }) => {
    try {
      console.log("送信されたURL:", request.url);
      const url = new URL(request.url);
      const params = Object.fromEntries(url.searchParams.entries());

      console.log("受け取った検索パラメータ:", params);

      const activeSearchFields = Object.keys(params).filter(
        (key) => params[key] !== "" && params[key] !== undefined
      ).length;

      const filteredData = ebmv02MockData.filter((item) => {
        let matchCount = 0;

        if (params.org_id && item.org_id.includes(params.org_id)) matchCount++;
        if (params.user_name && item.user_name.includes(params.user_name))
          matchCount++;
        if (
          params.company_name &&
          item.company_name.includes(params.company_name)
        )
          matchCount++;
        if (
          params.corporate_number &&
          item.corporate_number.includes(params.corporate_number)
        )
          matchCount++;
        if (
          params.agreement_category &&
          item.agreement_category === params.agreement_category
        )
          matchCount++;

        return matchCount === activeSearchFields;
      });

      console.log("フィルタリング後のデータ:", filteredData);

      // ここで、モックの返却は result プロパティでラップ
      return HttpResponse.json({ result: filteredData }, { status: 200 });
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);

// モックデータ
const msbg01MockData: BuildingGroup[] = [
  {
    corporate_number: "2025042100104",
    agreement_category: "03",
    org_id: "TEP",
    group_id: "2025042100104011",
    group_name: "エリア",
    select_item1: "北海道・東北",
    select_item2: "関東",
    select_item3: "中部",
    select_item4: "近畿",
    select_item5: "中国",
    select_item6: "四国",
    select_item7: "九州・沖縄",
  },
  {
    corporate_number: "2025042100104",
    agreement_category: "03",
    org_id: "TEP",
    group_id: "2025042100104012",
    group_name: "お茶",
    select_item1: "麦茶",
    select_item2: "",
    select_item3: "ルイボスティー",
    select_item4: "緑茶",
    select_item5: "",
    select_item6: "ほうじ茶",
    select_item7: "コーン茶",
  },
  {
    corporate_number: "2025042100104",
    agreement_category: "03",
    org_id: "TEP",
    group_id: "2025042100104013",
    group_name: "野菜",
    select_item1: "キャベツ",
    select_item2: "",
    select_item3: "白菜",
    select_item4: "レタス",
    select_item5: "",
    select_item6: "",
    select_item7: "",
  },
  {
    corporate_number: "2025042100104",
    agreement_category: "03",
    org_id: "TEP",
    group_id: "2025042100104014",
    group_name: "惑星",
    select_item1: "",
    select_item2: "",
    select_item3: "",
    select_item4: "",
    select_item5: "",
    select_item6: "",
    select_item7: "地球",
  },
  {
    corporate_number: "2025042100104",
    agreement_category: "03",
    org_id: "TEP",
    group_id: "2025042100104015",
    group_name: "風邪",
    select_item1: "鼻",
    select_item2: "",
    select_item3: "",
    select_item4: "",
    select_item5: "",
    select_item6: "",
    select_item7: "のど",
  },
  {
    corporate_number: "2025042100104",
    agreement_category: "04",
    org_id: "REP002",
    group_id: "2025042100104025",
    group_name: "春夏秋冬",
    select_item1: "春",
    select_item2: "夏",
    select_item3: "秋",
    select_item4: "冬",
    select_item5: "",
    select_item6: "",
    select_item7: "",
  },
];

const agreementCategoryMasterMock: AgreementCategoryMaster[] = [
  {
    code: "03",
    jp_code_name: "可視化アライアンス（アスエネ）",
  },
  {
    code: "04",
    jp_code_name: "可視化アライアンス（ゼロボード）",
  },
  {
    code: "05",
    jp_code_name: "可視化アライアンス（ブースト）",
  },
  {
    code: "06",
    jp_code_name: "可視化アライアンス（JFS）",
  },
];

// モックハンドラー
const msbg01GetHandler = http.get(
  `http://localhost:5173/api/building/group/master/detail`,
  async ({ request }) => {
    try {
      console.log("送信されたURL:", request.url);
      const url = new URL(request.url);
      const params = Object.fromEntries(url.searchParams.entries());

      console.log("受け取った検索パラメータ:", params);
      console.log(
        "user_id（org_id取得用・フィルタには未使用）:",
        params.user_id
      );

      const activeSearchFields = Object.keys(params).filter(
        (key) =>
          key !== "user_id" && // ← user_id はフィルタ対象から除外
          params[key] !== "" &&
          params[key] !== undefined
      ).length;

      const filteredData = msbg01MockData.filter((item) => {
        let matchCount = 0;

        if (
          params.corporate_number &&
          item.corporate_number.includes(params.corporate_number)
        )
          matchCount++;

        if (
          params.agreement_category &&
          item.agreement_category === params.agreement_category
        )
          matchCount++;

        return matchCount === activeSearchFields;
      });

      console.log("フィルタリング後のデータ:", filteredData);

      return HttpResponse.json(
        {
          result: {
            building_group_info: filteredData,
            agreement_category_master_info: agreementCategoryMasterMock,
          },
        },
        { status: 200 }
      );
    } catch (error) {
      console.error("リクエスト処理中にエラーが発生しました:", error);
      return HttpResponse.json(
        { error_message_list: "サーバーでエラーが発生しました。" },
        { status: 500 }
      );
    }
  }
);
const msbg01PostHandler = [
  // 登録・更新の正常系 / 異常系
  http.post("/api/building/group/master/update", async ({ request }) => {
    const body = await request.json();

    console.log("MOCK: 登録リクエスト受信:", body);

    const url = new URL(request.url);
    const shouldFail = url.searchParams.get("fail") === "true";

    if (shouldFail) {
      return new Response(
        JSON.stringify({ message: "不正な入力です（モック）" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response(
      JSON.stringify({ message: "登録成功（モック）", result: true }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  }),
];

export const ebmg03PostHandler = http.post(
  "/api/building/energy-info/detail",
  async ({ request }) => {
    try {
      const body = await request.json();
      console.log("MOCK: 受信したPOSTデータ:", body);

      return HttpResponse.json(
        {
          result: ebmg03MockData,
        },
        { status: 200 }
      );
    } catch (error) {
      console.error("MOCK: データ取得中にエラーが発生しました:", error);
      return HttpResponse.json(
        {
          error_message_list:
            "サーバーエラーが発生しました。管理者に連絡してください。",
        },
        { status: 500 }
      );
    }
  }
);


export const ebmg03UpdatePostHandler = [
  http.post("/api/building/energy-register", async ({ request }) => {
    const body = await request.json() as EnergyRegisterRequest;

    console.log("MOCK: エネルギー情報登録リクエスト受信:", body);

    const url = new URL(request.url);
    const shouldFail = url.searchParams.get("fail") === "true";

    const draftFlag = body.entry_draft_flag;
    if (draftFlag !== "0" && draftFlag !== "1") {
      return new Response(
        JSON.stringify({ message: "entry_draft_flag が不正です（モック）" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    if (shouldFail) {
      return new Response(
        JSON.stringify({ message: "登録に失敗しました（モック）" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response(
      JSON.stringify({
        ok: true,
        registration_seq: 13,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  }),
];

export const ebmg03AutoFillElectricityHandler = http.post(
  "/api/building/energy-info/auto",
  async ({ request }) => {
    try {
      const body = await request.json();
      console.log("MOCK: 電力自動入力API 受信POSTデータ:", body);

      return HttpResponse.json(
        {
          result: ebmg03AutoFillElectricityMockData,
        },
        { status: 200 }
      );
    } catch (error) {
      console.error("MOCK: 電力自動入力API エラー:", error);
      return HttpResponse.json(
        {
          error_message_list:
            "サーバーエラーが発生しました。管理者に連絡してください。",
        },
        { status: 500 }
      );
    }
  }
);

// ハンドラーをまとめてエクスポート
export const handlers = [
  getHandler,
  postHandler,
  postPdfHandler,
  getInputDataHandler,
  postExcelMockHandler,
  getBuildingListHandler,
  ebmv02Handler,
  msbg01GetHandler,
  ...msbg01PostHandler,
  ebmg03PostHandler,
  ...ebmg03UpdatePostHandler,
  ebmg03AutoFillElectricityHandler,
];
