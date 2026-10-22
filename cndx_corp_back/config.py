import json
import os
import platform
from datetime import timedelta
from pathlib import Path

from .constant import constants as Constants

TBL_WORKBOOK_NAME = "CO2企業カルテ_STEP2_dev"
TBL_DATASOURCE_NAME = "bnk_datasouce_step3"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_FOLDER = "temp_uploads"
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_TIMEOUT = 30

    # JWT設定
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev")  # "cndxjwt"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(hours=3)
    # JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=2)
    # JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=3)
    JWT_ALGORITHM = "RS256"  # 署名アルゴリズムをRS256に変更
    PRIVATE_KEY_PATH = "/etc/jwt/jwt_private.pem"
    PUBLIC_KEY_PATH = "/etc/jwt/jwt_public.pem"
    REVERPROXY_PUBLIC_KEY_PATH = "/etc/reverproxy_jwt/nameid_public_key.pem"

    # セッションタイムアウト設定（環境変数から取得、デフォルト3時間）
    # 環境変数 SESSION_TIMEOUT_HOURS で時間数を指定（例: "3"）
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "3"))
    SESSION_TIMEOUT = timedelta(hours=SESSION_TIMEOUT_HOURS)

    TABLEAU_SERVER_URL = "http://10.191.33.99"  # Tableau Server の URL

    TABLEAU_USERNAME = os.getenv("TABLEAU_USERNAME")  # ユーザー名
    TABLEAU_PASSWORD = os.getenv("TABLEAU_PASSWORD")  # パスワード

    HDFS_BASE_PATH = "dtap://TenantStorage"

    @staticmethod
    def get_env_mode():
        if platform.system() == "Linux":
            return os.environ.get("CORP_RUN_MODE")
        return Constants.RunMode.DEV.value


class ProductionConfig(Config):
    AIRFLOW_URL = "https://data.ts.tdh.tepcube.jp:10020/api/v1"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://data.ts.tdh.tepcube.jp:10134")

    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True

    @staticmethod
    def get_db_uri():
        return os.getenv("DATABASE_URL")

    @staticmethod
    def get_tbl_wb_nm():
        return "CO2企業カルテ_STEP2"

    @staticmethod
    def get_tbl_ds_nm():
        return "step2_datasource"


class StagingConfig(Config):
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True
    # AIRFLOW_URL = "https://data.ts.tdh.tepcube.jp:10030/api/v1"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://data.ts.tdh.tepcube.jp:10147")

    @staticmethod
    def get_db_uri():
        return os.getenv("DATABASE_URL")

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


class DevelopmentConfig(Config):
    JWT_COOKIE_DOMAIN = "localhost"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_HTTPONLY = True

    ABS_DIR = os.path.dirname(os.path.abspath(__file__))
    CONF_DIR = os.path.join(ABS_DIR, "conf")

    # ファイルを指定する場合
    PRIVATE_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_private.pem")
    PUBLIC_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_public.pem")
    REVERPROXY_PUBLIC_KEY_PATH = os.path.join(
        CONF_DIR, "keys", "maint", "nameid_public_key.pem"
    )

    @staticmethod
    def get_db_uri():
        config_path = Path(Config.BASE_DIR) / Constants.DBURL.DB_CONNECTOR_DEV_URL.value
        with open(config_path, "r") as f:
            config = json.load(f)["postgre"]
        return (
            f"postgresql://"
            f"{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}"
            f"/{config['database']}"
        )

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


class ItConfig(Config):
    # JWT_COOKIE_DOMAIN = "localhost"
    # JWT_COOKIE_SECURE = False

    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True

    ABS_DIR = os.path.dirname(os.path.abspath(__file__))
    CONF_DIR = os.path.join(ABS_DIR, "conf")

    # ファイルを指定する場合
    PRIVATE_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_private.pem")
    PUBLIC_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_public.pem")
    REVERPROXY_PUBLIC_KEY_PATH = os.path.join(
        CONF_DIR, "keys", "maint", "nameid_public_key.pem"
    )

    @staticmethod
    def get_db_uri():
        config_path = Path(Config.BASE_DIR) / Constants.DBURL.DB_CONNECTOR_IT_URL.value
        with open(config_path, "r") as f:
            config = json.load(f)["postgre"]
        return (
            f"postgresql://"
            f"{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}"
            f"/{config['database']}"
        )

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


