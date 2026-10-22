// 建物グループマスタ用IF

// 建物グループマスタ
export type BuildingGroup = {
    corporate_number: string;
    agreement_category: string;
    org_id: string;
    group_id: string;
    group_name: string;
    select_item1: string;
    select_item2: string;
    select_item3: string;
    select_item4: string;
    select_item5: string;
    select_item6: string;
    select_item7: string;
};

export type AgreementCategoryMaster = {
    code : string;
    jp_code_name : string;
}

export type Encoding = "utf-8" | "sjis" | "utf-8-sig";