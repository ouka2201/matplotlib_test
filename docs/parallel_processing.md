# メモリ上の画像と1000件の並列処理
固定の画像フォルダーは使用しません。No.0〜No.7はページFigureへ直接描画し、`ChartService.save()` が完成した2ページだけを `io.BytesIO` にPNG化します。HTMLは文字列、PDFはbytesとして扱います。完成PDFの保存時だけ、出力先と同じフォルダーに固有名の一時ファイルを作り、成功後に置き換えます。デバッグ用画像・HTMLは単体CLIで `--debug-dir` を明示した場合だけ保存します。各No.の中間Figure・PNGは作成しません。
共通の入力画像として、青い助言枠用の`assets/ICON.png`（幅90×高さ89ピクセル）を配置します。`rendering/icons.py`でワーカープロセスごとに一度だけ読み込み、メモリ上で再利用します。このPNGは読み取り専用の入力であり、顧客ごとに画像を出力する場所ではありません。画像を差し替えた場合はワーカープロセスを起動し直してください。

### 単体実行
```bash
python main.py --csv examples/sample.csv --config examples/customer.json --font /path/to/font.ttf --output output/report.pdf
# 画像とHTMLも確認したい場合だけ指定
python main.py --csv examples/sample.csv --config examples/customer.json --font /path/to/font.ttf --output output/report.pdf --debug-dir output/debug
```
### 1000件の実行
`examples/jobs.csv.json` と同じ形式で1000件のジョブを列挙します。顧客IDは英数字・ハイフン・アンダースコアを使用し、全件で一意にしてください。csv/configの相対パスはジョブJSONの配置場所基準です。PDFは保存先の `顧客ID.pdf` に出力されます。
```json
[
  {"id": "customer_0001", "csv": "data/0001.csv", "config": "config/0001.json"},
  {"id": "customer_0002", "csv": "data/0002.csv", "config": "config/0002.json"}
]
```
```bash
# 利用可能な論理CPU数で並列処理
python batch.py --jobs jobs.json --output-dir output/reports --font /path/to/font.ttf
# メモリに応じて並列数を調整
python batch.py --jobs jobs.json --output-dir output/reports --font /path/to/font.ttf --workers 4
```
`ProcessPoolExecutor`を`spawn`で使い、MatplotlibとChromiumをワーカープロセスごとに分離します。各ワーカーはフォント・テンプレート・Chromiumを再利用し、顧客ごとに新しいブラウザーコンテキストを作成して最後に閉じます。親プロセスは同時投入をワーカー数の2倍までに制限します。1000件分のDataFrame・画像・PDFを親で保持せず、ワーカーにはパスだけを渡し、成功／失敗と保存先のみを返します。1件のデータ不正でも他の顧客の処理は続き、結果は `results.json` に保存されます。ワーカーの異常終了や初期化失敗は処理全体のエラーとして通知します。

既定の並列数は利用可能な論理CPU数です。Python 3.13以降は`os.process_cpu_count()`、旧版ではCPU affinityまたは`os.cpu_count()`を使います。コンテナーのCPU quotaがこれらに反映されない環境では`--workers`を明示してください。WindowsのExecutor上限は61です。Chromiumもメモリを使用するので、実測した1ワーカー当たりの使用量と空きメモリから適切な並列数を決めてください。数値計算ライブラリのスレッド数は、外部設定がなければ1に抑えます。

### 他の方法との比較
- `BytesIO`＋data URI：今回の既定方式。画像ファイルの競合を避け、フォルダー管理も不要です。base64化には元のPNGに対して約4/3のサイズが必要です。
- `TemporaryDirectory`：メモリが不足する場合や、ファイルパス必須の外部処理を組み込む場合に向きます。顧客／ジョブごとに作れば同名画像でも競合しませんが、ディスクI/Oが発生します。
- `SpooledTemporaryFile`：一定サイズまではメモリ、超過後は一時ファイルへ移します。画像データ自体を退避する用途に使えますが、HTMLのbase64化とChromiumのメモリ消費までなくなるわけではありません。


## 管理テーブルを入口にする場合
`batch.py --from-management`で管理テーブルの作成依頼・エラーを取得し、各レコードを1件ずつ既存のプロセス並列処理に渡します。親プロセスの取得用DB接続はワーカー起動前に閉じ、各ワーカーで独立したDBサービスを作ります。0件ならワーカーは起動しません。詳細は[管理テーブルからの並列処理](managed_batch.md)を参照してください。
