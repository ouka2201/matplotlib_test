# テーブルへテストデータを登録する

`examples/insert_test_data.py`で、30分値取込管理・ARVEお客さま情報・EP契約電力・EP30分値の4テーブルへ架空データをINSERTします。4テーブルには同じ22桁の供給地点特定番号を設定します。GoogleスタイルのDocstringと日本語コメントを付けています。

## データ準備と後続処理

1. このスクリプトで4テーブルを準備する。30分値取込管理は`CREATE_STATUS=3`（完了）。
2. 取込確認処理が、対象年月の取込完了とレポート管理の未登録を確認し、ARVEと供給地点で照合してレポート管理を作成する。
3. レポート管理を使ってPDFを作成する。

このスクリプトの対象は手順1です。`T_POWER_REPORT_MNG_INFO`の作成・INSERT・UPDATEは行いません。既存のレポート管理レコードも保持します。`--init-sqlite`で作るのも投入対象の4テーブルだけです。

画像の取込確認仕様では、レポート管理の企業IDをARVEから取得し、加入フラグをARVEのレコードタイプIDで判定します。そのため、準備するARVE行にも企業IDとレコードタイプIDを設定します。

取込確認のINSERT-SELECT処理はこのスクリプトに含めていません。画像ではその処理がレポート管理の状態を`2`（作成中）で登録します。一方、既存の`batch.py --from-management`は`1`（作成依頼）・`5`（エラー）を取得し、着手時に`2`へ更新する方式です。取込確認処理との接続には、この状態遷移を合わせる必要があります。テストデータの準備直後に`--from-management`でPDFが生成できる、という手順にはしていません。

## 投入先と供給地点の対応

`N`を供給地点数、`D`を実績日数とすると、新規登録時の件数は次のとおりです。テーブル名はDB設定で変更できます。

| 設定名 | テーブル | 供給地点特定番号の列 | 件数 |
| --- | --- | --- | --- |
| `import_management_table` | `T_30MIN_IMPORT_MNG` | `SUPPLY_POINT_NUMBER` | N |
| `customer_table` | `T_ARVE_CUSTOMER_INFO` | `CMN_SupplyPointSpecificNum__c` | N |
| `contract_table` | `T_EP_CONTRACTED_POWER` | `QSQB_DCIS2_SPL_PT_SPC_NO` | N |
| `daily_table` | `T_EP_ELECTRICITY_DATA_30MIN` | `T01_KYO_CTN_TOK_NO` | N × D |

物理名の列は異なりますが、登録する番号は全て同じです。既定では`999900`＋16桁の連番で22桁にします。先頭の0を保持する例として、`--point-prefix 000090`も指定できます。

30分値取込管理は、指定した対象年月YYYYMMごとに1行/供給地点を登録します。主キーは供給地点＋対象年月です。画像の定義に合わせ、供給地点VARCHAR(22)、状態VARCHAR(1)、エラーメッセージ・紐付けエラーメッセージ・紐付け日時、作成/更新者と日時を扱います。

新規の取込管理行は`CREATE_STATUS=3`、`ERROR_MESSAGE`・`LINKED_ERROR_MESSAGE`・`LINKED_DATE`はNULLです。実列に存在する監査項目には、作成/更新者として`test_data_seed`、日時として実行時の日本時間を設定します。

## 既存の検証DBへ登録する

実テーブルはPostgreSQLです。プロジェクトのルートで実行します。`examples/database.json`をコピーし、検証用PostgreSQLのスキーマ・テーブル名・ARVE列名を指定してください。既存の4テーブルを読み取り、実列の型に合わせてINSERTします。SQLiteのテーブル作成機能は手元の検証用です。

ドライバーは実バッチと同じPsycopg2を使用し、`requirements.txt`に`psycopg2-binary==2.9.10`を固定しています。Pythonでのモジュール名は`psycopg2`です。

```bash
python -m pip install -r requirements.txt
```

接続URLは設定の`url_env`で指定した環境変数に設定します。通常の設定では`REPORT_DATABASE_URL`です。`USER`・`PASSWORD`・`HOST`・`DBNAME`を実際の値に置き換えてください。

PowerShellの場合：

```powershell
$env:REPORT_DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME"
```

bashの場合：

```bash
export REPORT_DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME"
```

URLの`+psycopg2`でPsycopg2のドライバーを明示します。ユーザー名・パスワード内の`@`・`/`等はURLエンコードして指定します。接続URLをJSONへ保存する必要はありません。

`DatabaseSource`もPostgreSQLの接続URLを`postgresql+psycopg2`へ統一します。`postgresql://`形式や旧版のドライバー表記が残っていても、認証情報・ホスト・ポート・DB名・SSL等の接続オプションを保持してPsycopg2を使用します。単体レポート・管理バッチ・テストデータ登録で共通の接続処理を使います。

