"""HTMLをメモリでレンダリングし、ChromiumでPDFへ変換する。"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from playwright.sync_api import sync_playwright


class HtmlRenderer:
    """画像を配置するHTMLテンプレートをプロセス内で再利用する。"""

    def __init__(self):
        """レンダリングに必要な静的情報を読み込む。

        文字はmatplotlibでページPNGに含めるため、HTML側のフォント設定は不要。
        """
        # テンプレートを読み込む。値不足はエラーにし、文字列はHTMLとして安全にエスケープする。
        env = Environment(
            loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
            autoescape=select_autoescape(["html"]),
            undefined=StrictUndefined,
        )
        self.template = env.get_template("report.html")

    def render(self, context):
        """表示用辞書からHTML文字列を作る。

        Args:
            context (dict): 集計結果とchartsの画像data URI。

        Returns:
            str: ページPNGを埋め込んだHTML。
        """
        return self.template.render(**context)


class PdfPrinter:
    """1プロセス内でChromiumを再利用する同期PDFプリンター。"""

    def __init__(self, executable=None):
        """ブラウザーを起動する。

        Args:
            executable (pathlib.Path | None): 任意のChromium実行ファイル。
        """
        self.playwright = sync_playwright().start()
        try:
            options = {"headless": True}
            if executable:
                options["executable_path"] = str(Path(executable).resolve())
            self.browser = self.playwright.chromium.launch(**options)
        except Exception:
            self.playwright.stop()
            raise

    def print_html(self, html):
        """HTML文字列を直接読み込み、PDFをメモリへ返す。

        Args:
            html (str): data URIの画像を含む完成HTML。

        Returns:
            bytes: A4横のPDFバイト列。

        Raises:
            RuntimeError: 印刷領域からはみ出している場合。
            playwright.sync_api.Error: 読み込みや印刷に失敗した場合。
        """
        # Chromium本体は再利用し、顧客ごとに独立したコンテキストを作る。
        # 前の顧客のページや画像が次の顧客に残らないよう、最後に閉じる。
        context = self.browser.new_context()
        try:
            page = context.new_page()
            # HTMLファイルを経由せず、メモリ上の文字列を直接読み込ませる。
            page.set_content(html, wait_until="load")
            page.emulate_media(media="print")
            # ページPNGのデコードを待ち、画像欠落を防ぐ。
            page.evaluate("""async () => {
                await Promise.all(Array.from(document.images, img => img.decode()));
            }""")
            # HTML側でページ全体のはみ出しを検査する。
            # PNG内部の文字はここでは検査できないため、描画関数で文字幅を検査している。
            problems = page.evaluate(
                """() => Array.from(document.querySelectorAll('[data-fit]')).flatMap(el =>
                el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2
                ? [el.id || el.className] : [])"""
            )
            if problems:
                raise RuntimeError(f"印刷領域からはみ出しています: {problems}")
            return page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            context.close()

    def close(self):
        """ブラウザーとPlaywrightを終了する。"""
        try:
            self.browser.close()
        finally:
            self.playwright.stop()


def save_pdf(data, output):
    """PDFを固有の一時ファイルへ書き、成功時だけ保存先と置き換える。

    Args:
        data (bytes): 完成したPDF。
        output (pathlib.Path): 顧客ごとに異なるPDF保存先。

    Raises:
        OSError: 書き込みまたは置き換えに失敗した場合。
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # 最終PDFを直接上書きしない。同じ出力フォルダー内に固有名で一時保存する。
    temporary = None
    try:
        with NamedTemporaryFile(
            dir=output.parent, suffix=".pdf.tmp", delete=False
        ) as file:
            temporary = Path(file.name)
            file.write(data)
        # 完全に書き終わってから最終名へ置き換える。途中失敗では既存PDFを保持する。
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
