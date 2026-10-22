
const API_BASE = ""
 
export const API_ENDPOINTS = {
  LOGIN: {
    API_LOGIN: `${API_BASE}/api/login`,//ログインAPI
    API_LOGOUT: `${API_BASE}/api/logout`,//ログアウトAPI
    API_ANNOUCEMENT: `${API_BASE}/api/annoucement`,//お知らせ一覧照会API
  },
  USERS: {
    API_USERS_UPDATE: `${API_BASE}/api/user/update`,//ユーザ情報登録・更新API
    API_USERS_LIST: `${API_BASE}/api/user/list`,//ユーザ一覧検索API
    API_USERS_DETAIL: `${API_BASE}/api/user/detail`,//ユーザ情報照会API
    API_USERS_PASSWORD_CHANGE: `${API_BASE}/api/user/password/change`,//パスワード変更API
    API_USERS_HISTORY_LIST: `${API_BASE}/api/user/history/list`,//履歴照会API
  },
  CORP_ORG: {
    API_CORP_ORG_INFO_UPDATE: `${API_BASE}/api/user/mst_organization/corpration/auth_update`,//利用者組織情報更新API
    API_CORP_ORG_INFO_REGIST: `${API_BASE}/api/user/mst_organization/corpration/auth_register`,//利用者組織情報登録API
    API_CORP_ORG_INFO_LIST: `${API_BASE}/api/user/mst_organization/corpration/detail/auth`,//利用者組織情報検索API
    API_CORP_ORG_INFO_DETAIL: `${API_BASE}/api/user/mst_organization/corpration/detail/auth`,//利用者組織情報照会API
  },
  CUSTOMER_MASTER: {
    MASTER_REGIST: `${API_BASE}/api/mst_manage/corpration/info`,//企業基本情報登録API
    MASTER_LIST: `${API_BASE}/api/mst_manage/corpration/info`,//企業基本情報検索API
    MASTER_DETAIL: `${API_BASE}/api/master/detail`,//企業基本情報照会API
  },
  BUILDING:{
    BUILDING_UPDATE: `${API_BASE}/building/update`,//建物マスタ登録API
    BUILDING_LIST: `${API_BASE}/building/list`,//建物マスタ検索API
    BUILDING_DETAIL: `${API_BASE}/building/detail`,//建物マスタ照会API
    BUILDING_GROUP_MASTER_DETAIL: `${API_BASE}/building/group/master/detail`,//建物グループマスタ照会API
    BUILDING_GROUP_MASTER_UPDATE: `${API_BASE}/building/group/master/update`,//建物グループマスタ登録・更新API
    BUILDING_GROUP_SET: `${API_BASE}/building/group/set`,//グループ設定API
    BUILDING_INFO_DETAIL: `${API_BASE}/api/building/basic_info`,//建物情報照会API
  },
  ENERGY:{
    BUILDING_ENERGY_INFO: `${API_BASE}/building/energy_info`,//建物・エネルギー情報登録・更新API
    BUILDING_ENERGY_INFO_DETAIL: `${API_BASE}/building/energy_info/detail`,//建物・エネルギー情報照会API
    BUILDING_PER_30M_DATA_UPDATE: `${API_BASE}/building/per_30m_data/update`,//30分値登録API
    BUILDING_PER_30M_DATA_LIST: `${API_BASE}/building/per_30m_data/list`,//30分値検索API
    BUILDING_PER_30M_DATA_DELETE: `${API_BASE}/building/per_30m_data/delete`,//30分値削除API
  },
  REPORT:{
    REPORT_STATUS_LIST: `${API_BASE}/report/status/list`,//レポートステータス検索API
    REPORT_PDF_CN_REPORT_CREATE: `${API_BASE}/report/pdf/cn_report/create`,//CNレポートレポートPDF作成API
    REPORT_PDF_VISUALIZE_REPORT_CREATE: `${API_BASE}/report/pdf/visualize_report/create`,//電力使用状況見える化レポートPDF作成API
    REPORT_PDF_LACKAGE_LIST_CREATE: `${API_BASE}/report/pdf/lackage_list/create`,//欠損一覧PDF作成API
    REPORT_CSV_KPI_LIST_CREATE: `${API_BASE}/report/csv/kpi_list/create`,//KPI一覧CSV作成API
  },
  CN_EMISSION:{
    CN_EMISSION_CSV_EXPORT: `${API_BASE}/cn_emission/csv/export`,//CO2排出量集計CSV作成/ダウンロードAPI
  },
  UPLODE:{
    API_FILE_HEARING_DATA: `${API_BASE}/api/file/hearing_data`,//ファイル(ヒアリングデータ)アップロードチェックAPI
    API_FILE_PER_30M_DATA: `${API_BASE}/api/file/per_30m_data`,//ファイル(30分値データ)アップロードチェックAPI
    API_FILE_BUILDING_MASTER_DATA: `${API_BASE}/api/file/buiding_master_data`,//ファイル(建物マスタデータ)アップロードチェックAPI
    API_FILE_INPUT_SHEET: `${API_BASE}/api/file/input_sheet`,//ファイル(行員向け入力シートデータ)アップロードチェックAPI
    API_FILE_ENERGY_DATA: `${API_BASE}/api/file/energy_data`,//ファイル(エネルギーデータ)アップロードチェックAPI
    API_FILE: `${API_BASE}//api/file`,//ファイルダウンロードAPI
    API_FILE_STATIC_FILE: `${API_BASE}//api/file/static_file`,//静的ファイルアップロードAPI
  },
  CONTACT_PERSON: {
    API_CONTACT_PERSON_DETAIL: `${API_BASE}/api/contact-person/detail`, // 担当者情報取得API
    API_CONTACT_PERSON_ADD_USER_INQUIRY: `${API_BASE}/api/contact-person/addUser/inquiry`, // 担当者のユーザーIDによるユーザー情報取得API
    API_CONTACT_PERSON_UPDATE: `${API_BASE}/api/contact-person/update`, // 担当者情報登録API
  }
} as const;