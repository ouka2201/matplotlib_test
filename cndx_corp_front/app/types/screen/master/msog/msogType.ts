// お客さま詳細情報用IF

import { z } from "zod";
import { mscsSchema } from "~/lib/validations/mscs";

// 建物情報
export type Building = {
    org_id?: string;
    agreement_category: string;
    building_address_city: string;
    building_id: string;
    building_name: string;
    building_address_prefecture: string;
    ep_customer_number: string;
    group1?: string;
    group2?: string;
    group3?: string;
    group4?: string;
    group5?: string;
    supply_point_number: string;
    delete_flg?: boolean
};

// お客さま情報
export type CustomerCompany = {
    user_id?: string;
    usage_type?: string;
    company_name: string;
    company_name_kana: string;
    corporate_number: string;
    company_address_prefecture: string;
    company_address_city: string;
    consentInfo?: ConsentInfo;
    // numberField?: number;
    // calendarField?: Date | null;
    // calendarRangeField?: [undefined, undefined],
    // remarks?: string;
    office_info_list?: Building[];
};

// 不要 TODO
export type BuildingErrors ={
    company_name?: string;
    fulikana?: string;
    corpNm?: string;
    address?: string;
    addressInput?: string;
};

// 不要 TODO
export interface Customer {
    id: string;
    name: string;
    number: string;
    address: string;
}

// 同意書経路情報
export type ConsentInfo = {
    route1: string;
    route2: string;
    obtained_date: string;
    document_no: string;
};

/** コード：名称 コードマスタマッピング */
export interface CdNmOption {
    id: string;
    name: string;
}

export interface MCode {
    code: string;
    code_type: string;
    jp_code_name: string;
    target_year: string;
}

// 入力チェック用スキーマ
export type msogInputs = z.infer<typeof mscsSchema>;