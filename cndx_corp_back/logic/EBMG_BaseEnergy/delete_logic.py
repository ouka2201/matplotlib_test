import os
import traceback
from datetime import datetime

import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, delete, func, select, text, update
from sqlalchemy.engine import Result

import cndx_corp_back.logic.EBMG_BaseEnergy.auto_entry_logic as AutoEntryLogic
from cndx_corp_back.common.decorators import component
from cndx_corp_back.dto.EBMG.energy_delete_in_dto import (
    EnergyDeleteIn,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_annual_building_energy_aggregation_entity import (
    TAnnualBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_annual_corporate_energy_aggregation_entity import (
    TAnnualCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_corporate_energy_aggregation_entity import (
    TMonthlyCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.utils.utils import get_message

# from cndx_corp_back.common.hql_processor import (
#    execute_update
# )


@component
def dto_to_df(indto: EnergyDeleteIn, logger=None):
    target_year_month_list = AutoEntryLogic.yyyymm_list(indto.start_year_month, 12)

    base = {
        "corporate_number": indto.corporate_number,
        "agreement_category": indto.agreement_category,
        "org_id": indto.org_id,
        "fiscal_year": indto.fiscal_year,
        "registration_seq": indto.registration_seq,
        "target_year_month": target_year_month_list,  # 月次系のIN句に使用
        "target_year": indto.fiscal_year,  # 年次系の絞り込みに使用
    }

    rows = []

    for ub in indto.updated_building_delete:
        # energy_info が無ければ「建物単位（energy_code=None）」で1行
        if not ub.energy_info:
            r = {**base, "building_id": ub.building_id, "energy_code": None}
            rows.append(r)
            continue

        # energy_info があれば「エネルギーコード単位」で複数行
        for ei in ub.energy_info:
            code = ei.energy_code
            r = {**base, "building_id": ub.building_id, "energy_code": code}
            rows.append(r)

    cols = [
        "corporate_number",
        "agreement_category",
        "org_id",
        "fiscal_year",
        "registration_seq",
        "target_year_month",
        "target_year",
        "building_id",
        "energy_code",
    ]
    basic_df = pd.DataFrame(rows, columns=cols)
    return basic_df


@component
def delete_input_data(session, basic_df: pd.DataFrame, org_id, user_id, logger=None):
    # BUILDING_IDのリストを取得
    building_ids = basic_df["building_id"].dropna().unique().tolist()

    try:
        # 該当レコードを取得
        stmt = select(MBuilding.building_id).where(
            MBuilding.building_id.in_(building_ids),
            MBuilding.corporate_number == basic_df["corporate_number"].iloc[0],
        )
        existing = session.execute(stmt).scalars().all()

        # 存在チェック
        if len(building_ids) != len(existing):
            missing = set(building_ids) - set(existing)
            abort(400, get_message("NOT_UPDATE", field="建物情報"))

        registration_seq = int(basic_df["registration_seq"].iloc[0])
        tBuildingInfo = (
            session.query(TBuildingInfo)
            .filter(
                TBuildingInfo.corporate_number == basic_df["corporate_number"].iloc[0],
                TBuildingInfo.agreement_category
                == basic_df["agreement_category"].iloc[0],
                TBuildingInfo.org_id == basic_df["org_id"].iloc[0],
                TBuildingInfo.building_id.in_(building_ids),
                TBuildingInfo.fiscal_year == basic_df["fiscal_year"].iloc[0],
                TBuildingInfo.registration_seq == registration_seq,
            )
            .first()
        )

        if tBuildingInfo.entry_draft_flag == "1":
            logger.info("下書きデータの削除処理を実行します。")
            # 下書きデータ削除処理
            # DataFrame の先頭行を取得
            head = basic_df.iloc[0]

            # 各テーブルで共通して使用するキー項目
            common_key = {
                "corporate_number": head["corporate_number"],  # 法人番号
                "agreement_category": head["agreement_category"],  # 協定区分
                "org_id": head["org_id"],  # 組織ID
                "fiscal_year": head["fiscal_year"],  # 年度
                "registration_seq": int(head["registration_seq"]),  # 登録連番
                "target_year_month": head["target_year_month"],  # 対象年月
            }

            delete_stmts = [
                # CN申請情報テーブル
                delete(TCnApplicationInfo).where(
                    TCnApplicationInfo.corporate_number
                    == common_key["corporate_number"],
                    TCnApplicationInfo.agreement_category
                    == common_key["agreement_category"],
                    TCnApplicationInfo.org_id == common_key["org_id"],
                    TCnApplicationInfo.fiscal_year == common_key["fiscal_year"],
                    TCnApplicationInfo.registration_seq
                    == common_key["registration_seq"],
                ),
            ]

            # 個別キー
            for _, row in basic_df.iterrows():
                building_id = row["building_id"]  # 建物ID
                energy_code = row["energy_code"]  # エネルギーコード

                delete_stmts += [
                    # 建物情報テーブル
                    delete(TBuildingInfo).where(
                        TBuildingInfo.corporate_number
                        == common_key["corporate_number"],
                        TBuildingInfo.agreement_category
                        == common_key["agreement_category"],
                        TBuildingInfo.org_id == common_key["org_id"],
                        TBuildingInfo.building_id == building_id,
                        TBuildingInfo.fiscal_year == common_key["fiscal_year"],
                        TBuildingInfo.registration_seq
                        == common_key["registration_seq"],
                    ),
                    # 年次 建物別 エネルギー集計テーブル
                    delete(TAnnualBuildingEnergyAggregation).where(
                        TAnnualBuildingEnergyAggregation.corporate_number
                        == common_key["corporate_number"],
                        TAnnualBuildingEnergyAggregation.agreement_category
                        == common_key["agreement_category"],
                        TAnnualBuildingEnergyAggregation.org_id == common_key["org_id"],
                        TAnnualBuildingEnergyAggregation.building_id == building_id,
                        TAnnualBuildingEnergyAggregation.fiscal_year
                        == common_key["fiscal_year"],
                        TAnnualBuildingEnergyAggregation.registration_seq
                        == common_key["registration_seq"],
                        TAnnualBuildingEnergyAggregation.energy_code == energy_code,
                    ),
                    # 年次 法人別 エネルギー集計テーブル
                    delete(TAnnualCorporateEnergyAggregation).where(
                        TAnnualCorporateEnergyAggregation.corporate_number
                        == common_key["corporate_number"],
                        TAnnualCorporateEnergyAggregation.agreement_category
                        == common_key["agreement_category"],
                        TAnnualCorporateEnergyAggregation.org_id
                        == common_key["org_id"],
                        TAnnualCorporateEnergyAggregation.fiscal_year
                        == common_key["fiscal_year"],
                        TAnnualCorporateEnergyAggregation.registration_seq
                        == common_key["registration_seq"],
                        TAnnualCorporateEnergyAggregation.energy_code == energy_code,
                    ),
                    # 月次 建物別 エネルギー集計テーブル
                    delete(TMonthlyBuildingEnergyAggregation).where(
                        TMonthlyBuildingEnergyAggregation.corporate_number
                        == common_key["corporate_number"],
                        TMonthlyBuildingEnergyAggregation.agreement_category
                        == common_key["agreement_category"],
                        TMonthlyBuildingEnergyAggregation.org_id
                        == common_key["org_id"],
                        TMonthlyBuildingEnergyAggregation.building_id == building_id,
                        TMonthlyBuildingEnergyAggregation.fiscal_year
                        == common_key["fiscal_year"],
                        TMonthlyBuildingEnergyAggregation.registration_seq
                        == common_key["registration_seq"],
                        TMonthlyBuildingEnergyAggregation.energy_code == energy_code,
                    ),
                    # 月次 法人別 エネルギー集計テーブル
                    delete(TMonthlyCorporateEnergyAggregation).where(
                        TMonthlyCorporateEnergyAggregation.corporate_number
                        == common_key["corporate_number"],
                        TMonthlyCorporateEnergyAggregation.agreement_category
                        == common_key["agreement_category"],
                        TMonthlyCorporateEnergyAggregation.org_id
                        == common_key["org_id"],
                        TMonthlyCorporateEnergyAggregation.target_year_month.in_(
                            [str(x) for x in common_key["target_year_month"]]
                        ),
                        TMonthlyCorporateEnergyAggregation.registration_seq
                        == common_key["registration_seq"],
                        TMonthlyCorporateEnergyAggregation.energy_code == energy_code,
                    ),
                ]

            # 削除件数の合計
            total_rowcount = 0

            # 各 DELETE 文を順に実行
            for stmt in delete_stmts:
                result = session.execute(stmt)
                total_rowcount += result.rowcount

            return total_rowcount
        else:
            # 共通更新値
            update_values = {
                "updated_at": datetime.now(),
                "updated_by": user_id,
                "delete_flg": True,
            }
            # 更新対象のテーブル
            TARGET_TABLES = [
                TBuildingInfo,
                TCnApplicationInfo,
                TAnnualBuildingEnergyAggregation,
                TMonthlyBuildingEnergyAggregation,
                TAnnualCorporateEnergyAggregation,
                TMonthlyCorporateEnergyAggregation,
            ]
            MODEL_PK_MAP = {
                TBuildingInfo: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "building_id",
                    "registration_seq",
                    "fiscal_year",
                ],
                TCnApplicationInfo: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "fiscal_year",
                    "registration_seq",
                ],
                TAnnualBuildingEnergyAggregation: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "building_id",
                    "energy_code",
                    "target_year",
                    "fiscal_year",
                    "registration_seq",
                ],
                TMonthlyBuildingEnergyAggregation: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "building_id",
                    "energy_code",
                    "target_year_month",
                    "registration_seq",
                ],
                TAnnualCorporateEnergyAggregation: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "energy_code",
                    "target_year",
                    "fiscal_year",
                    "registration_seq",
                ],
                TMonthlyCorporateEnergyAggregation: [
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "energy_code",
                    "target_year_month",
                    "registration_seq",
                ],
            }

            # corporate テーブルのスキップ条件（energy_code=None を除外）
            CORPORATE_TABLES = {
                TAnnualCorporateEnergyAggregation,
                TMonthlyCorporateEnergyAggregation,
            }

            # basic_df に list が入っている列だけ tuple に変える
            if "target_year_month" in basic_df:
                basic_df["target_year_month"] = basic_df["target_year_month"].apply(
                    lambda v: tuple(v) if isinstance(v, list) else v
                )

            # 各モデルごとにループして UPDATE
            total_rowcount = 0
            for model in TARGET_TABLES:
                pk_cols = MODEL_PK_MAP[model]

                df_model = basic_df.copy()
                if model in CORPORATE_TABLES:
                    df_model = df_model[df_model["energy_code"].notna()]

                if df_model.empty:
                    continue

                # 重複の抑止：PK 列で一意に
                df_model = df_model[pk_cols].drop_duplicates()

                for _, row in df_model.iterrows():
                    conditions = []
                    for pk in pk_cols:
                        column = getattr(model, pk)
                        value = row[pk]

                        if isinstance(value, (list, tuple)):
                            conditions.append(
                                column.in_(value) if value else text("FALSE")
                            )
                        elif pd.isna(value):
                            conditions.append(column.is_(None))
                        else:
                            conditions.append(column == value)

                    if not conditions:
                        continue

                    upd = update(model).where(and_(*conditions)).values(**update_values)

                    compiled = upd.compile(
                        dialect=session.connection().dialect,
                        compile_kwargs={
                            "literal_binds": True,
                            "render_postcompile": True,
                        },
                    )
                    logger.info(f"UPDATE SQL: {compiled}")

                    result: Result = session.execute(upd)
                    total_rowcount += result.rowcount
            return total_rowcount

    except Exception as e:
        logger.error(f"{os.path.basename(__file__)}のデータ削除が失敗しました。")
        session.rollback()
        raise
