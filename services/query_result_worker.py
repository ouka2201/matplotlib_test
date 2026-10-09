"""既存バッチの取得結果を、専用プロセスでPDF化する入口。"""

from multiprocessing.util import Finalize
from pathlib import Path

_service = None


def _close_query_worker():
    """ワーカー終了時に、再利用していた帳票サービスを閉じる。"""
    if _service is not None:
        _service.close()


def initialize_query_worker(font=None, browser=None, bold_font=None):
    """各PDFワーカーでReportServiceを一度だけ初期化する。

    Args:
        font (str | None): 通常書体のパス。
        browser (str | None): Chromium実行ファイルのパス。
        bold_font (str | None): 太字書体のパス。
    """
    global _service
    from services.report_service import ReportService

    _service = ReportService(
        font=Path(font) if font else None,
        browser=Path(browser) if browser else None,
        bold_font=Path(bold_font) if bold_font else None,
    )
    Finalize(None, _close_query_worker, exitpriority=10)


def render_query_result_job(payload):
    """通常の辞書と値だけを受け取り、1件のPDFを作成する。

    Args:
        payload (dict): generate_query_resultsへ渡すキーワード引数。
            DBセッション・Result・ReportServiceは含めない。

    Returns:
        dict: PDF保存先、バイト数、成功ステータス。

    Raises:
        RuntimeError: ワーカー初期化なしで呼び出した場合。
    """
    if _service is None:
        raise RuntimeError("initialize_query_workerでPDFワーカーを初期化してください")
    return _service.generate_query_results(**payload)
