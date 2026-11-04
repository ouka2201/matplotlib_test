"""営業担当引継予定の問い合わせ。値は実行時にパラメータで渡す。"""

SELECT_ASSIGNED_COMPANIES = """
    SELECT DISTINCT corporate_number FROM db_corp.m_staff_info
    WHERE user_id = :from_user AND org_id = :from_org
      AND delete_flg = false ORDER BY corporate_number
"""

UPSERT_HANDOVER = """
    INSERT INTO db_corp.t_sales_user_handover_info AS h
        (corporate_number, handover_from_org_id, handover_from_user_id,
         handover_to_org_id, handover_to_user_id, handover_schedule_date,
         report_data_flg, handover_status, handover_type, creator_id,
         creator_org_id, insert_datetime, created_by, created_at)
    VALUES (:corporate_number, :from_org, :from_user, :to_org, :to_user,
            :schedule, :report_flg, :status, :type, :user_id, :org_id,
            CURRENT_TIMESTAMP, :user_id, CURRENT_TIMESTAMP)
    ON CONFLICT (corporate_number, handover_from_org_id, handover_from_user_id)
    DO UPDATE SET handover_to_org_id = EXCLUDED.handover_to_org_id,
        handover_to_user_id = EXCLUDED.handover_to_user_id,
        handover_schedule_date = EXCLUDED.handover_schedule_date,
        report_data_flg = EXCLUDED.report_data_flg,
        handover_type = EXCLUDED.handover_type,
        creator_id = EXCLUDED.creator_id,
        creator_org_id = EXCLUDED.creator_org_id,
        insert_datetime = CURRENT_TIMESTAMP,
        updated_by = :user_id, updated_at = CURRENT_TIMESTAMP
    WHERE h.handover_status = :status
    RETURNING corporate_number
"""

SELECT_PLANNED_COMPANIES = """
    SELECT corporate_number FROM db_corp.t_sales_user_handover_info
    WHERE handover_from_org_id = :from_org
      AND handover_from_user_id = :from_user AND handover_status = :status
"""

DELETE_PLANNED_HANDOVER = """
    DELETE FROM db_corp.t_sales_user_handover_info
    WHERE corporate_number = :corporate_number
      AND handover_from_org_id = :from_org
      AND handover_from_user_id = :from_user AND handover_status = :status
"""
