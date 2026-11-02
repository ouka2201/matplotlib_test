# 電力見える化レポート一括作成

このフォルダーが既存バッチに組み込まれた実装です。本バッチのテストは
`tests/generate_all_power_report` に配置しています。

## 実行

Python 3.12と本フォルダーの依存ライブラリ、PlaywrightのChromiumを用意します。
`DATABASE_URL` は実行環境に設定してください。認証情報をソースへ記載しません。
Tableauの認証情報が必要な環境では `TABLEAU_USERNAME`、`TABLEAU_PASSWORD` も環境から渡します。

バッチ本体はプロジェクトルート（`C:\STEP4\electricity_report`）で実行します。

```powershell
$env:REPORT_OUTPUT_DIR = 'C:\STEP4\electricity_report\output\reports'
python -m cndx_corp_batch.entrypoints.generate_all_power_report
```

`REPORT_OUTPUT_DIR` の省略時は、設計書の保存先
`/bd-fs-mnt/TenantShare/corp/electricity_vis_middle/power_report` を使います。
実行日を指定して再実行する場合は次のように指定します。

```powershell
python -m cndx_corp_batch.entrypoints.generate_all_power_report --batch-date 2026-05-15
```

既定では1～14日は実行月の3か月前、15日以降は2か月前を対象にします。
`CUT_OFF_DAY`、`REPORT_MONTH_OFFSET_BEFORE`、`REPORT_MONTH_OFFSET_AFTER` で整数値を指定できます。

取込完了・管理情報未登録の対象を登録してから、状態2・5の対象をCPU数に応じて処理します。
対象0件ならワーカーを起動せず終了します。

- PDF名は未加入なら `企業ID_供給地点特定番号_YYYYMM.pdf`、加入なら `企業ID_供給地点特定番号_syousapo_YYYYMM.pdf`。
- 数値変換エラーは状態4「完了（警告）」を登録して、その対象のPDF生成をスキップします。
  DBメッセージは `数値変換エラー：取得年月日` とし、供給地点は管理行で識別します。
  契約電力は供給地点以外の主キーがないため、コロンの後は空になります。
  ログには `LMMRCRC0401`、エラー文、主キー、列名、供給地点、対象年月を出力します。
- 変換・描画・PDF保存で生じたその他の例外は状態5と100文字以内のメッセージを登録します。
- 個別の失敗後も後続対象を処理し、個別失敗だけでバッチ全体を異常終了させません。
- 契約・30分値のDB取得失敗は従来どおり親処理でログに出し、管理状態は変更しません。

## pytestによる自動テスト

`cndx_corp_batch` フォルダーで次を実行します。実DBやTableauには接続せず、SQLiteとPDF生成の代替処理で検証します。

```powershell
Set-Location C:\STEP4\electricity_report\cndx_corp_batch
python -m pip install -r test/requirements.txt
python -m pytest .\tests\generate_all_power_report -q
```

自動テストは `pytest` を介して実行します。以下のテストデータ投入PGは `python -m` で起動します。

分岐カバレッジを計測する場合は、次を実行します。対象は
`cndx_corp_batch.domains.generate_all_power_report` で、未カバー行を端末に表示し、
プロジェクト直下の `output/coverage.xml` にXMLレポートを出力します。設計書のC0/C1目標に合わせて、
合計カバレッジが90%未満の場合は未達として表示します。

```powershell
Set-Location C:\STEP4\electricity_report\cndx_corp_batch
python -m pytest .\tests\generate_all_power_report -q --cov --cov-report=term-missing --cov-report=xml --cov-fail-under=90
```

数値変換時の状態・ログ、後続対象の継続、ファイル名、期間境界、対象登録、
15日の月切替、環境変数、実行日引数、終了処理を確認します。
追加のpytestでは、48枠の時刻対応・単位換算、エラーの行と列、12か月の境界、
列名の大小文字、枠列の不足を確認します。既存のunittest形式の16件も一緒に実行します。
本体の依存ライブラリもテスト用requirementsからインストールされます。テストでChromiumは起動しません。
`test/test_generate_all_power_report.py` のDB接続用スクリプトは、
対象を `tests` に限定しているため自動収集されません。

