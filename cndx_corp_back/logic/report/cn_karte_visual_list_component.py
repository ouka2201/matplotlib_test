# cndx_corp_back/logic/report/cn_karte_visual_list_component.py
import os
import traceback

import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_

from cndx_corp_back.common.constants_values import ReportStatus, ReportTypeValue
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_consent_route_info_entity import MConsentRouteInfo
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_cn_ranking_snapshot import TCnRankingSnapshot
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo


class CnKarteVisualListComponent:
    @component
    def execute(self, request_dict: dict, user_context, logger=None) -> list:
        """
        CNカルテ可視化一覧取得
        - 企業全体 / グループ / 単拠点 の3パターンに対応
        - グループ選択時はフロントエンドの選択（例：「関東」等）を優先表示
        - group1..group5 の“番号（1～7）→ラベル”変換を行い、group*_label を付与
        - 同意書名は T 側の契約区分で結合し、Building 側が無い場合でも欠損を減らす
        """
        if logger is None:
            logger = current_app.logger

        corporate_number = request_dict.get("corporate_number")
        org_id = request_dict.get("org_id")
        agreement_category = request_dict.get("agreement_category")
        login_org_id = user_context.get("org_id")
        logger.info(
            f"{os.path.basename(__file__)} execute 開始 法人番号={corporate_number}, 組織ID={org_id}"
        )

        try:
            # --- フロントエンドで選択したグループ値（グループ作成時の表示用）
            # 例: {"group1": "関東", "group2": "工場", ...}
            group_selected_values = request_dict.get("group_selected_values", {})

            # --- 番号の軽量正規化（"０１" / "01" / " 1 " → "1"）
            #     ・全角→半角
            #     ・前後スペース除去
            #     ・数字のみなら先頭ゼロを除去
            trans_table = str.maketrans("０１２３４５６７８９", "0123456789")

            def _normalize_num_like(val: object) -> tuple[str, bool]:
                """
                値を文字列化して軽量正規化する。
                戻り値: (正規化後文字列, is_digit)
                """
                s = "" if val is None else str(val)
                s = s.strip().translate(trans_table)
                if s.isdigit():
                    s_norm = s.lstrip("0") or "0"
                    return s_norm, True
                return s, False

            with get_scoped_session() as session:
                # ------------------------------------------------------------------
                # グループマスタ取得
                #   key = (agreement_category, group_id)
                #   value = {'1': select_item1, ..., '7': select_item7}
                #   企業毎・契約区分毎に選択肢の中身が異なるため、agreement_category をキーに含める
                # ------------------------------------------------------------------
                group_items = (
                    session.query(MBuildingGroup)
                    .filter(
                        MBuildingGroup.corporate_number == corporate_number,
                        MBuildingGroup.org_id == org_id,
                        MBuildingGroup.agreement_category == agreement_category,
                        MBuildingGroup.delete_flg.is_not(True),
                    )
                    .all()
                )

                group_mapping: dict[tuple[str, str], dict[str, str]] = {}
                for item in group_items:
                    select_map = {}
                    for i in range(1, 8):
                        label = getattr(item, f"select_item{i}")
                        if label:
                            select_map[str(i)] = label
                    key = (str(item.agreement_category), str(item.group_id))
                    group_mapping[key] = select_map

                try:
                    logger.debug(
                        f"[CnKarteVisualList] group_mapping keys(sample)={list(group_mapping.keys())[:5]}, total={len(group_mapping)}"
                    )
                except Exception:
                    pass

                # ------------------------------------------------------------------
                # レポート + 建物 JOIN（可視化一覧のベースデータ）
                # 重要ポイント：
                #  - MBuilding は LEFT OUTER JOIN（仮想拠点漏れ/歴史データを許容）
                #  - 同意書名称 / 組織名は T 側キーで外部結合（NULL を減らす）
                #  - 契約区分は Building 側（優先）と T 側（フォールバック）を両方持つ
                # ------------------------------------------------------------------

                stmt = (
                    session.query(
                        TReportStorageInfo.corporate_number,
                        TCnApplicationInfo.company_name,
                        TReportStorageInfo.org_id,
                        TReportStorageInfo.report_selection_period_from,
                        TReportStorageInfo.format_type,  # ★ コード or ラベル
                        TReportStorageInfo.site_selection_type,  # ★ コード or ラベル
                        TReportStorageInfo.creation_id,
                        TReportStorageInfo.building_id,
                        # TReportStorageInfo.agreement_category,
                        TReportStorageInfo.fiscal_year,
                        MBuilding.building_name,
                        MBuilding.location_identifier_name,
                        # 建物側のグループ値（仮想拠点に格納された番号が入る想定）
                        TReportStorageInfo.group1,
                        TReportStorageInfo.group2,
                        TReportStorageInfo.group3,
                        TReportStorageInfo.group4,
                        TReportStorageInfo.group5,
                        # 契約区分（B 側優先 / T 側はフォールバック用）
                        # MBuilding.agreement_category.label("agreement_category_b"),
                        TReportStorageInfo.agreement_category.label(
                            "agreement_category_t"
                        ),
                        # 名称は T 側キーで外部結合
                        MConsentRouteInfo.agreement_name,
                        MUserOrganizationInfo.org_name,
                        TReportStorageInfo.report_classify,
                        TReportStorageInfo.report_save_path,
                        TReportStorageInfo.report_status,
                        TReportStorageInfo.report_created_at,
                        TReportStorageInfo.report_created_by,
                    )
                    .outerjoin(  # ★ T 側契約区分で同意書名を結合
                        MConsentRouteInfo,
                        TReportStorageInfo.agreement_category
                        == MConsentRouteInfo.agreement_category,
                    )
                    .outerjoin(
                        TCnApplicationInfo,
                        and_(
                            TCnApplicationInfo.corporate_number
                            == TReportStorageInfo.corporate_number,
                            TCnApplicationInfo.agreement_category
                            == TReportStorageInfo.agreement_category,
                            TCnApplicationInfo.org_id == TReportStorageInfo.org_id,
                            TCnApplicationInfo.fiscal_year
                            == TReportStorageInfo.fiscal_year,
                            TCnApplicationInfo.registration_seq
                            == TReportStorageInfo.registration_seq,
                        ),
                    )
                    .outerjoin(
                        TCnRankingSnapshot,
                        and_(
                            TCnRankingSnapshot.creation_id
                            == TReportStorageInfo.creation_id
                        ),
                    )
                    .outerjoin(  # ★ T 側 org_id で組織名を結合
                        MUserOrganizationInfo,
                        MUserOrganizationInfo.org_id == TCnRankingSnapshot.org_id,
                    )
                    .outerjoin(  # ★ T 側 org_id で組織名を結合
                        MBuilding,
                        and_(
                            # MBuilding.agreement_org == TReportStorageInfo.org_id,
                            MBuilding.agreement_category
                            == TReportStorageInfo.agreement_category,
                            MBuilding.corporate_number
                            == TReportStorageInfo.corporate_number,
                            MBuilding.building_id == TReportStorageInfo.building_id,
                            MBuilding.delete_flg.is_(False),
                        ),
                    )
                    .filter(
                        TReportStorageInfo.corporate_number == corporate_number,
                        # TReportStorageInfo.org_id.in_([org_id, login_org_id]),
                        TReportStorageInfo.agreement_category == agreement_category,
                        TReportStorageInfo.delete_flg.is_not(True),
                        TReportStorageInfo.registration_seq == 0,
                    )
                )

                stmt_queue = session.query(
                    TReportStorageInfo.corporate_number,
                    TReportStorageInfo.org_id,
                    TReportStorageInfo.fiscal_year,
                    TReportStorageInfo.creation_id,
                    # 建物側のグループ値（仮想拠点に格納された番号が入る想定）
                    TReportStorageInfo.group1,
                    TReportStorageInfo.group2,
                    TReportStorageInfo.group3,
                    TReportStorageInfo.group4,
                    TReportStorageInfo.group5,
                    # 契約区分（B 側優先 / T 側はフォールバック用）
                    # MBuilding.agreement_category.label("agreement_category_b"),
                    TReportStorageInfo.agreement_category.label("agreement_category_t"),
                    TReportStorageInfo.report_classify,
                    TReportStorageInfo.report_save_path,
                    TReportStorageInfo.report_status,
                    TReportStorageInfo.report_created_at,
                    TReportStorageInfo.report_created_by,
                ).filter(
                    TReportStorageInfo.delete_flg.is_not(True),
                    TReportStorageInfo.report_classify
                    == ReportTypeValue.CN_REPORT_PDF.value,
                    TReportStorageInfo.report_status == ReportStatus.WORKING.value,
                )

                result_queue = stmt_queue.all()

                if (
                    login_org_id != "TEP"
                    and not login_org_id.startswith("REP")
                    and not login_org_id.startswith("TCS")
                ):
                    stmt = stmt.filter(TCnApplicationInfo.org_id == login_org_id)

                result = session.execute(stmt).mappings().all()

                if not result:
                    return []

                sorted_queue_results = sorted(
                    result_queue, key=lambda r: r.report_created_at
                )

                sorted_results = sorted(result, key=lambda r: r.report_created_at)

                results_with_queue = []
                queue_no = 0

                for r in sorted_queue_results:
                    row = dict(r._mapping)  # SQLAlchemy Row → dict

                    if (
                        row.get("report_status") == ReportStatus.WORKING.value
                        and row.get("report_classify")
                        == ReportTypeValue.CN_REPORT_PDF.value
                    ):
                        queue_no += 1
                        row["queue_no"] = queue_no
                    else:
                        row["queue_no"] = None  # 0以外は設定しない

                    results_with_queue.append(row)

                filtered_results = [
                    r
                    for r in sorted_results
                    if r["corporate_number"] == corporate_number
                    and (
                        not agreement_category
                        or r["agreement_category_t"] == agreement_category
                    )
                ]

                # joinキー定義
                join_keys = ("creation_id",)

                # sorted_queue_results = [dict(r._mapping) for r in sorted_queue_results]

                # sorted_queue_results を lookup辞書化
                queue_lookup = {
                    tuple(row[k] for k in join_keys): row.get("queue_no")
                    for row in results_with_queue
                }

                # filtered_results に queue_no を追加
                merged_results = []
                for row in filtered_results:
                    key = tuple(row[k] for k in join_keys)  # RowMapping は参照はOK
                    d = dict(row)  # ここで編集可能な dict にする
                    d["queue_no"] = queue_lookup.get(key)  # 追加OK
                    merged_results.append(d)

                filtered_results = merged_results  # 見つからない場合は None

                if not filtered_results:
                    return {}
                # --- DataFrame へ変換
                df = pd.DataFrame(filtered_results)
                df["queue_no"] = df["queue_no"].astype("string")
                # ------------------------------------------------------------------
                # report_classify を列名にマッピングして横持ち化
                # （※ classify の定義は実運用に合わせること）
                # ------------------------------------------------------------------
                mapping = {
                    "1": "cn_pdf",  # CNレポート PDF
                    "2": "cn_csv",  # CNレポート CSV
                    "3": "data_loss_pdf",  # 欠損一覧 ZIP（PDF まとめ）
                    "4": "kpi_csv",  # KPI CSV
                }
                df["report_type_name"] = df["report_classify"].map(mapping)

                pivot_df = df.pivot_table(
                    index=["creation_id", "building_id"],
                    columns="report_type_name",
                    values="report_save_path",
                    aggfunc="first",
                ).reset_index()

                for col in ["cn_pdf", "cn_csv", "data_loss_pdf", "kpi_csv"]:
                    if col not in pivot_df.columns:
                        pivot_df[col] = None

                # ------------------------------------------------------------------
                # ベース情報（重複排除）＋ 横持ち結果をマージ
                #  - ラベル解決用に agreement_category_b / agreement_category_t を保持
                # ------------------------------------------------------------------
                base_cols = [
                    "creation_id",
                    "company_name",
                    "report_type_name",
                    "report_selection_period_from",
                    "format_type",
                    "site_selection_type",
                    "group1",
                    "group2",
                    "group3",
                    "group4",
                    "group5",
                    "building_id",
                    "building_name",
                    "location_identifier_name",
                    # "agreement_category_b",      # 建物側
                    "agreement_category_t",  # T 側（フォールバック）
                    "agreement_name",
                    "org_name",
                    "report_status",
                    "queue_no",
                    "report_created_at",
                    "report_created_by",
                ]
                base_info = df[base_cols].drop_duplicates(
                    subset=["creation_id", "building_id"]
                )
                final_df = pd.merge(
                    base_info, pivot_df, on=["creation_id", "building_id"], how="left"
                )

                # ================================================================
                # コード値 → 表示ラベルの統一化（重要）
                #   上流から site_selection_type / format_type にコードが入ってくるケースに対応
                # ================================================================
                SITE_TYPE = {"01": "企業全体", "02": "グループ", "03": "個別"}
                FORMAT_TYPE = {
                    "0": "CNカルテ(簡易版)",
                    "00": "CNカルテ(簡易版)",
                    "1": "CNカルテ(標準版)",
                    "01": "CNカルテ(標準版)",
                }

                final_df["site_selection_type"] = (
                    final_df["site_selection_type"]
                    .astype(str)
                    .map(lambda x: SITE_TYPE.get(x, x))
                )
                final_df["format_type"] = (
                    final_df["format_type"]
                    .astype(str)
                    .map(lambda x: FORMAT_TYPE.get(x, x))
                )

                # ------------------------------------------------------------------
                # 表示値の整形
                # 1) 企業全体 → "全体"
                # 2) グループ → フロント指定値で上書き（指定があれば）
                # 3) 個別     → Building の番号を維持（後でラベル化）
                # ------------------------------------------------------------------
                final_df.loc[
                    final_df["site_selection_type"] == "企業全体",
                    ["group1", "group2", "group3", "group4", "group5"],
                ] = "全体"

                mask_group = final_df["site_selection_type"] == "グループ"
                for g in ["group1", "group2", "group3", "group4", "group5"]:
                    if g in group_selected_values:
                        # フロントの明示指定があればそれを優先（例：「関東」など）
                        final_df.loc[mask_group, g] = group_selected_values[g]

                # ------------------------------------------------------------------
                # group1..group5 のラベル列を付与（group*_label）
                #   個別/グループ： (agreement_category, group_id=列番号) のマスタから select_item<番号> を取得
                #   企業全体      ： "全体"
                #   それ以外      ： 値をそのまま表示（保険）
                #   ※ agreement_category は Building 側が無ければ T 側にフォールバック
                #   ※ 番号は軽量正規化してマスタヒット率を上げる（"０１"/"01"→"1"）
                # ------------------------------------------------------------------
                for gi in range(1, 6):
                    final_df[f"group{gi}_label"] = None

                def _resolve_label(row, gi: int) -> str | None:
                    val = row.get(f"group{gi}")
                    stype = str(row.get("site_selection_type") or "")
                    if val in (None, ""):
                        return None

                    # 企業全体 → 固定表示
                    if stype == "企業全体":
                        return "全体"

                    # 契約区分（B 側優先 / 無ければ T 側）
                    # ac_b = row.get("agreement_category_b")
                    ac = row.get("agreement_category_t")
                    # ac = ac_b if (ac_b not in (None, "")) else ac_t

                    # 値を正規化
                    s_norm, is_digit = _normalize_num_like(val)

                    if stype in ("個別", "グループ") and ac:
                        key = (str(ac), str(gi))
                        # 数字なら select_item<番号> を引く
                        if is_digit:
                            label = (group_mapping.get(key, {}) or {}).get(s_norm)
                            if label is not None:
                                return label
                            # マスタ未ヒット時は（安全策として）None返し
                            try:
                                logger.debug(
                                    f"[CnKarteVisualList] label not found: ac={ac}, group_id={gi}, value={s_norm}"
                                )
                            except Exception:
                                pass
                            return None
                        else:
                            # 文字（例：「関東」）はそのまま表示
                            return s_norm

                    # 想定外 / 契約区分欠損 → 文字として返す
                    return s_norm

                for gi in range(1, 6):
                    final_df[f"group{gi}_label"] = final_df.apply(
                        lambda r: _resolve_label(r, gi), axis=1
                    )

                # --- 日付整形
                final_df["report_created_at"] = pd.to_datetime(
                    final_df["report_created_at"], errors="coerce"
                )
                final_df["report_created_at"] = final_df["report_created_at"].apply(
                    lambda x: x.strftime("%Y/%m/%d %H:%M:%S") if pd.notnull(x) else None
                )

                # --- NaN を None に変換（JSON の null 対応）
                final_df = final_df.where(pd.notnull(final_df), None)

                # ------------------------------------------------------------------
                # 出力列順序（数値とラベルを併記。数値を出したくない場合は *_label のみ残す）
                #  agreement_category_* は内部計算用のため返却しない
                # ------------------------------------------------------------------
                display_cols = [
                    "creation_id",
                    "company_name",
                    "report_type_name",
                    "building_id",
                    "building_name",
                    "location_identifier_name",
                    "report_selection_period_from",
                    "format_type",
                    "site_selection_type",
                    "group1",
                    "group1_label",
                    "group2",
                    "group2_label",
                    "group3",
                    "group3_label",
                    "group4",
                    "group4_label",
                    "group5",
                    "group5_label",
                    "agreement_name",
                    "org_name",
                    "cn_pdf",
                    "cn_csv",
                    "data_loss_pdf",
                    "kpi_csv",
                    "report_status",
                    "queue_no",
                    "report_created_at",
                    "report_created_by",
                ]
                final_df = final_df[display_cols]

                # --- dict list へ変換
                response = final_df.to_dict(orient="records")
                logger.debug(f"Response example: {response[:1]}")
                return response

        except Exception as e:
            logger.error(e)
            abort(500)
