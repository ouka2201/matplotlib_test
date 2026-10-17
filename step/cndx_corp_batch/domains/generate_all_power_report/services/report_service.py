"""処理6・9～19：帳票No.0～7を2ページに描画し、電力見える化レポートをPDFで保存する。"""

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
        """取得済みの契約情報・30分値を帳票用に変換し、PDFを作成する。

        Args:
            customer_row (Mapping | sqlalchemy.Row): 契約情報の1行。
            daily_rows (Iterable[Mapping]): 日付・48枠(kWh)を持つ全日分の取得行。
            supply_point (str): 供給地点特定番号。
            report_month (str): 対象年月。YYYYMM形式。
            output (pathlib.Path): PDFの保存先。
            debug_dir (pathlib.Path | None): 確認用の画像・HTMLの保存先。指定は任意。
            **column_options: prepare_query_resultsのcustomer_columns、date_column、
                slot_columns、quality_columns、configを任意指定する。

        Returns:
            dict: PDF保存先、バイト数、成功ステータス。

        Raises:
            KeyError: 契約情報または30分値の必須列がない場合。
            ValueError: 数値・日時を変換できない場合、または契約電力が正の有限数でない場合。
        """
        from .query_result_service import prepare_query_results

        frame, config = prepare_query_results(
            customer_row, daily_rows, supply_point, report_month, **column_options
        )
        return self.generate_frame(frame, config, output, debug_dir)

    def generate_frame(self, df, config, output, debug_dir=None):
        """処理9～19：30分需要電力を集計し、帳票画像・HTMLを経由してPDFを保存する。

        Args:
            df (pandas.DataFrame): timestamp・kw列を持つ30分需要電力。kwはkWhから換算済みの値。
            config (dict): 契約情報と対象月。
            output (pathlib.Path): 顧客固有のPDF保存先。
            debug_dir (pathlib.Path | None): 確認用ファイルの保存先。指定は任意。

        Returns:
            dict: PDF保存先、バイト数、成功ステータス。
        """
        # 処理5・21の実装差：通常はワークディレクトリを作らず、ページ画像をHTMLに埋め込む。
        # debug_dir指定時は確認用PNG・HTMLを保存する。確認用ファイルは自動削除しない。
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
            # 描画途中で失敗した場合も、このワーカーに残ったFigureを閉じる。
            plt.close("all")

    def close(self):
        """プロセス終了前にブラウザーを閉じる。"""
        self.printer.close()
