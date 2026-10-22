export const Messages = {
  // 共通
  REQUIRED: "必須項目です。",
  INVALID_EMAIL: "有効なメールアドレスを入力してください。",
  UNKNOWN_ERROR: "予期せぬエラーが発生しました。",
  VALIDATION_ERROR: "入力値が不正です。",
  SYSTEM_ERROR: "システムエラーが発生しました。",
  CONFIRM_ERROR_ITEMS: "エラー項目を確認してください。",

  // ログイン関連
  LOGIN_FAILED: "ログインに失敗しました。IDまたはパスワードをご確認ください。",
  LOGIN_SUCCESS: "ログインしました。",

  // フォーム関連
  FORM_SUBMIT_SUCCESS: "送信が完了しました。",
  FORM_SUBMIT_ERROR: "送信に失敗しました。再度お試しください。",

  // 登録関連
  REGISTER_SUCCESS: "登録が完了しました。",
  REGISTER_ERROR: "登録時にエラーが発生しました。",
  REGISTER_FAILED: "登録に失敗しました。システム管理者に連絡してください。",
  SAVE_SUCCESS: "保存が完了しました。",
  SAVE_ERROR: "保存時にエラーが発生しました。",
  SAVE_FAILED: "保存に失敗しました。システム管理者に連絡してください。",

  //削除関連
  DELETED_SUCCESS: "削除が完了しました。",
  DELETED_ERROR: "削除時にエラーが発生しました。",
  DELETED_FAILED: "削除に失敗しました。システム管理者に連絡してください。",

  // ダウンロード
  PDF_DOWNLOAD_SUCCESS: "PDFダウンロードに成功しました。",

  // ユーザー関連
  USER_CREATED: "ユーザーを作成しました。",
  USER_UPDATED: "ユーザー情報を更新しました。",
  USER_DELETED: "ユーザーを削除しました。",

  // お客さま関連
  CORP_SEARCH_NONE: "該当するお客さまが見つかりません。",

  // 電気事業者
  ELECTRIC_SEARCH_NONE: "該当する電気事業者が見つかりません。",

  // 都市ガス事業者
  CITYGAS_SEARCH_NONE: "該当する都市ガス供給事業者が見つかりません。",

  // 熱供給事業者
  HEAT_SEARCH_NONE: "該当する熱供給事業者が見つかりません。",

  // 該当データなし
  SEARCH_NONE: "該当するデータが見つかりません。",

  AGREEMENT_CATEGORY: {
    unselected: "同意書取得経路を選択してください。",
    none: "候補が見つかりません。",
  },

  // バリデーションメッセージ例（項目名 + 定数）
  VALIDATION: {
    name: {
      required: "名前は必須です。",
      maxLength: "名前は50文字以内で入力してください。",
    },
    email: {
      required: "メールアドレスは必須です。",
      invalid: "メールアドレスの形式が不正です。",
    },
    corporate_number: {
      required: "法人番号は必須です。",
      error: "法人番号が取得できませんでした。",
    },
    agreement_category: {
      error: "同意書取得経路の取得に失敗しました。",
    },
    form: {
      error: "フォームにエラーがあります。",
    },
    api: {
      error: "APIリクエスト処理に失敗しました。",
      corp_search_error: "お客さま情報の取得に失敗しました。",
      top_error: "お知らせの取得に失敗しました。",
      search_error: "検索に失敗しました。",
      fetch_error: "データの取得に失敗しました。",
      load_error: "データの読み込みに失敗しました。",
      empty_response: "APIから空のレスポンスを受け取りました。",
    },
    data: {
      invalid: "データの形式が正しくありません。",
      unselected: "対象データを選択してください。",
      none: "該当するデータが存在しません。",
      token_none: "No token found in session.",
      email_none: "No email (user_id) found in session.",
      session_none: "Session data is not available.",
      fetch_master_error: "マスタの取得に失敗しました。",
      sent_url: "送信のURL:",
      raw: "raw:",
    },
    file: {
      invalid: "許可されていないファイル形式です。",
      unselected: "ファイルを選択してください。",
    },
  },
  // バリデーション（関数形式で項目名を可変に）
  validation: {
    required: (field: string) => `${field}は必須項目です。入力してください。`,
    maxLength: (field: string, max: number) => `${field}は${max}文字以内で入力してください。`,
    invalidField: () => `入力形式が正しくありません。`,
  },
  common: {
    confirm: "この内容で登録を実行してもよろしいですか？",
    pulldown_default: "選択してください",
  },
  building_list: {
    customer_data: "受け取ったcustomerData: ",
    search_condition: "検索条件: ",
    clicked_button: "ボタンがクリックされました",
    available_token: "Token is available, loading items...",
    feature_date_unselectable: "未来日は選択できません。",
    invalid_start_date: "開始日は終了日を超えています。",
    invalid_end_date: "終了日は開始日より前に設定できません。",
    select_checkbox_target: "チェックボックスで対象を選択してください。",
    select_group: "グループと選択肢を選択してください。",
    group_none: "グループ設定が見つかりません。",
    invalid_option: "選択肢が正しくありません。",
    group_update_error: "グループ更新に失敗しました。",
  },
  master: {
    msbg01: {
      update_success: "拠点グループの設定が正常に更新されました。",
      invalid_data: "無効なデータ項目:",
      changed_item_none: "変更された内容がありません。",
    },
    msus01: {
      user_status_unsekected: "ステータスを選択してください。",
      csv_download_failed: "CSVの取得に失敗しました。",
      csv_download_error: "CSVダウンロード中にエラーが発生しました。",
      no_update_target_rows: "更新対象となる変更行がありません。",
      force_logout_failed: "ユーザーの強制ログアウトに失敗しました。",
      logout_target_not_selected: "ログアウト対象のユーザーが選択されていません。",
      session_expired: "セッションが切れました。再ログインしてください。",
      user_update_failed: "ユーザー情報の更新に失敗しました。",
    },
  },
  energy_building: {
    ebmv01: {
      session_error: "セッションの取得に失敗しました。",
      file_unselected: "ファイルを選択してください。",
      file_type_error: "アップロードできるファイル形式はcsvのみです。",
      file_loading_failed: "ファイルの読み込みに失敗しました。",
    },
    ebrc01: {
      json_error: "JSONの解析エラー:",
      invalid_json_response: "レスポンスは有効なJSONではありません:",
      invalid_response: "レスポンス形式が正しくありません。",
      location_unselected: "拠点を選択してください。",
      period_unselected: "期間を選択してください。",
      report_type_unselected: "レポートタイプを選択してください。",
      agreement_category_unselected: "同意書取得経路を選択してください。",
      org_name_unselected: "登録組織名を選択してください。",
      group_location_type_unselected: "少なくとも1つのグループと拠点タイプを選択してください。",
      group_unselected: "グループを選択してください。",
      location_type_unselected: "拠点タイプを選択してください。",
      create_multi_location_report_error: "複数拠点レポートの作成に失敗しました。",
      create_single_location_report_error: "単一拠点レポートの作成に失敗しました。",
      location_none: "選択した条件に一致する拠点が見つかりませんでした。",
      filter_error: "絞り込み処理中にエラーが発生しました。",
      confirm: "選択した条件でレポートを作成します。よろしいですか？",
      close: "入力中の内容は保存されません。本当に閉じてもよろしいですか？",
      file_path_unselected: "ファイルパスが未設定です",
      file_name_error: "ファイル名の抽出に失敗しました",
      create_request_accepted: "CNカルテ作成のリクエストを受け付けました",
      cn_karte_creating: "CNカルテを作成中です。\nしばらく経ってから画面を更新してください。",
    },
    ebrc03: {
      industry_response_data: "industry response data:",
      industry_data_fetch_failed: "産業分類データの取得に失敗しました。",
      industry_data_fetch_error: "産業分類データの取得中にエラーが発生しました。",
      update_success: "お客さま情報の設定が正常に更新されました。",
    },
    ebrc04: {
      token_error: "token が取得できませんでした。",
      period_duplicate_error: "すでに登録されています。",
      period_input_none: "情報登録期間を入力してください。",
    },
    ebrc06: {
      invalid_date: "日付の形式が正しくありません。",
      sent_parameter: "送信パラメータ:",
      create_pdf_error: "PDF作成中にエラーが発生しました。",
      file_none: "表示ファイルが存在しません。",
      file_data_none: "ファイルデータが存在しません。",
      display_error: "全画面表示に失敗しました。",
      download_file_none: "ダウンロードファイルが存在しません。",
      pdf_download_failed: "PDFダウンロードに失敗しました。",
      result: "結果:",
      input_none: "拠点名、対象期間、対象月を指定し、対象月の契約電力を入力してください。",
      modal_closed: "モーダル閉じた",
      create_request_accepted: "電力見える化レポート作成のリクエストを受け付けました",
      create_request_note: "※「作成済」になりましたらダウンロードできます",
      electricity_visible_creating: "電力見える化レポートを作成中です。\nしばらく経ってから画面を更新してください。",
    },
  },
  energy_building_info: {
    ebmg03: {
      org_id_none: "No orgId found in session.",
      json_parse_failed: "reportStatusInfo のパースに失敗しました",
      changed_data_none: "変更されたデータはありません。",
      leave: "入力内容が保存されていません。ページを離れますか？",
      industry_major_error: "産業分類（大分類）は必須項目です。お客さま基本情報タブから入力してください",
      industry_middle_error: "産業分類（中分類）は必須項目です。お客さま基本情報タブから入力してください",
      electricity_usage_required: "電気の使用量を1つ以上入力してください",
    },
  },
  data_upload: {
    confirm: "こちらのデータを登録してもよろしいですか？",
    format_error: "アップロードしたファイルのフォーマットが正しくありません。",
    data_error: "アップロードしたファイルのデータが正しくありません。",
    location_error: "アップロードしたファイルの拠点情報が正しくありません。",
    company_name_mismatch:
      "アップロードしたファイルのお客さま名が異なっています。こちらのデータを登録してもよろしいですか？",
    register_success: "データが正しく登録されました。",
    register_error: "システムエラーが発生しました。管理者に連絡してください。",
  },
  login: {
    idp_redirect_error: "IdPのリダイレクト先が取得できませんでした。",
    api_redirect_error: "APIからリダイレクト先が返却されませんでした。",
    // SAML削除対応 Start
    // saml_request_error: "SAML認証リクエストでエラーが発生しました。",
    // saml_request_failed: "SAML認証リクエストが失敗しました (status: ",
    // saml_response_error: "SAML認証でエラーが発生しました。",
    // saml_response_failed: "SAML認証に失敗しました。再度ログインしてください。",
    // SAML削除対応 End
  },
  help: {
    dounload_success: "ファイルをダウンロードしました。",
    invalid_dounload_response: "レスポンスがResponseオブジェクトではありません:",
    file_name_error: "Content-Dispositionヘッダーからファイル名を取得できませんでした。",
    file_download_failed: "ファイルのダウンロードに失敗しました。",
  },
} as const;
