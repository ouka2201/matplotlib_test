# 画面・APIの項番別テストデータ準備

`Docs/テストケース` の画面4表・API4表に対応する起動PGを分けています。どのPGも `--list` で項番とDB条件を表示し、`--case 番号` で指定します。`--apply` は初回準備、`--reset` は同じケースの初期状態への再設定、`--cleanup` は作成データの削除です。省略時はDBを読んで事前条件を確認します。項番・手順・期待結果の原文は `api_screen_case_catalog.json` に保存しています。

| テスト表 | 起動PG | 項番 | 主なDB条件 |
| --- | --- | --- | --- |
| 30分値データ登録画面 | `prepare_data30_screen_cases.py` | 1～11 | 5は0件、4・6は複数拠点 |
| LMMVMV-API-02 | `prepare_api02_cases.py` | 1～10 | 6は0件、5・7・8は複数拠点 |
| お客さま企業マスタ照会・編集画面 | `prepare_corp_screen_cases.py` | 1～11 | 5は未登録、6は2企業 |
| LMMBCS-API-04 | `prepare_api04_cases.py` | 1～10 | 5は未登録、7は2企業 |
| 引継確認画面 | `prepare_handover_screen_cases.py` | 1～13 | 5は企業データ0件、他は2企業 |
| LMMGMG-API-05 | `prepare_api05_cases.py` | 1～10 | 6は個別の既存引継予定1件 |
| LMMGMG-API-06 | `prepare_api06_cases.py` | 1～10 | 6は一括の既存引継予定2件 |
| 担当者設定情報管理画面 | `prepare_staff_screen_cases.py` | 1～11 | 検索用担当者2名 |

PowerShellの例（プロジェクトルートから実行）：

```powershell
python cndx_corp_back/test/prepare_api02_cases.py --list
$env:TEST_DATABASE_URL = 'postgresql+psycopg2://USER:PASSWORD@HOST/TEST_DB'
$per30 = @('--corp-number','9999999999001','--org-id','UT30-O1',
           '--other-org-id','UT30-O2','--supply-point-1','9999999999999999999001',
           '--supply-point-2','9999999999999999999002','--create-masters')
python cndx_corp_back/test/prepare_api02_cases.py --case 6 @per30 --apply
python cndx_corp_back/test/prepare_api02_cases.py --case 6 @per30 --reset
python cndx_corp_back/test/prepare_api02_cases.py --case 6 @per30 --cleanup
```

企業マスタ/API-04は、法人番号・供給地点番号・同意組織を指定します。2企業ケースでは、指定番号とその次の番号を使用します。

```powershell
$corp = @('--corp-number','9999999999001','--supply-point','9999999999999999999001',
          '--consent-org-id','UT30-BANK01')
python cndx_corp_back/test/prepare_api04_cases.py --case 7 @corp --apply
python cndx_corp_back/test/prepare_api04_cases.py --case 7 @corp --reset
```

引継画面/API-05・06は、既存の検証用管理者と元・先組織を指定します。ケース6では、更新対象の引継予定を事前に作成します。削除時にも同じIDと実施日を指定してください。

```powershell
$handover = @('--login-user-id','00000001','--from-org-id','BNK0001000',
              '--to-org-id','BNK0001001','--schedule-date','2026-12-21')
python cndx_corp_back/test/prepare_api05_cases.py --case 6 @handover --apply
python cndx_corp_back/test/prepare_api05_cases.py --case 6 @handover --reset
python cndx_corp_back/test/prepare_api05_cases.py --case 6 @handover --cleanup
```

PGはテスト前のDB状態を準備し、実行時に項番のテスト手順を表示します。画面操作、HTTPリクエスト、権限の異なるログイン、入力不正値、Exception注入は表示された手順に従って実施してください。DBの作成者やキーが想定と異なる場合は削除・上書きを中止します。
