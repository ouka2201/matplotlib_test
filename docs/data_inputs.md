# CSV・DB入力と単位
保存値の単位は**kWh**です。`T_EP_ELECTRICITY_DATA_30MIN`の1行を1日分として読み、`T01_30T_SYR01`〜`T01_30T_SYR48`を1枠1行へ展開します。timestampは取得日`T01_GET_YMD`に枠番号から求めた開始時刻を足します。1は00:00、2は00:30、48は23:30です。30分使用電力量を0.5時間で割るため、描画用の`kw = 保存kWh × 2`になります。月別kWhは`sum(kw × 0.5)`なので元の保存値の合計と一致します。

### 対象期間と契約電力
指定したレポート作成年月を**含む12か月**を取得します。例：2026-06なら2025-07-01 00:00以上、2026-07-01 00:00未満。日付列はVARCHARのYYYYMMDDのため、SQLでは20250701以上・20260701未満で絞ります。供給地点`T01_KYO_CTN_TOK_NO`もWHERE条件に指定します。供給地点特定番号は22文字の文字列として先頭の0を保持し、お客さま番号とは別に扱います。
この12か月は取得可能な最大範囲です。1年未満の場合は、範囲内で取得できた最初の日〜最後の日を実績期間にします。前後の実績がない日や月は0で補完しません。CSV・DBとも各実績日には48枠を要求し、実績期間途中の欠落日・枠はエラーにします。実績が全くない場合も明確なエラーにします。期間の前後に実績がない理由（契約開始・終了など）の照合は、現時点では入力に契約期間がないため行いません。
契約電力は`T_EP_CONTRACTED_POWER`の`QSQB_DCIS2_SPL_PT_SPC_NO`で検索し、`QSQB_DCIS2_HVPW_CTRT`をkWとして使います。configの契約電力はこのDB値で上書きします。画像の契約電力テーブルには期間別の履歴が示されていないため、参照時点の1行を使用します。単体CLI・従来のジョブJSONでは名義・住所・お客さま番号を顧客設定から取得します。`--from-management`では`T_ARVE_CUSTOMER_INFO`から取得します。

### 接続設定
実テーブルはPostgreSQLです。`examples/database.json`をコピーし、実環境のスキーマ・テーブル名を指定してください。引用符なしで作った識別子はPostgreSQL側で小文字になります。`"DB_CORP"`のように二重引用符付きで作った場合は、設定のスキーマ名も`DB_CORP`に合わせます。テーブル名も同様です。列名は実定義を読み取った後に大小文字を区別せず解決します。`requirements.txt`に`psycopg2-binary==2.9.10`を含めています。接続URLは設定ファイルでなく`REPORT_DATABASE_URL`環境変数へ設定し、`postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME`の形式を使用します。
`quality_columns`には欠測・不正値件数列を指定しています。0以外の日がある場合は生成を中断し、欠損を0と見なしません。実テーブルに列がない場合は設定を空配列にして、枠値の欠損・不正値検査だけを利用できます。

### 単体生成
架空データを30分値取込管理・ARVE・EP契約電力・EP30分値の4テーブルへ登録する場合は、[テストデータの登録手順](test_data.md)を参照してください。供給地点を全テーブルで一致させ、取込管理は完了状態で準備します。対象件数・実績月数または日数・最大電力を指定でき、SQLiteの最小検証テーブルも用意できます。レポート管理への登録は後続の取込確認処理で行います。

```bash
python main.py --supply-point 0000000000000000000001 --report-month 2026-06 --db-config db_config.json --config customer.json --font /path/to/font.ttf --output output/customer_0001.pdf
```
### 1000件の並列生成
管理テーブルから作成対象を取得する場合は、1000件のジョブJSONを用意する必要はありません。
```bash
python batch.py --from-management --db-config db_config.json --output-dir output/reports
```
`T_POWER_REPORT_MNG_INFO`の作成依頼・エラーを取得し、供給地点と`TARGET_YEAR_MONTH`の年月ごとに1件ずつ処理します。名義・住所・お客さま番号はARVEテーブルで照合します。詳細は[管理テーブルからの並列処理](managed_batch.md)を参照してください。

従来のJSON方式も利用できます。
`examples/jobs.db.json`と同じ形式で1000件の顧客を記載します。各ワーカーでDB Engineを作り、親や他のワーカーとは接続を共有しません。DB接続は日別データと契約電力の取得中だけ使用し、画像描画の前に返します。
```bash
python batch.py --jobs jobs.db.json --db-config db_config.json --report-month 2026-06 --output-dir output/reports --font /path/to/font.ttf
```
`--report-month`は全DBジョブの対象月を統一します。省略時はジョブの`report_month`、さらに省略時は顧客設定の`target_month`を使います。SQLの供給地点・日付条件はバインド変数で渡します。既存のCSV入力も利用できます。

単体テストで日時対応、kWhからkWへの変換、月別電力量の一致、うるう年、欠損・重複・不正値とDB条件を確認しています。SQLiteのテーブルから2ワーカーでPDFを生成し、同じデータのCSV版と両ページの表示が一致することを確認しました。実テーブルはPostgreSQLですが、接続先・認証情報は未提供のため、実PostgreSQLへの接続確認は未実施です。