### スキーマ・テーブル名

PostgreSQLでは、引用符なしで作った`DB_CORP.T_30MIN_IMPORT_MNG`は、小文字の`db_corp.t_30min_import_mng`として扱われます。この場合は同梱設定の小文字名を使用します。二重引用符付きで`"DB_CORP"."T_30MIN_IMPORT_MNG"`を作った場合は、設定もその大文字名へ変更します。JSONの値に引用符そのものを含める必要はありません。

PostgreSQLへの投入時に`--init-sqlite`は指定しません。スキーマ・テーブルのCREATE、既存行のUPDATE・DELETEは行わず、4テーブルへのINSERTを1トランザクションで行います。接続ユーザーには対象スキーマのUSAGEと対象テーブルのSELECT・INSERTが必要です。追加列にシーケンスの既定値を使用している場合は、そのシーケンスの利用権限も必要です。

`import_management_table`は取込管理、`management_table`は後続のレポート管理です。両方に同じテーブル名を指定した場合は登録を中止します。追加必須列の`seed_defaults`でも、取込管理の種別名には`import_management`を使用してください。旧版の`management`指定はエラーにします。

### ARVEの企業ID・レコードタイプID

ARVEの列名は次の設定で指定できます。既定の物理名は以前のARVE定義画像に合わせています。

```json
{
  "customer_columns": {
    "company_id": "CMN_KigyoID_Fk__c",
    "record_type_id": "RecordTypeId"
  },
  "seed_record_type_ids": {
    "joined": "実際の加入用ID",
    "not_joined": "実際の未加入用ID"
  }
}
```

これはDB設定に追加する項目の例です。元の名義・住所・お客さま番号の設定も保持してください。画像には省エネサポートサービスの実際のレコードタイプIDが示されていないため、環境で使用する値へ置き換えます。実列の長さは20文字です。ここに書いた日本語は説明用のプレースホルダーです。

`--syousapo alternate`（既定）は奇数番号に`not_joined`、偶数番号に`joined`のIDを設定します。全件加入なら`--syousapo joined`、全件未加入なら`--syousapo not-joined`です。選んだモードで使用するIDを必ず設定します。交互モードの2つのIDが同じ場合はエラーにします。

`customer_filters`でレコードタイプIDを固定している場合は、生成モードもそのIDに合わせてください。例えば加入用IDで固定している設定では`--syousapo joined`を指定します。矛盾する指定は登録前にエラーにします。

企業IDは`TEST0000000001`から始まる14文字をARVEへ登録します。お客さま番号は別項目で、`0000000000000001`から始まる16桁です。名義・住所も架空の値を用意します。

### 登録・予定件数確認

1000地点、2026年6月を最終月とする3か月分の例：

```bash
python examples/insert_test_data.py --db-config examples/database.json --report-month 2026-06 --count 1000 --months 3 --max-kw 1200 --contract-kw 1600
```

2026年4月1日〜6月30日の実績を登録します。`--months 12`なら1年分、`--days 1`なら6月30日だけの48枠を登録でき、1年未満のレポートも検証できます。`--months`と`--days`は同時に指定できません。

登録せずに列定義・値・既存キーと登録予定件数を確認する場合：

```bash
python examples/insert_test_data.py --db-config examples/database.json --report-month 2026-06 --count 1000 --months 3 --dry-run
```

結果はJSONで表示します。`dry_run: true`の場合、各テーブルの`inserted`は登録予定件数です。DB側の外部キー・トリガー等によるINSERT時の検査は、実際の登録時に行われます。

## SQLiteで手元の動作確認をする

`examples/database.test.json`にはSQLite用の設定と、検証用のレコードタイプIDを用意しています。`TEST_SYOUSAPO`・`TEST_OTHER`は実際のサービスのIDではありません。取込確認処理の試験では、判定に使う加入IDもこの検証用IDに合わせます。

`--init-sqlite`を指定すると、投入対象の最小4テーブルを作成します。既存テーブルを変更・削除する処理はありません。本番の全列・全制約を再現するDDLではありません。旧版で作ったSQLiteにはARVEの新しい列がないため、次の例では新しいDBファイル名を使用しています。

PowerShellの場合：

```powershell
$env:REPORT_TEST_DATABASE_URL = "sqlite:///test_report_import.sqlite"
python examples/insert_test_data.py --db-config examples/database.test.json --report-month 2026-06 --count 10 --months 3 --init-sqlite
```

bashの場合：

```bash
export REPORT_TEST_DATABASE_URL="sqlite:///test_report_import.sqlite"
python examples/insert_test_data.py --db-config examples/database.test.json --report-month 2026-06 --count 10 --months 3 --init-sqlite
```