## レポート作成用のテストデータ

`test/insert_test_data.py` は、レポートSQLが読む取込管理・ARVEお客さま情報・
EP契約電力・EP30分値の4テーブルへ整合した架空データを投入します。
対象月を含む直近12か月が既定で、`--months` または `--days` で期間を短縮できます。

```powershell
Set-Location C:\STEP4\electricity_report
$env:REPORT_DATABASE_URL = 'postgresql+psycopg2://ユーザー:パスワード@ホスト/検証用DB名'
python -m cndx_corp_batch.test.insert_test_data `
    --db-config cndx_corp_batch/test/database.json `
    --report-month 2026-06 --count 3 --months 12
```

`--report-month` は `2026-06` と `202606` の両方を受け付けます。
取込管理は指定月を状態3（完了）で登録します。レポート管理はバッチ本体が登録します。
`--max-kw` は生成する30分平均電力の最大値、`--contract-kw` は正の整数の契約電力です。
EP30分値にはkWhを格納し、欠測・不正値件数を文字列の0、作成者・作成日時を自動設定します。
現行バッチは入力をkWhとして扱うため、`value_unit` にkW・Whは指定できません。

省エネサポート加入・未加入は既定で交互に生成します。`--syousapo joined` または
`--syousapo not-joined` で統一できます。現行SQLの加入判定に合わせ、加入側の
RecordTypeIdは `省エネサポートサービス` とします。設定JSONの `seed_record_type_ids` を
指定する場合もこの条件を満たす必要があります。

`--dry-run` は既存テーブルへ接続して検証・予定件数の表示のみ行います。
同じキーがあれば既定で中止します。`--on-existing skip` は既存行を変更せず不足分だけを追加します。
ARVEの既存判定は、現在の主キーである供給地点のみで行います。
途中で失敗した場合は4テーブルのINSERTをまとめてロールバックします。

SQLiteで投入処理を確認する場合は、設定JSONを次のように作成し、`--init-sqlite` を指定します。
DBファイルの親フォルダーは事前に作成してください。

```json
{"url": "sqlite:///output/report_seed.db", "schema": null}
```

`--init-sqlite` は現行の列名・型・必須監査列を持つ最小4テーブルを作成します。
既存テーブルの定義は変更しません。旧PGで作成したSQLiteは新しいDBファイルに切り替えてください。
`--dry-run` と `--init-sqlite` は同時に指定できません。
このPGは建物・企業マスタや連携先の生データを準備しないため、顧客情報と30分値の連携には次のPGを使います。

## 顧客情報と30分値データ連携用のテストデータ

PG2-1-01の単体テスト仕様書に沿ってケース別のデータを準備する場合は、
`test/prepare_link_customer_30min_cases.py` を使用します。
一覧表示、投入方法、仕様書との差異は [ケース別データ準備の手順](test/link_customer_30min_cases.md) を参照してください。
以下の既存PGは、件数・日数を指定した正常系のデータ生成に使用できます。

連携バッチの確認に必要な、取込管理・企業・建物・ARVE顧客情報・EP30分値を
まとめて登録するPGを `test/insert_link_customer_30min_data.py` に用意しています。
接続先は `--db-config` の `url` または `url_env` から取得します。

```powershell
Set-Location C:\STEP4\electricity_report
$env:REPORT_DATABASE_URL = 'postgresql+psycopg2://ユーザー:パスワード@ホスト/DB名'
python -m cndx_corp_batch.test.insert_link_customer_30min_data `
    --db-config cndx_corp_batch/test/database.json `
    --target-month 2026-03 `
    --count 3
```

既定では対象月の全日について48枠の30分値を作成し、取込管理を状態3（完了）で
登録します。`--days` で生成日数、`--missing-count` と `--invalid-count` で
欠測・不正件数を指定できます。再実行時に既存行を残す場合は
`--on-existing skip`、登録せず内容だけ確認する場合は `--dry-run` を指定します。
このPGは連携先の `t_electricity_data_30min` には登録しません。
