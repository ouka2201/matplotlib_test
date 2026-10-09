# 電力使用状況見える化レポート

Python 3.12で、2ページのPDFを作成します。既存バッチで取得した対象リストを`run_reports()`へ渡すのが主な使い方です。

## 準備

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

`assets/ICON.png`には見本から取り出した90×89ピクセルの青い電球画像を同梱しています。書体はメイリオです。Windowsでは自動検出し、別環境では通常・太字のパスを指定します。フォント本体は同梱していません。PostgreSQLのドライバーは`psycopg2-binary==2.9.10`です。

## 既存バッチから呼ぶ

```python
from services.batch_service import run_reports

results = run_reports(
    targets=targets,
    report_month=report_ym,
    get_session=get_session,
    load_sql_file=load_sql_file,
    output_dir="output/reports",
)
```

`targets`は指定年月・状態2/5で取得した、供給地点・企業ID・省サポ加入フラグのリストです。`get_session`と`load_sql_file`は既存の関数を使います。対象年月はYYYY-MM、YYYYMM、日付を受け付けます。並列数は既定でCPU数、変更時は`workers=4`等を指定します。

1つのプロセスプールで、各ワーカーが「SQL取得→データ変換→PDF保存」を1件ずつ行います。ReportServiceはワーカー内で再利用し、全件の実績や画像を親プロセスへ集めません。1件の失敗は結果へ記録し、他の対象を継続します。

get_session/load_sql_fileは**モジュール直下の関数**にし、DBセッションは呼ばれた子プロセス内で作成します。Windowsの実行入口は`if __name__ == "__main__":`で囲みます。管理状態の更新は既存バッチ側で行い、必要なら`on_result`へ結果を受け取る関数を指定します。

SQL列名と画像のJobクラスへの接続は[組み込み手順](docs/existing_sql_integration.md)を参照してください。

## 単体でPDFを作る

取得済みの契約情報1行と日別48枠を渡します。終了処理はwithが行います。

```python
from pathlib import Path
from services.report_service import ReportService

with ReportService() as service:
    result = service.generate_query_results(
        customer_row=report_cust,
        daily_rows=daily_rows,
        supply_point=supply_point,
        report_month="2026-06",
        output=Path("output/report.pdf"),
    )
```

CSVでレイアウトを確認する場合：

```bash
python main.py --csv examples/sample.csv --output output/report.pdf
```

管理テーブルの取得・状態更新をこのプログラムに任せる場合：

```bash
python batch.py --from-management --report-month 2026-06 --db-config examples/database.json --output-dir output/reports
```

CLIのDB接続・状態更新は[管理バッチ](docs/managed_batch.md)を参照してください。こちらも同じ共通プロセスプールを使用します。

## 編集する場所

| ファイル・フォルダー | 役割 |
| --- | --- |
| `services/batch_service.py` | 並列処理、1件のSQL取得、PDF名 |
| `services/report_service.py` | 1件のPDF生成、ブラウザーの開始・終了 |
| `services/query_result_service.py` | SQL取得結果の列対応とkWh→kW変換 |
| `services/data_service.py` | 実績の検証・集計 |
| `rendering/sections/no0_*.py`〜`no7_*.py` | 各No.の文字・表・グラフ |
| `rendering/pages/` | 1・2ページ目の配置 |
| `examples/insert_test_data.py` | 4テーブルへのテストデータ登録 |

全No.をページへ直接描画し、PNGはBytesIO、HTMLは文字列で扱います。通常は最終PDFだけを保存します。30分値はkWhを2倍して平均電力kWへ変換します。実績が1年未満でも扱い、実績期間内の欠測・重複・不正値はエラーにします。

[No.0〜No.7の仕様](docs/report_specs.md)・[入力データ](docs/data_inputs.md)・[テストデータ登録](docs/test_data.md)・[書体](docs/fonts.md)に詳細をまとめています。

## 確認

```bash
python -m unittest discover -s tests -v
```

テストは実績変換・レイアウト・管理状態・4テーブルへの登録・並列処理を確認します。描画テストにもICON.pngが必要です。実DBの接続と1000件のPDF生成時間・最大メモリは実環境で確認してください。
