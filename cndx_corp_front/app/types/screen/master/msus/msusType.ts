// ユーザー情報登録管理IF

export type UserMasterState = {
  isLoading: boolean;
  hasPermission: boolean;
  searchCondition: {
    company_name: string;
    branch_name: string;
    user_name: string;
    user_status: string;
  };
  searchResults: UserInfoList[];
  showResults: boolean;
};

export type UserList = {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
};

export type MasterRequest =
  | string
  | {
      name: string;
      params?: Record<string, string>;
    };

export type UserInfoList = {
  user_id: string;
  org_id: string;
  company_name: string;
  branch_name: string;
  user_name: string;
  email_address: string;
  user_role: string;
  user_status: string;
  start_date: string;
  end_date: string;
  last_login_datetime: string;
  selected?: boolean;
};

export type UserInfoForm = {
  rows: UserInfoList[];
};

export type UserInfoRow = UserInfoList;

export type Encoding = "utf-8" | "sjis" | "utf-8-sig";
