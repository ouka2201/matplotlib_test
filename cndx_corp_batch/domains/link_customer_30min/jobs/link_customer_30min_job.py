import getpass
from datetime import date

from sqlalchemy import bindparam, text

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import calc_offset_month, get_current_time, month_end
from cndx_corp_batch.jobs.base import BaseJob


class LinkCustomer30MinJob(BaseJob):
    """BLMMVMVBUILDING：取込済みの30分値をLecMocの顧客情報に紐付ける。"""

    def __init__(self, context, batch_date: date | None = None, batch_size: int = 1000):
        super().__init__(context)
        if batch_size <= 0:
            raise ValueError("取得件数は1以上を指定してください。")
        self.batch_size = batch_size
        # 更新仕様No.1・2：18日までは3か月前、19日以降は2か月前を対象とする。
        self.batch_date = batch_date or get_current_time().date()
        target = calc_offset_month(self.batch_date, 
            self.context.config.cut_off_day,
            self.context.config.report_month_offset_before,
            self.context.config.report_month_offset_after,).replace(day=1)
        self.params = {
            "target_year_month": target.strftime("%Y%m"),
            "start_date": target.strftime("%Y%m%d"),
            "end_date": month_end(target).strftime("%Y%m%d"),
            "executed_by": getpass.getuser(),
            "batch_size": batch_size,
        }
        self.select_targets = text(load_sql_file("select_customer_30min_targets.sql"))
        self.upsert_data = self._point_query("upsert_customer_30min.sql")
        self.update_linked = self._point_query("update_customer_30min_linked.sql")
        self.update_error = self._point_query("update_customer_30min_error.sql")

    @staticmethod
    def _point_query(filename):
        return text(load_sql_file(filename)).bindparams(
            bindparam("supply_points", expanding=True)
        )

    def execute(self):
        linked_count = 0
        last_point = ""
        page_number = 0
        while True:
            points = []
            try:
                # 処理2～4：取得した管理行をロックし、生データと紐付け日時をまとめて確定する。
                with get_session() as session:
                    params = {**self.params, "last_point": last_point}
                    points = session.execute(self.select_targets, params).scalars().all()
                    if not points:
                        break
                    page_number += 1
                    self.logger.info(
                        "30分値紐付けページ取得。ページ=%s 対象年月=%s "
                        "バッチサイズ=%s 取得件数=%s 先頭供給地点=%s 最終供給地点=%s",
                        page_number,
                        self.params["target_year_month"],
                        self.batch_size,
                        len(points),
                        points[0],
                        points[-1],
                    )
                    params.update(
                        supply_points=points,
                        current_time=get_current_time().replace(tzinfo=None),
                    )
                    linked = set(session.execute(self.upsert_data, params).scalars())
                    if linked:
                        session.execute(
                            self.update_linked,
                            {**params, "supply_points": sorted(linked)},
                        )
                linked_count += len(linked)
                # 結合先が不足する行は未紐付けのまま残し、同一実行内での再取得を避ける。
                last_point = points[-1]
                self.logger.info(
                    "30分値紐付け処理単位完了。単位番号=%s 取得件数=%s "
                    "紐付け件数=%s 保留件数=%s 累計紐付け件数=%s",
                    page_number,
                    len(points),
                    len(linked),
                    len(points) - len(linked),
                    linked_count,
                )
                if len(linked) != len(points):
                    self.logger.warning(
                        "結合先データがないため紐付けを保留しました。対象年月=%s 件数=%s",
                        self.params["target_year_month"], len(points) - len(linked),
                    )
            except Exception as exc:
                if points:
                    self._record_error(points, exc)
                # 処理内容定義書：例外発生時は後続処理を行わず終了する。
                raise
        self.logger.info(
            "顧客情報と30分値データの紐付け完了。ページ数=%s 紐付け件数=%s",
            page_number,
            linked_count,
        )
        return linked_count

    def _record_error(self, points, error):
        # 更新仕様No.6：登録処理をロールバックした後、エラー情報だけを別途確定する。
        try:
            with get_session() as session:
                session.execute(
                    self.update_error,
                    {
                        **self.params,
                        "supply_points": points,
                        "error_message": str(error)[:100],
                        "current_time": get_current_time().replace(tzinfo=None),
                    },
                )
        except Exception:
            self.logger.exception("30分値取込管理への紐付けエラーの記録に失敗しました。")

import getpass
from datetime import date

from sqlalchemy import bindparam, text

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import calc_offset_month, get_current_time, month_end
from cndx_corp_batch.jobs.base import BaseJob


class LinkCustomer30MinJob(BaseJob):
    """BLMMVMVBUILDING：取込済みの30分値をLecMocの顧客情報に紐付ける。"""

    def __init__(self, context, batch_date: date | None = None, batch_size: int = 1000):
        super().__init__(context)
        if batch_size <= 0:
            raise ValueError("取得件数は1以上を指定してください。")
        self.batch_size = batch_size
        # 更新仕様No.1・2：18日までは3か月前、19日以降は2か月前を対象とする。
        self.batch_date = batch_date or get_current_time().date()
        target = calc_offset_month(self.batch_date, 19, 3, 2).replace(day=1)
        self.params = {
            "target_year_month": target.strftime("%Y%m"),
            "start_date": target.strftime("%Y%m%d"),
            "end_date": month_end(target).strftime("%Y%m%d"),
            "executed_by": getpass.getuser(),
            "batch_size": batch_size,
        }
        self.select_targets = text(load_sql_file("select_customer_30min_targets.sql"))
        self.upsert_data = self._point_query("upsert_customer_30min.sql")
        self.update_linked = self._point_query("update_customer_30min_linked.sql")
        self.update_error = self._point_query("update_customer_30min_error.sql")

    @staticmethod
    def _point_query(filename):
        return text(load_sql_file(filename)).bindparams(
            bindparam("supply_points", expanding=True)
        )

    def execute(self):
        linked_count = 0
        last_point = ""
        while True:
            points = []
            try:
                # 処理2～4：取得した管理行をロックし、生データと紐付け日時をまとめて確定する。
                with get_session() as session:
                    params = {**self.params, "last_point": last_point}
                    points = session.execute(self.select_targets, params).scalars().all()
                    if not points:
                        break
                    params.update(
                        supply_points=points,
                        current_time=get_current_time().replace(tzinfo=None),
                    )
                    linked = set(session.execute(self.upsert_data, params).scalars())
                    if linked:
                        session.execute(
                            self.update_linked,
                            {**params, "supply_points": sorted(linked)},
                        )
                linked_count += len(linked)
                # 結合先が不足する行は未紐付けのまま残し、同一実行内での再取得を避ける。
                last_point = points[-1]
                if len(linked) != len(points):
                    self.logger.warning(
                        "結合先データがないため紐付けを保留しました。対象年月=%s 件数=%s",
                        self.params["target_year_month"], len(points) - len(linked),
                    )
            except Exception as exc:
                if points:
                    self._record_error(points, exc)
                # 処理内容定義書：例外発生時は後続処理を行わず終了する。
                raise
        self.logger.info("顧客情報と30分値データの紐付け完了。件数=%s", linked_count)
        return linked_count

    def _record_error(self, points, error):
        # 更新仕様No.6：登録処理をロールバックした後、エラー情報だけを別途確定する。
        try:
            with get_session() as session:
                session.execute(
                    self.update_error,
                    {
                        **self.params,
                        "supply_points": points,
                        "error_message": str(error)[:100],
                        "current_time": get_current_time().replace(tzinfo=None),
                    },
                )
        except Exception:
            self.logger.exception("30分値取込管理への紐付けエラーの記録に失敗しました。")
