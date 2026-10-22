-- 更新仕様No.3：移行完了・未紐付けで、有効な建物マスタがある管理行を取得する。
SELECT m.supply_point_number
FROM db_corp.t_30min_import_mng AS m
WHERE m.create_status = '3'
  AND m.target_year_month = :target_year_month
  AND m.linked_date IS NULL
  AND m.supply_point_number > :last_point
  AND EXISTS (
      SELECT 1 FROM db_corp.m_building AS b
      WHERE b.supply_point_number = m.supply_point_number
        AND b.delete_flg = FALSE
  )
ORDER BY m.supply_point_number
LIMIT :batch_size
FOR UPDATE OF m
