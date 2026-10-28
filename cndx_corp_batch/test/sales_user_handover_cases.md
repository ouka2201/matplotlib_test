# 担当者引継ぎ実行のケース別テストデータ準備

`prepare_sales_user_handover_cases.py` は、単体テストケース表の項番1～64に対応する初期データを作成します。
ケースの前提・手順・期待結果・仕様確認事項は `sales_user_handover_cases.json` に保存しています。
実行時にExcelは不要です。Python 3.12とバッチの既存依存ライブラリSQLAlchemyを使用します。
PostgreSQLへの投入には既存の `psycopg2-binary` も必要です。

## 使い方

2026-10-28に80ケースから64ケースへ整理し、1～64に再採番しました。以降のコマンドはすべて**新番号**です。
[削除・統合理由と新旧対応](sales_user_handover_case_reorganization.md)を参照してください。
旧計画JSONは再利用せず再生成します。準備データの法人番号・組織ID・担当者IDも新番号に合わせています。


リポジトリのルートで実行します。既存のバッチ実行用Python環境を使ってください。

```powershell
Set-Location C:\STEP4\electricity_report
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases --list

# DB接続せず、ケース19の全投入行と実行手順を保存
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 19 --dry-run --output output/sales_user_handover/case19.json
```

出力JSONには物理列名を使った全投入行、Excel行番号、ケースの期待結果、識別子対応、バッチ実行日・コマンド、追加操作を含みます。
`--output` のファイルは投入前の計画です。投入成功やバッチの合格証跡ではありません。
DBへの投入に成功したときだけ、コンソールに「投入完了」（`--reset` は「初期化・再投入完了」）と各テーブルの件数を出力します。

## PostgreSQLへ投入する

1. ケース専用の検証DBにテーブルを作成します。このPGはDDLを実行しません。
2. `sales_user_handover_database.example.json` を作業用設定にコピーします。
3. 引継種別は `0=個別`、`1=一括` です。設定例にはこの値を設定済みで、省略時も同じ値を使用します。
4. 必要に応じて組織・ユーザー等のテスト用参照マスタを用意し、設定の値を合わせます。
5. 接続先を環境変数に設定し、投入します。

```powershell
Copy-Item cndx_corp_batch/test/sales_user_handover_database.example.json `
    output/sales_user_handover/database.json

# コピー先JSONの接続先・参照マスタ設定を確認して実行
$env:REPORT_DATABASE_URL = 'postgresql+psycopg2://ユーザー:パスワード@ホスト/検証用DB名'
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 19 --db-config output/sales_user_handover/database.json `
    --output output/sales_user_handover/case19.json
```

`--handover-type 0`（個別）または `--handover-type 1`（一括）を指定すると、設定JSONの値より優先します。
ケース49は `bulk`、それ以外は `individual` を参照します。
未指定の場合はケース49に `1`、それ以外に `0` を設定します。`0`・`1`以外の値は受け付けません。

引継実施ステータスは `0=完了`、`1=予定`、`2=引継中止`、`3=登録エラー` です。
ケース4には引継中止の行を含め、実行日が一致しても予定以外の行を処理しないことを確認します。

既存のデータ投入PGと同じ `url` / `url_env` / `schema` を利用できます。
本PGの既定環境変数は `REPORT_DATABASE_URL`、既定スキーマは `db_corp` です。
接続先や認証情報は計画JSONへ出力しません。

任意の設定項目は次のとおりです。

| 設定 | 内容 |
| --- | --- |
| `identifiers` | `O1`・`O2`・`O3`・`U1`・`U2`・`U3`の実値を指定するオブジェクト。省略時はケース専用IDを生成 |
| `agreement_category` | 同意書取得区分。既定値は既存の投入PGと同じ `01` |
| `energy_code` | 既存のテスト用エネルギーコード。既定値 `ELECTRICITY` は架空値 |
| `tables` | テーブル別名が必要な場合の対応。キーは `corporate`・`staff`・`handover`・`A`～`H` |

