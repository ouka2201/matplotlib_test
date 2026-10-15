-- 処理4／データ項目更新仕様説明書No.4：対象年月の状態2（作成中）・5（エラー）を取得する。
-- 設計書のソート説明は降順、掲載SQLはASC。本実装は掲載SQLに合わせて作成日時の昇順とする。
SELECT
  supply_point_number,
  company_id,
  syousapo_flg
FROM db_corp.t_power_report_mng_info as a
WHERE
  target_year_month = :report_ym
AND
  create_status in ('2','5')
ORDER BY a.created_at ASC;