class maintConfig(Config):
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True

    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True
    # PRIVATE_KEY_PATH = Path(Config.BASE_DIR) /"conf"/ "keys" / "maint" / "private_key.pem"
    # PUBLIC_KEY_PATH = Path(Config.BASE_DIR) / "conf" / "keys" / "maint" / "public_key.pem"

    ABS_DIR = os.path.dirname(os.path.abspath(__file__))
    CONF_DIR = os.path.join(ABS_DIR, "conf")

    # ファイルを指定する場合
    PRIVATE_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_private.pem")
    PUBLIC_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_public.pem")
    REVERPROXY_PUBLIC_KEY_PATH = os.path.join(
        CONF_DIR, "keys", "maint", "nameid_public_key.pem"
    )

    # AIRFLOW_URL = "https://data.ts.tdh.tepcube.jp:10030/api/v1"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://data.ts.tdh.tepcube.jp:10147")

    @staticmethod
    def get_db_uri():
        config_path = (
            Path(Config.BASE_DIR) / Constants.DBURL.DB_CONNECTOR_MAINT_URL.value
        )
        with open(config_path, "r") as f:
            config = json.load(f)["postgre"]
        return (
            f"postgresql://"
            f"{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}"
            f"/{config['database']}"
        )

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


class TestingConfig(Config):
    TESTING = True

    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_TIMEOUT = 30

    @staticmethod
    def get_db_uri():
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if test_db_url:
            return test_db_url

        config_path = (
            Path(Config.BASE_DIR) / Constants.DBURL.DB_CONNECTOR_TEST_URL.value
        )
        with open(config_path, "r") as f:
            config = json.load(f)["postgre"]

        return (
            f"postgresql://"
            f"{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}"
            f"/{config['database']}"  # テスト用のDB名にする
        )

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


class LocalTestingConfig(Config):
    TESTING = True

    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_TIMEOUT = 30

    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True

    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_HTTPONLY = True
    ABS_DIR = os.path.dirname(os.path.abspath(__file__))
    CONF_DIR = os.path.join(ABS_DIR, "conf")

    # ファイルを指定する場合
    PRIVATE_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_private.pem")
    PUBLIC_KEY_PATH = os.path.join(CONF_DIR, "keys", "maint", "jwt_public.pem")
    REVERPROXY_PUBLIC_KEY_PATH = os.path.join(
        CONF_DIR, "keys", "maint", "nameid_public_key.pem"
    )

    # AIRFLOW_URL = "https://data.ts.tdh.tepcube.jp:10030/api/v1"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://data.ts.tdh.tepcube.jp:10147")

    @staticmethod
    def get_db_uri():
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if test_db_url:
            return test_db_url

        config_path = (
            Path(Config.BASE_DIR) / Constants.DBURL.DB_CONNECTOR_LOCAL_URL.value
        )
        with open(config_path, "r") as f:
            config = json.load(f)["postgre"]

        return (
            f"postgresql://"
            f"{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}"
            f"/{config['database']}"  # テスト用のDB名にする
        )

    @staticmethod
    def get_tbl_wb_nm():
        return TBL_WORKBOOK_NAME

    @staticmethod
    def get_tbl_ds_nm():
        return TBL_DATASOURCE_NAME


def get_config():
    if os.getenv("FLASK_ENV") == "production":
        return ProductionConfig
    elif (
        os.getenv("FLASK_ENV") == "staging"
        or os.getenv("FLASK_ENV") == "it"
        or os.getenv("FLASK_ENV") == "maint"
    ):
        return StagingConfig
    elif os.getenv("FLASK_ENV") == "testing":
        return TestingConfig
    else:
        print("DevelopmentConfig")
        return LocalTestingConfig
