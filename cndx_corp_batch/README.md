# 電力見える化レポート一括作成

顧客情報と30分値データの連携バッチ（BLMMVMVBUILDING）は、
[実行方法と処理仕様](domains/link_customer_30min/README.md)を参照してください。

このフォルダーが既存バッチに組み込まれた実装です。プロジェクト直下の
`services` と `tests` は別実装なので、本バッチの確認には下記のテストを使います。

## 実行

Python 3.12と本フォルダーの依存ライブラリ、PlaywrightのChromiumを用意します。
`DATABASE_URL` は実行環境に設定してください。認証情報をソースへ記載しません。
Tableauの認証情報が必要な環境では `TABLEAU_USERNAME`、`TABLEAU_PASSWORD` も環境から渡します。

`step` フォルダーで実行します。

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

`step` フォルダーで次を実行します。実DBやTableauには接続せず、SQLiteとPDF生成の代替処理で検証します。

```powershell
python -m pip install -r cndx_corp_batch/test/requirements.txt
python -m pytest -c cndx_corp_batch/test/pytest.ini
```

数値変換時の状態・ログ、後続対象の継続、ファイル名、期間境界、対象登録、
15日の月切替、環境変数、実行日引数、終了処理を確認します。
追加のpytestでは、48枠の時刻対応・単位換算、エラーの行と列、12か月の境界、
列名の大小文字、枠列の不足を確認します。既存のunittest形式の16件も一緒に実行します。
本体の `requirements.txt` の依存ライブラリも必要ですが、テストでChromiumは起動しません。
`test/test_generate_all_power_report.py` はDBに接続するローカル実行用スクリプトのため、
`conftest.py` で自動収集から除外しています。
