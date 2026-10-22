import datetime
import math

import numpy as np
import pandas as pd
import pytz
from flask import abort, current_app
from sqlalchemy import and_, func, not_

import cndx_corp_back.constant.constants as constants
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import (
    MCorporateDetailsInfo,
)
from cndx_corp_back.utils.utils import get_message


# 企業基本情報更新
class CorprationBasicUpdateComponent:

    @component
    def execute(self, request_dict: dict, logger=None):

        # 建物情報取得
        df_corpInfos = pd.DataFrame(request_dict)

        # 企業情報取得
        if not request_dict["office_info_list"]:
            df_corpInfos = pd.DataFrame([request_dict])

        # 建物情報切り出し
        office_info_df = pd.DataFrame(
            df_corpInfos["office_info_list"].to_dict()
        ).transpose()

        if logger is None:
            logger = current_app.logger

        if not office_info_df.empty:
            office_info_df["business_office_count"] = office_info_df.groupby(
                ["agreement_category"]
            )["agreement_category"].transform("count")

        with get_scoped_session() as session:

            # 企業基本情報取得
            df_corpInfos_firdst_row = df_corpInfos.iloc[0]

            # DBの企業基本情報取得
            corporate_basic_info = (
                session.query(MCorporateBasic)
                .filter_by(corporate_number=df_corpInfos_firdst_row["corporate_number"])
                .all()
            )

            # 新規登録の場合、企業基本情報のみ登録
            if df_corpInfos.iloc[0]["usage_type"] == "0":

                if not self.orm_list_to_df(corporate_basic_info).empty:
                    abort(
                        404,
                        description=get_message(
                            "GROUP_MASTER_DUPLICATED", item_name="法人番号"
                        ),
                    )

                # 企業基本情報新規登録
                self.corp_basic_info_insert(session, df_corpInfos_firdst_row)
                session.commit()
                return

            # 建物情報取得
            building_id_info = (
                session.query(MBuilding)
                .filter_by(corporate_number=df_corpInfos_firdst_row["corporate_number"])
                .all()
            )

            df_building_id_info = pd.DataFrame()

            if not office_info_df.empty:
                office_info_df["building_id_str"] = office_info_df[
                    "building_id"
                ].astype(str)
            if building_id_info and len(building_id_info) > 0:
                # 建物情報をDFへ変換
                df_building_id_info = self.orm_list_to_df(building_id_info)

                df_building_columns = constants.building_columns
                # 建物情報カラム設定
                if df_building_id_info.empty:
                    df_building_id_info = pd.DataFrame(columns=df_building_columns)

                # office_info_df["building_id_str"] = office_info_df["building_id"].astype(str)

            vis_flg = False

            if not office_info_df.empty:
                vis_rows = office_info_df[
                    ((office_info_df["building_id_str"].fillna("").str.contains(r"\D")))
                    & (
                        ~office_info_df.apply(
                            lambda r: str(df_corpInfos["corporate_number"].iloc[0])
                            in str(r["building_id_str"]),
                            axis=1,
                        )
                    )
                ]

                if len(vis_rows) > 0:
                    vis_flg = True
                office_info_df = get_building_id(
                    df_corpInfos_firdst_row,
                    office_info_df,
                    df_building_id_info,
                    vis_flg,
                )

                df_corpInfos = pd.concat(
                    [
                        df_corpInfos[
                            [
                                "user_id",
                                "company_name",
                                "company_name_kana",
                                "corporate_number",
                                "company_address_prefecture",
                                "company_address_city",
                                "usage_type",
                            ]
                        ],
                        office_info_df,
                    ],
                    axis=1,
                )

            # 更新分の場合
            # 企業基本情報登録
            self.corp_basic_Info_update(corporate_basic_info, df_corpInfos_firdst_row)

            # 企業詳細情報取得
            corporate_details_info = (
                session.query(MCorporateDetailsInfo)
                .filter_by(corporate_number=df_corpInfos_firdst_row["corporate_number"])
                .all()
            )

            if not office_info_df.empty:

                # 建物情報をDFへ変換
                df_building_id_info = self.orm_list_to_df(building_id_info)
                # 企業詳細情報をDFへ変換
                df_corporate_details_info = self.orm_list_to_df(corporate_details_info)

                df_building_columns = constants.building_columns
                df_corporate_details_columns = constants.corporate_details_columns
                # 建物情報カラム設定
                if df_building_id_info.empty:
                    df_building_id_info = pd.DataFrame(columns=df_building_columns)

                # 企業詳細情報カラム設定
                if df_corporate_details_info.empty:
                    df_corporate_details_info = pd.DataFrame(
                        columns=df_corporate_details_columns
                    )

                # 合併キー
                building_merge_keys = ["corporate_number", "building_id"]
                corporate_details_merge_keys = [
                    "corporate_number",
                    "agreement_category",
                ]

                # 請求情報に建物情報ある
                if "building_id" in df_corpInfos.columns:
                    # 建物情報更新レコード分
                    df_corpInfos_update_rec = pd.merge(
                        df_corpInfos,
                        df_building_id_info,
                        on=building_merge_keys,
                        how="inner",
                        suffixes=("", "_drop"),
                    )

                    # 建物情報登録レコード分
                    df_diff = pd.merge(
                        df_corpInfos,
                        df_building_id_info,
                        on=building_merge_keys,
                        how="left",
                        indicator=True,
                        suffixes=("", "_drop"),
                    )
                    df_corpInfos_insert_rec = df_diff[
                        df_diff["_merge"] == "left_only"
                    ].drop(columns=["_merge"])

                    # 企業詳細情報更新レコード分
                    df_corp_detail_update_rec = pd.merge(
                        df_corpInfos,
                        df_corporate_details_info,
                        on=corporate_details_merge_keys,
                        how="inner",
                        suffixes=("", "_drop"),
                    )

                    # 企業詳細情報登録レコード分
                    df_diff = pd.merge(
                        df_corpInfos,
                        df_corporate_details_info,
                        on=corporate_details_merge_keys,
                        how="left",
                        indicator=True,
                        suffixes=("", "_drop"),
                    )
                    df_corp_detail_insert_rec = df_diff[
                        df_diff["_merge"] == "left_only"
                    ].drop(columns=["_merge"])
                # 請求情報建物情報なし
                else:
                    df_corpInfos_update_rec = df_corpInfos
                    df_corpInfos_insert_rec = pd.DataFrame()  # insert分なし
                    df_corp_detail_update_rec = df_corpInfos
                    df_corp_detail_insert_rec = pd.DataFrame()  # insert分なし

                # 既存レコード更新
                if not df_corpInfos_update_rec.empty:
                    if not vis_flg:
                        self.check_t_building_info(session, df_corpInfos_update_rec)
                        self.building_info_update(
                            building_id_info, df_corpInfos_update_rec
                        )

                # 新規レコード登録
                if not df_corpInfos_insert_rec.empty:
                    if not vis_flg:
                        self.check_t_building_info(session, df_corpInfos_insert_rec)
                        # 建物情報登録
                        self.building_info_insert(session, df_corpInfos_insert_rec)

                # 既存レコード更新
                if not df_corp_detail_update_rec.empty:
                    self.corp_details_Info_update(
                        corporate_details_info, df_corp_detail_update_rec
                    )

                # 新規レコード登録
                if not df_corp_detail_insert_rec.empty:
                    # 同じ同意書取得区分を統一にする
                    df_corp_details_info = df_corp_detail_insert_rec[
                        [
                            "corporate_number",
                            "org_id",
                            "agreement_category",
                            "user_id",
                            "business_office_count",
                        ]
                    ]
                    df_corp_details_info = df_corp_details_info.drop_duplicates()

                    for index, corp_detail in df_corp_details_info.iterrows():
                        mCorporateDetailsInfo = MCorporateDetailsInfo()
                        mCorporateDetailsInfo.corporate_number = corp_detail[
                            "corporate_number"
                        ]
                        mCorporateDetailsInfo.org_id = "TEP"
                        mCorporateDetailsInfo.business_office_count = corp_detail[
                            "business_office_count"
                        ]
                        mCorporateDetailsInfo.agreement_category = corp_detail[
                            "agreement_category"
                        ]
                        mCorporateDetailsInfo.delete_flg = False
                        mCorporateDetailsInfo.created_by = corp_detail["user_id"]

                        session.add(mCorporateDetailsInfo)
            else:
                for corporate_detail in corporate_details_info:
                    corporate_detail.delete_flg = True

                for building in building_id_info:
                    building.delete_flg = True

            session.commit()

    def check_t_building_info(self, session, df):
        """
        お客様番号、供給地点特定番号存在チェック処理
        """
        for index, row in df.iterrows():
            old_tBuilding = (
                session.query(MBuilding)
                .filter(
                    not_(
                        and_(
                            MBuilding.building_id == row["building_id"],
                            MBuilding.agreement_category == row["agreement_category"],
                        )
                    ),
                    MBuilding.corporate_number == row["corporate_number"],
                    MBuilding.agreement_org == row["agreement_org"],
                    MBuilding.delete_flg == False,
                )
                .all()
            )

            ep_customer_number = row["ep_customer_number"]
            supply_point_number = row["supply_point_number"]

            # お客さま番号重複件数
            ep_count = (
                sum(
                    1
                    for b in old_tBuilding
                    if b.ep_customer_number == ep_customer_number
                )
                if ep_customer_number
                else 0
            )

            # 供給地点特定番号重複件数
            supply_count = sum(
                1 for b in old_tBuilding if b.supply_point_number == supply_point_number
            )

            if bool(ep_customer_number) and ep_count > 0:
                abort(
                    400,
                    description=f"お客さま番号:{ep_customer_number}は既に登録されています。",
                )

            if supply_count > 0:
                abort(
                    400,
                    description=f"供給地点特定番号:{supply_point_number}は既に登録されています。",
                )

    def get_current_timestamp(self):
        # タイムゾーンが取得する
        timezone = pytz.timezone("Asia/Tokyo")
        # UTC時間が東京時間を変換する
        # local_time = datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone)
        local_time = datetime.datetime.now()
        return local_time.strftime("%Y-%m-%d %H:%M:%S")

    def orm_list_to_df(self, orm_list):
        """
        リストからdataframeへ変換処理
        """
        if not orm_list:
            return pd.DataFrame()

        return pd.DataFrame([row.__dict__ for row in orm_list]).drop(
            columns=["_sa_instance_state"]
        )

    def building_info_update(self, building_id_info, df_corpInfos_update_rec):
        """
        建物情報更新処理
        """

        # 該当企業の建物情報一回ロジック削除にする
        for row in building_id_info:
            row.delete_flg = True
            # row.updated_by = update_data['user_id']
            row.updated_at = self.get_current_timestamp()

        # 詳細情報全部削除
        if "building_id" not in df_corpInfos_update_rec.columns:
            return

        for building in building_id_info:
            # update_data = df_corpInfos_update_rec.to_dict().get(building.building_id)
            update_data_rec = df_corpInfos_update_rec.loc[
                df_corpInfos_update_rec["building_id"] == building.building_id
            ]
            for idx, update_data in update_data_rec.iterrows():
                # 建物の同意有無フラグ設定
                agreement_category_flg = True
                if update_data["agreement_category"] == "00":
                    agreement_category_flg = False
                building.corporate_number = update_data["corporate_number"]
                building.org_id = "TEP"
                building.agreement_category = update_data[
                    "agreement_category"
                ]  # TODO 主キー変更している、リスクあり、恒久対応要（画面で変更していいものではない）
                building.building_id = update_data["building_id"]
                building.building_name = update_data["building_name"]
                building.location_identifier_name = update_data[
                    "location_identifier_name"
                ]
                building.building_address_prefecture = update_data[
                    "building_address_prefecture"
                ]
                building.building_address_city = update_data["building_address_city"]
                supply_point_number = update_data["supply_point_number"]

                ep_office_code = update_data.get("ep_office_code")
                ep_customer_number = update_data.get("ep_customer_number")

                if ep_office_code is None or (
                    isinstance(ep_office_code, float) and math.isnan(ep_office_code)
                ):
                    building.ep_office_code = None
                else:
                    building.ep_office_code = str(ep_office_code)

                if ep_customer_number is None or (
                    isinstance(ep_customer_number, float)
                    and math.isnan(ep_customer_number)
                ):
                    building.ep_customer_number = None
                else:
                    building.ep_customer_number = str(ep_customer_number)

                if supply_point_number is None or (
                    isinstance(supply_point_number, float)
                    and math.isnan(supply_point_number)
                ):
                    building.supply_point_number = None
                else:
                    building.supply_point_number = str(supply_point_number)

                building.building_consent_flag = agreement_category_flg
                building.delete_flg = False
                building.updated_by = update_data["user_id"]
                building.updated_at = self.get_current_timestamp()
                building.agreement_org = update_data["agreement_org"]

        return building_id_info

    def corp_basic_Info_update(self, corporate_basic_info, df_corpInfos_update_rec):
        """
        企業基本情報更新処理
        """
        for corporate_basic in corporate_basic_info:
            corporate_basic.corporate_number = df_corpInfos_update_rec[
                "corporate_number"
            ]
            corporate_basic.company_name = df_corpInfos_update_rec["company_name"]
            corporate_basic.company_name_kana = df_corpInfos_update_rec[
                "company_name_kana"
            ]
            corporate_basic.company_address_prefecture = df_corpInfos_update_rec[
                "company_address_prefecture"
            ]
            corporate_basic.company_address_city = df_corpInfos_update_rec[
                "company_address_city"
            ]
            corporate_basic.updated_by = df_corpInfos_update_rec["user_id"]
            corporate_basic.updated_at = self.get_current_timestamp()
            break

        return corporate_basic_info

    def corp_details_Info_update(self, corporate_details_info, df_corpInfos_update_rec):
        """
        企業詳細情報更新処理
        """

        # 該当企業の詳細情報一回ロジック削除にする
        for row in corporate_details_info:
            row.delete_flg = True
            # row.updated_by = update_data['user_id']
            row.updated_at = self.get_current_timestamp()

        # 詳細情報全部削除
        if "building_id" not in df_corpInfos_update_rec.columns:
            return

        # 企業詳細情報マスタへ更新する
        for corporate_detail in corporate_details_info:
            update_data_rec = df_corpInfos_update_rec.loc[
                df_corpInfos_update_rec["agreement_category"]
                == corporate_detail.agreement_category
            ]
            for idx, update_data in update_data_rec.iterrows():
                corporate_detail.corporate_number = update_data["corporate_number"]
                corporate_detail.business_office_count = update_data[
                    "business_office_count"
                ]
                corporate_detail.org_id = "TEP"
                corporate_detail.agreement_category = update_data["agreement_category"]
                corporate_detail.delete_flg = False
                corporate_detail.updated_by = update_data["user_id"]
                corporate_detail.updated_at = self.get_current_timestamp()
                break

        return corporate_details_info

    def corp_basic_info_insert(self, session, df_corpInfos_insert_rec):
        """
        企業基本情報登録処理
        """
        mCorporateBasic = MCorporateBasic()
        mCorporateBasic.corporate_number = df_corpInfos_insert_rec[
            "corporate_number"
        ]  # 法人番号
        mCorporateBasic.company_name = df_corpInfos_insert_rec["company_name"]  # 法人名
        mCorporateBasic.company_name_kana = df_corpInfos_insert_rec[
            "company_name_kana"
        ]  # 法人名かな
        mCorporateBasic.company_address_prefecture = df_corpInfos_insert_rec[
            "company_address_prefecture"
        ]  # 所在地（都道府県）
        mCorporateBasic.company_address_city = df_corpInfos_insert_rec[
            "company_address_city"
        ]  # 所在地（市区町村以降）
        mCorporateBasic.delete_flg = False
        mCorporateBasic.created_by = df_corpInfos_insert_rec["user_id"]

        session.add(mCorporateBasic)

    def building_info_insert(self, session, df_corpInfos_insert_rec):
        """
        建物情報登録処理
        """
        for index, building in df_corpInfos_insert_rec.iterrows():
            mBuilding = MBuilding()
            mBuilding.corporate_number = building["corporate_number"]  # 法人番号
            mBuilding.org_id = "TEP"  # 組織ID（FK）
            mBuilding.agreement_category = building[
                "agreement_category"
            ]  # 同意書取得区分
            mBuilding.building_id = building["building_id"]  # 建物ID（FK）
            mBuilding.building_name = building["location_identifier_name"]  # 建物名
            mBuilding.location_identifier_name = building["location_identifier_name"]
            mBuilding.building_address_prefecture = building[
                "building_address_prefecture"
            ]  # 所在地（都道府県）
            mBuilding.building_address_city = building[
                "building_address_city"
            ]  # 所在地（市区町村以降）

            ep_office_code = building.get("ep_office_code")
            ep_customer_number = building.get("ep_customer_number")
            supply_point_number = building.get("supply_point_number")

            if ep_office_code is None or (
                isinstance(ep_office_code, float) and math.isnan(ep_office_code)
            ):
                mBuilding.ep_office_code = None
            else:
                mBuilding.ep_office_code = str(ep_office_code)

            if ep_customer_number is None or (
                isinstance(ep_customer_number, float) and math.isnan(ep_customer_number)
            ):
                mBuilding.ep_customer_number = None
            else:
                mBuilding.ep_customer_number = str(ep_customer_number)

            # 供給地点特定番号
            if supply_point_number is None or (
                isinstance(supply_point_number, float)
                and math.isnan(supply_point_number)
            ):
                mBuilding.supply_point_number = None
            else:
                mBuilding.supply_point_number = str(supply_point_number)

            mBuilding.delete_flg = False
            mBuilding.created_by = building["user_id"]
            mBuilding.agreement_org = building["agreement_org"]

            session.add(mBuilding)


