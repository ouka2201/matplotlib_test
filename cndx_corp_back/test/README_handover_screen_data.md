# 引継画面・登録・バッチ実行のテストデータ

`prepare_handover_screen_data.py` は検索専用の担当者2名を作成します。
`--create-organizations` を指定すると引継元・先の組織も作成します。省略時は既存組織を使います。
`--with-business-data` を追加すると担当企業2社と過去データ8表を作成し、画面登録からバッチ完了まで検証できます。
既存の組織、管理者、権限設定は変更しません。アプリの起動処理を読み込まず、SQLAlchemyで接続します。

## 実行

バックエンドの依存ライブラリ（SQLAlchemyとPostgreSQLドライバ）が入ったPythonを使います。
リポジトリのルートで、`TEST_DATABASE_URL` にアプリと同じ検証DBの接続URLを設定してください。
URL形式は `postgresql+psycopg2://ユーザー:パスワード@ホスト:5432/DB名` です。

以下のIDは例なので、実在する検証用IDに置き換えてください。
ログイン用には、画面にログイン可能なEP管理者（組織種別01・ロール0）または本店管理者（02・9）が必要です。
本店管理者の場合、元・先組織はいずれもログイン組織と同じ先頭7文字（BNK＋銀行コード）にします。
同じ組織を元・先に指定しても構いません。

```powershell
$seedArgs = @(
  '--login-user-id', '00000001',
  '--from-org-id', 'BNK0001001',
  '--to-org-id', 'BNK0001002'
)

# 接続先の前提とID衝突を確認。書き込みなし。
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs

# 投入（全件を1トランザクションで処理）
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --apply
```

既定ユーザーIDは `99009001`、`99009002` です。衝突時は
`--from-user-id` / `--to-user-id` で未使用の8桁以内のIDを指定してください。
既存データは上書きしません。担当者・組織のみの作成では、同じ条件の再実行時に作成済みデータを保持します。
業務データありの場合は、登録・バッチの結果を保持するため、作成済み法人への再投入は停止します。
このPGが作成した行でも、内容が変更されていれば停止します。

## 組織も作成する場合

ログイン管理者とその所属組織は既存のものを使い、元・先には未使用の組織IDを指定します。
以下は銀行コード0001の本店管理者を使う例です。IDは環境に合わせて変更してください。

```powershell
$seedArgs = @(
  '--login-user-id', '00000001',
  '--from-org-id', 'BNK0001901',
  '--to-org-id', 'BNK0001902',
  '--create-organizations'
)
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --apply
```

新規組織の種別は既定で03（支店）、親組織はログイン管理者の所属組織です。
EP管理者で別種別の組織を作る場合は `--org-type-code`（01～06）を指定できます。
02・03の場合、組織IDは `BNK`＋銀行コード4桁＋支店識別子にします。
組織名は `引継画面テスト組織`＋組織IDです。元・先に同じIDを指定すると1組織を作成します。
既存組織とIDが衝突した場合は上書きせず停止します。
組織と担当者は同一トランザクションで作成するため、途中で失敗した場合は全件を取り消します。

## 画面操作

1. 指定した既存管理者でログインし、「営業担当登録・管理」→「担当引継」を開く。
2. 引き継ぎ前の検索欄に `handover-99009001@example.invalid` を入力して「検索」。結果を選択する。
3. 引き継ぎ後は `handover-99009002@example.invalid` で同様に選択する。
4. 実施日にPGが出力した日付（省略時は実行日の7日後）を入力する。
5. 「一括引継」を押し、登録確認モーダルが表示されることを確認する。
6. 「いいえ」で戻り、元・先担当者と実施日が保持されていることを確認する。

検索語 `handover-` で2名、検索タイプ「すべての項目」で `引継画面テスト` を検索できます。
異なるBNK組織同士の場合だけ、過去データ引継のチェックが操作可能です。
同じ担当者を元・先に選択するとエラー、当日以前の日付を入力するとエラーになります。

`--with-business-data` を省略した場合は**確認モーダル表示まで**です。担当企業を割り当てないため、登録・バッチの確認には次の手順を使ってください。
作成した担当者のメールは送信先として使わない予約ドメインで、ログイン用途でもありません。

## 登録からバッチ完了まで

同じ検証DBをフロント経由のAPI、データ作成PG、バッチで使用します。バックエンドだけでなく
`cndx_corp_batch` のソースと依存ライブラリも必要です。既存の担当者・組織をこのPGで作成済みなら、
そのときのIDと組織作成オプションを維持して `--with-business-data` を追加できます。

