import re
from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import abort
from pydantic import BaseModel, ValidationError, field_validator

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.ext import db
from cndx_corp_back.utils.utils import get_current_timestamp, get_message


class UserUpdLogic:
    @component
    def upd_user(self, request_data, user_id, session, logger=None):
        """
        ユーザ情報更新を処理する
        """

        # 現在日時のローカライズ
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        current_timestamp = now_local.strftime("%Y-%m-%d %H:%M:%S")

        # 更新前のチェック処理
        try:
            request_data = request_data.get("users", [])
            upd_users = [UserDTO.model_validate(item) for item in request_data]
            # upd_users = [UserDTO(**item) for item in request_data]
        except ValidationError as e:
            raise e

        # 組織種別ごとに付与禁止の権限を定義
        invalid_role_map = {
            "01": ["9"],
            "03": ["9"],
            "04": ["9"],
            "05": ["9"],
            "02": ["0", "1"],
            "06": ["1", "9"],
        }

        update_data = []
        # データベースに該当のメールアドレスが存在するか確認
        for user in upd_users:
            start_date = None
            end_date = None

            old_user = (
                session.query(MUser)
                .filter(
                    MUser.user_id == user.user_id,
                )
                .first()
            )

            if old_user.delete_flg:
                abort(400, description="削除済のユーザーは更新できません。")

            exists = (
                session.query(MUser)
                .filter(
                    MUser.email_address == user.email_address,
                    MUser.delete_flg == False,
                    MUser.user_id != user.user_id,
                    MUser.user_status != "5",
                )
                .first()
            )

            if exists:
                # 存在する場合はエラーメッセージを返す
                abort(400, description=get_message("REGISTERED", data="メールアドレス"))

            user_org_info = self.get_user_org_info(session, user.org_id)

            # 該当組織に禁止ロールがあり、今回のロールがその中に含まれていたらエラー
            if user.user_role in invalid_role_map.get(user_org_info.org_type_code, []):
                abort(403, description="選択した企業では、この権限を付与できません。")

            if old_user.user_status != "0" and user.user_status == "0":
                start_date = current_timestamp
            else:
                start_date = old_user.start_date

            if old_user.user_status != "5" and user.user_status == "5":
                end_date = current_timestamp
            else:
                end_date = old_user.end_date

            if user.user_status == "4":
                abort(409, description="ステータスを失効中に更新することはできません。")

            if (old_user.user_status == "4" and user.user_status != "4") or (
                old_user.user_status == "5" and user.user_status != "5"
            ):
                end_date = datetime.strptime("9999/12/31", "%Y/%m/%d")

            update_item = {
                "user_id": user.user_id,
                "user_name": user.user_name,
                "email_address": user.email_address,
                "user_role": user.user_role,
                "user_status": user.user_status,
                "updated_by": user_id,
                "start_date": start_date,
                "end_date": end_date,
            }

            update_data.append(update_item)

        # 一括更新を実行
        db.session.bulk_update_mappings(MUser, update_data)
        db.session.commit()

        return {"success": "ok"}

    def get_user_org_info(self, session, org_id):
        result = (
            session.query(
                MUserOrganizationInfo.org_type_code, MUserOrganizationInfo.max_user_reg
            )
            .filter(
                MUserOrganizationInfo.org_id == org_id,
                MUserOrganizationInfo.delete_flg == False,
            )
            .first()
        )
        return result


FORBIDDEN_PATTERN = re.compile(
    r"[ｦ-ﾟ 　ァ-ンぁ-ん一-龥]"  # 半角カナ、半角スペース、全角カナ、ひらがな、漢字、全角スペース
)


class UserDTO(BaseModel):
    user_id: str
    org_id: str
    user_name: str
    email_address: str
    user_role: str
    user_status: str

    @field_validator(
        "user_id", "org_id", "user_name", "email_address", "user_role", "user_status"
    )
    def not_empty(cls, v, info):
        file_name_map = {
            "user_id": "ユーザーID",
            "org_id": "組織ID",
            "user_name": "氏名",
            "email_address": "メールアドレス",
            "user_role": "権限",
            "user_status": "ステータス",
        }
        if not v or not v.strip():
            raise ValueError(f"{file_name_map.get(info.field_name)}は必須です。")
        return v

    @field_validator("email_address")
    def email_format(cls, v):
        if FORBIDDEN_PATTERN.search(v) or not re.match(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v
        ):
            raise ValueError("メールアドレス形式が不正です。")
        return v
