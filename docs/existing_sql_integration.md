# 既存バッチのSQL取得結果からPDFを作成する

画像の`CreatePowerReport.execute(row)`で取得した契約情報と日別48枠を、新しい`ReportService.generate_query_results()`へ渡せます。この入口はDBへの再接続・SQL実行を行いません。既存のget_session/load_sql_fileとSQLファイルを使用します。

## SELECT結果の列名

契約情報SQLには次の別名を付けてください。画像にはSQL本文がないため、実際の名義列等は決め打ちしていません。

| 取得項目 | SELECTの別名 | 型・単位 |
| --- | --- | --- |
| 契約名義 | `customer_name` | 空欄でない文字列 |
| 契約住所 | `address` | 空欄でない文字列 |
| お客さま番号 | `customer_number` | 先頭ゼロを保った文字列 |
| 契約電力 | `contract_kw` | kW。正の数値または数値文字列 |

日別SQLは`t01_get_ymd`と`t01_30t_syr01`〜48を取得します。日付はYYYYMMDD、48枠はkWhです。供給地点列をSELECTしない場合は検索した供給地点を補います。取得列名の大小文字は区別しません。供給地点列がある場合、他の地点の混入も検証します。

ASを変更しない場合は`customer_columns`で取得列名を指定できます。右側を実際のSELECT結果へ合わせてください。

```python
column_options = {
    "customer_columns": {
        "customer_name": "SQLで取得した名義列名",
        "address": "cmn_demandlocationaddress__c",
        "customer_number": "cmn_oldcustomernum__c",
        "contract_kw": "qsqb_dcis2_hvpw_ctrt",
    },
}
```

日付は`date_column`、枠は枠1〜48の順の48列を`slot_columns`で指定できます。品質件数検査は取得した列名を`quality_columns`へ渡すと有効になります。共通の注記・休日等は`config`へ辞書で渡します。

## 画像のSQL取得部分を変更する

セッション内で契約情報を`mappings().one()`、日別48枠を`mappings().all()`で取得し、辞書へ変換します。`first()`では最初の1日しか使用できません。ResultやセッションをPDFプロセスへ渡しません。

```python
with get_session() as session:
    sql_query = load_sql_file("select_power_report_cust.sql")
    report_cust = dict(session.execute(text(sql_query), params).mappings().one())

# boundsにはYYYY-MMで渡す。画像のstrftime("%Y%m")から変更する。
report_month = self.report_ym.strftime("%Y-%m")
start_date, end_date, _ = bounds(report_month)
params = {
    "supply_point_number": row.supply_point_number,
    "start_date": start_date.strftime("%Y%m%d"),
    "end_date": end_date.strftime("%Y%m%d"),
}
with get_session() as session:
    sql_query = load_sql_file("select_power_report_30min.sql")
    daily_rows = [
        dict(item)
        for item in session.execute(text(sql_query), params).mappings().all()
    ]
```

SQLの日付条件は`取得年月日 >= :start_date AND 取得年月日 < :end_date`です。終了日は対象月の翌月1日で、含めません。指定月を含む直近12か月の中で、実績の最初の日〜最後の日に毎日48枠あれば、1年未満でも処理できます。

単体で使用する場合は、同じプロセスで作ったReportServiceへ次のように渡し、終了時にcloseします。

```python
result = service.generate_query_results(
    customer_row=report_cust,
    daily_rows=daily_rows,
    supply_point=row.supply_point_number,
    report_month=report_month,
    output=Path("output/report.pdf").resolve(),
    # **column_options,  # 取得列の別名を変更していない場合
)
```

この単体呼び出しを画像のThreadPoolの各スレッドで並列に実行しないでください。現在のMatplotlib設定・Figure管理と同期Playwrightはプロセス専用です。PDF生成は下記のプロセスプールへ渡します。

## 既存の2つのJobクラスを維持する場合

`examples/existing_sql_batch.py`の`create_report_from_existing_sql()`は、上記2つのSQL取得とPDFプロセスへの受け渡しをまとめています。get_session/load_sql_fileのimportとBaseJobの初期化は既存のものを使用します。