列名の大文字・小文字は吸収します。必要な列、主キー、NOT NULL、文字列長を検査し、条件に必要な列を黙って捨てません。
利用者・組織・同意書取得経路・エネルギー等の参照マスタは作成しません。FKやCHECK制約があるDBでは有効な参照値が必要です。
特に建物マスタ未存在のケースでFK制約と前提が両立しない場合は、制約を無効化せず、その存在チェックをスタブで再現してください。

## 作成するデータ

| 記号 | 物理テーブル | 主な内容 |
| --- | --- | --- |
| corporate | m_corporate_basic | 使用する全法人の親データ |
| staff | m_staff_info | 引継元、登録済み引継先、比較用担当者 |
| handover | t_sales_user_handover_info | 予定・完了・引継中止・登録エラー、実施予定日、元／先ID、フラグ |
| A | t_monthly_building_energy_aggregation | 月別建物エネルギー |
| B | t_annual_building_energy_aggregation | 年度別建物エネルギー |
| C | t_monthly_corporate_energy_aggregation | 月別法人エネルギー |
| D | t_annual_corporate_energy_aggregation | 年度別法人エネルギー |
| E | t_report_storage_info | レポート格納情報 |
| F | m_building | 建物マスタ。引継対象項目は `agreement_org` |
| G | t_cn_application_info | CN対策実施申込情報 |
| H | t_building_info | 建物情報 |

法人番号は `9900000000000 + 開始番号 + 法人の通番` を使用します（通番は0開始）。
開始番号の既定値は `ケース番号×1000+1`。`--start-id` で1～999700の範囲に変更できます。
組織・担当者IDも開始番号に連動し、元・先・比較用を区別します。Excelには既定の実値を記載し、設定変更時の実値はJSONの `identifiers` で確認できます。
担当者IDは引継情報の列定義に合わせて8文字以内です。

更新範囲ケースでは、同一法人・元組織の対象2行と、別組織・別法人・引継先組織の比較行を生成します。
比較行には異なる明細キーを使い、組織IDの正常な変更だけで主キー衝突が起きないようにしています。
建物名・エネルギー量などには保持を確認できる値を設定します。架空のレポートパスを登録しますが、PDFファイル自体は作成しません。

## ケースごとの追加操作

Q02は2026-10-28に確定しました。担当者情報マスタは担当者ユーザーIDだけを更新し、組織IDを保持します。ケース14では組織IDが引継元の値のままであることを確認します。過去データ8表の組織更新は従来どおり、過去データ引継ぎフラグに従います。

| 項番 | 準備内容・実施上の注意 |
| --- | --- |
| 1～3 | 日付引数・対象0件。ケース1はアプリ内時計を2026-10-26に固定 |
| 4～7 | 対象・非対象混在、抽出順。同時刻の順序は合否対象外 |
| 8～11 | 登録締切の境界。Q01の回答後に期待結果を確定 |
| 12～15 | 担当者更新範囲、組織ID保持、先担当者登録済み |
| 16～17 | 元・先不在時の削除、他法人だけに担当者が存在する場合。16は後続法人と2回目も確認 |
| 18～21 | 過去データFALSE／TRUE／NULL。19で完了日時と正常ログも確認 |
| 22～37 | 各過去データテーブルの更新範囲・存在確認、建物マスタの同意書取得組織 |
| 38～40 | 建物マスタ不在・取得組織不一致・全過去データなし。38で業務エラーログも確認 |
| 41 | 過去日引数でも実施日時はDB現在時刻。処理前後のDB時刻を記録 |
| 42～47 | 状態更新処理11／13を単体で呼ぶ。44～46はtarget／comparisonに分けて実施 |
| 48～49 | 個別1法人とTRUE／FALSE混在の一括3法人 |
| 50～51 | 完了後の2回目、登録エラー状態の再実行。16・50は途中で再投入しない |
| 52 | 業務エラー後の後続法人。Q05・Q06を確認 |
| 53～62 | 障害到達用データ。例外・COMMIT失敗はスタブ等で別途設定 |
| 63～64 | 元不在・同じ法人に先登録済み。FALSEは過去データ保持、TRUEは過去データ更新 |

