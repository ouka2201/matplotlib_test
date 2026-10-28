# 30分値データ登録画面／一覧取得API テストデータ準備PG

`prepare_per_30min_data.py` は、テストケース表の D01・D02 と、DB値を変更して確認する派生条件を用意する。`--create-masters` で企業基本・企業詳細・組織O1/O2・拠点B20/B10も新規作成できる。従来どおり既存マスタから拠点を複製する使い方もできる。利用者や権限は変更しない。

## 前提

- `TEST_DATABASE_URL` に**検証DB**のSQLAlchemy接続URLを設定する。
- `--create-masters` では、検証DBに未登録のC1法人番号（13桁）とO1/O2組織IDを指定する。都道府県コードの既定値`13`は検証DBの共通都道府県マスタに存在することを確認する。必要なら `--prefecture-code` で変更する。
- 既存マスタを使う場合は、C1・区分01・O1 に属する複製元拠点IDを `--template-building-id` に指定する。企業基本・企業詳細・O1/O2・複製元拠点は削除扱いでないこと。
- P1/P2 には、検証用の異なる供給地点特定番号（22文字以内）を使う。既定の B20=`UT30-B20`、B10=`UT30-B10` が既存レコードと重なる場合は別IDを指定する。B10 < B20 とする。
- `--apply` または `--cleanup` を付けない実行は検証DBを読み、準備件数だけ表示する。書き込みは行わない。

PowerShell の例：

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME'
$common = @(
  '--corp-number', '9999999999001',
  '--org-id', 'UT30-O1',
  '--other-org-id', 'UT30-O2',
  '--supply-point-1', '9999999999999999999001',
  '--supply-point-2', '9999999999999999999002',
  '--create-masters'
)
python cndx_corp_back/test/prepare_per_30min_data.py @common --case base
python cndx_corp_back/test/prepare_per_30min_data.py @common --case base --apply
python cndx_corp_back/test/prepare_per_30min_data.py @common --case two-buildings --apply
python cndx_corp_back/test/prepare_per_30min_data.py @common --cleanup
```

既存マスタを使うときは `$common` から `--create-masters` を外し、`--template-building-id 既存拠点ID` を追加する。この場合、企業基本・企業詳細・O1/O2は既存行を参照し、B20/B10と30分値だけを作成する。

`python` はSQLAlchemyとPostgreSQLドライバをインストールしたプロジェクトのPythonを使う。接続URLをコマンド引数へ書かず環境変数で渡す。

## ケースと投入内容

| `--case` | 主な用途 |
| --- | --- |
| `base` | D01。A拠点(B20)に20260102・20260104の2日分。ARVE名・コード・番号、更新日時の基本値を用意 |
| `two-buildings` | D01＋D02。B拠点(B10)に20260103を追加。複数拠点・名称順・拠点切替 |
| `no-data` | D01の建物だけを用意。0件表示・空配列 |
| `one-day` | D01の20260102のみ。1日集計・updated_at未設定時の補完 |
| `year-cross` | 20261231・20270101。年跨ぎ表示 |
| `leap-day` | 20240229の1日。うるう日表示 |
| `arve-null` / `arve-empty` | D01のARVE3項目を全行NULL／空文字 |
| `raw-deleted` / `raw-null-delete` | 生データの削除行追加／削除フラグNULL |
| `building-deleted` / `building-null-delete` | 建物マスタの削除フラグTRUE／NULL |
| `no-building` | 生データのみ。対応建物なし。DBに外部キー制約がある場合は使用不可 |
| `no-timestamps` | 生データの登録・更新日時を両方NULL |

D01 の生データは取得日 `20260102` と `20260104`、ARVE値は `ARVE試験会社` / `012` / `0000000000045`。後者の更新日時は `2026-01-05 10:20:30`。ファイル更新日時は両行 `2025-12-01 00:00:00`。電力量48項目は各 `1` とする。

APIリクエストの Q0 は、表示された C1/O1/B20 の実値を `corp_number` / `org_id` / `building_id` に設定し、`agreement_category=01` を付ける。複数拠点を確認するときは `building_id` を空欄にする。画面の拠点選択には、既存企業詳細・組織・認証済み利用者が必要。

入力値不足・権限・HTTP異常・DB例外・ページング・CSVの内容自体はこのPGの対象外。テストケース表のスタブ、既存利用者、既存正常CSVを使用する。C2・区分02・O2の追加行や結合キー不一致は既存マスタを伴う個別ケースとして、ケース表の指示に従い別途準備する。

## 再実行と削除

PGの作成行は `created_by=UT30_PER30MIN` で識別する。`--apply` のたびに対象のPG作成行をトランザクション内で入れ替える。他者が作成した同じIDの行があればエラーにして既存データを守る。`--cleanup` はこのPGの作成行だけを子テーブルから順に削除する。既存マスタを使った場合、その既存行と複製元には触れない。試験中に作成行の `created_by` を変更した場合は削除対象から外れるため、変更前に退避して元に戻す。