```python
from examples.existing_sql_batch import create_report_from_existing_sql

def execute(self, row, pdf_pool):
    self.logger.info("%s レポート作成開始", row.supply_point_number)
    result = create_report_from_existing_sql(
        target=row,
        report_month=self.report_ym,
        get_session=get_session,
        load_sql_file=load_sql_file,
        pdf_pool=pdf_pool,
        output_dir="output/reports",
        # column_options=column_options,
    )
    self.logger.info("%s レポート作成完了", row.supply_point_number)
    return result
```

`GenerateAllPowerReportJob.execute`では既存ThreadPoolの外側にPDF用ProcessPoolを作り、`execute(row, pdf_pool)`へ渡します。対象リストは既存の管理SQLで指定年月・状態2/5を取得します。SELECT件数はrowcountではなく、取得したリストのlenを使用します。

```python
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing
from batch import cpu_workers
from services.query_result_worker import initialize_query_worker

def execute(self):
    # get_report_target_job側で、セッション内に全行を取得してください。
    targets = list(self.get_report_target_job.execute())
    if not targets:
        return []
    count = min(cpu_workers(), len(targets))
    results = []
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=initialize_query_worker,
        initargs=(None, None, None),
    ) as pdf_pool:
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = {
                executor.submit(self.create_report_job.execute, row, pdf_pool): row
                for row in targets
            }
            for future in as_completed(futures):
                row = futures[future]
                try:
                    results.append(future.result())
                except Exception:
                    self.logger.exception("%s レポート作成失敗", row.supply_point_number)
    return results
```

targetsを辞書で取得している場合、ログのrow.supply_point_numberはrow["supply_point_number"]へ合わせます。画像はRowの属性アクセスなので、その形で例を示しています。

Windowsの実行入口は`if __name__ == "__main__":`で囲みます。DBセッション・BaseJob・ロガー・Resultは子へ渡しません。PDFワーカーでReportServiceを一度だけ作り、複数件で再利用します。initargsは通常書体・Chromium・太字書体のパスの順です。WindowsではNoneでメイリオを検出し、別環境は書体のパスを指定してください。

## 関数だけで組み込む場合

次の関数はCPU数分のDB取得スレッドとPDF生成プロセスを作ります。各スレッドは1件のPDF終了まで待つため、全件の日別データを一括取得しません。1件の失敗を結果に記録し、他の対象を継続します。

```python
from examples.existing_sql_batch import run_existing_sql_batch

results = run_existing_sql_batch(
    targets=targets,
    report_month=self.report_ym,
    get_session=get_session,
    load_sql_file=load_sql_file,
    output_dir="output/reports",
    # workers=4,
    # column_options=column_options,
    # on_result=既存のログまたは管理状態更新関数,
)
```

on_resultは親で1件の完了結果を受け取る任意のコールバックです。status、supply_point_number、成功時のoutput/bytes、失敗時のerrorが得られます。get_sessionはスレッドごとに新しいセッションを返す関数にしてください。

PDF名は既存のmanaged_report_filenameを使い、未加入は`企業ID_供給地点特定番号_YYYYMM.pdf`、加入は`企業ID_供給地点特定番号_syousapo_YYYYMM.pdf`です。assets/ICON.png（90×89）と通常・太字のフォントを用意します。最終PDF以外の画像・HTMLは通常保存しません。

この既存SQL用の入口は管理状態の着手・更新やロックを実行しません。既存バッチの状態更新処理へ成功・失敗結果を渡してください。従来のbatch.py --from-managementは、引き続きReportJobSourceで処理権と状態更新を行う独立した入口です。

| ファイル | 役割 |
| --- | --- |
| services/report_service.py | generate_query_results。取得済み結果からPDFを生成 |
| services/query_result_service.py | 契約設定・timestamp/kwへの変換 |
| services/query_result_worker.py | PDFプロセスの初期化と1件の描画 |
| examples/existing_sql_batch.py | 既存関数を使う組み込み例 |
| tests/test_query_results.py | 列対応・換算・全日取得・終了日・失敗継続の検証 |

既存SQLファイル、BaseJob、get_session/load_sql_fileの本体は画像では提供されていないため同梱していません。実SQLのSELECT列名は標準のASまたは対応表へ合わせてください。