追加要件画像の指示を優先し、引継元が不在でも同じ法人に引継先が存在すれば、過去データ引継ぎフラグの判定へ進みます。FALSEは過去データを変更せず完了更新、TRUEは過去データの存在確認・更新へ進みます。元・先とも不在なら該当法人の引継情報を削除し、次の法人を処理します。
ケース16では元・先とも不在の法人の後に正常法人が完了し、同日再実行で変更がないこと、ケース63・64では引継先登録済みのFALSE／TRUEを確認します。

### ケース44～46は2回に分けて実施する

営業担当引継情報の主キーは `(corporate_number, handover_from_org_id, handover_from_user_id)` です。
先組織・状態・予定日だけを変えた2行は同時に登録できません。
主キーやケースの条件を勝手に変えず、次の2種類の計画を使用します。

```powershell
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 44 --variant target --dry-run --output output/sales_user_handover/case44_target.json
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 44 --variant comparison --dry-run --output output/sales_user_handover/case44_comparison.json
```

`target` を投入して対象行が更新されることを確認後、同じ設定・開始番号で `--variant comparison --reset` を指定して比較用の初期状態に戻します。
比較時にも**元のC1/O1/U1→O2/U2、予定日D**を状態更新処理の引数として使い、比較行が更新されないことを確認します。
比較行の値を引数に渡してはいけません。ケース45・46も同様です。

## バッチの実行

投入PGはバッチを自動実行しません。データ準備後、計画JSONのコマンドと追加操作に従って実施します。
通常のケース19は次のコマンドです。

```powershell
$env:DATABASE_URL = $env:REPORT_DATABASE_URL
$env:TZ = 'Asia/Tokyo'
python -m cndx_corp_batch.entrypoints.sales_user_handover_batch --batch-date 2026-10-26
```

`BatchContext` が必要とする環境設定は既存のバッチ環境を使用します。
ケース1・53は引数を付けず、テスト用時計を固定してください。本PGはOS時計を変更しません。
仕様確認待ちの期待結果は元のケース表に従い、確認後に確定してください。現在の実装の挙動を設計上の正解として書き換えません。

## 既存データと再実行

### 同じケースを最初からやり直す

`--reset` を付けると、指定ケースの法人番号に属する作成済みデータを削除し、初回実行前の状態を再投入します。
初回も同じコマンドを使えます。完了・登録エラー・予定のどの状態からでも初期化できます。
引継ぎ済みの担当者・過去データ、削除済みの引継情報も復元対象です。

```powershell
# 変更範囲を確認（DB接続なし。作成者の実データ検査は本実行時）
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 49 --reset --dry-run --db-config output/sales_user_handover/database.json

# ケース49を初期化。初回も再テスト時もこのコマンド
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 49 --reset --db-config output/sales_user_handover/database.json `
    --output output/sales_user_handover/case49.json

# 「初期化・再投入完了」を確認後に実行し、結果を確認・保存する
$env:DATABASE_URL = $env:REPORT_DATABASE_URL
$env:TZ = 'Asia/Tokyo'
python -m cndx_corp_batch.entrypoints.sales_user_handover_batch --batch-date 2026-10-26
```

同じケースをやり直す際は、初期化とバッチ実行を繰り返してください。
以前 `--start-id` を指定した場合は同じ値を使用します。`identifiers`・参照コード・接続先・テーブル設定も初回と揃えてください。
初期化すると前回の結果は消えるため、結果の確認・保存を先に済ませます。バッチと準備PGは同時実行しないでください。

### 別ケースに切り替える

前のケースを `--cleanup` で片付けてから、次のケースを投入します。`--cleanup` は再投入を行いません。
前のケースの未処理予定や担当者が次のテストに影響するのを防げます。

```powershell
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 49 --cleanup --db-config output/sales_user_handover/database.json

# 「削除完了」を確認後、次のケースを準備
python -m cndx_corp_batch.test.prepare_sales_user_handover_cases `
    --case 4 --reset --db-config output/sales_user_handover/database.json
```

まず試す組み合わせはケース1・4・15・16・20・49・50・52・59です。
**ケース50・16の1回目と2回目のバッチ実行の間には、reset・cleanupを行いません。** 初回の結果を残して二重処理しないことを確認します。
ケース1の時計固定、ケース59の例外注入などの追加操作は、引き続き計画JSONに従って実施してください。

