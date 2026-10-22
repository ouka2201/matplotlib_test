import datetime
import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from flask import g
from flask_jwt_extended import get_jwt_identity


class DailyFileHandler(logging.FileHandler):
    def __init__(self, log_dir, auth_flg=None):
        self.log_dir = log_dir
        self.current_date = datetime.datetime.now().strftime("%Y%m%d")
        self.prefix = "auth" if auth_flg else "log"
        filename = f"{log_dir}/{self.prefix}_{self.current_date}.log"
        super().__init__(filename, encoding="utf-8")

    def emit(self, record):
        today = datetime.datetime.now().strftime("%Y%m%d")

        if today != self.current_date:
            self.current_date = today
            self.stream.close()
            self.baseFilename = f"{self.log_dir}/{self.prefix}_{today}.log"
            self.stream = self._open()

        super().emit(record)

class CorpLogger:
    """
    アプリケーションのロギングを管理するクラス。

    環境変数からログレベルを取得し、設定されたレベルに応じてログ出力を行います。
    INFO, ERROR, WARNING, CRITICAL, DEBUGのログレベルが利用可能です。
    """

    def __init__(self):
        """
        クラスの初期化メソッド。

        環境変数'LOG_LEVEL'からログレベルを読み取り、ログレベルを設定します。
        ログレベルが設定されていない場合は、デフォルトとしてINFOレベルが使用されます。
        """
        self.screen_id = None
        self.api_id = None
        self.user_id = None

        # --- ログレベル設定 ---
        log_level_str = os.environ.get("LOG_LEVEL", "info").lower()
        log_level_map = {
            "error": logging.ERROR,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
            "debug": logging.DEBUG,
            "info": logging.INFO,
        }
        log_level = log_level_map.get(log_level_str, logging.INFO)

        # --- ログディレクトリ作成 ---
        app_log_for_splunk_dir = './log/application'
        app_log_dir = '/bd-fs-mnt/TenantShare/log'
        auth_log_dir = '/var/log/auth'
        auth_log_dir_bk = '/bd-fs-mnt/TenantShare/log/auth'
        os.makedirs(app_log_dir, exist_ok=True)
        os.makedirs(app_log_for_splunk_dir, exist_ok=True)
        os.makedirs(auth_log_dir, exist_ok=True)
        os.makedirs(auth_log_dir_bk, exist_ok=True)

        # --- ISO 8601 タイムスタンプに差し替え ---
        logging.Formatter.formatTime = (
            lambda self, record, datefmt=None: datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc
            )
            .astimezone(datetime.timezone(datetime.timedelta(hours=9)))
            .isoformat(sep="T", timespec="milliseconds")
        )

        # ========== corp logger ==========
        self.logger = logging.getLogger("corp")
        self.logger.setLevel(log_level)

        log_file_suffix = "%Y%m%d"
        if not self.logger.handlers:
            # コンソール出力
            stream_handler = logging.StreamHandler()
            self.logger.addHandler(stream_handler)

            # ファイル出力
            if os.getenv("FLASK_ENV") in ("it", "maint", "production"):
                file_handler = DailyFileHandler(app_log_dir)
                file_handler.setLevel(log_level)
                file_handler.suffix = log_file_suffix
                file_handler.namer = lambda name: name.replace("log.log.", "log_") + ".log"
                self.logger.addHandler(file_handler)

            file_handler_splunk = DailyFileHandler(app_log_for_splunk_dir)
            file_handler_splunk.setLevel(log_level)
            file_handler_splunk.suffix = log_file_suffix
            file_handler_splunk.namer = lambda name: name.replace("log.log.", "log_") + ".log"
            self.logger.addHandler(file_handler_splunk)
            

        # ========== auth logger ==========
        self.auth_logger = logging.getLogger("auth")
        self.auth_logger.setLevel(log_level)

        if not self.auth_logger.handlers:
            auth_handler = DailyFileHandler(auth_log_dir, auth_flg=True)
            auth_handler.setLevel(log_level)
            auth_handler.suffix = log_file_suffix
            auth_handler.namer = lambda name: name.replace("log.log.", "auth_") + ".log"
            self.auth_logger.addHandler(auth_handler)

            auth_bk_handler = DailyFileHandler(auth_log_dir_bk)
            auth_bk_handler.setLevel(log_level)
            auth_bk_handler.suffix = log_file_suffix
            auth_bk_handler.namer = lambda name: name.replace("auth.log.", "auth_") + ".log"
            self.auth_logger.addHandler(auth_bk_handler)

        # 必要ならここに共通出力先を記憶（任意）
        self.ch = self.logger.handlers + self.auth_logger.handlers
        self.logger.propagate = False

    def _get_user_id(self):
        """JWT から `user_id` を取得（認証なしなら `None`）"""
        try:
            res = get_jwt_identity()
        except Exception as e:
            res = None
        return res

    def _get_request_id(self):
        """Flask `g` から `request_id` を取得"""
        return getattr(g, "request_id", "N/A")

    def _set_formatter(self):
        """
        ログのフォーマッタを設定します。
        """
        formatter = logging.Formatter(
            "%(asctime)s "
            "levelname:%(levelname)s "
            "filename:%(filename)s "
            "funcname:%(funcName)s "
            "message:%(message)s"
        )
        for handler in self.ch:
            handler.setFormatter(formatter)

    def _set_formatter_for_logging(self):
        """
        ログのフォーマッタを設定します。
        """
        formatter = logging.Formatter(
            "%(asctime)s "
            "%(levelname)s "
            "user_id:%(user_id)s "
            "screen_id:%(screen_id)s "
            "api_id:%(api_id)s "
            "request_id:%(request_id)s "
            "%(filename)s "
            "funcname:%(funcName)s "
            "msg:%(message)s"
        )
        for handler in self.ch:
            handler.setFormatter(formatter)

    def info(self, msg, auth=None):
        """
        INFOレベルのログを出力します。

        パラメータ:
            msg (str): ログに出力するメッセージ。
        """
        if auth:
            self._set_formatter()
            self.auth_logger.info(msg, stacklevel=2)
        else:
            self._set_formatter_for_logging()
            extra = {
                # "user_id": "local",
                "user_id": self._get_user_id(),
                "request_id": self._get_request_id(),
                "screen_id": self.screen_id,
                "api_id": self.api_id
            }
            self.logger.info(msg, extra=extra, stacklevel=2)

    def warning(self, msg, auth=None):
        """
        WARNINGレベルのログを出力します。

        パラメータ:
            msg (str): ログに出力するメッセージ。
        """
        if auth:
            self._set_formatter()
            self.auth_logger.info(msg, stacklevel=2)
        else:
            self._set_formatter_for_logging()
            extra = {
                "user_id": self._get_user_id(),
                "request_id": self._get_request_id(),
                "screen_id": self.screen_id,
                "api_id": self.api_id
            }
            self.logger.warning(msg, extra=extra, stacklevel=2)

    def error(self, msg, auth=None):
        """
        ERRORレベルのログを出力します。

        パラメータ:
            msg (str): ログに出力するメッセージ。
        """
        if auth:
            self._set_formatter()
            self.auth_logger.info(msg, stacklevel=2)
        else:
            self._set_formatter_for_logging()
            extra = {
                "user_id": self._get_user_id(),
                "request_id": self._get_request_id(),
                "screen_id": self.screen_id,
                "api_id": self.api_id
            }
            self.logger.error(msg, extra=extra, stacklevel=2, exc_info=True)

    def critical(self, msg, auth=None):
        """
        CRITICALレベルのログを出力します。

        パラメータ:
            msg (str): ログに出力するメッセージ。
        """
        if auth:
            self._set_formatter()
            self.auth_logger.info(msg, stacklevel=2)
        else:
            self._set_formatter_for_logging()
            extra = {
                "user_id": self._get_user_id(),
                "request_id": self._get_request_id(),
                "screen_id": self.screen_id,
                "api_id": self.api_id
            }
            self.logger.critical(msg, extra=extra, stacklevel=2)

    def debug(self, msg, auth=None):
        """
        DEBUGレベルのログを出力します。

        パラメータ:
            msg (str): ログに出力するメッセージ。
        """
        if auth:
            self._set_formatter()
            self.auth_logger.info(msg, stacklevel=2)
        else:
            self._set_formatter_for_logging()
            extra = {
                "user_id": self._get_user_id(),
                "request_id": self._get_request_id(),
                "screen_id": self.screen_id,
                "api_id": self.api_id
            }
            self.logger.debug(msg, extra=extra, stacklevel=2)


def log_writer(logger):
    """
    ロガーを使用して関数の開始、終了、および引数をデバッグログに記録するデコレータ。

    パラメータ:
        logger (CorpLogger): ログ出力に使用するCorpLoggerインスタンス。

    戻り値:
        function: デコレートされた関数。
    """

    def _log_writer(func):

        def wrapper(*args, **kwargs):
            logger.debug("start " + func.__name__)
            for k, v in kwargs.items():
                logger.debug(str(k) + " :" + str(v))

            result = func(*args, **kwargs)

            logger.debug(func.__name__ + " returns :" + str(result))
            logger.debug("end " + func.__name__)
            return result

        return wrapper

    return _log_writer