```powershell
# 再確認・削除時もこの日付を維持してください。
$handoverDate = (Get-Date).AddDays(7).ToString('yyyy-MM-dd')
$seedArgs = @(
  '--login-user-id', '00000001',
  '--from-org-id', 'BNK0001901',
  '--to-org-id', 'BNK0001902',
  '--create-organizations',
  '--with-business-data',
  '--start-id', '900001',
  '--schedule-date', $handoverDate
)
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --apply
```

上のIDは例です。ログイン管理者は実在するIDに、組織IDはその管理者が検索できるものに置き換えてください。
`--start-id` は1～999700で、法人番号は `9900000000000 + start-id` とその次の番号です。
既定値では `9900000900001` と `9900000900002` を作成します。
同意書取得区分は `--agreement-category`（既定01）、エネルギーコードは `--energy-code`（既定ELECTRICITY）で指定できます。
参照マスタに外部キー制約がある環境では、既存の有効なコードに合わせてください。

作成する業務データは次のとおりです。各表に2法人分を作成します。

| データ | 用途 |
| --- | --- |
| 企業基本・企業詳細 | テスト企業の情報 |
| 担当者情報 | 2社を引継元担当者に割り当て |
| 建物マスタ | 過去データ引継ぎに必要な建物 |
| 月別・年別の建物／企業エネルギー集計（4表） | 組織IDの引継確認 |
| レポート保管・CN申請・建物情報（3表） | 組織IDの引継確認 |

レポート保管情報はDB行のみです。PDFファイルの作成やダウンロード確認は対象外です。
**引継予定はPGでは作成しません。次の画面操作で登録してください。**

1. 指定した管理者でログインし、上記「画面操作」と同様に元・先担当者を選択する。
2. 実施日に `$handoverDate` を `YYYY/MM/DD` 形式で入力する。
3. 過去データの更新を確認する場合は「拠点・エネルギーデータ、レポートも引き継ぐ」にチェックする。異なるBNK組織同士が必要。
4. 「一括引継」→「はい」を押し、成功トーストを確認する。
5. 登録結果を確認する。

```powershell
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --verify-stage registered
```

2件の予定（ステータス1）、元・先・登録者・予定日の一致、担当者と過去データが引継前の状態であることを検証します。

次に、画面に指定した実施日で既存バッチを実行します。未来日でも `--batch-date` で検証できます。
バッチは**指定日に予定されている全法人**を処理するため、他の予定がない専用検証DBを使用してください。

```powershell
$env:DATABASE_URL = $env:TEST_DATABASE_URL
python -m cndx_corp_batch.entrypoints.sales_user_handover_batch --batch-date $handoverDate
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --verify-stage completed
```

完了確認では2件のステータス0と実施日時を確認します。担当者IDは先担当者に変わり、
担当者情報の組織IDは元のままであることが既存バッチの仕様です。
過去データ引継ぎをチェックした場合は8表が先組織へ、未チェックなら元組織のままであることを確認します。
検証に失敗した場合は理由を表示し、終了コードを非0にします。検証オプションはDBを更新しません。

チェックあり／なしの両方を試す場合は、以下の後片付け後に再投入して同じ手順を繰り返してください。

## 後片付け

投入時と同じ引数（IDを変更した場合はそのIDも）で実行します。

登録・バッチ実行後に同じ初期データへ戻す場合は `--reset` を使います。対象ユーザー・業務データ・引継予定を所有者とキーで確認し、削除と再投入を1トランザクションで行います。`--with-business-data`、`--start-id`、`--schedule-date`、`--create-organizations` などは投入時と同じ値を指定してください。

```powershell
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --reset
```

```powershell
python cndx_corp_back/test/prepare_handover_screen_data.py @seedArgs --cleanup
```

対象IDかつ作成者マーカーが一致する2名だけを削除します。
業務データなしの場合、担当者設定や引継予定に使用されていれば削除せず停止します。
`--with-business-data` を付けた場合、対象法人の業務データと今回の元・先・登録者・予定日に一致する
引継予定（完了済みも含む）を先に削除します。別の作成者の業務データや別条件の予定が混ざると停止します。
`--start-id`、`--schedule-date` も投入・登録時と同じ値を指定してください。
既存管理者と組織は残します。
組織も作成した場合は、削除時にも `--create-organizations` と同じ種別・IDを指定してください。
このPGが作成した組織のみ、担当者の削除後に削除します。DB内の組織ID列（`org_id`、
`*_org_id`）に参照が残っている場合は、担当者の削除も含めて取り消します。
オプションを省略して削除した場合は担当者のみ削除し、組織は残します。
