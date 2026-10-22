import inspect
import logging
import os
import time
from dataclasses import fields
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlparse

from flask import g, jsonify, make_response, request, session
from flask_jwt_extended import (
    get_csrf_token,
    get_jwt,
    get_jwt_identity,
    unset_jwt_cookies,
    verify_jwt_in_request,
)
from jwt import ExpiredSignatureError

from cndx_corp_back.api.auth.util.session_validation import validate_and_update_session
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.entity.m_organization_authority_info_entity import (
    MOrganizationAuthorityInfo,
)
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.utils.utils import get_message

from .log import CorpLogger

logger = CorpLogger()

# セッション検証をスキップするエンドポイントのリスト
SESSION_VALIDATION_SKIP_PATHS = [
    "/api/auth/login",
    "/api/auth/auth_init",  # 認証初期化処理（認証前のため）
    "/api/auth/user_info_init",  # SAML認証直後のユーザー情報初期化処理（まだセッションIDが発行されていないため）
    "/api/auth/refresh",
    "/api/auth/signout",
]


def controller(f):
    """
    コントローラーの共通処理を行うデコレーター

    Args:
        obj: デコレート対象の関数

    Returns:
        decorated_function: デコレートされた関数

    Raises:
        Exception: 処理中に発生した例外
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        """
        デコレーターの実装関数

        Args:
            *args: 位置引数
            **kwargs: キーワード引数

        Returns:
            result: デコレート対象関数の実行結果

        Raises:
            Exception: 処理中に発生した例外
        """

        status_code = 200
        try:
            # 呼び出し元情報取得
            file_path = inspect.getsourcefile(f)
            file_name = os.path.basename(file_path) if file_path else "<unknown>"

            class_name = (
                args[0].__class__.__name__
                if args and hasattr(args[0], "__class__")
                else None
            )
            func_name = f.__name__
            logger.info(
                f"{file_name}：{class_name}：コントローラの{func_name}処理開始..."
            )

            client_location = request.headers.get("X-CLIENT-LOCATION")
            if client_location:
                parsed_url = urlparse(client_location)
                screen_id = parsed_url.path  # クエリなしでパスだけ
            else:
                screen_id = ""

            def is_blank(value: str) -> bool:
                return not value or str(value).strip() == ""

            user_id = logger.user_id
            if is_blank(user_id):
                user_id = "dummy"
            logger.user_id = user_id
            logger.screen_id = screen_id
            logger.api_id = request.path
            if request.content_type and "multipart/form-data" in request.content_type:
                dict_request_data = request.form.to_dict()
            else:
                # フロント画面データを取得
                if request.method == "GET":
                    dict_request_data = request.args.to_dict()
                else:
                    # POST リクエストの場合
                    if request.is_json:
                        # application/json の場合
                        dict_request_data = request.get_json()
                    elif request.form:
                        # application/x-www-form-urlencoded の場合（SAML認証レスポンスなど）
                        dict_request_data = request.form.to_dict()
                    else:
                        return (
                            jsonify({"error": "Content-Type must be application/json"}),
                            400,
                        )

            # セッション検証（シングルログイン実現のため）
            # スキップすべきエンドポイントでない場合のみ実行
            if (
                request.path not in SESSION_VALIDATION_SKIP_PATHS
                and request.method != "OPTIONS"
            ):
                # Cookieからsession_idを取得
                session_id = request.cookies.get("session_id")

                if session_id:
                    # セッション検証と最終ログイン日時更新
                    with get_scoped_session() as db_session:
                        validation_error = validate_and_update_session(
                            db_session, session_id, use_db_timestamp=True
                        )

                        if validation_error is not None:
                            error_message, http_status, error_code = validation_error
                            logger.warning(
                                f"セッション検証失敗: {error_message}, "
                                f"session_id: {session_id}, "
                                f"error_code: {error_code}, "
                                f"http_status: {http_status}"
                            )

                            response = make_response(
                                jsonify(
                                    {"message": error_message, "error_code": error_code}
                                ),
                                http_status,
                            )

                            unset_jwt_cookies(response)
                            response.delete_cookie("session_id", path="/")

                            return response
                # session_idが存在しない場合は警告のみ（新規ログイン前など）
                # セッション検証をスキップするエンドポイントでは警告を出さない
                elif request.path not in SESSION_VALIDATION_SKIP_PATHS:
                    logger.warning(f"session_idがCookieに存在しません: {request.path}")

            # ロガーとデータをデコレーター関数に渡す
            kwargs["logger"] = logger
            kwargs["dict_request_data"] = dict_request_data

            response = f(*args, **kwargs)
            # 戻り値からHTTPステータスを取得（Flaskレスポンス or タプル）
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            elif hasattr(response, "status_code"):
                status_code = response.status_code
            else:
                status_code = 200  # デフォルト成功
            return response
        except Exception as e:
            status_code = getattr(e, "code", 500)
            logger.error(
                f"{class_name}コントローラの{func_name}処理失敗。HttpStatus:{status_code}"
            )
            raise
        finally:
            logger.info(
                f"{class_name}コントローラの{func_name}処理終了。HttpStatus:{status_code}"
            )

    return decorated_function


def service(f):
    """
    サービスの共通処理を行うデコレーター

    Args:
        f: デコレート対象の関数

    Returns:
        decorated_function: デコレートされた関数

    Raises:
        Exception: 処理中に発生した例外
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        """
        デコレーターの実装関数

        Args:
            *args: 位置引数
            **kwargs: キーワード引数
        """
        try:
            # 呼び出し元情報取得
            file_path = inspect.getsourcefile(f)
            file_name = os.path.basename(file_path) if file_path else "<unknown>"
            class_name = (
                args[0].__class__.__name__
                if args and hasattr(args[0], "__class__")
                else None
            )
            func_name = f.__name__
            logger.info(f"{file_name}：{class_name}：サービスの{func_name}処理開始...")

            kwargs["logger"] = logger

            response = f(*args, **kwargs)
            # 戻り値からHTTPステータスを取得（Flaskレスポンス or タプル）
            status_code = 200
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            elif hasattr(response, "status_code"):
                status_code = response.status_code
            else:
                status_code = 200  # デフォルト成功
            return response
        except Exception as e:
            status_code = getattr(e, "code", 500)
            logger.error(
                f"{class_name}サービスの{func_name}処理失敗。HttpStatus:{status_code}"
            )
            raise
        finally:
            logger.info(f"{class_name}サービスの{func_name}処理終了。")

    return decorated_function


