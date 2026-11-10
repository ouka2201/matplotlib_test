# テストデータ準備PGの対応

各表のExcel項番を `--case` で指定できます。画面・API用PGは表ごとの起動ファイルから共通の準備処理を使用します。実行例は `cndx_corp_back/test/README_api_screen_cases.md` を参照してください。

| テストケース表 | 準備PG | ケース別の使い方 |
| --- | --- | --- |
| 30分値連携.xlsx（UT-001～112） | `cndx_corp_batch/test/prepare_link_customer_30min_ut_cases.py` | `--case UT-番号`、`--reset`、`--cleanup`。詳細は `cndx_corp_batch/test/link_customer_30min_ut_cases.md` |
| PG2-1-01_担当者引継ぎ実行.xlsx（1～48） | `cndx_corp_batch/test/prepare_sales_user_handover_cases.py` | `--case 番号`、`--reset`、`--cleanup` |
| 30分値データ登録画面 | `cndx_corp_back/test/prepare_data30_screen_cases.py` | `--case 1～11`、`--apply`、`--reset`、`--cleanup` |
| LMMVMV-API-02 | `cndx_corp_back/test/prepare_api02_cases.py` | `--case 1～10`、同上 |
| お客さま企業マスタ照会・編集画面 | `cndx_corp_back/test/prepare_corp_screen_cases.py` | `--case 1～11`、同上 |
| LMMBCS-API-04 | `cndx_corp_back/test/prepare_api04_cases.py` | `--case 1～10`、同上 |
| 引継確認画面 | `cndx_corp_back/test/prepare_handover_screen_cases.py` | `--case 1～13`、同上 |
| LMMGMG-API-05 | `cndx_corp_back/test/prepare_api05_cases.py` | `--case 1～10`、同上 |
| LMMGMG-API-06 | `cndx_corp_back/test/prepare_api06_cases.py` | `--case 1～10`、同上 |
| 担当者設定情報管理画面 | `cndx_corp_back/test/prepare_staff_screen_cases.py` | `--case 1～11`、同上 |

画面入力の必須・桁数・文字種、認証権限、画面遷移はDB行を増やさず、テスト手順の入力値・利用者で確認します。想定外ExceptionやWARNINGを発生させるケースはモック／注入点が必要です。PGはDB制約を迂回しません。
