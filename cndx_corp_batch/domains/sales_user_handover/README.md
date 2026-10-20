# 担当者引継ぎ実行

`docs/バッチ設計書_担当者引継ぎ実行 (1).xlsx` のバッチID
`BLMMGMGHANDOVER` に対応する実装です。テーブル名・物理項目名は
`docs/STEP4_テーブル一覧・定義書・ER図.xlsx` に合わせています。

## 実行

プロジェクトルートから `DATABASE_URL` を設定して実行します。

```powershell
python -m cndx_corp_batch.entrypoints.sales_user_handover_batch
python -m cndx_corp_batch.entrypoints.sales_user_handover_batch --batch-date 2026-12-21
```

引数を省略した場合は、日本時間の実行日を使用します。

## 処理内容

- 引継実施ステータスが「予定（1）」で、引継実施予定日が実行日と一致する対象を取得します。
- 対象は登録日時、更新日時の昇順で、法人番号単位に順次処理します。
- 引継元担当者が担当者情報マスタに存在する場合、組織IDと担当者ユーザーIDを引継先へ更新します。
- 引継元担当者が存在しない場合は、該当する引継情報を削除します。
- 過去データ引継ぎフラグが有効な場合、8表の元組織データを確認します。建物マスタが存在しない場合は登録エラーとし、存在する表だけを引継先組織へ更新します。
- 正常終了はステータス「完了（0）」、データ不足は「登録エラー（3）」として引継実施日時を更新します。
- DB例外時は処理中のトランザクションをロールバックし、別トランザクションで「登録エラー（3）」を記録してバッチを異常終了します。

## 対象データ表

過去データ引継ぎでは、次の表を確認・更新します。建物マスタだけは組織IDではなく
`AGREEMENT_ORG`（同意書取得組織）を使用します。

- `T_MONTHLY_BUILDING_ENERGY_AGGREGATION`
- `T_ANNUAL_BUILDING_ENERGY_AGGREGATION`
- `T_MONTHLY_CORPORATE_ENERGY_AGGREGATION`
- `T_ANNUAL_CORPORATE_ENERGY_AGGREGATION`
- `T_REPORT_STORAGE_INFO`
- `M_BUILDING`
- `T_CN_APPLICATION_INFO`
- `T_BUILDING_INFO`
