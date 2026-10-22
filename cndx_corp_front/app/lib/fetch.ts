/* eslint-disable @typescript-eslint/no-explicit-any */
// 環境変数からAPI URL取得
const BASE_URL = process.env.VITE_API_URL;

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

// ローカル確認用: すべてのCookieをコンソールログで確認
function logAllCookies() {
  if (process.env.NODE_ENV === "development" || import.meta.env.DEV) {
    const cookies = document.cookie.split(";").reduce((acc, cookie) => {
      const [name, value] = cookie.trim().split("=");
      if (name) {
        acc[name] = decodeURIComponent(value || "");
      }
      return acc;
    }, {} as Record<string, string>);
    return cookies;
  }
  return {};
}

function getCsrfToken(): string | null {
  return (
    getCookie("csrf_access_token") ||
    getCookie("csrf_refresh_token") ||
    sessionStorage.getItem("csrf_access_token") ||
    sessionStorage.getItem("csrf_refresh_token")
  );
}

export async function postData(
  url: string,
  data: any = {}, // JSON データ用
  headers: Record<string, string> = {},
  formData?: FormData // 外部から渡す FormData
) {
  let csrfToken = getCsrfToken();
  if ("/api/auth/refresh" == url) {
    csrfToken = getCookie("csrf_refresh_token");
  }
  const fetchOptions: RequestInit = {
    method: "POST",
    mode: "cors",
    cache: "no-cache",
    credentials: "include",
    headers: {
      "X-CSRF-TOKEN": csrfToken ?? "",
      "X-CLIENT-LOCATION": location.href,
      // ...getAuthHeaders(headers)
      ...headers,
    },
    redirect: 'manual'
  };

  if (formData) {
    // 外部から渡された FormData を body に設定
    fetchOptions.body = formData;
    // Content-Type は設定しない
  } else {
    // JSON データを送信する場合
    fetchOptions.headers = {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    };
    fetchOptions.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${BASE_URL}${url}`, fetchOptions);

    if (url == "/api/auth/refresh") {
      if (!response.ok && response.status === 401) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: await response.text() };
        }

        const errorCode = errorData?.error_code;
        if (errorCode === "SINGLE_LOGIN_VIOLATION") {
          window.dispatchEvent(
            new CustomEvent("singleLoginViolation", {
              detail: { message: errorData.message },
            })
          );
          // エラーをthrowして、呼び出し元で適切に処理されるようにする
          const error: any = new Error(errorData?.message || "Single login violation");
          error.status = response.status;
          error.data = errorData;
          throw error;
        } else {
          window.dispatchEvent(new Event("sessionExpired"));
          // エラーをthrowして、呼び出し元で適切に処理されるようにする
          const error: any = new Error(errorData?.message || "Session expired");
          error.status = response.status;
          error.data = errorData;
          throw error;
        }
      }
    } else {
      // const response = new Response(null, { status: 504 });
      if (!response.ok && response.status === 504) {
        const errorData: any = { 
          message: "サーバーとの通信がタイムアウトしました。処理が完了していない可能性があります。" 
        };

        const error: any = new Error(errorData.message);
        error.status = response.status;
        throw error;
      }
      // 403エラーの処理（ユーザーステータス関連のエラー）
      if (!response.ok && response.status === 403) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          try {
            errorData = { message: await response.text() };
          } catch {
            errorData = { message: "エラーが発生しました。" };
          }
        }


        const errorCode = errorData?.error_code;


        // ユーザーステータス関連のエラーコードを検出
        if (
          errorCode &&
          (errorCode === "USER_STATUS_REGISTERING" ||
            errorCode === "USER_STATUS_APPLIED" ||
            errorCode === "USER_STATUS_CANCELLED" ||
            errorCode === "USER_STATUS_INVALIDATED" ||
            errorCode === "USER_STATUS_DELETED" ||
            errorCode === "USER_STATUS_INVALID")
        ) {
          // エラーメッセージを保存（sessionStorage.clear()の前に保存）
          const errorMessage = errorData?.message;
          try {
            sessionStorage.setItem("sessionUserStatusErrorMessage", errorMessage);
          } catch {}
         
          // セッション情報をクリア
          try {
            localStorage.clear();
          } catch {}
          try {
            // エラーメッセージは保持するため、clear()の代わりに個別に削除
            const errorMsg = sessionStorage.getItem("sessionUserStatusErrorMessage");
            sessionStorage.clear();
            // エラーメッセージを再保存
            if (errorMsg) {
              sessionStorage.setItem("sessionUserStatusErrorMessage", errorMsg);
            }
          } catch {}
          try {
            document.cookie.split(";").forEach((c) => {
              document.cookie = c.trim().replace(/=.*/, "=;expires=" + new Date(0).toUTCString() + ";path=/");
            });
          } catch {}
          // sessionUserStatusErrorイベントを発火
          window.dispatchEvent(
            new CustomEvent("sessionUserStatusError", {
              detail: { message: errorMessage },
            })
          );
          const error: any = new Error(errorMessage || "Something went wrong");
          error.status = response.status;
          error.data = errorData;
          throw error;
        }

        // 403エラーだがユーザーステータス関連でない場合もエラーをthrow（レスポンスボディは既に読み取り済み）
        const error: any = new Error(errorData?.message || "Something went wrong");
        error.status = response.status;
        error.data = errorData;
        throw error;
      }

      if (!response.ok && response.status === 401) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: await response.text() };
        }

        const errorCode = errorData?.error_code;

        // シングルログイン違反またはセッションタイムアウトの場合はリフレッシュを試みない
        if (errorCode === "SINGLE_LOGIN_VIOLATION") {
          window.dispatchEvent(
            new CustomEvent("singleLoginViolation", {
              detail: { message: errorData.message },
            })
          );
          // イベントハンドラーが実行される時間を確保するため、少し待機
          await new Promise(resolve => setTimeout(resolve, 100));
          const error: any = new Error(errorData?.message || "Something went wrong");
          error.status = response.status;
          error.data = errorData;
          throw error;
        } else if (errorCode === "SESSION_TIMEOUT") {
          window.dispatchEvent(new Event("sessionExpired"));
          // イベントハンドラーが実行される時間を確保するため、少し待機
          await new Promise(resolve => setTimeout(resolve, 100));
          const error: any = new Error(errorData?.message || "Something went wrong");
          error.status = response.status;
          error.data = errorData;
          throw error;
        }
        
        // その他の401エラーはリフレッシュトークンで再試行
        // ただし、元のレスポンスにerror_codeが含まれている場合は、リフレッシュを試みない
        if (errorCode) {
          // error_codeが存在するが、SINGLE_LOGIN_VIOLATIONやSESSION_TIMEOUTでない場合
          // これは想定外のエラーコードなので、エラーをthrowする
          const error: any = new Error(errorData?.message || "Something went wrong");
          error.status = response.status;
          error.data = errorData;
          throw error;
        }

        try {
          const refresh_response = await postData("/api/auth/refresh", {}, {});

          if (refresh_response.status == "ok") {
            const new_csrfToken = getCsrfToken();
            if (fetchOptions.headers && !(fetchOptions.headers instanceof Headers)) {
              (fetchOptions.headers as Record<string, string>)["X-CSRF-TOKEN"] = new_csrfToken ?? "";
            }
            const new_response = await fetch(`${BASE_URL}${url}`, fetchOptions);
            // JSON or text
            const new_text = await new_response.text();
            try {
              return JSON.parse(new_text);
            } catch {
              return new_text;
            }
          }
        } catch (refreshError: any) {
          // リフレッシュトークンでエラーが発生した場合（SINGLE_LOGIN_VIOLATIONやSESSION_TIMEOUTなど）
          // イベントは既にpostData関数内で発火されているため、エラーを再throwするだけ
          throw refreshError;
        }
      }

      if (!response.ok && response.status === 0) {
        
          window.dispatchEvent(new Event("sessionExpired"));
          // イベントハンドラーが実行される時間を確保するため、少し待機
          await new Promise(resolve => setTimeout(resolve, 100));
          throw new Error("sessionExpired");
        
      }
    }

    // その他のエラーの処理（401と403は上で処理済み）
    if (!response.ok && response.status !== 401 && response.status !== 403) {
      let errorData: any = null;
      try {
        errorData = await response.json();
      } catch {
        try {
          errorData = { message: await response.text() };
        } catch {
          errorData = { message: "エラーが発生しました。" };
        }
      }

      const error: any = new Error(errorData?.message || "Something went wrong");
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // JSON or text
    // const text = await response.text();
    // try {
    //   return JSON.parse(text);
    // } catch {
    //   return text;
    // }
    // ---- CSV / バイナリ対応（最小パッチ）----
    const contentType = response.headers.get("content-type") || "";

    // CSV（text/csv）または バイナリ（octet-stream）なら blob で返す
    if (contentType.includes("text/csv") || contentType.includes("application/octet-stream")) {
      return await response.blob();
    }

    // ---- JSON or TEXT（既存ロジックそのまま）----
    const text = await response.text();
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  // } catch (error) {
  //   console.error("想定外のエラーが発生しました。", error);
  //   throw error;
  // }
  } catch (error: any) {
    console.error("通信エラーが発生しました。", error);

    // fetch がレスポンスを受け取れなかった場合
    if (
      error instanceof TypeError &&
      (error.message === "Failed to fetch" ||
      error.message?.includes("Failed to fetch"))
    ) {
      const customError: any = new Error(
        "通信がタイムアウトしました。\n" +
        "処理が完了していない可能性があります。\n" +
        "恐れ入りますが、時間をおいて再度お試しください。"
      );
      customError.status = "NETWORK_TIMEOUT";
      throw customError;
    }

    // それ以外はそのまま投げる
    throw error;
  }
}

export async function getData(url: string, headers: Record<string, string> = {}, options: RequestInit = {}) {
  const csrfToken = getCsrfToken();

  const response = await fetch(`${BASE_URL}${url}`, {
    method: "GET",
    mode: "cors",
    cache: "no-cache",
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json", // ← JSON 通信用
      "X-CSRF-TOKEN": csrfToken ?? "",
      "X-CLIENT-LOCATION": location.href,
      // ...getAuthHeaders(headers), // ← 共通 Auth ヘッダーをマージ
      ...headers,
    },
    redirect: 'manual'
  });



  if (options.redirect === "manual") {
    return response;
  }

  // 403エラーの処理（ユーザーステータス関連のエラー）
  if (!response.ok && response.status === 403) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      try {
        errorData = { message: await response.text() };
      } catch {
        errorData = { message: "エラーが発生しました。" };
      }
    }


    const errorCode = errorData?.error_code;


    // ユーザーステータス関連のエラーコードを検出
    // /api/auth/user_info_init の場合は、handleForbiddenResponse を呼ばない
    // （認証フロー内で直接エラーハンドリングするため）
    const isUserInfoInitApi = url === "/api/auth/user_info_init";
    
    if (
      errorCode &&
      (errorCode === "USER_STATUS_REGISTERING" ||
        errorCode === "USER_STATUS_APPLIED" ||
        errorCode === "USER_STATUS_CANCELLED" ||
        errorCode === "USER_STATUS_INVALIDATED" ||
        errorCode === "USER_STATUS_DELETED" ||
        errorCode === "USER_STATUS_INVALID")
    ) {
     
      
      // /api/auth/user_info_init の場合は、sessionUserStatusErrorイベントを発火しない
      // エラーをそのままthrowし、呼び出し側（auth.user_info_init.tsx）で処理
      if (!isUserInfoInitApi) {
        // エラーメッセージを保存（sessionStorage.clear()の前に保存）
        const errorMessage = errorData?.message;
        try {
          sessionStorage.setItem("sessionUserStatusErrorMessage", errorMessage);
        } catch {}

        // セッション情報をクリア
        try {
          localStorage.clear();
        } catch {}
        try {
          // エラーメッセージは保持するため、clear()の代わりに個別に削除
          const errorMsg = sessionStorage.getItem("sessionUserStatusErrorMessage");
          sessionStorage.clear();
          // エラーメッセージを再保存
          if (errorMsg) {
            sessionStorage.setItem("sessionUserStatusErrorMessage", errorMsg);
          }
        } catch {}
        try {
          document.cookie.split(";").forEach((c) => {
            document.cookie = c.trim().replace(/=.*/, "=;expires=" + new Date(0).toUTCString() + ";path=/");
          });
        } catch {}
        // sessionUserStatusErrorイベントを発火
        window.dispatchEvent(
          new CustomEvent("sessionUserStatusError", {
            detail: { message: errorMessage },
          })
        );
      }
      
      const error: any = new Error(errorData?.message || "Something went wrong");
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // ユーザーステータス関連のエラーコードがない場合でも、403エラーはthrowする
    // （body stream already readエラーを防ぐため）
    const error: any = new Error(errorData?.message || "Forbidden");
    error.status = response.status;
    error.data = errorData;
    throw error;
  }

  if (!response.ok && response.status === 401 && url != "/api/auth/refresh") {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      errorData = { message: await response.text() };
    }

    const errorCode = errorData?.error_code;

    // シングルログイン違反またはセッションタイムアウトの場合はリフレッシュを試みない
    if (errorCode === "SINGLE_LOGIN_VIOLATION") {
      window.dispatchEvent(
        new CustomEvent("singleLoginViolation", {
          detail: { message: errorData.message },
        })
      );
      // イベントハンドラーが実行される時間を確保するため、少し待機
      await new Promise(resolve => setTimeout(resolve, 100));
      const error: any = new Error(errorData?.message || "Something went wrong");
      error.status = response.status;
      error.data = errorData;
      throw error;
    } else if (errorCode === "SESSION_TIMEOUT") {
      window.dispatchEvent(new Event("sessionExpired"));
      // イベントハンドラーが実行される時間を確保するため、少し待機
      await new Promise(resolve => setTimeout(resolve, 100));
      const error: any = new Error(errorData?.message || "Something went wrong");
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // その他の401エラーはリフレッシュトークンで再試行
    try {
      const refresh_response = await postData("/api/auth/refresh", {}, {});

      if (refresh_response.status == "ok") {
        // ② 再リクエスト
        const new_response = await fetch(`${BASE_URL}${url}`, {
          method: "GET",
          mode: "cors",
          cache: "no-cache",
          credentials: "include",
          ...options,
          headers: {
            "Content-Type": "application/json", // ← JSON 通信用
            "X-CSRF-TOKEN": csrfToken ?? "",
            "X-CLIENT-LOCATION": location.href,
            // ...getAuthHeaders(headers), // ← 共通 Auth ヘッダーをマージ
            ...headers,
          },
        });
        const new_contentType = new_response.headers.get("content-type") || "";

        if (new_contentType.includes("application/json")) {
          return new_response.json();
        }

        // JSON 以外（PDF, ZIP など）は Response オブジェクトそのまま返す
        return new_response;
      } else {
        window.dispatchEvent(new Event("sessionExpired"));
      }
    } catch (refreshError: any) {
      // リフレッシュトークンでエラーが発生した場合（SINGLE_LOGIN_VIOLATIONやSESSION_TIMEOUTなど）
      // イベントは既にpostData関数内で発火されているため、エラーを再throwするだけ
      throw refreshError;
    }
  }

  if (!response.ok && response.status === 0) {
    
      window.dispatchEvent(new Event("sessionExpired"));
      // イベントハンドラーが実行される時間を確保するため、少し待機
      await new Promise(resolve => setTimeout(resolve, 100));
      throw new Error("sessionExpired");
    
  }
  // その他のエラーの処理（401と403は上で処理済み）
  if (!response.ok && response.status !== 401 && response.status !== 403) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      try {
        errorData = { message: await response.text() };
      } catch {
        errorData = { message: "エラーが発生しました。" };
      }
    }

    const error: any = new Error(errorData?.message || "Something went wrong");
    error.status = response.status;
    error.data = errorData;
    throw error;
  }
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  // JSON 以外（PDF, ZIP など）は Response オブジェクトそのまま返す
  return response;
}

export async function putData(url: string, data = {}, headers = {}) {
  const csrfToken = getCsrfToken();



  const response = await fetch(`${BASE_URL}${url}`, {
    method: "PUT",
    mode: "cors",
    cache: "no-cache",
    credentials: "include", // Cookieを常に送信
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-TOKEN": csrfToken ?? "",
      "X-CLIENT-LOCATION": location.href,
      ...headers,
    },
    body: JSON.stringify(data),
  });

  // ローカル確認用: レスポンス後のCookieをログ出力
  if (process.env.NODE_ENV === "development" || import.meta.env.DEV) {
    const setCookieHeader = response.headers.get("set-cookie");
    if (setCookieHeader) {
    }
  }

  if (!response.ok && response.status === 403) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      try {
        errorData = { message: await response.text() };
      } catch {
        errorData = { message: "403 Forbidden" };
      }
    }

    const errorCode = errorData?.error_code;

    // ユーザーステータスのみ対応
    const userStatusErrors = [
      "USER_STATUS_REGISTERING",
      "USER_STATUS_APPLIED",
      "USER_STATUS_CANCELLED",
      "USER_STATUS_INVALIDATED",
      "USER_STATUS_DELETED",
      "USER_STATUS_INVALID",
    ];

    if (userStatusErrors.includes(errorCode)) {
      // エラーメッセージを保存（sessionStorage.clear()の前に保存）
      const errorMessage = errorData?.message;
      try {
        sessionStorage.setItem("sessionUserStatusErrorMessage", errorMessage);
      } catch {}
      
      // セッション情報をクリア
      try {
        localStorage.clear();
      } catch {}
      try {
        // エラーメッセージは保持するため、clear()の代わりに個別に削除
        const errorMsg = sessionStorage.getItem("sessionUserStatusErrorMessage");
        sessionStorage.clear();
        // エラーメッセージを再保存
        if (errorMsg) {
          sessionStorage.setItem("sessionUserStatusErrorMessage", errorMsg);
        }
      } catch {}
      try {
        document.cookie.split(";").forEach((c) => {
          document.cookie = c.trim().replace(/=.*/, "=;expires=" + new Date(0).toUTCString() + ";path=/");
        });
      } catch {}
      // sessionUserStatusErrorイベントを発火
      window.dispatchEvent(
        new CustomEvent("sessionUserStatusError", {
          detail: { message: errorMessage },
        })
      );
    }

    const error: any = new Error(errorData?.message || "Forbidden");
    error.status = response.status;
    error.data = errorData;
    throw error;
  }

  return response.json();
}

export async function deleteData(url: string, headers = {}) {
  const csrfToken = getCsrfToken();



  const response = await fetch(`${BASE_URL}${url}`, {
    method: "DELETE",
    mode: "cors",
    cache: "no-cache",
    credentials: "include", // Cookieを常に送信
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-TOKEN": csrfToken ?? "",
      "X-CLIENT-LOCATION": location.href,
      ...headers,
    },
  });

  // ローカル確認用: レスポンス後のCookieをログ出力
  if (process.env.NODE_ENV === "development" || import.meta.env.DEV) {
    const setCookieHeader = response.headers.get("set-cookie");

    if (!response.ok && response.status === 403) {
      let errorData: any = null;
      try {
        errorData = await response.json();
      } catch {
        try {
          errorData = { message: await response.text() };
        } catch {
          errorData = { message: "403 Forbidden" };
        }
      }

      const errorCode = errorData?.error_code;

      // ユーザーステータスのみ対応
      const userStatusErrors = [
        "USER_STATUS_REGISTERING",
        "USER_STATUS_APPLIED",
        "USER_STATUS_CANCELLED",
        "USER_STATUS_INVALIDATED",
        "USER_STATUS_DELETED",
        "USER_STATUS_INVALID",
      ];

      if (userStatusErrors.includes(errorCode)) {
        // エラーメッセージを保存（sessionStorage.clear()の前に保存）
        const errorMessage = errorData?.message;
        try {
          sessionStorage.setItem("sessionUserStatusErrorMessage", errorMessage);
        } catch {}
        
        // セッション情報をクリア
        try {
          localStorage.clear();
        } catch {}
        try {
          // エラーメッセージは保持するため、clear()の代わりに個別に削除
          const errorMsg = sessionStorage.getItem("sessionUserStatusErrorMessage");
          sessionStorage.clear();
          // エラーメッセージを再保存
          if (errorMsg) {
            sessionStorage.setItem("sessionUserStatusErrorMessage", errorMsg);
          }
        } catch {}
        try {
          document.cookie.split(";").forEach((c) => {
            document.cookie = c.trim().replace(/=.*/, "=;expires=" + new Date(0).toUTCString() + ";path=/");
          });
        } catch {}
        // sessionUserStatusErrorイベントを発火
        window.dispatchEvent(
          new CustomEvent("sessionUserStatusError", {
            detail: { message: errorMessage },
          })
        );
      }

      const error: any = new Error(errorData?.message || "Forbidden");
      error.status = response.status;
      error.data = errorData;
      throw error;
    }
  }

  return response.json();
}

function getAuthHeaders(headers: Record<string, string> = {}) {
  if (typeof window !== "undefined") {
    const sessionData = sessionStorage.getItem("session");
    if (sessionData) {
      const token = JSON.parse(sessionData).token;
      if (token) {
        return {
          Authorization: `Bearer ${token}`,
          ...headers,
        };
      }
    }
  }
  return headers;
}

function handleForbiddenResponse(message?: string) {
  console.error("403 Forbidden:", message);

  try {
    localStorage.clear();
  } catch {}
  try {
    sessionStorage.clear();
  } catch {}

  try {
    document.cookie.split(";").forEach((c) => {
      document.cookie = c.trim().replace(/=.*/, "=;expires=" + new Date(0).toUTCString() + ";path=/");
    });
  } catch {}

  setTimeout(() => {
    navigate("/");
  }, 50);
}
