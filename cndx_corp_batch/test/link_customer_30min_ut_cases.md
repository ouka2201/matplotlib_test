# 30分値連携バッチ UT-001～UT-112 のデータ準備

対象は `Docs/テストケース/30分値連携.xlsx` の「単体テスト1ケース・結果一覧表」です。`prepare_link_customer_30min_ut_cases.py` は UT 番号から同表の TD 番号を引き、ケースごとに異なる架空の法人番号・供給地点を作ります。項番、手順、期待結果、TD 説明は `link_customer_30min_ut_catalog.json` に保存しています。旧72ケース用の `prepare_link_customer_30min_cases.py` とは番号体系が異なります。

```powershell
python -m cndx_corp_batch.test.prepare_link_customer_30min_ut_cases --list
python -m cndx_corp_batch.test.prepare_link_customer_30min_ut_cases --case UT-071 --dry-run

$env:REPORT_DATABASE_URL = 'postgresql+psycopg2://USER:PASSWORD@HOST/TEST_DB'
python -m cndx_corp_batch.test.prepare_link_customer_30min_ut_cases `
    --case UT-071 --db-config cndx_corp_batch/test/database.json
python -m cndx_corp_batch.test.prepare_link_customer_30min_ut_cases `
    --case UT-071 --db-config cndx_corp_batch/test/database.json --reset
python -m cndx_corp_batch.test.prepare_link_customer_30min_ut_cases `
    --case UT-071 --db-config cndx_corp_batch/test/database.json --cleanup
```

`--reset` は同じケースの投入済み行を削除し、初期データを再投入します。`--cleanup` は削除のみです。いずれも元データの作成者と連携先の法人・拠点キーを照合してから1トランザクションで実行します。別ケースの未処理行が残るとバッチの処理件数が変わるため、ケース専用DBを使うか前ケースを削除してください。0件ケース（UT-002、UT-022、UT-100）は他の未処理行がないDBで実行します。

新表の日付境界に合わせ、バッチ実行時には `CUT_OFF_DAY=19`、`REPORT_MONTH_OFFSET_BEFORE=3`、`REPORT_MONTH_OFFSET_AFTER=2` を設定します。PG が出力する `batch_command` と `batch_environment` を同じDBで使用してください。999／1000／1001／2001件のケースはそれぞれ実件数を作成します。

TD-11、14、39、46はDBのNULL・日時・電力量列制約により投入できない場合があります。TD-55の同一キー元データ2行も一意制約があるDBでは直接投入できません。TD-23、54、57、61～64、71は二段階操作、対象外行の比較、またはモックによる例外注入が必要です。PG の計画JSONに注意事項を出します。TD-33は現行ARVE表に姓・名の別列がないため、結合名の空値を準備します。これらの確認にはテスト手順側の操作・モックを併用してください。

`--init-sqlite` は `schema: null` のSQLite設定で投入処理を検証するときだけ使います。CASTエラーや実DBの制約確認はPostgreSQLで実施してください。
