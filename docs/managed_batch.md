# 管理テーブルから取得して1件ずつ並列処理する

添付の「レポート作成対象情報取得」に対応する入口は`batch.py --from-management`です。対象ごとのジョブJSONを作る必要はありません。

## 実行

`REPORT_DATABASE_URL`に実DBの接続URLを設定し、`examples/database.json`のスキーマ・テーブル名を実環境へ合わせます。書体と90×89ピクセルの`assets/ICON.png`を用意してください。

```bash
python batch.py --from-management --report-month 2026-06 --db-config examples/database.json --output-dir output/reports
```

並列数は既定で利用可能なCPUコア数です。明示する場合は`--workers 4`などを指定します。Windowsでは最大61プロセスです。共通の注記等を変える場合は`--config common_config.json`を指定します。管理方式では名義・住所・お客さま番号・契約電力・対象月をDB取得値に置き換え、共通設定のサンプル値を使いません。

`--report-month`は必須です。`2026-06`と`202606`を受け付け、管理テーブルの`TARGET_YEAR_MONTH`を`202606`で検索します。取得するのは指定年月の`CREATE_STATUS IN ('2', '5')`だけです。対象ごとのジョブにはその検索年月を引き継ぎ、過去12か月の実績取得にも同じ年月を使います。1年未満の実績を扱う既存の処理も維持しています。

取得SQLは次の条件です（SQLAlchemyが値をバインドします）。

```sql
SELECT supply_point_number, company_id, syousapo_flg
FROM corp.t_power_report_mng_info
WHERE target_year_month = :report_ym
  AND create_status IN ('2', '5');
```

ご提示の`db.corp.t_power_report_mng_info`を「データベース`db`、スキーマ`corp`、テーブル`t_power_report_mng_info`」として設定しています。接続URLのDB名を`db`にし、`management_schema`を`corp`へ設定してください。`db_corp`というスキーマを指している場合は、`management_schema`を`db_corp`へ変更します。`examples/database.json`は管理スキーマだけ`corp`、その他のテーブルの共通`schema`は従来の`db_corp`です。全テーブルが`corp`にある場合は共通`schema`も`corp`へ合わせます。

## 処理の流れと編集場所

| 順序 | 処理 | 場所 |
| --- | --- | --- |
| 1 | 指定年月・状態2/5の3列をリストとして取得し、親のDB接続を閉じる | `ReportJobSource.fetch_targets()`、`load_managed_jobs()` |
| 2 | 各ワーカーでブラウザー・フォント・DBサービスを初期化する | `batch._init_worker()` |
| 3 | 取得した各レコードを1件ずつ投入する。投入中はワーカー数の2倍まで | `batch.run_jobs()` |
| 4 | 主キーごとの処理権を取得し、状態2へ更新する | `ReportJobSource.claim()` |
| 5 | ARVEの名義・住所・お客さま番号、EPの契約電力・日別48枠を取得する | `load_customer()`、既存の`DatabaseSource.load()` |
| 6 | matplotlib→BytesIOのPNG→Jinja2のHTML→PlaywrightのPDFをメモリでつなぐ | 既存の`ReportService.generate_database()` |
| 7 | 最終PDFを原子的に保存し、完了状態・ファイル情報を更新する | `save_pdf()`、`ReportJobSource.finish()` |

PDF名は次の規則で生成します。値は管理テーブルの`COMPANY_ID`、`SUPPLY_POINT_NUMBER`、`SYOUSAPO_FLG`、`TARGET_YEAR_MONTH`から取得します。

| 省サポ加入フラグ | PDF名 |
| --- | --- |
| False（未加入） | `企業ID_供給地点特定番号_YYYYMM.pdf` |
| True（加入） | `企業ID_供給地点特定番号_syousapo_YYYYMM.pdf` |

企業IDと供給地点は文字列のまま使用して先頭ゼロを保持します。企業IDが空欄・14文字超過・パス区切りを含む場合、または加入フラグがboolでない場合は、その1件を作成エラーにします。`batch.managed_report_filename()`に命名規則を集約しています。`FILE_NAME`・`FILE_PATH`にも実際の保存名を記録します。

添付に記載された共有フォルダーを使用する場合は、次のように保存先を指定します。

```bash
python batch.py --from-management --report-month 2026-06 --db-config examples/database.json --output-dir /bd-fs-mnt/TenantShare/corp/electricity_vis_middle/power_report
```

同じ供給地点でも対象月が違えば別ファイルになります。同一主キーの再作成時は、完成したPDFを保存してから既存ファイルと置き換えます。画像・HTMLの中間保存用ワークディレクトリは不要です。最終PDFを原子的に保存するための固有名の一時ファイルだけ作成し、保存後に削除します。

## 管理テーブルと状態

管理テーブル名は`t_power_report_mng_info`です。スキーマは`management_schema`を優先し、省略時は共通`schema`を使います。配布設定では`management_schema=corp`です。テーブル名は`management_table`で変更できます。大小文字を引用して作ったスキーマ・テーブルは、実DBの表記に合わせてください。物理列の大小文字は取得時に解決します。

