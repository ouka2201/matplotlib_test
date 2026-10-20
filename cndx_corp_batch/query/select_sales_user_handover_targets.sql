-- バッチ処理内容定義書 2：本日が引継実施予定日で、引継実施ステータスが「予定」の対象を取得する。
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
ORDER BY h.insert_datetime ASC NULLS LAST, h.updated_at ASC NULLS LAST