def component(f):
    """
    コンポーネントの共通処理を行うデコレーター

    Args:
        f: デコレート対象の関数

    Returns:
        decorated_function: デコレートされた関数

    Raises:
        Exception: 処理中に発生した例外
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        """
        デコレーターの実装関数

        Args:
            *args: 位置引数
            **kwargs: キーワード引数
        """
        try:
            # 呼び出し元情報取得
            file_path = inspect.getsourcefile(f)
            file_name = os.path.basename(file_path) if file_path else "<unknown>"
            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__
            else:
                # f.__qualname__ からクラス名を推定
                class_name = f.__qualname__ if f.__qualname__ else None
            func_name = f.__name__
            logger.info(
                f"{file_name}：{class_name}：コンポネントの{func_name}処理開始..."
            )

            kwargs["logger"] = logger

            response = f(*args, **kwargs)
            # 戻り値からHTTPステータスを取得（Flaskレスポンス or タプル）
            status_code = 200
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            elif hasattr(response, "status_code"):
                status_code = response.status_code
            else:
                status_code = 200  # デフォルト成功
            return response
        except Exception as e:
            status_code = getattr(e, "code", 500)
            logger.error(
                f"{class_name}コンポネントの{func_name}処理失敗。 HttpStatus:{status_code}"
            )
            raise
        finally:
            logger.info(f"{class_name}コンポネントの{func_name}処理終了。")

    return decorated_function


def auto_filter_kwargs(cls):
    """
    クラスのキーワード引数をフィルタリングするデコレーター

    Args:
        cls: デコレート対象のクラス

    Returns:
        cls: デコレートされたクラス
    """
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, **kwargs):
        """
        デコレーターの実装関数

        Args:
            **kwargs: キーワード引数
        """
        field_names = {f.name for f in fields(cls)}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in field_names}
        original_init(self, **filtered_kwargs)

    cls.__init__ = new_init
    return cls


def jwt_user_context(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()

        identity = get_jwt_identity()
        claims = get_jwt()

        # JWT からユーザー情報とカスタムクレームを取得
        auth_context = {
            "user_id": identity,
            "user_name": claims.get("name"),
            "role": claims.get("role"),
            "org_id": claims.get("org_id"),
            "org_type_code": claims.get("org_type_code"),
            "authority_code_map": claims.get("authority_code_map", {}),
        }

        # 必要に応じて Flask の g にセットも可能
        g.auth_context = auth_context

        # 関数に渡す
        return fn(auth_context, *args, **kwargs)

    return wrapper


def get_user_permissions(user_id: str):
    """_summary_

    Args:
        user_id (str): _description_

    Returns:
        _type_: _description_
    """
    with get_scoped_session() as session:
        user = (
            session.query(MUser)
            .filter(MUser.user_id == user_id, MUser.delete_flg.isnot(True))
            .first()
        )

        if not user:
            return jsonify({"error": get_message("NOT_FOUND", item_name="ユーザ")}), 404

        org_info = (
            session.query(MUserOrganizationInfo)
            .filter(
                MUserOrganizationInfo.org_id == user.org_id,
                MUserOrganizationInfo.delete_flg.isnot(True),
            )
            .first()
        )

        if not org_info:
            return (
                jsonify({"message": get_message("NOT_FOUND", item_name="組織情報")}),
                404,
            )

        authorities = (
            session.query(MOrganizationAuthorityInfo)
            .filter(
                MOrganizationAuthorityInfo.org_type_code == org_info.org_type_code,
                MOrganizationAuthorityInfo.user_role == user.user_role,
                MOrganizationAuthorityInfo.authority_code != "2",
                MOrganizationAuthorityInfo.delete_flg.isnot(True),
            )
            .all()
        )

        # authority_code_map = [{a.authority_id: a.authority_code for a in authorities}]
        authority_code_map = [
            (item.authority_id, item.authority_code) for item in authorities
        ]

        mapped_list = [
            {"authority_id": aid, "authority_code": acode}
            for aid, acode in authority_code_map
        ]

        user_context = {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "role": user.user_role,
            "org_id": user.org_id,
            "org_type_code": org_info.org_type_code,
            "authority_code_map": mapped_list,
            "email_address": user.email_address,
        }

    return user_context


def jwt_user_context_db_bk(refresh: bool = False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # トークンの種類に応じて verify 方法を変更
            if refresh:
                # verify_jwt_in_request(refresh=refresh,locations=["cookies"])
                verify_jwt_in_request(refresh=refresh)
            else:
                verify_jwt_in_request(refresh=refresh)
            user_id = get_jwt_identity()
            g.user_id = user_id
            user_context = get_user_permissions(user_id)
            return fn(*args, user_context=user_context, **kwargs)

        return wrapper

    return decorator


def jwt_user_context_db(refresh: bool = False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Cookie からトークン検証
            try:
                verify_jwt_in_request(refresh=refresh, locations=["cookies"])
                # payload = get_jwt()
                # def ts_to_str(ts):
                #     return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                # print("iat =", payload.get("iat"), ts_to_str(payload.get("iat")))
                # print("nbf =", payload.get("nbf"), ts_to_str(payload.get("nbf")))
                # print("exp =", payload.get("exp"), ts_to_str(payload.get("exp")))
                # 成功 → refresh token は有効
                # return {"status": "ok"}

            except ExpiredSignatureError:
                # refresh token が期限切れ
                return {"status": "error"}, 401

            except Exception as e:
                # その他のJWTエラー（偽造、存在しない、間違ったtokenタイプなど）
                return {"status": "error", "detail": str(e)}, 401
            # CSRF トークン検証
            # csrf_token = request.headers.get("X-CSRF-TOKEN")
            # if not csrf_token or csrf_token != get_csrf_token():
            #     return jsonify({"error": "Invalid CSRF token"}), 403

            user_id = get_jwt_identity()
            g.user_id = user_id
            user_context = get_user_permissions(user_id)
            return fn(*args, user_context=user_context, **kwargs)

        return wrapper

    return decorator


def _call_chain(max_depth=1):
    chain = []
    frame = inspect.currentframe()
    frame = frame.f_back

    depth = 0
    while frame and depth < max_depth:
        code = frame.f_code
        func = code.co_name
        mod = frame.f_globals.get("__name__", "")

        if mod and mod != "__main__":
            chain.append(f"{mod}.{func}")
        else:
            chain.append(f"{func}")

        frame = frame.f_back
        depth += 1

    chain = list(reversed(chain))
    return " -> ".join(chain)


def log_time(func):
    filename = os.path.basename(func.__code__.co_filename)
    func_name = func.__name__

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            chain = _call_chain(max_depth=1)

            logger.info(
                f"レスポンス調査用★"
                f"[{chain} -> {func_name}] "
                f"elapsed={elapsed:.3f}s "
                f"(func={func_name}, file={filename})"
            )

    return wrapper
