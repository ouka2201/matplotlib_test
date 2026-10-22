import re
from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import abort
from flask_sqlalchemy import SQLAlchemy
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import insert

from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.ext import db
from cndx_corp_back.utils.utils import get_message


class UserInsertLogic:
    @component
    def insert_user(
        self, request_data, user_id, login_org_type_code, session, logger=None
    ):
        """
        ユーザ情報登録を処理する
        """
        current_timestamp = get_current_timestamp()

        # 登録前のチェック処理
        try:
            new_user = UserDTO(**request_data)

            # データベースに該当のメールアドレスが存在するか確認（意図的に削除フラグは条件に入れない）
            exists_list = (
                session.query(MUser)
                .filter(
                    MUser.email_address == new_user.email_address,
                )
                .all()
            )

            # 取得したリストの中に、user_status が "削除" 以外のユーザーが1人でもいるか判定
            is_registered = any(str(user.user_status) != "5" for user in exists_list)

            if is_registered:
                # ステータス削除以外の現役ユーザーが既に存在する場合はエラー
                abort(400, description=get_message("REGISTERED", data="メールアドレス"))
                # return jsonify({"error": get_message("REGISTERED", data="メールアドレス")}), 400

            user_org_info = self.get_user_org_info(session, new_user.org_id)

            org_type_code = user_org_info["org_type_code"]

            parent_org_id = None

            if new_user.branch_code != user_org_info["branch_code"]:
                new_user_org_info = self.get_user_org_info_from_branch_cd(
                    session, user_org_info["bank_code"], new_user.branch_code
                )

                org_type_code = new_user_org_info["org_type_code"]

                max_user_reg = new_user_org_info["max_user_reg"]

                new_user.org_id = new_user_org_info["org_id"]

                parent_org_id = new_user_org_info["parent_org_id"]

            # 組織種別ごとに付与禁止の権限を定義
            invalid_role_map = {
                "01": ["9"],
                "03": ["9"],
                "04": ["9"],
                "05": ["9"],
                "02": ["0", "1"],
                "06": ["1", "9"],
                "07": ["1", "9"],
            }

            # 該当組織に禁止ロールがあり、今回のロールがその中に含まれていたらエラー
            if new_user.user_role in invalid_role_map.get(org_type_code, []):
                abort(403, description="選択した企業では、この権限を付与できません。")

            if org_type_code in ("02", "03"):
                org_ids = (
                    session.query(MUserOrganizationInfo.org_id)
                    .filter(
                        MUserOrganizationInfo.bank_code == user_org_info["bank_code"],
                        MUserOrganizationInfo.delete_flg == False,
                    )
                    .subquery()
                )

                user_count = (
                    session.query(MUser)
                    .filter(MUser.org_id.in_(org_ids), MUser.delete_flg == False)
                    .count()
                )
            else:
                user_count = (
                    session.query(MUser)
                    .filter(MUser.org_id == new_user.org_id, MUser.delete_flg == False)
                    .count()
                )

            max_user_reg = user_org_info["max_user_reg"]
            if parent_org_id is not None:
                parent_max_user_reg = self.get_parent_max_user_reg(
                    session, parent_org_id
                )
                max_user_reg = parent_max_user_reg

            if (
                org_type_code == "02" or org_type_code == "03"
            ) and max_user_reg is None:
                max_user_reg = 1

            if max_user_reg is not None and user_count >= max_user_reg:
                abort(409, description="ユーザー数が上限に達しています。")

            # ステータス設定
            userStatus = self.get_user_status(login_org_type_code)

            m_user = MUser(
                user_name=new_user.user_name,
                company_name=new_user.company_name,
                department_id=new_user.branch_code or None,
                org_id=new_user.org_id,
                user_role=new_user.user_role,
                user_status=userStatus,
                start_date=datetime.strptime("9999/12/31", "%Y/%m/%d"),
                end_date=datetime.strptime("9999/12/31", "%Y/%m/%d"),
                delete_flg=False,
                created_by=user_id,
                created_at=current_timestamp,
                updated_by=None,
                updated_at=current_timestamp,
                email_address=new_user.email_address,
            )

            db.session.add(m_user)
            db.session.commit()
            db.session.close()
        except ValidationError as e:
            raise e
        except Exception as e:
            raise

        return {"success": "ok"}

    def get_parent_max_user_reg(self, session, parent_org_id):
        result = (
            session.query(MUserOrganizationInfo.max_user_reg)
            .filter(
                MUserOrganizationInfo.org_id == parent_org_id,
                MUserOrganizationInfo.delete_flg == False,
            )
            .first()
        )

        if result is None:
            return None

        return result.max_user_reg

    def get_user_org_info(self, session, org_id):
        result = (
            session.query(
                MUserOrganizationInfo.org_type_code,
                MUserOrganizationInfo.max_user_reg,
                MUserOrganizationInfo.bank_code,
                MUserOrganizationInfo.branch_code,
            )
            .filter(
                MUserOrganizationInfo.org_id == org_id,
                MUserOrganizationInfo.delete_flg == False,
            )
            .first()
        )

        if result is None:
            return None

        user_org_info = {
            "org_type_code": result.org_type_code,
            "max_user_reg": result.max_user_reg,
            "bank_code": result.bank_code,
            "branch_code": result.branch_code,
        }
        return user_org_info

    def get_user_org_info_from_branch_cd(self, session, bank_code, branch_code):
        result = (
            session.query(
                MUserOrganizationInfo.org_type_code,
                MUserOrganizationInfo.max_user_reg,
                MUserOrganizationInfo.org_id,
                MUserOrganizationInfo.parent_org_id,
            )
            .filter(
                MUserOrganizationInfo.bank_code == bank_code,
                MUserOrganizationInfo.branch_code == branch_code,
                MUserOrganizationInfo.delete_flg == False,
            )
            .first()
        )

        if result is None:
            return None

        user_org_info = {
            "org_type_code": result.org_type_code,
            "max_user_reg": result.max_user_reg,
            "org_id": result.org_id,
            "parent_org_id": result.parent_org_id,
        }
        return user_org_info

    def get_user_status(self, org_type_code):
        """
        ステータスの取得
        """
        if org_type_code == "02":
            return "2"
        else:
            return "1"


FORBIDDEN_PATTERN = re.compile(
    r"[ｦ-ﾟ 　ァ-ンぁ-ん一-龥]"  # 半角カナ、半角スペース、全角カナ、ひらがな、漢字、全角スペース
)


class UserDTO(BaseModel):
    user_name: str
    company_name: str
    branch_code: str
    org_id: str
    user_role: str
    email_address: str

    @field_validator(
        "user_name", "company_name", "org_id", "user_role", "email_address"
    )
    def not_empty(cls, v, info):
        file_name_map = {
            "org_id": "組織ID",
            "user_name": "氏名",
            "email_address": "メールアドレス",
            "user_role": "権限",
            "company_name": "企業名",
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


def get_current_timestamp():
    """
    Return the current timestamp localized to Asia/Tokyo.
    """
    utc_now = datetime.now(timezone.utc)
    tokyo_now = utc_now.astimezone(ZoneInfo("Asia/Tokyo"))
    return tokyo_now.replace(tzinfo=None)
