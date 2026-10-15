"""画像・HTML・PDFをメモリでつなぐ帳票生成サービス。"""

from pathlib import Path

import matplotlib.pyplot as plt

from .chart_service import ChartService
from .data_service import build_context, validate_data
from .pdf_service import HtmlRenderer, PdfPrinter, save_pdf


class ReportService:
    """ワーカープロセス専用の帳票生成サービス。スレッド間で共有しない。"""

    def __init__(self, browser=None):
        """テンプレート、Chromiumを一度だけ初期化する。

        Args:
            browser (pathlib.Path | None): Chromium実行ファイル。
        """
        # 顧客ごとに作り直す必要のないフォント・テンプレート・ブラウザーを準備する。
        self.charts = ChartService()
        self.html = HtmlRenderer()
        self.printer = PdfPrinter(browser)

    def generate_query_results(
        self,
        customer_row,
        daily_rows,
        supply_point,
        report_month,
        output,
        debug_dir=None,
        **column_options,
    ):
        """PDFを作成する。


        Args:
            customer_row (Mapping | sqlalchemy.Row): 契約情報の1行。
            daily_rows (Iterable[Mapping]): 日付・48枠(kWh)を持つ全日分の取得行。
            supply_point (str): 供給地点特定番号。
            report_month (str): 対象年月。YYYYMM形式。
            output (pathlib.Path): PDFの保存先。
            debug_dir (pathlib.Path | None): 任意の確認用画像・HTML保存先。
            **column_options: prepare_query_resultsのcustomer_columns、date_column、
                slot_columns、quality_columns、configを任意指定する。

        Returns:
            dict: PDF保存先、バイト数、成功ステータス。

        Raises:
            ValueError: 取得列・実績・契約情報が不正な場合。
        """
        from .query_result_service import prepare_query_results

        frame, config = prepare_query_results(
            customer_row, daily_rows, supply_point, report_month, **column_options
        )
        return self.generate_frame(frame, config, output, debug_dir)

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
        self.printer.close()
