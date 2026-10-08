# 電力使用状況レポート
A4横・2ページの帳票を、matplotlib → メモリ上のPNG → Jinja2 → Playwrightの順に作成します。書体はメイリオの通常書体・太字です。

## No.0〜No.7を変更する場所
仕様書のNo.とファイルを1対1で対応させています。見出し・文字・グラフ・表・説明欄の位置や内容を変更するときは、次のファイルの`draw_noN()`を編集してください。

| 仕様書No. | 内容 | 編集するファイル |
| --- | --- | --- |
| No.0 | タイトル・契約情報 | [no0_contract.py](rendering/sections/no0_contract.py) |
| No.1 | ①日ごとの最大電力・カレンダー・TOP3 | [no1_daily_maximum.py](rendering/sections/no1_daily_maximum.py) |
| No.2 | ②30分ごとの需要電力 | [no2_daily_demand.py](rendering/sections/no2_daily_demand.py) |
| No.3 | TEPCOロゴ・注記 | [no3_footer.py](rendering/sections/no3_footer.py) |
| No.4 | ③月ごとの使用電力量 | [no4_monthly_energy.py](rendering/sections/no4_monthly_energy.py) |
| No.5 | ④月ごとの最大電力 | [no5_monthly_power.py](rendering/sections/no5_monthly_power.py) |
| No.6 | ⑤デュレーションカーブ・TOP50 | [no6_duration.py](rendering/sections/no6_duration.py) |
| No.7 | ⑥ロードカーブ・日別表 | [no7_load_curve.py](rendering/sections/no7_load_curve.py) |

全No.が共通のページFigureへ直接描画します。`draw_noN(page, ...)`の`page`が描画先です。完成した各ページだけをBytesIOでPNG化するため、部品PNGや固定画像フォルダーは不要です。各ファイルの先頭に目的、関数に日本語のGoogleスタイルのDocstringを記載しています。

## 全体の役割
| 場所 | 役割 |
| --- | --- |
| `main.py` | 1顧客分の実行入口 |
| `batch.py` | 複数顧客のCPUコア数に応じたプロセス並列処理 |
| `services/database_source.py` | テーブルの取得・日別48列の展開・kWh→kW換算 |
| `services/data_service.py` | 入力検証・対象期間・No.別の集計 |
| `services/report_service.py` | 取得・集計・描画・PDF保存の流れ |
| `services/chart_service.py` | 完成した2ページだけをBytesIOでPNG化 |
| `rendering/pages/` | 1・2ページ目の合成と描画順 |
| `rendering/canvas.py` | mm座標、見出し、注釈、グラフ軸、表の共通描画 |
| `rendering/icons.py` | 青い助言枠の電球アイコン（図形で描画） |
| `rendering/styles.py` | 用紙内枠の寸法、配色、数値書式、共通注記 |
| `services/font_service.py` | 通常・太字の準備・登録・終了処理を一か所で管理 |
| `services/pdf_service.py` | Jinja2のHTML生成・PlaywrightのPDF化・保存 |
| `templates/report.html` | A4横、黒い外枠、1ページ目中央の破線 |
| `assets/` | 帳票で使用するTEPCOロゴと出典 |
| `examples/` | サンプルCSV・顧客設定・DB設定・ジョブ一覧 |
| `tests/` | 単位・集計・各No.の描画・フォントの検証 |

全No.のページ配置は左上原点・mm単位です。グラフ軸の中では日時・電力などのデータ座標を使います。ページ全体の合成は`rendering/pages/first_page.py`と`second_page.py`、黒枠・破線はHTMLで調整します。No.4・No.5を同じ条件分岐で描く旧処理は分割し、各No.の座標をそのファイルで確認できる形にしています。

## 実行
Python 3.10以降を使用します。以下はプロジェクトのルートで実行してください。
```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python main.py --csv examples/sample.csv --output output/report.pdf
```
顧客設定の既定値は`examples/customer.json`です。実データでは`--config customer.json`を指定します。CSVの`kw`は30分平均電力(kW)、DBの48枠は使用電力量(kWh)で、取得時に2倍してkWへ換算します。取得対象は指定月を含む直近12か月ですが、その中の実績が1年未満でも作成できます。実績の最初の日〜最後の日について、毎日48枠の連続データが必要です。実績期間の前後は補完せず、途中の欠測・重複・不正値はエラーにします。対象月に実績がなくても、月別・期間全体のグラフを生成し、No.1・No.2は実績なしと表示します。
Windowsではメイリオを自動検出します。別環境で通常・太字のフォントを明示する場合：
```bash
python main.py --csv examples/sample.csv --font /path/to/meiryo.ttc --font-bold /path/to/meiryob.ttc --output output/report.pdf
```
同じフォルダーに`meiryo.ttc`と`meiryob.ttc`があれば太字指定を省略できます。他のTTF/OTFでは通常・太字を両方指定します。フォント本体は同梱していません。

### テーブル入力
`examples/database.json`を実環境に合わせてコピーし、SQLAlchemyの接続URLを`REPORT_DATABASE_URL`環境変数に設定します。ご使用のDB用ドライバーもインストールしてください。
```bash
python main.py --supply-point 0000000000000000000001 --report-month 2026-06 --db-config examples/database.json --config examples/customer.json --output output/report.pdf
```

### 並列実行
```bash
python batch.py --jobs examples/jobs.csv.json --output-dir output/reports
python batch.py --jobs examples/jobs.db.json --db-config examples/database.json --report-month 2026-06 --output-dir output/reports
```
既定は利用可能CPU数のプロセス並列です。必要なら`--workers 4`などで指定します。1000件の一覧では顧客IDを全件一意にしてください。CSV・顧客設定の相対パスはジョブJSONの配置場所基準です。各ワーカーはブラウザー・フォント・DBサービスを再利用します。

### 確認用出力とサンプル生成
1年未満の動作確認用に`examples/sample_short.csv`（2026年4月〜6月）を同梱しています。`python main.py --csv examples/sample_short.csv --output output/short_report.pdf`で生成できます。
通常は完成PDFのみを保存します。必要なときだけ`--debug-dir output/debug`で完成ページPNG・HTMLを保存します。新しいサンプルを生成する場合：
```bash
python examples/generate_sample.py
```

## 詳細仕様と確認
[No.0〜No.7の仕様](docs/report_specs.md)、[CSV・DBと単位](docs/data_inputs.md)、[メモリと並列処理](docs/parallel_processing.md)、[メイリオ](docs/fonts.md)に用途ごとの説明をまとめています。
```bash
python -m unittest discover -s tests -v
```
58件のテストを使用しています。実DBの接続確認と1000件の所要時間・最大メモリ測定は、実行環境で行ってください。

## 今回の整理
No.別の描画を専用モジュールへ分割し、古いページ・部品描画ファイルは削除しました。未使用のグラフ書式・色定義・HTMLファイル経由の互換関数も削除しています。重複していた顧客サンプル設定は`examples/customer.json`に集約しました。古い確認用PNG・HTML・PDFとPythonキャッシュは配布ソースから除き、必要なロゴ・テスト・実行例を保持しています。
