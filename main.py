"""CSV → 集計 → matplotlib PNG → Jinja2 HTML → Playwright PDF."""

import argparse
import json
from pathlib import Path

from services.report_service import ReportService


def main():
    """コマンドライン引数に従い、CSVから2ページの帳票を生成する。

    --csv、--config、--output、--font、--font-bold、--browser、--debug-dirを受け取る。
    集計、PNG生成、HTML生成、PDF印刷の順に実行し、
    通常は画像とHTMLをメモリで扱い、PDFだけを保存する。

    Raises:
        ValueError: 入力データ、設定値、描画領域に不正がある場合。
        OSError: 入力ファイルの読み込みまたは出力に失敗した場合。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    # CSV入力とDB入力を同時に指定させない。
    # どちらの入力でも、最終的には同じtimestamp・kw形式で描画する。
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path)
    source.add_argument("--supply-point", help="供給地点特定番号（文字列）")
    parser.add_argument("--db-config", type=Path)
    parser.add_argument("--report-month", help="指定月を含む12か月の最終月")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "examples" / "customer.json",
    )
    parser.add_argument("--output", type=Path, default=Path("output/report.pdf"))
    parser.add_argument(
        "--font", type=Path, help="通常書体のTTF/OTF/TTC。省略時はメイリオ"
    )
    parser.add_argument(
        "--font-bold", type=Path, help="太字書体（メイリオならmeiryob.ttc）"
    )
    parser.add_argument("--browser", type=Path, help="任意のChromium実行ファイル")
    parser.add_argument(
        "--debug-dir", type=Path, help="指定時だけPNGとHTMLを保存するフォルダー"
    )
    args = parser.parse_args()
    # 帳票の名義・住所などを読み込む。DB入力時の契約電力は後でDB値に置き換える。
    config = json.loads(args.config.read_text(encoding="utf-8"))
    # DB接続用サービスはDB入力の場合だけ作る。CSV利用者にはDB接続設定は不要。
    db_source = None
    if args.supply_point:
        if not args.db_config:
            parser.error("テーブル入力には--db-configが必要です")
        from services.database_source import DatabaseSource

        db_source = DatabaseSource(
            json.loads(args.db_config.read_text(encoding="utf-8"))
        )
    try:
        # withでフォント・ブラウザーの準備と終了処理をまとめる。
        with ReportService(args.font, args.browser, args.font_bold) as service:
            if db_source is not None:
                service.generate_database(
                    db_source,
                    args.supply_point,
                    args.report_month or config["target_month"],
                    config,
                    args.output.resolve(),
                    args.debug_dir,
                )
            else:
                service.generate(
                    args.csv, config, args.output.resolve(), args.debug_dir
                )
    finally:
        if db_source is not None:
            db_source.close()
    print(f"PDF: {args.output.resolve()}")


if __name__ == "__main__":
    main()
