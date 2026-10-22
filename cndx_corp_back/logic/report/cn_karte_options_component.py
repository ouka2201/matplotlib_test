# cndx_corp_back/logic/report/cn_karte_options_component.py
import os
import traceback
from collections import Counter

from entity.t_cn_application_info_entity import TCnApplicationInfo
from flask import abort, current_app
from sqlalchemy import String, case, cast, exists, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class CnKarteOptionsComponent:
    @component
    def execute(
        self,
        corporate_number: str,
        org_id: str,
        agreement_category,
        user_context,
        logger=None,
    ) -> dict:
        """
        CNカルテ画面 初期表示用オプション取得コンポーネント

        変更ポイント（重要）:
        - グループ定義は  (agreement_category, group_id)  をキーにして保持する
        - 各建物の group1..group5 の「数値」は、該当 group_id の select_item<数値> を意味する
          （例）group1=3 なら、 (AC, group_id=1) の select_item3 をラベルとして表示
        - 以前の実装のように「数値」を group_id と誤解しないこと
        """
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"{os.path.basename(__file__)} execute 開始 法人番号={corporate_number}, 組織ID={org_id}"
        )

        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")
        role_id = user_context.get("role")
        user_id = user_context.get("user_id")

        is_ep = org_type_code == "01"
        is_rep = org_type_code == "04"
        is_vis = org_type_code == "06"

        # REP、TCSログインの場合
        if login_org_id != "TEP" and org_id == "TEP":
            org_id = login_org_id

        vis_category_dict = {
            "TEP": "11",
            "ASE": "12",
            "ZRB": "13",
            "JFS": "14",
        }
        with get_scoped_session() as session:
            # ------------------------------------------------------------------
            # 1) レポート開始年・月（画面の期間選択用）
            # ------------------------------------------------------------------
            stmt = (
                session.query(TMonthlyBuildingEnergyAggregation.target_year_month)
                .filter(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    # TMonthlyBuildingEnergyAggregation.agreement_category == vis_category_dict.get(org_id),
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    # TMonthlyBuildingEnergyAggregation.org_id.in_([org_id,login_org_id]),
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                )
                .distinct()
            )

            # print(
            #     stmt.statement.compile(
            #         dialect=session.connection().dialect,
            #         compile_kwargs={"literal_binds": True},
            #     )
            # )

            start_year_months = stmt.all()

            if not start_year_months:
                abort(400, description="対象エネルギー情報は登録されていません")

            start＿year＿month = sorted(
                {str(row) for row in start_year_months if row[0]}
            )
            end_year_month = max(row[0] for row in start_year_months)

            # ------------------------------------------------------------------
            # 2) グループマスタ取得
            #    キー: (agreement_category, group_id)
            #    値  : {
            #            "group_name": ...,
            #            "options": [select_item1..7],
            #            "options_map": {"1": select_item1, ... "7": select_item7}
            #          }
            #    ※ 企業・契約区分ごとに項目が異なるため、agreement_category を必ずキーに含める
            # ------------------------------------------------------------------
            group_def_map: dict[tuple[str, str], dict] = {}
            group_entities = (
                session.query(MBuildingGroup)
                .filter(
                    MBuildingGroup.corporate_number == corporate_number,
                    # MBuildingGroup.org_id == org_id,
                    MBuildingGroup.delete_flg.is_not(True),
                )
                .all()
            )
            for g in group_entities:
                opts = [
                    g.select_item1,
                    g.select_item2,
                    g.select_item3,
                    g.select_item4,
                    g.select_item5,
                    g.select_item6,
                    g.select_item7,
                ]
                options = [v for v in opts if v]  # None を除去
                options_map = {str(i + 1): v for i, v in enumerate(opts) if v}

                key = (str(g.agreement_category), str(g.group_id))
                group_def_map[key] = {
                    "group_name": g.group_name,
                    "options": options,
                    "options_map": options_map,
                }

            # デバッグ：取得した定義の件数を出力
            try:
                logger.debug(
                    f"[Options] group_def_map count={len(group_def_map)} "
                    f"sample_keys={list(group_def_map.keys())[:5]}"
                )
            except Exception:
                pass
        try:
            # ------------------------------------------------------------------
            # 3) 建物一覧（エリア/用途などのラベル化に agreement_category を使用）
            # ------------------------------------------------------------------
            # subq = (
            #     session.query(
            #         TMonthlyBuildingEnergyAggregation.building_id.label("b_id"),
            #         func.string_agg(
            #             func.distinct(
            #                 cast(TMonthlyBuildingEnergyAggregation.fiscal_year, String)
            #             ),
            #             ","
            #         ).label("fiscal_years")
            #     )
            #     .filter(
            #         TMonthlyBuildingEnergyAggregation.corporate_number == corporate_number,
            #     )
            #     .group_by(TMonthlyBuildingEnergyAggregation.building_id)
            # ).subquery()

            subq = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id.label("b_id"),
                    TMonthlyBuildingEnergyAggregation.org_id,
                    func.string_agg(
                        func.distinct(
                            cast(
                                TMonthlyBuildingEnergyAggregation.target_year_month,
                                String,
                            )
                        ),
                        ",",
                    ).label("target_year_months"),
                )
                .filter(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                )
            ).subquery()

            query = (
                session.query(
                    MBuilding.building_id,
                    MBuilding.building_name,
                    MBuilding.location_identifier_name,
                    MBuilding.group1,
                    MBuilding.group2,
                    MBuilding.group3,
                    MBuilding.group4,
                    MBuilding.group5,
                    MBuilding.agreement_category,
                    MBuilding.agreement_org,
                    subq.c.org_id,
                    subq.c.target_year_months,
                )
                .join(subq, subq.c.b_id == MBuilding.building_id)
                .filter(
                    MBuilding.corporate_number == corporate_number,
                    MBuilding.agreement_category == agreement_category,
                    MBuilding.delete_flg.is_not(True),
                )
            )

            building_rows = query.all()

            # 利用されている契約区分の中から「最頻値」を 画面の group_options 用に採用
            # （同一組織で契約区分が複数混在する場合の表示一貫性のため）
            ac_list = [
                str(r.agreement_category)
                for r in building_rows
                if r.agreement_category is not None
            ]
            agreement_category_for_options = None
            # if ac_list:
            #     agreement_category_for_options = Counter(ac_list).most_common(1)[0][
            #         0
            #     ]
            if ac_list:
                # Counterの代わりにsetを使って重複を削除
                agreement_category_for_options = list(set(ac_list))

            # 建物行ごとに group1..5 をラベル化
            building_list: list[dict] = []

            def to_label(ac: str | None, grp_index: int, value) -> str:
                """
                指定の契約区分 ac について、group<grp_index> の "value"(1..7) を select_item にマッピング
                ac / 定義が見つからない / value が不正なら "-".
                """
                if value in (None, "", 0):
                    return "-"
                if ac is None:
                    return "-"
                key = (str(ac), str(grp_index))
                definition = group_def_map.get(key)
                if not definition:
                    # 定義未登録（契約区分や group_id が存在しない）
                    return "-"
                return definition["options_map"].get(str(value), "-")

            for row in building_rows:
                row_dict = {
                    "building_id": row.building_id,
                    "building_name": row.building_name,
                    "location_identifier_name": row.location_identifier_name,
                    "agreement_category": row.agreement_category,
                    "agreement_org": row.agreement_org,
                    "target_year_months": row.target_year_months,
                    "org_id": row.org_id,
                }
                # group1..5 を順にラベル化
                values = [
                    row.group1,
                    row.group2,
                    row.group3,
                    row.group4,
                    row.group5,
                ]
                for idx, v in enumerate(values, start=1):
                    row_dict[f"group{idx}"] = to_label(row.agreement_category, idx, v)
                building_list.append(row_dict)

            # ------------------------------------------------------------------
            # 4) 画面上部のグループ選択肢（group_options）
            #    ※ 複数の契約区分が混在する場合は「最頻値」の契約区分を代表で返す
            # ------------------------------------------------------------------
            group_options: dict[str, dict] = {}
            if agreement_category_for_options is not None:
                for ac in agreement_category_for_options:
                    for group_id in range(1, 6):
                        key = (str(ac), str(group_id))
                        definition = group_def_map.get(key)
                        if definition:
                            # acとgroup_idを組み合わせたユニークなキーを作成
                            group_key = f"ac{ac}_group{group_id}"
                            group_options[group_key] = {
                                "agreement_category": ac,
                                "group_no": group_id,
                                "group_name": definition["group_name"],
                                "options": definition["options_map"],
                            }

            # ------------------------------------------------------------------
            # 5) 組織名一覧
            # ------------------------------------------------------------------
            # tcn_query = session.query(
            #     TCnApplicationInfo.org_id,
            # ).filter(
            #     TCnApplicationInfo.corporate_number == corporate_number,
            # )

            # if login_org_id != "TEP":
            #     tcn_query = tcn_query.filter(
            #         TCnApplicationInfo.org_id == login_org_id
            #     )

            # tcn_rows = tcn_query.distinct().all()
            # # org_ids = {row.org_id for row in tcn_rows}
            # org_ids = {
            #     "TEP" if row.org_id.startswith("REP") else row.org_id
            #     for row in tcn_rows
            # }

            # org_entities = (
            #     session.query(
            #         MUserOrganizationInfo.org_id, MUserOrganizationInfo.org_name
            #     ).filter(
            #         MUserOrganizationInfo.org_id.in_(org_ids),
            #         # MUserOrganizationInfo.org_id == login_org_id,
            #         MUserOrganizationInfo.delete_flg.is_not(True),
            #     )
            #     .all()
            # )

            # REP → TEP 変換式
            # normalized_org_id = case(
            #     (
            #         TCnApplicationInfo.org_id.startswith("REP"),
            #         "TEP"
            #     ),
            #     else_=TCnApplicationInfo.org_id
            # )

            query = (
                session.query(
                    TCnApplicationInfo.org_id,
                    MUserOrganizationInfo.org_name,
                    TCnApplicationInfo.agreement_category,
                )
                .join(
                    MUserOrganizationInfo,
                    MUserOrganizationInfo.org_id == TCnApplicationInfo.org_id,
                )
                .filter(
                    TCnApplicationInfo.corporate_number == corporate_number,
                    TCnApplicationInfo.agreement_category == agreement_category,
                    MUserOrganizationInfo.delete_flg.is_not(True),
                )
            )

            if login_org_id != "TEP" and not login_org_id.startswith("TCS"):
                query = query.filter(TCnApplicationInfo.org_id == login_org_id)

            org_entities = query.distinct().all()

            org_names = [
                {
                    "org_id": r.org_id,
                    "org_name": r.org_name,
                    "agreement_category": r.agreement_category,
                }
                for r in org_entities
            ]

            logger.info(f"{os.path.basename(__file__)} execute 正常終了")
            return {
                "start_year_months": start_year_month,
                "end_year_month": end_year_month,
                "group_options": group_options,  # 代表となる契約区分の定義
                "building_list": building_list,  # 各建物はラベル化済み
                "org_names": org_names,
            }

        except Exception:
            logger.error("CNカルテ初期表示用選択肢取得失敗\n" + traceback.format_exc())
            abort(500)
