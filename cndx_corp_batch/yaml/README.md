# Kubernetes バッチ

`docs/Cronjob共通設計書.xlsx` の「バッチ実行一覧」に従い、5つの CronJob を定義しています。すべて日本時間のスケジュールです。`timeZone` の利用には Kubernetes 1.27 以降が必要です。

| ファイル | バッチ | 実行時刻 |
| --- | --- | --- |
| `electricvis_middle_data_cronjob.yml` | 30分値・顧客情報取込 → 顧客情報と30分値データの自動連携 | 毎日12～21時の毎時0分 |
| `electricvis_middle_report_cronjob.yml` | 電力見える化レポート一括作成 | 毎時0分 |
| `electricvis_middle_zip_cronjob.yml` | 担当者別ZIPファイル作成 | 毎時0分 |
| `regular_delete_cronjob.yml` | 定期削除 | 毎日2時 |
| `handover_cronjob.yml` | 担当者引継ぎ実行 | 毎日1時 |

取込が正常終了した場合だけ、同じ Job で連携バッチを続けて実行します。設計書の `co2report_cronjob.yml` に対応する CO2集計レポートの `entrypoints` は、このリポジトリに存在しないため未作成です。`prepare_periodic_delete_data.py` は検証DBへテストデータを投入するため、CronJob の対象外です。

```sh
kubectl apply -f cndx_corp_batch/yaml/
kubectl create job --from=cronjob/electricvis-middle-report electricvis-middle-report-manual
```

`epdb-secret` の `DATABASE_URL` キーが必要です。`tableau-secret` と `cndx-corp-config` は既存の `envFrom` で読み込みます。取込バッチには追加で `tdv-secret` の `username` と `password` キーが必要です。ZIP作成バッチには `cndx-corp-config` の `USER_POWER_REPORT_FILE_PATH` キー（ZIPの保存先）が必要です。

取込・レポート・ZIP作成で使う切替日、対象月のオフセット、取込件数、API実行時間帯などは、それぞれの YAML にコードの既定値を明記しています。環境に合わせて値を変更する場合は該当 YAML を編集してください。`REGILAR_CHUNK_SIZE` はソースで使用している環境変数名の綴りです。

PDF と ZIP の保存先、および定期削除で参照する ZIP は、各 Pod から同じパスで読み書きできるようにしてください。マニフェストには環境固有のボリュームを定義していません。