### 削除範囲と失敗時の動作

通常実行は従来どおりINSERTのみです。`--reset` / `--cleanup` は、このPGが扱う11テーブルのうち、計画JSONの `cleanup_scope.corporate_numbers` に一致する行を削除します。
対象法人に `created_by = 'handover_test_seed'` 以外（NULLを含む）の行が1件でもあれば、削除前に中止します。
別法人、利用者・組織等の参照マスタは削除しません。制約解除・CASCADE指定は行いません。
検証DB専用で使用してください。DBに外部キーの削除連鎖がある場合、そのDB定義による影響も事前に確認してください。

削除と再投入は全テーブルを1トランザクションで行います。再投入・制約検査・COMMITで失敗した場合は、削除も含めてロールバックします。
`--cleanup` も削除全件を1トランザクションで行い、対象が既に空なら0件で完了します。

次の場合は投入を中止します。

- 通常実行で同じ法人番号が対象テーブルに既に存在する（`--reset` でやり直せます）。
- 引継元ユーザーIDが別法人の担当者として既に存在する。
- バッチ実行日の予定状態の行が既に存在する（別ケースの巻込みを防止）。
- 主キーが既存行と重複する、または計画内で重複する。
- 必須列・値が不足する、または状態・引継種別コードが定義外。

`--reset` や `--start-id` を指定しても、別ケースの未処理予定の混在は許可しません。前ケースを `--cleanup` で削除するか、ケース専用の検証DBを使用してください。
再実行ケース16・50・51は、データ準備PGの再実行ではなく、同じ準備データに対する**バッチの再実行**を確認します。

## NoSuchTableErrorが表示された場合

接続先DBで、指定したテーブルが見つからないか参照できない状態です。
PGは「見つからないテーブル」「定義取得対象」「設定キー」を表示して、INSERT前に停止します。
外部キーの参照先が未作成の場合は、見つからないテーブルが定義取得対象と異なることもあります。

`schema` が `db_corp` の場合は、接続しているDBで次のSQLを実行して確認します。

```sql
SELECT current_database(), current_user;

SELECT table_schema, table_name
FROM information_schema.tables
WHERE lower(table_schema) = 'db_corp'
ORDER BY table_schema, table_name;
```

エラーに出た名前と、一覧の実際のスキーマ・テーブル名（大文字・小文字も含む）を比較してください。
接続先が違う場合は `REPORT_DATABASE_URL`、スキーマが違う場合は設定の `schema` を修正します。
検証DBでテーブル名を変更している場合は、`tables` の該当キーに実際の名前を指定します。
たとえば `tables.handover` は営業担当引継情報のテーブル名に対応します。
バッチ本体のSQLは `db_corp` の既定テーブル名を使用するため、準備PGの設定だけでは本体の参照先は変わりません。

未作成の場合は正式なDDLを適用してください。自動で空テーブルを作ったり、見つからないテーブルをスキップしたりはしません。
一覧に表示されない場合は、テーブルの存在に加えて接続ユーザーの参照権限も確認してください。

## 投入PGの確認

```powershell
python -m pytest cndx_corp_batch/tests/test_prepare_sales_user_handover_cases.py -q
```

SQLiteの一時DBに、既存エンティティから作ったテーブルと設計書準拠の引継情報テーブルを使用します。
全64ケース（44～46の分割を含む67パターン）の投入、実際の対象抽出SQL・8種類の更新SQL、重複防止、初期化・片付け、他法人・他作成者の保護、失敗時のロールバックを検証します。
ケース16・63・64は、実際のSQLを使ってバッチを呼び出し、元・先とも不在時の削除・後続法人の処理、先が存在する場合の担当者保持とフラグに応じた過去データ更新・完了も検証します。
これは投入PGの検証であり、PostgreSQL上の担当者引継ぎバッチの単体テスト結果ではありません。

参照資料：`docs/STEP4_テーブル一覧・定義書・ER図.xlsx`、担当者引継ぎバッチ設計書、
`docs/PG2-1-01_単体テストケース・結果一覧表_担当者引継ぎ実行.xlsx`、既存エンティティ・担当者引継ぎSQL。
