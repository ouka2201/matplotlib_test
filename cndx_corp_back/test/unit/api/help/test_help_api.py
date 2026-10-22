import os
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, Response
from werkzeug.exceptions import Forbidden, GatewayTimeout, InternalServerError, NotFound

from cndx_corp_back.api.help import help_bp
from cndx_corp_back.api.help.help_api import HelpApi

LOCAL_DOWNLOAD_TEST_CASES = [
    ("/api/help/manual_EP", "LecMocマニュアル_EP.pdf", "application/pdf"),
    ("/api/help/manual_TCS", "LecMocマニュアル_TCS.pdf", "application/pdf"),
    ("/api/help/manual_REP", "LecMocマニュアル_REP.pdf", "application/pdf"),
    ("/api/help/manual_financial", "LecMocマニュアル_金融機関.pdf", "application/pdf"),
    (
        "/api/help/consent_form_EP",
        "データ提供同意書（ミドル）_EP.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    (
        "/api/help/consent_form_REP",
        "データ提供同意書（ミドル）_REP.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    (
        "/api/help/consent_form_financial",
        "データ提供同意書_金融機関.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
]


def _build_local_file_path(filename: str) -> str:
    """help_api.py 配下の local_data への絶対パスを取得"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    help_api_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    )
    help_api_dir = os.path.join(help_api_dir, "api", "help")
    return os.path.join(help_api_dir, "local_data", filename)


def _build_expected_availability(flag_map):
    """
    endpointキーからなる期待結果を生成
    """
    expected = {}
    for endpoint, file_path in HelpApi.ENDPOINT_FILE_MAP.items():
        key = endpoint.split("/")[-1]
        expected[key] = flag_map[file_path]
    return expected


@pytest.fixture
def app():
    """Flaskアプリケーションのフィクスチャ"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["JWT_COOKIE_DOMAIN"] = "localhost"
    # JWT設定（最小限）
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=1)
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # テストではCSRF保護を無効化
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    # Flask-JWT-Extendedのクッキー名設定
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token_cookie"
    # CSRF関連の設定（CSRF保護が無効でも設定が必要）
    app.config["JWT_ACCESS_CSRF_HEADER_NAME"] = "X-CSRF-ACCESS"
    app.config["JWT_REFRESH_CSRF_HEADER_NAME"] = "X-CSRF-REFRESH"
    app.config["JWT_ACCESS_CSRF_FIELD_NAME"] = "csrf_token"
    app.config["JWT_REFRESH_CSRF_FIELD_NAME"] = "csrf_token"
    app.register_blueprint(help_bp)
    return app


@pytest.fixture
def client(app):
    """テストクライアントのフィクスチャ"""
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_decorators():
    """JWT認証とコントローラーデコレータをモック（全テストで自動適用）"""
    with patch(
        "cndx_corp_back.api.help.help_api.jwt_user_context_db"
    ) as mock_jwt, patch(
        "cndx_corp_back.api.help.help_api.controller"
    ) as mock_controller, patch(
        "cndx_corp_back.common.decorators.verify_jwt_in_request"
    ), patch(
        "cndx_corp_back.common.decorators.get_jwt_identity", return_value="test_user"
    ), patch(
        "cndx_corp_back.common.decorators.get_user_permissions", return_value={}
    ):
        # デコレータをパススルーするように設定
        mock_jwt.return_value = lambda f: f
        mock_controller.return_value = lambda f: f
        yield


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
@pytest.mark.parametrize("endpoint,filename,_mimetype", LOCAL_DOWNLOAD_TEST_CASES)
def test_local_environment_downloads_all_files(
    mock_system, app, endpoint, filename, _mimetype
):
    """ローカル環境で全ファイルがダウンロードできることを確認"""
    with app.test_request_context(endpoint):
        fake_path = f"/local_data/{filename}"
        with patch(
            "cndx_corp_back.api.help.help_api.current_app"
        ) as mock_current_app, patch.object(
            HelpApi, "_resolve_local_file_path", return_value=fake_path
        ) as mock_resolve, patch.object(
            HelpApi, "_send_local_file", return_value="dummy-response"
        ) as mock_send:
            mock_current_app.logger = object()
            view = HelpApi.as_view("help_api")
            response = view()

            assert response == "dummy-response"
            mock_resolve.assert_called_once_with(HelpApi.ENDPOINT_FILE_MAP[endpoint])
            mock_send.assert_called_once()
            sent_path, _ = mock_send.call_args.args
            assert sent_path == fake_path


@patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Linux")
@pytest.mark.parametrize("endpoint,filename,mimetype", LOCAL_DOWNLOAD_TEST_CASES)
def test_production_linux_uses_fsmount(mock_system, app, endpoint, filename, mimetype):
    """本番環境（Linux）で全ファイルがFsMount経由で取得されることを確認"""
    with app.test_request_context(endpoint):
        app.config["JWT_COOKIE_DOMAIN"] = "example.com"
        with patch(
            "cndx_corp_back.api.help.help_api.current_app"
        ) as mock_current_app, patch(
            "cndx_corp_back.api.help.help_api.FsMountFileDownloadService"
        ) as mock_service_class:
            mock_response = Response()
            mock_response.headers = {}
            mock_service_instance = MagicMock()
            mock_service_instance.execute.return_value = mock_response
            mock_service_class.return_value = mock_service_instance

            mock_current_app.logger = object()
            view = HelpApi.as_view("help_api")
            response = view()

            assert response == mock_response
            mock_service_instance.execute.assert_called_once()
            called_kwargs = mock_service_instance.execute.call_args.kwargs
            assert called_kwargs["file_path"] == HelpApi.ENDPOINT_FILE_MAP[endpoint]
            # loggerはCorpLoggerインスタンスのため、存在することのみ確認
            assert "logger" in called_kwargs


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_availability_api_uses_local_checks(mock_system, app, client):
    flag_map = {
        path: idx % 2 == 0
        for idx, path in enumerate(HelpApi.ENDPOINT_FILE_MAP.values())
    }
    expected = _build_expected_availability(flag_map)

    with patch.object(
        HelpApi, "_local_file_exists", side_effect=lambda path, logger: flag_map[path]
    ) as mock_local, patch(
        "cndx_corp_back.api.help.help_api.FsMountFileCheckService"
    ) as mock_service_class:
        response = client.get("/api/help/availability")

    assert response.status_code == 200
    assert response.json == expected
    mock_local.assert_called()
    mock_service_class.assert_not_called()


@patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Linux")
def test_availability_api_uses_fsmount_checks(mock_system, app, client):
    app.config["JWT_COOKIE_DOMAIN"] = "example.com"
    flag_map = {
        path: idx % 2 == 1
        for idx, path in enumerate(HelpApi.ENDPOINT_FILE_MAP.values())
    }
    expected = _build_expected_availability(flag_map)

    with patch.object(HelpApi, "_local_file_exists") as mock_local, patch(
        "cndx_corp_back.api.help.help_api.FsMountFileCheckService"
    ) as mock_service_class:
        mock_service_instance = MagicMock()
        mock_service_instance.execute.side_effect = lambda file_path, logger: flag_map[
            file_path
        ]
        mock_service_class.return_value = mock_service_instance

        response = client.get("/api/help/availability")

    assert response.status_code == 200
    assert response.json == expected
    mock_local.assert_not_called()
    mock_service_instance.execute.assert_called()


@patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_availability_api_non_linux_returns_false(mock_system, app, client):
    app.config["JWT_COOKIE_DOMAIN"] = "example.com"
    with patch.object(HelpApi, "_local_file_exists") as mock_local, patch(
        "cndx_corp_back.api.help.help_api.FsMountFileCheckService"
    ) as mock_service_class:
        response = client.get("/api/help/availability")

    assert response.status_code == 200
    assert all(value is False for value in response.json.values())
    mock_local.assert_not_called()
    mock_service_class.assert_not_called()


@patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False)
@pytest.mark.parametrize(
    "exception_class",
    [NotFound, Forbidden, GatewayTimeout, InternalServerError],
)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Linux")
def test_production_download_errors_propagate(mock_system, app, exception_class):
    app.config["JWT_COOKIE_DOMAIN"] = "example.com"
    with app.test_request_context("/api/help/manual_EP"):
        from flask import current_app

        with patch("cndx_corp_back.api.help.help_api.current_app", current_app), patch(
            "cndx_corp_back.api.help.help_api.FsMountFileDownloadService"
        ) as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.execute.side_effect = exception_class("error")
            mock_service_class.return_value = mock_service_instance

            view = HelpApi.as_view("help_api")
            with pytest.raises(exception_class):
                view()


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
def test_get_undefined_endpoint(app):
    """未定義のエンドポイント（異常系）"""
    with app.test_request_context("/api/help/undefined_endpoint"):
        from flask import current_app

        with patch("cndx_corp_back.api.help.help_api.current_app", current_app):
            view = HelpApi.as_view("help_api")

            with pytest.raises(NotFound):
                view()


@patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_production_non_linux_returns_500(mock_system, app):
    app.config["JWT_COOKIE_DOMAIN"] = "example.com"
    with app.test_request_context("/api/help/manual_EP"):
        from flask import current_app

        with patch(
            "cndx_corp_back.api.help.help_api.current_app", current_app
        ), pytest.raises(InternalServerError):
            view = HelpApi.as_view("help_api")
            view()


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_send_local_file_uses_prepare_file_download_response(mock_system, app):
    """_send_local_fileがprepare_file_download_responseを使用することを確認"""
    with app.test_request_context("/api/help/manual_EP"):
        from urllib.parse import quote

        from flask import current_app

        # テスト用のファイルパス
        test_file_path = _build_local_file_path("LecMocマニュアル_EP.pdf")
        # テスト用のファイルが存在しない場合は、os.path.isfileとos.accessをモック
        with patch("cndx_corp_back.api.help.help_api.current_app", current_app), patch(
            "cndx_corp_back.api.help.help_api.os.path.isfile", return_value=True
        ), patch(
            "cndx_corp_back.api.help.help_api.os.access", return_value=True
        ), patch(
            "cndx_corp_back.api.help.help_api.send_file"
        ) as mock_send_file, patch(
            "cndx_corp_back.api.help.help_api.prepare_file_download_response"
        ) as mock_prepare:
            # send_fileのモックレスポンス
            mock_response = Response()
            mock_response.status_code = 200
            mock_send_file.return_value = mock_response

            # prepare_file_download_responseのモックレスポンス
            prepared_response = Response()
            prepared_response.headers["Content-Disposition"] = (
                "attachment; filename*=UTF-8''test.pdf"
            )
            mock_prepare.return_value = prepared_response

            # HelpApiインスタンスを作成して_send_local_fileを呼び出す
            help_api = HelpApi()
            result = help_api._send_local_file(test_file_path, current_app.logger)

            # send_fileが正しいパラメータで呼ばれたことを確認
            mock_send_file.assert_called_once()
            call_args = mock_send_file.call_args
            assert call_args.kwargs["mimetype"] == "application/pdf"
            assert call_args.kwargs["as_attachment"] is True
            assert call_args.kwargs["download_name"] == quote("LecMocマニュアル_EP.pdf")

            # prepare_file_download_responseが呼ばれたことを確認
            mock_prepare.assert_called_once()
            prepare_args = mock_prepare.call_args
            assert prepare_args.args[0] == mock_response
            assert prepare_args.args[1] == quote("LecMocマニュアル_EP.pdf")

            # 結果がprepare_file_download_responseの戻り値であることを確認
            assert result == prepared_response


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_send_local_file_file_not_found(mock_system, app):
    """_send_local_fileがファイルが見つからない場合に404を返すことを確認"""
    with app.test_request_context("/api/help/manual_EP"):
        from flask import current_app

        test_file_path = _build_local_file_path("nonexistent.pdf")
        with patch("cndx_corp_back.api.help.help_api.current_app", current_app), patch(
            "cndx_corp_back.api.help.help_api.os.path.isfile", return_value=False
        ):
            help_api = HelpApi()
            with pytest.raises(NotFound):
                help_api._send_local_file(test_file_path, current_app.logger)


@patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False)
@patch("cndx_corp_back.api.help.help_api.platform.system", return_value="Windows")
def test_send_local_file_no_permission(mock_system, app):
    """_send_local_fileがファイルへのアクセス権限がない場合に403を返すことを確認"""
    with app.test_request_context("/api/help/manual_EP"):
        from flask import current_app

        test_file_path = _build_local_file_path("LecMocマニュアル_EP.pdf")
        with patch("cndx_corp_back.api.help.help_api.current_app", current_app), patch(
            "cndx_corp_back.api.help.help_api.os.path.isfile", return_value=True
        ), patch("cndx_corp_back.api.help.help_api.os.access", return_value=False):
            help_api = HelpApi()
            with pytest.raises(Forbidden):
                help_api._send_local_file(test_file_path, current_app.logger)
