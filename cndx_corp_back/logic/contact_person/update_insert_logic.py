import os
from datetime import datetime
from typing import Dict, List, Tuple

from flask import current_app
from sqlalchemy import text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.query.contact_person_query import QueryMst


# 企業基本情報更新
class ContactPersonUpdateLogic:

    @component
    def update(self, corporate_number, login_user_id, df_staff_list, logger=None):
        """
        df_staff_list に基づき、M_STAFF_INFO を更新または挿入し、
        画面にない既存レコードの削除対象をリストで返却。
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        target_list = []

        with get_scoped_session() as session:
            # 既存レコードを一括フェッチ
            existing: List[MStaffInfo] = (
                session.query(MStaffInfo)
                .filter(MStaffInfo.corporate_number == corporate_number)
                .all()
            )

            # (agreement_category, org_id, user_id) をキーにしてマップ化
            existing_map = {
                (e.agreement_category, e.org_id, e.user_id): e for e in existing
            }
            seen_keys = set()

            # DataFrame の行をループ
            for _, row in df_staff_list.iterrows():
                key = (row.agreement_category, row.org_id, row.user_id)
                seen_keys.add(key)

                consent_date = row.consent_receipt_date.replace("-", "")
                rec = existing_map.get(key)

                if rec:
                    # # レコードが存在 → 同意書受領日が変わっていれば更新
                    # if rec.consent_receipt_date != consent_date:
                    #     session.query(MStaffInfo).filter_by(
                    #         corporate_number=corporate_number,
                    #         agreement_category=row.agreement_category,
                    #         org_id=row.org_id,
                    #         user_id=row.user_id
                    #     ).update({
                    #         "consent_receipt_date": consent_date,
                    #         "updated_by": login_user_id,
                    #     }, synchronize_session=False)

                    # 担当者＆同意書取得経路が既に存在し、削除フラグが立っている場合、
                    # 削除フラグを解除（deleteFlag → false）し、画面の入力内容で更新を行う。
                    base_query = session.query(MStaffInfo).filter_by(
                        corporate_number=corporate_number,
                        agreement_category=row.agreement_category,
                        org_id=row.org_id,
                        user_id=row.user_id,
                    )

                    mStaffInfo = base_query.first()

                    update_values = {
                        "consent_receipt_date": consent_date,
                        "updated_by": login_user_id,
                    }

                    # 削除フラグが立っている場合は復活
                    if mStaffInfo.delete_flg:
                        update_values["delete_flg"] = False
                    # 削除されていない場合は、日付変更時のみ更新
                    elif mStaffInfo.consent_receipt_date == consent_date:
                        continue

                    base_query.update(update_values, synchronize_session=False)

                else:
                    # 存在しない → 新規挿入
                    new_rec = MStaffInfo(
                        corporate_number=corporate_number,
                        agreement_category=row.agreement_category,
                        org_id=row.org_id,
                        user_id=row.user_id,
                        consent_receipt_date=consent_date,
                        created_by=login_user_id,
                    )
                    session.add(new_rec)

            # DataFrame のキーセットを作成
            seen_keys = {
                (row.agreement_category, row.org_id, row.user_id)
                for _, row in df_staff_list.iterrows()
            }

            # 削除対象辞書
            target_dict: Dict[Tuple[str, str, str], dict] = {}

            for rec in existing:
                key = (rec.agreement_category, rec.org_id, rec.user_id)

                # 画面にない & delete_flg=False → 削除対象
                if key not in seen_keys and not rec.delete_flg:
                    target_dict[key] = {
                        "corporate_number": rec.corporate_number,
                        "agreement_category": rec.agreement_category,
                        "org_id": rec.org_id,
                        "user_id": rec.user_id,
                        "login_user_id": login_user_id,
                    }

            session.commit()

        return target_dict

        with get_scoped_session() as session:
            # 担当者情報取得（削除済み含め）
            where_corporate_number = corporate_number
            df_db_staff = (
                session.query(MStaffInfo)
                .filter_by(corporate_number=where_corporate_number)
                .all()
            )
            sql = None

            # 作成日時・更新日時を取得
            target_list = []
            for i, df_list in df_staff_list.iterrows():
                agreement_category = df_list["agreement_category"]
                org_id = df_list["org_id"]
                user_id = df_list["user_id"]
                consent_receipt_date = df_list["consent_receipt_date"]
                update_insert_flg = False
                for df_staff_info in df_db_staff:
                    if (
                        corporate_number == df_staff_info.corporate_number
                        and agreement_category == df_staff_info.agreement_category
                        and org_id == df_staff_info.org_id
                        and user_id == df_staff_info.user_id
                    ):
                        if (
                            df_list["consent_receipt_date"]
                            != df_staff_info.consent_receipt_date
                        ):
                            # 同意書受領日の値が異なる場合更新
                            sql = QueryMst.STAFF_UPDATE.value.format(
                                corporate_number=corporate_number,
                                agreement_category=agreement_category,
                                org_id=org_id,
                                user_id=user_id,
                                consent_receipt_date=consent_receipt_date.replace(
                                    "-", ""
                                ),
                                login_user_id=login_user_id,
                                now_datetime=datetime.now(),
                            )
                        # 既存データの場合削除対象外にするため常にフラグをTrueにする
                        update_insert_flg = True
                        break  # 一致するデータがある場合ループを抜ける
                    elif not update_insert_flg:  # 追加処理(1度だけ処理する対応)
                        sql = QueryMst.STAFF_INSERT.value.format(
                            corporate_number=corporate_number,
                            agreement_category=agreement_category,
                            org_id=org_id,
                            user_id=user_id,
                            consent_receipt_date=consent_receipt_date.replace("-", ""),
                            login_user_id=login_user_id,
                            now_datetime=datetime.now(),
                        )
                        update_insert_flg = True
                if not update_insert_flg:
                    sql = QueryMst.STAFF_INSERT.value.format(
                        corporate_number=corporate_number,
                        agreement_category=agreement_category,
                        org_id=org_id,
                        user_id=user_id,
                        consent_receipt_date=consent_receipt_date.replace("-", ""),
                        login_user_id=login_user_id,
                        now_datetime=datetime.now(),
                    )
                logger.info(f"実行SQL: {sql} ")
                session.execute(text(sql))
            session.commit()
            # 画面上で上書きされた削除対象データを抽出する
            for delete_target in df_db_staff:
                agreement_category = delete_target.agreement_category
                org_id = delete_target.org_id
                user_id = delete_target.user_id
                delete_flg = delete_target.delete_flg
                target_flg = True
                for i, df_list in df_staff_list.iterrows():
                    # 画面上にないデータかつ削除されていないデータは削除対象
                    if (
                        agreement_category == df_list["agreement_category"]
                        and org_id == df_list["org_id"]
                        and user_id == df_list["user_id"]
                    ):
                        target_flg = False
                        break
                if target_flg and not delete_flg:
                    target_list.append(
                        [
                            corporate_number,
                            agreement_category,
                            org_id,
                            user_id,
                            login_user_id,
                        ]
                    )
        logger.info(f"削除対象: {target_list} ")
        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return target_list
