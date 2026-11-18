-- バッチ処理内容定義書 2：予定日・状態に加え、実行年月日01:00より前に登録された対象を取得する。
SELECT
    h.corporate_number,
    h.handover_from_org_id,
    h.handover_from_user_id,
    h.handover_to_org_id,
    h.handover_to_user_id,
    h.report_data_flg
FROM db_corp.t_sales_user_handover_info AS h
WHERE h.handover_status = :handover_status
  AND h.handover_schedule_date = :batch_date
  AND h.insert_datetime < :registration_cutoff
ORDER BY h.insert_datetime ASC NULLS LAST, h.updated_at ASC NULLS LAST