def get_building_id(
    df_corpInfos_firdst_row,
    office_info_df,
    df_building_id_info,
    vis_flg,
):
    """
    building_id取得
    corp(13桁) + suffix(6桁) = 19桁固定
    末尾が数字でない場合は suffix を 0 起点で採番する
    """

    corp_no = str(df_corpInfos_firdst_row["corporate_number"]).zfill(13)
    INITIAL_SUFFIX_NUM = 0  # 初回採番基準

    # building_id を文字列として正規化
    office_info_df["building_id"] = (
        office_info_df["building_id"].fillna("0").replace("", "0").astype(str)
    )

    # 既存 building_id から suffix 最大値を取得
    def get_max_suffix(df):
        if df.empty:
            return None

        suffix_list = []

        for bid in df["building_id"].astype(str):
            # 末尾6桁だけを見る
            suffix = bid[-6:]

            # 数字の場合のみリストに追加
            if suffix.isdigit():
                suffix_list.append(int(suffix))

        return max(suffix_list) if suffix_list else None

    max_suffix = get_max_suffix(df_building_id_info)

    # 初回 or 追加登録の基準suffix
    if (office_info_df["building_id"] == "0").all():
        # 初回登録
        base_suffix = INITIAL_SUFFIX_NUM if max_suffix is None else max_suffix
    else:
        if not vis_flg:
            # 既存IDがあるが、suffixが全て無効（末尾が字母など）の場合
            base_suffix = INITIAL_SUFFIX_NUM if max_suffix is None else max_suffix
        else:
            return office_info_df

    # 採番
    suffix_index = 0
    for i, row in office_info_df.iterrows():
        if row["building_id"] != "0":
            continue

        suffix_index += 1
        new_suffix = base_suffix + suffix_index
        office_info_df.at[i, "building_id"] = f"{corp_no}{new_suffix:06d}"

    return office_info_df
