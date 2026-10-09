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
| `batch.py` | 管理テーブル・JSONの対象を1件ずつCPUコア数に応じて並列処理 |
| `services/report_job_source.py` | 管理テーブルの作成対象取得・状態更新・ARVE契約情報取得 |
| `services/database_source.py` | テーブルの取得・日別48列の展開・kWh→kW換算 |
| `services/data_service.py` | 入力検証・対象期間・No.別の集計 |
| `services/report_service.py` | 取得・集計・描画・PDF保存の流れ |
| `services/chart_service.py` | 完成した2ページだけをBytesIOでPNG化 |
| `rendering/pages/` | 1・2ページ目の合成と描画順 |
| `rendering/canvas.py` | mm座標、見出し、注釈、グラフ軸、表の共通描画 |
| `rendering/icons.py` | 青い助言枠の左上に`assets/ICON.png`を配置 |
| `rendering/styles.py` | 用紙内枠の寸法、配色、数値書式、共通注記 |
| `services/font_service.py` | 通常・太字の準備・登録・終了処理を一か所で管理 |
| `services/pdf_service.py` | Jinja2のHTML生成・PlaywrightのPDF化・保存 |
| `templates/report.html` | A4横、黒い外枠、1ページ目中央の破線 |
| `assets/` | TEPCOロゴ、青い電球の`ICON.png`、画像の説明 |
| `examples/` | サンプルCSV・顧客設定・DB設定・ジョブ一覧 |
| `examples/insert_test_data.py` | 取込管理・ARVE・契約電力・日別48枠へ同じ供給地点の架空データをINSERT |
| `tests/` | 単位・集計・各No.の描画・フォントの検証 |

全No.のページ配置は左上原点・mm単位です。グラフ軸の中では日時・電力などのデータ座標を使います。ページ全体の合成は`rendering/pages/first_page.py`と`second_page.py`、黒枠・破線はHTMLで調整します。No.4・No.5を同じ条件分岐で描く旧処理は分割し、各No.の座標をそのファイルで確認できる形にしています。

## 実行
Python 3.10以降を使用します。以下はプロジェクトのルートで実行してください。
実行前に、青い電球の画像を**幅90×高さ89ピクセルの`assets/ICON.png`**として配置してください。ファイル名の大文字・小文字も一致させます。画像本体は同梱していません。No.4〜No.7の全ての青い助言枠でこの画像を使用し、幅3.3mm・元の縦横比で左上に配置します。透過PNGに対応します。画像がない場合やサイズが異なる場合は、配置場所・必要サイズを示すエラーになります。
画像はワーカープロセスごとに一度だけ読み込み、以降はメモリ内の画像を再利用します。画像を差し替えた場合はワーカープロセスを起動し直してください。
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
実テーブルはPostgreSQLです。`requirements.txt`にPsycopg2のドライバーを含めています。`examples/database.json`を実環境に合わせてコピーし、接続URLを`REPORT_DATABASE_URL`環境変数に設定します。ドライバーを明示するため、URLは`postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME`の形式です。スキーマ・テーブル名は実際の定義に合わせます。設定とテストデータ登録の例は[登録手順](docs/test_data.md)を参照してください。
```bash
python main.py --supply-point 0000000000000000000001 --report-month 2026-06 --db-config examples/database.json --config examples/customer.json --output output/report.pdf
```

### 並列実行
既存バッチのSQLで契約情報・日別48枠を取得済みの場合は、`ReportService.generate_query_results()`へ直接渡せます。[既存SQLからの組み込み手順](docs/existing_sql_integration.md)に、画像のJobクラスとThreadPoolへ接続する例を記載しています。`examples/existing_sql_batch.py`は既存の`get_session()`と`load_sql_file()`を使用し、PDF生成だけをプロセスへ渡します。

