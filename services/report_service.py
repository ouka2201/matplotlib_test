"""画像・HTML・PDFをメモリでつなぐ帳票生成サービス。"""

from pathlib import Path
import matplotlib.pyplot as plt
from services.chart_service import ChartService
from services.data_service import load_data, build_context, validate_data
from services.pdf_service import HtmlRenderer, PdfPrinter, save_pdf


class ReportService:
    """ワーカープロセス専用の帳票生成サービス。スレッド間で共有しない。"""

    def __init__(self, font=None, browser=None, bold_font=None):
        """フォント、テンプレート、Chromiumを一度だけ初期化する。

        Args:
            font (pathlib.Path | None): 通常書体。省略時はメイリオを検出する。
            browser (pathlib.Path | None): Chromium実行ファイル。
            bold_font (pathlib.Path | None): 同じファミリーの太字書体。
        """
        # 顧客ごとに作り直す必要のないフォント・テンプレート・ブラウザーを準備する。
        self.charts = ChartService(font=font, bold_font=bold_font)
        try:
            self.html = HtmlRenderer()
            self.printer = PdfPrinter(browser)
        except Exception:
            self.charts.fonts.close()
            raise

    def generate(self, csv_path, config, output, debug_dir=None):
        """1顧客分を生成する。通常は完成PDFだけをファイルへ保存する。

        Args:
            csv_path (pathlib.Path): 12か月分の電力CSV。
            config (dict): 契約情報・対象月などの設定。
            output (pathlib.Path): この顧客のPDF保存先。
            debug_dir (pathlib.Path | None): 指定時だけPNGとHTMLを保存する。

        Returns:
            dict: PDF保存先、バイト数、成功ステータス。

        Raises:
            ValueError: データや設定、描画領域に不正がある場合。
            OSError: 入出力に失敗した場合。
        """
        return self.generate_frame(
            load_data(csv_path, config["target_month"]), config, output, debug_dir
        )

    def generate_database(
        self, source, supply_point, report_month, config, output, debug_dir=None
    ):
        """テーブルの48枠と契約電力を取得してPDFを作る。

        Args:
            source (DatabaseSource): 現ワーカー専用のDB取得サービス。
            supply_point (str): 供給地点特定番号。
            report_month (str): 指定月を含む12か月の最終月。
            config (dict): 名義・住所・お客さま番号などの帳票設定。
            output (pathlib.Path): 顧客固有のPDF保存先。
            debug_dir (pathlib.Path | None): 任意の確認用画像・HTMLの保存先。

        Returns:
            dict: PDF保存先と成功ステータス。
        """
        # DBで日別48枠と契約電力を取得する。この関数へ戻る時点でDB接続は返却済み。
        df, contract = source.load(supply_point, report_month)
        # 顧客設定はコピーし、今回の対象月とDBの契約電力だけを反映する。
        # 共有された元の設定を変更して、次の顧客に影響させないため。
        config = {**config, "target_month": report_month, "contract_kw": contract}
        return self.generate_frame(df, config, output, debug_dir)

    def generate_frame(self, df, config, output, debug_dir=None):
        """CSVやDBから得た共通DataFrameをメモリで描画する。

        Args:
            df (pandas.DataFrame): timestamp・kw列を持つ30分データ。
            config (dict): 契約情報と対象月。
            output (pathlib.Path): 顧客固有のPDF保存先。
            debug_dir (pathlib.Path | None): 任意の確認用ファイル保存先。

        Returns:
            dict: PDF保存先、バイト数、成功ステータス。
        """
        # 通常はNoneでファイルを作らない。明示指定された確認用フォルダーだけ使用する。
        self.charts.output_dir = Path(debug_dir) if debug_dir else None
        if self.charts.output_dir:
            self.charts.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            df = validate_data(df, config["target_month"])
            # 共通データを集計し、PNGバイト列→data URI付きHTML→PDFバイト列の順につなぐ。
            context, series = build_context(df, config)
            context["charts"] = self.charts.create_all(series, config, context)
            html = self.html.render(context)
            if debug_dir:
                (Path(debug_dir) / "report.html").write_text(html, encoding="utf-8")
            pdf = self.printer.print_html(html)
            # 中間画像・HTMLを通常は保存せず、完成したPDFだけを書き出す。
            save_pdf(pdf, output)
            return {"status": "succeeded", "output": str(output), "bytes": len(pdf)}
        finally:
            # 1顧客分の画像を解放してから次のジョブへ進む。
            # 失敗時に残ったFigureも閉じ、1000件分の画像を蓄積しない。
            self.charts.png_bytes.clear()
            plt.close("all")

    def close(self):
        """プロセス終了前にブラウザーを閉じる。"""
        try:
            self.printer.close()
        finally:
            self.charts.fonts.close()
