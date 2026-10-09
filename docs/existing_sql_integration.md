# 既存バッチへの組み込み

入口は`services.batch_service.run_reports()`です。既存の対象取得、get_session、load_sql_fileを使い、1件のSQL取得からPDF保存までを同じ子プロセスで行います。ThreadPoolとPDF用ProcessPoolを組み合わせる処理は不要になりました。

## Jobクラスからの呼び出し

画像のGenerateAllPowerReportJob.executeで、取得した対象リストを渡します。個別Jobへプールを渡す処理は不要です。

```python
from services.batch_service import run_reports

def execute(self):
    targets = list(self.get_report_target_job.execute())
    return run_reports(
        targets=targets,
        report_month=self.create_report_job.report_ym,
        get_session=get_session,
        load_sql_file=load_sql_file,
        output_dir="output/reports",
    )
```

get_report_target_job側は、セッション内で全行を取得して返してください。SELECT件数はrowcountではなくlen(targets)を使います。対象行は辞書、RowMapping、SQLAlchemy Rowを受け付けます。

```sql
SELECT supply_point_number, company_id, syousapo_flg
FROM corp.t_power_report_mng_info
WHERE target_year_month = :report_ym
  AND create_status IN ('2', '5');
```

targetsと指定年月は親で取得し、ワーカーには軽い対象行だけを渡します。日別データ・画像・PDFをプロセス間で渡しません。run_reportsにはYYYY-MM/ YYYYMM/日付を指定でき、内部ではYYYY-MMへ揃えます。

get_sessionとload_sql_fileはモジュール直下で定義された関数を渡します。lambda、ローカル関数、DBセッションやBaseJobのオブジェクトは渡しません。get_sessionは子プロセス内でも接続設定を準備し、新規セッションを返す関数にしてください。親で初期化した接続を子へ引き継ぐ設計は使いません。Windowsの呼び出し入口は`if __name__ == "__main__":`で囲みます。

## 使用する2つのSQL

ワーカーは画像と同じファイル名を使用します。

| SQLファイル | バインドする値 | 取得する結果 |
| --- | --- | --- |
| select_power_report_cust.sql | supply_point_number | 契約情報1行 |
| select_power_report_30min.sql | supply_point_number、start_date、end_date | 全日分の日付+48枠 |

契約情報SQLは次の別名で取得してください。ASを使うと列対応の設定が不要です。

| 項目 | SELECTの別名 | 型・単位 |
| --- | --- | --- |
| 契約名義 | customer_name | 文字列 |
| 契約住所 | address | 文字列 |
| お客さま番号 | customer_number | 先頭ゼロを保った文字列 |
| 契約電力 | contract_kw | kWの数値または数値文字列 |

日別SQLはt01_get_ymdとt01_30t_syr01〜48を取得します。日付はYYYYMMDD、48枠はkWhです。列名の大小文字は区別しません。供給地点列は省略できます。

日付条件は`取得年月日 >= :start_date AND 取得年月日 < :end_date`です。終了日は対象月の翌月1日で含めません。ワーカーはセッション内でmappings().one()/all()を使い、全行を取り出してからPDFを作ります。first()で1日だけ取得する処理は不要です。

ASを変更できない場合だけ、任意のcolumn_optionsを指定します。

```python
column_options = {
    "customer_columns": {
        "customer_name": "実際の名義列名",
        "address": "cmn_demandlocationaddress__c",
        "customer_number": "cmn_oldcustomernum__c",
        "contract_kw": "qsqb_dcis2_hvpw_ctrt",
    },
}
# run_reports(..., column_options=column_options)
```

日付・枠にも別名がある場合はdate_column/slot_columnsを使用できます。取得済み品質件数列はquality_columns、注記や休日はconfigで渡せます。通常は標準の列名だけで使用してください。

## 結果と状態更新

結果は完了順のリストです。各行にstatusとsupply_point_number、成功時にoutput/bytes、失敗時にerrorを返します。対象0件ではプロセスを起動せず空リストを返します。1件の失敗後も他の対象を続けます。

既存の状態更新処理は、run_reportsのon_resultへ結果を受け取る関数として渡せます。この関数は親で呼び出します。run_reports自身は管理テーブルへの着手・更新やロックを行いません。管理処理を本プログラムに任せる場合は、既存のbatch.py --from-managementを使用します。

PDF名は未加入が`企業ID_供給地点特定番号_YYYYMM.pdf`、加入が`企業ID_供給地点特定番号_syousapo_YYYYMM.pdf`です。assets/ICON.png（90×89）とメイリオを用意してください。別環境の書体はfont/bold_font、並列数はworkersで指定できます。

旧examples/existing_sql_batch.pyとservices/query_result_worker.pyは削除し、処理をservices/batch_service.pyへまとめました。旧run_existing_sql_batchの呼び出しはrun_reportsへ変更してください。取得済みデータを1件だけ渡すgenerate_query_resultsは引き続き使用できます。

既存SQL・BaseJob・get_session/load_sql_fileの本体は画像だけなので同梱していません。SELECTの実列名はASまたは対応表へ合わせてください。
