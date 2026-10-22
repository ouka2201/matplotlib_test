import logging
import uuid

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from sqlalchemy import event
from werkzeug.middleware.proxy_fix import ProxyFix

from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.config import (
    Config,
    ItConfig,
    TestingConfig,
    get_config,
    maintConfig,
)
from cndx_corp_back.ext import bcrypt, db, jwt
from cndx_corp_back.utils import utils


def create_app(config_name=None):
    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_port=1)
    app.logger = CorpLogger()

    bcrypt.init_app(app)
    jwt.init_app(app)

    # CORS設定
    if config_name == "production":
        CORS(
            app,
            supports_credentials=True,
            resources={
                r"/api/*": {
                    "origins": [
                        "https://data.ts.tdh.tepcube.jp:10138",
                        "https://localhost:10138",
                    ],
                    "allow_headers": [
                        "Content-Type",
                        "Authorization",
                        "X-CSRF-TOKEN",
                        "headers",
                        "X-CLIENT-LOCATION",
                    ],
                    "expose_headers": ["Content-Disposition"],
                    "methods": ["GET", "POST", "OPTIONS"],
                }
            },
        )
    elif config_name == "staging":
        CORS(
            app,
            supports_credentials=True,
            resources={
                r"/api/*": {
                    "origins": [
                        "https://data.ts.tdh.tepcube.jp:10134",
                        "https://localhost:10134",
                    ],
                    "allow_headers": [
                        "Content-Type",
                        "Authorization",
                        "X-CSRF-TOKEN",
                        "headers",
                        "X-CLIENT-LOCATION",
                    ],
                    "expose_headers": ["Content-Disposition"],
                    "methods": ["GET", "POST", "OPTIONS"],
                }
            },
        )
    else:
        CORS(
            app,
            supports_credentials=True,
            methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-CSRF-TOKEN",
                "headers",
                "X-CLIENT-LOCATION",
            ],
            expose_headers=["Content-Disposition"],
        )

    # コンフィグ設定
    if config_name == "testit":
        config_class = ItConfig
    elif config_name == "testmaint":
        config_class = maintConfig
    else:
        config_class = get_config()

    app.config.from_object(config_class)

    # ProxyFix を使っているので trust proxy 前提
    app.config["PREFERRED_URL_SCHEME"] = "https"

    # Flask-JWT-Extended setup
    # app.config["JWT_SECRET_KEY"] = config_class.JWT_SECRET_KEY
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_COOKIE_SECURE"] = (
        config_class.JWT_COOKIE_SECURE
    )  # ローカル開発ならFalseに
    app.config["JWT_COOKIE_SAMESITE"] = config_class.JWT_COOKIE_SAMESITE
    app.config["JWT_COOKIE_HTTPONLY"] = config_class.JWT_COOKIE_HTTPONLY
    # app.config["JWT_COOKIE_SAMESITE"] = "Lax"  # Noneにするとsecure必須なので要注意
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = config_class.JWT_ACCESS_TOKEN_EXPIRES
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = config_class.JWT_REFRESH_TOKEN_EXPIRES
    app.config["JWT_ALGORITHM"] = config_class.JWT_ALGORITHM
    with open(config_class.PRIVATE_KEY_PATH, "rb") as f:
        app.config["JWT_PRIVATE_KEY"] = f.read()
    with open(config_class.PUBLIC_KEY_PATH, "rb") as f:
        app.config["JWT_PUBLIC_KEY"] = f.read()
    with open(config_class.REVERPROXY_PUBLIC_KEY_PATH, "rb") as f:
        app.config["REVERPROXY_JWT_PUBLIC_KEY"] = f.read()

    # Tableau設定
    app.config["TABLEAU_WORKBOOK_NAME"] = config_class.get_tbl_wb_nm()
    app.config["TABLEAU_DATASOURCE_NAME"] = config_class.get_tbl_ds_nm()

    # データベース初期化
    app.config["SQLALCHEMY_DATABASE_URI"] = config_class.get_db_uri()
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "max_overflow": 20,
        "connect_args": {"options": "-csearch_path=db_corp,db_common"},
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_SESSION_OPTIONS"] = {"expire_on_commit": False}
    db.init_app(app)

    from cndx_corp_back.common.load_master import load_mst_data

    # ログレベル設定
    utils.set_log_level(Config.get_env_mode())

    # エラーハンドラー登録
    from cndx_corp_back.common.error_handler import register_error_handlers

    register_error_handlers(app)

    # 登録ブループリント

    # ファイルAPI
    # 認証API
    from cndx_corp_back.api.auth import auth_bp

    # 建物管理API
    from cndx_corp_back.api.building import building_bp

    # 建物グループ情報管理API
    from cndx_corp_back.api.building_group_management import (
        building_group_management_bp,
    )

    # お知らせ情報API
    from cndx_corp_back.api.CMTP_Announcements import announcements_bp

    # 担当者設定API
    from cndx_corp_back.api.contact_person import contact_person_bp

    # 企業管理API
    from cndx_corp_back.api.corp import corp_bp

    # 拠点エネルギー管理API
    from cndx_corp_back.api.EBMG_BaseEnergy import base_energy_info_inquiry_bp

    # 対象建物・事業所取得API
    # 30分値対象建物選択API
    from cndx_corp_back.api.EBMV_Per30minData import (
        corp_building_info_bp,
        per_30min_data_bp,
    )

    # ファイルAPI
    from cndx_corp_back.api.file import file_bp
    from cndx_corp_back.api.FLUL_30m_data import per_30m_data_upload_bp

    # ヘルプAPI
    from cndx_corp_back.api.help import help_bp

    # マスタ管理API
    # from cndx_corp_back.api.mst_manage import mst_manage_bp
    from cndx_corp_back.api.MSOG_corprationMstOperation import mst_manage_bp
    from cndx_corp_back.api.MSOG_userOrganizationMstOperation import (
        mst_organization_bp,
    )

    # マスタデータ管理API
    from cndx_corp_back.api.mst_data import mst_data_bp
    from cndx_corp_back.api.msus_user import user_bp

    # ユーザー情報管理API
    from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp

    # レポートAPI
    from cndx_corp_back.api.report import report_bp
    from cndx_corp_back.api.report_create_management import (
        report_create_management_bp,
    )

    # UI API
    from cndx_corp_back.api.ui import ui_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(mst_data_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(corp_bp)
    app.register_blueprint(building_bp)
    # app.register_blueprint(building_energy_bp)
    app.register_blueprint(mst_manage_bp)
    app.register_blueprint(contact_person_bp)
    app.register_blueprint(per_30m_data_upload_bp)
    app.register_blueprint(per_30min_data_bp)
    app.register_blueprint(corp_building_info_bp)
    app.register_blueprint(mst_organization_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(report_create_management_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(base_energy_info_inquiry_bp)
    app.register_blueprint(building_group_management_bp)
    app.register_blueprint(mst_user_info_bp)
    app.register_blueprint(help_bp)

    # ステータス管理API
    # from cndx_corp_back.api.status import status_bp
    # app.register_blueprint(status_bp)

    with app.app_context():

        # マスタデータを読込
        # TODO テストで一時コメントアウト
        load_mst_data(engine=db.engine)

        # SQL ロギングイベントを登録
        @event.listens_for(db.engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            logging.info(f"SQL: {statement} Params: {parameters}")

        @app.before_request
        def before_request():
            if request.method == "OPTIONS":
                return jsonify({"message": utils.get_message("OK")}), 200
            g.request_id = str(uuid.uuid4())

            if config_name == "development":
                # テスト用 token の場合
                if request.headers.get("Authorization") == "Bearer TEST_TOKEN":
                    from datetime import timedelta

                    from flask_jwt_extended import create_access_token

                    # dummy token 作成
                    dummy_token = create_access_token(
                        identity="ep1@test.com",
                        additional_claims={
                            "email": "ep1@test.com",
                            "role": "admin",
                            "env": "dev",
                        },
                        expires_delta=timedelta(hours=12),
                    )
                    request.environ["HTTP_AUTHORIZATION"] = f"Bearer {dummy_token}"

        @app.after_request
        def after_request(response):
            if (
                request.method != "OPTIONS"
            ):  # and not request.path.startswith("/api/auth"):
                if hasattr(g, "request_id"):
                    response.headers["X-Request-ID"] = (
                        g.request_id
                    )  # レスポンスヘッダーに追加
            return response

    # ステータス管理API
    # from cndx_corp_back.api.status import status_bp
    # app.register_blueprint(status_bp)

    # app.logger.debug(f"環境: {config_name}")

    return app