主キーは`SUPPLY_POINT_NUMBER`と`TARGET_YEAR_MONTH`です。対象年月は`202606`のような6桁文字列で保存し、内部では`2026-06`に変換します。供給地点・お客さま番号の先頭ゼロを保持します。

| CREATE_STATUS | 既定の取得 | 処理 |
| --- | --- | --- |
| 1 | 対象外 | 今回のSQLでは取得しない |
| 2 | 対象 | 上流が登録した作成対象。処理権を取得して状態2のまま作成 |
| 3: 完了 | 対象外 | 保存済み |
| 4: 完了（警告） | 対象外 | 完了扱い。警告条件が未提示のため4を設定する処理は追加していない |
| 5: エラー | 対象 | 処理権を取得して2へ変更し、再試行 |

`pending_statuses`の既定値は`["2", "5"]`です。エラーを自動再試行しない運用では`["2"]`へ変更します。1・3・4は取得設定に指定できません。

状態2を取得対象に含めるため、2へのUPDATEだけでは二重着手を防げません。PostgreSQLでは「管理スキーマ・テーブル・供給地点・対象年月」ごとに`pg_try_advisory_lock`でセッションロックを取得し、状態を再確認してから処理します。他ワーカーが処理中なら待機せず`skipped`にします。別の供給地点・年月は並列に処理できます。ロックはPDF作成と状態更新が終わるまで同じ接続で保持し、正常・異常終了時に解放します。新しい列やロックテーブルは不要です。

ロック用に1接続をワーカー内で保持します。着手・完了の更新は短いトランザクションで確定し、描画中は更新トランザクションを開いたままにしません。ARVE・実績取得にはワーカー自身の別の接続を一時利用します。接続先はPostgreSQLへの直接接続、またはセッションを維持するプールを使用してください。トランザクション単位でバックエンドが変わるプールには対応しません。SQLiteはテスト用で、書込トランザクションを1件の処理終了まで保持するため、書込処理は直列になります。CPU数分のPDF処理の本番運用はPostgreSQLで行います。

成功時は`FILE_NAME`、`FILE_PATH`、`REPORT_CREATED_AT`、`UPDATED_BY`、`UPDATED_AT`を更新し、`ERROR_MESSAGE`をクリアします。パスは絶対パスとして255文字以内を要求します。失敗時は5に戻し、エラーを100文字以内で記録します。全体の`results.json`には切り詰め前のエラーを記録し、他の対象は継続します。監査列の日時は日本時間、更新者は`batch_user`（既定`electricity_report_batch`）です。

対象0件ではワーカーを起動せず正常終了し、`results.json`に空配列を保存します。1件でも失敗すればCLIの終了コードは1、それ以外は0です。処理中に追加された依頼は次回実行で取得します。

ワーカーが異常終了して2が残った場合は、ロック用のDBセッションが切断されれば処理権が解放され、次回実行の対象になります。再作成する場合は、運用で完了済み行を2へ戻してから対象年月を指定して再実行できます。このプログラムは管理行の削除や新規依頼の登録を行いません。

## ARVEの契約情報

既定のテーブルは`T_ARVE_CUSTOMER_INFO`です。`customer_table`で変更できます。供給地点を`CMN_SupplyPointSpecificNum__c`で照合し、`customer_filters`の条件も適用します。例の設定は業務種別`CMN_BusinessType__c = "2"`です。画像の受領時の抽出条件が実テーブルで適用済みなら、必要に応じて`customer_filters`を空辞書にできます。

| 帳票の項目 | 物理列 |
| --- | --- |
| お客さま番号 | `CMN_OldCustomerNum__c` |
| 契約住所 | `CMN_DemandLocationAddress__c` |
| 契約名義 | `customer_columns.customer_name`で指定 |

添付で名義列の末尾を確認できないため、架空の完全な列名は固定していません。設定を省略した場合は、`CMN_DemandLocationFullName_`で始まる列が1つだけ存在する場合に使用します。候補が0個または複数ならエラーにし、`customer_columns.customer_name`に実DBの物理列名を指定してもらいます。住所・お客さま番号も`customer_columns`で変更できます。契約情報の未登録・重複・空欄は、該当する1件の作成エラーにします。

管理テーブルの`COMPANY_ID`・`SYOUSAPO_FLG`も取得してワーカーの帳票設定へ渡します。フラグによる帳票内容の変更規則は提示されていないため、No.0〜No.7の描画内容には条件分岐を追加していません。ファイル名は上記の通り加入フラグで分岐します。

## 確認した範囲

SQLiteの管理・ARVE・契約・48枠テーブルで、指定年月の状態2/5だけの抽出、複合主キーごとの状態更新、1日実績の取得、失敗継続、対象0件、2プロセスの同時着手をテストしています。1000件の投入テストでは、PDFを生成せず1件ずつの投入・指定並列数・待機上限を確認しています。PostgreSQLのセッションロックはDB接続のテストダブルで取得・保持・解放・競合・解放失敗時の接続破棄を確認しています。本番DBへの接続、実サーバーでのロック競合、実行権限、1000件のPDF生成時間と最大メモリは実環境で確認してください。