管理テーブルから対象を取得する場合は、次を実行します。`--report-month`で対象年月を指定し、その月のリストを1件ずつ並列処理します。`--workers`を省略すると利用可能なCPUコア数を使います。
```bash
python batch.py --from-management --report-month 2026-06 --db-config examples/database.json --output-dir output/reports
```
既定の取得対象は指定年月の`CREATE_STATUS IN ('2', '5')`です。PostgreSQLでは主キーごとのセッションロックにより同じ対象の同時作成を防ぎます。0件ならワーカーを起動せず正常終了します。着手時に「2:作成中」、PDF保存後に「3:完了」、失敗時に「5:エラー」へ更新します。No.0の名義・住所・お客さま番号はARVE、契約電力はEPテーブルから取得します。PDF名は未加入なら`企業ID_供給地点特定番号_YYYYMM.pdf`、加入なら`企業ID_供給地点特定番号_syousapo_YYYYMM.pdf`です。[管理テーブルからの並列処理](docs/managed_batch.md)に設定・状態・再実行手順を記載しています。

従来のジョブJSONを使用する場合：
```bash
python batch.py --jobs examples/jobs.csv.json --output-dir output/reports
python batch.py --jobs examples/jobs.db.json --db-config examples/database.json --report-month 2026-06 --output-dir output/reports
```
既定は利用可能CPU数のプロセス並列です。必要なら`--workers 4`などで指定します。1000件の一覧では顧客IDを全件一意にしてください。CSV・顧客設定の相対パスはジョブJSONの配置場所基準です。各ワーカーはブラウザー・フォント・DBサービスを再利用します。

### テーブルへテストデータを登録する
検証DBの接続・列設定と`seed_record_type_ids`の実際のIDを用意した後、次の例で1000地点・3か月分を登録できます。投入先は30分値取込管理・ARVE・EP契約電力・EP30分値の4テーブルです。全て同じ22桁の供給地点特定番号を使い、取込管理は`3:完了`で登録します。レポート管理の作成は後続の取込確認処理へ渡します。

```bash
python examples/insert_test_data.py --db-config examples/database.json --report-month 2026-06 --count 1000 --months 3
```

最大電力は`--max-kw`、契約電力は`--contract-kw`で指定できます。既存行は既定でエラーにし、`--on-existing skip`なら保持して不足分だけ追加します。`--dry-run`では登録予定件数を確認できます。手元で試すSQLite用設定・テーブル作成も用意しています。[テストデータの登録手順](docs/test_data.md)を参照してください。

### 確認用出力とサンプル生成
1年未満の動作確認用に`examples/sample_short.csv`（2026年4月〜6月）を同梱しています。`python main.py --csv examples/sample_short.csv --output output/short_report.pdf`で生成できます。
通常は完成PDFのみを保存します。必要なときだけ`--debug-dir output/debug`で完成ページPNG・HTMLを保存します。新しいサンプルを生成する場合：
```bash
python examples/generate_sample.py
```

## 詳細仕様と確認
[No.0〜No.7の仕様](docs/report_specs.md)、[CSV・DBと単位](docs/data_inputs.md)、[管理テーブルからの並列処理](docs/managed_batch.md)、[メモリと並列処理](docs/parallel_processing.md)、[メイリオ](docs/fonts.md)に用途ごとの説明をまとめています。
```bash
python -m unittest discover -s tests -v
```
113件のテストを使用しています。描画テストでも`assets/ICON.png`を使用します。管理状態・ARVE取得・2プロセスの重複着手防止・1000件の投入に加え、4テーブルの供給地点一致・取込完了状態・レポート管理への未投入・既存行の保持・ロールバック・366日分の実績を検証しています。1000件の検証ではPDFを生成せず、登録・キューの動作を確認しています。実DB接続・1000件のPDF所要時間・最大メモリ測定は実行環境で行ってください。

## 今回の整理
No.別の描画を専用モジュールへ分割し、古いページ・部品描画ファイルは削除しました。未使用のグラフ書式・色定義・HTMLファイル経由の互換関数も削除しています。重複していた顧客サンプル設定は`examples/customer.json`に集約しました。古い確認用PNG・HTML・PDFとPythonキャッシュは配布ソースから除き、必要なロゴ・テスト・実行例を保持しています。