この例では取込管理・ARVE・契約電力に各10行、日別実績に910行が入ります。レポート管理テーブルは作成しません。SQLite用の名義列`CMN_DemandLocationFullName_Test__c`は検証用の仮名です。実DBでは`customer_columns.customer_name`を実際の列名に変更してください。

データのINSERTだけなら、フォント・Playwrightのブラウザー・`ICON.png`の描画準備は不要です。`--dry-run`と`--init-sqlite`は同時指定できません。最初にテーブルを用意し、以降の確認では`--init-sqlite`を省略してください。

## 30分値の生成

日別48枠は1=00:00、2=00:30、…、48=23:30です。保存単位は設定に従い、既定のkWhでは生成した30分平均電力kWに0.5を掛けて登録します。

実績には時間帯・月・曜日による変動と乱数を加え、期間中央の日の17:00を`--max-kw`で指定した最大値にします。`--seed`、地点番号、期間が同じなら同じ実績を生成します。うるう年の日数にも対応し、各実績日には48枠を揃えます。品質件数列は0です。

## 再実行と追加登録

既定の`--on-existing error`では既存キーがあればエラーにし、その実行で行ったINSERT全体をロールバックします。既存行を保持して、足りない行だけ追加する場合：

```bash
python examples/insert_test_data.py --db-config examples/database.test.json --report-month 2026-06 --count 10 --months 3 --on-existing skip
```

既存行の実績・契約値・取込状態・紐付け情報・ARVE項目は更新しません。引数の最大電力・契約電力・加入モードを変えても、既存行の値は変わりません。

別の供給地点を追加するには、重ならない`--start-id`または`--point-prefix`を使用します：

```bash
python examples/insert_test_data.py --db-config examples/database.test.json --report-month 2026-06 --count 10 --days 1 --start-id 1001
```

同じ供給地点に別の対象月を追加する場合は`--on-existing skip`を指定します。ARVE・契約電力の既存行を保持し、日別実績の不足分と新しい取込管理キーを登録します。レポートには実績期間途中の欠落日を許容しないため、既存実績と連続する期間を指定してください。

重複の判定キーは、取込管理が供給地点＋対象年月、ARVEが供給地点＋顧客の絞り込み条件、契約電力が供給地点、実績が供給地点＋日付です。投入処理にUPDATE・DELETE・TRUNCATEを含めていません。

## 実テーブルに追加の必須列がある場合

実テーブルを読み取り、列の大小文字・型・文字数・必須列を検証します。自動採番やDBの既定値がなく、生成処理にも含まれない必須列は、設定の`seed_defaults`へ指定してください。外部キーがある列には、検証DBに存在する参照先の値を指定します。

例えば、ARVEに必須の`ORG_ID`がある場合：

```json
{
  "seed_defaults": {
    "customer": {"ORG_ID": "EXISTING_TEST_ORG_ID"},
    "import_management": {"CREATED_BY": "test_data_seed"}
  }
}
```

これはDB設定へ追加する項目の例です。実際の列名・登録可能な値に置き換えてください。種別は`import_management`・`customer`・`contract`・`daily`、内側のキーは物理列名です。供給地点・対象年月・企業ID・レコードタイプID・契約値・48枠等の生成項目は生成値を優先します。追加の参照先マスターを自動で作成する処理はありません。

## 件数とトランザクション

4テーブルへのINSERTは1トランザクションで行います。途中で例外が発生した場合、その実行で追加した行は全てロールバックします。`--init-sqlite`で作成したテーブル自体は残ります。

48枠の実績を全地点分まとめてメモリへ載せず、地点ごとに生成します。日別行のINSERTは既定で200行ずつまとめ、`--chunk-size`で変更できます。チャンクごとにコミットする方式ではありません。

1000地点の1年分は通常365,000行、うるう日を含む期間は366,000行の日別実績です。まず`--count 10 --days 1`などで接続・列設定を確認し、必要な規模で実行してください。

検証用SQLiteで、4テーブルの供給地点一致、1000地点・1日、366日、kWh換算、通常のレポート取得、既存行の保持、レポート管理への未投入、失敗時のロールバックをテストしています。接続先・認証情報が未提供のため、実PostgreSQLへの接続・登録は未実施です。

PostgreSQLの接続形式・識別子・ドライバーの参考資料：

- [SQLAlchemyのPsycopg2接続](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2)
- [SQLAlchemyのURLエンコード](https://docs.sqlalchemy.org/en/20/core/engines.html#escaping-special-characters-such-as-at-signs-in-passwords)
- [PostgreSQLの識別子](https://www.postgresql.org/docs/current/sql-syntax-lexical.html)
- [Psycopg2のインストール](https://www.psycopg.org/docs/install.html)
