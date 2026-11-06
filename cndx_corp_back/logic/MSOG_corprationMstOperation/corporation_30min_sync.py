"""企業基本情報登録時に建物の変更を 30 分値データへ反映する。"""

from datetime import datetime

from sqlalchemy import text

from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_electricity_data_30min_entity import TElectricityData30min
from cndx_corp_back.query.corporation_30min_query import INSERT_CORPORATION_30MIN


class Corporation30minSync:
    """変更された建物に対応する 30 分値データを同期する。"""

    @staticmethod
    def _key(building):
        """建物から 30 分値データの検索に使う識別子を取り出す。

        Args:
            building: 対象の建物。

        Returns:
            法人番号、契約区分、組織 ID、建物 ID を含む辞書。
        """
        return {
            "corporate_number": building.corporate_number,
            "agreement_category": building.agreement_category,
            "org_id": building.org_id,
            "building_id": building.building_id,
        }

    @classmethod
    def snapshot(cls, buildings):
        """更新前の建物 ID と供給地点番号、削除状態を保存する。

        Args:
            buildings: 更新前の建物の一覧。

        Returns:
            各建物と、更新前の識別子・供給地点番号・削除状態の辞書。
        """
        # 既存処理が主キーを変更する場合も、変更前のキーで生データを削除できるようにする。
        return [
            (
                building,
                cls._key(building),
                building.supply_point_number,
                building.delete_flg,
            )
            for building in buildings
        ]

    def execute(self, session, buildings_before, corporate_number, user_id):
        """建物の変更に合わせて 30 分値データを削除・登録する。

        削除された建物のデータは削除する。供給地点番号や識別子が変わった
        建物のデータは登録し直し、新しく登録された建物のデータも作成する。

        Args:
            session: 建物の更新と同じトランザクションで使うセッション。
            buildings_before: 更新前の建物情報を保存した一覧。
            corporate_number: 対象企業の法人番号。
            user_id: 登録者のユーザー ID。
        """
        to_insert = []
        for building, old_key, old_point, was_deleted in buildings_before:
            new_key = self._key(building)
            new_point = building.supply_point_number
            if building.delete_flg:
                if not was_deleted:
                    self._delete(session, old_key, [old_point])
            elif was_deleted or old_point != new_point or old_key != new_key:
                # 更新仕様No.10：対象拠点の変更前・変更後の供給地点番号を削除する。
                self._delete(session, old_key, [old_point, new_point])
                if old_key != new_key:
                    self._delete(session, new_key, [old_point, new_point])
                to_insert.append((building, False))

        # autoflush後の結果から新規登録された建物を取得する。vis_flg等の既存分岐に従う。
        existing = {building for building, *_ in buildings_before}
        buildings_after = (
            session.query(MBuilding).filter_by(corporate_number=corporate_number).all()
        )
        to_insert.extend(
            (building, True)
            for building in buildings_after
            if building not in existing and not building.delete_flg
        )
        for building, is_new in to_insert:
            if building.supply_point_number:
                self._insert(session, building, user_id, is_new)

    @staticmethod
    def _delete(session, key, supply_points):
        """指定した建物と供給地点番号に対応する 30 分値データを削除する。

        Args:
            session: 削除に使うデータベースセッション。
            key: 建物を特定する法人番号、契約区分、組織 ID、建物 ID。
            supply_points: 削除対象の供給地点番号。空の値は除外する。
        """
        points = {point for point in supply_points if point}
        if points:
            session.query(TElectricityData30min).filter(
                TElectricityData30min.corp_number == key["corporate_number"],
                TElectricityData30min.agreement_category == key["agreement_category"],
                TElectricityData30min.org_id == key["org_id"],
                TElectricityData30min.building_id == key["building_id"],
                TElectricityData30min.supply_point_number.in_(points),
            ).delete(synchronize_session=False)

    def _insert(self, session, building, user_id, is_new):
        """EP・ARVE データを結合し、建物の 30 分値データを登録する。

        新規建物は直近 5 年分、既存建物の変更時は期間を限定せず登録する。

        Args:
            session: 登録に使うデータベースセッション。
            building: 登録対象の建物。
            user_id: 登録者のユーザー ID。
            is_new: 新規建物なら ``True``。
        """
        # 更新仕様No.7は直近5年、No.11（供給地点変更）は期間制限なし。
        history_filter = ""
        if is_new:
            history_filter = """
                AND e.t01_get_ymd BETWEEN
                    to_char(CURRENT_DATE - INTERVAL '5 years', 'YYYYMMDD')
                    AND to_char(CURRENT_DATE, 'YYYYMMDD')
            """
        session.execute(
            text(INSERT_CORPORATION_30MIN + history_filter),
            {**self._key(building), "user_id": user_id, "current_time": datetime.now()},
        )
