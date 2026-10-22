import datetime

from flask import abort, current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.utils.utils import get_message


# 企業組織基本情報登録コンポネント
class UserOrgCorpAuthRegisterComponent:

    @component
    def execute(self, request_dict: dict, user_context, logger=None):

        if logger is None:
            logger = current_app.logger

        # 必須項目チェック
        # required_fields = [
        #     "org_id", "user_id", "org_name", "company_code", "company_name",
        #     "bank_code", "branch_code", "branch_name", "org_type_code",
        #     "org_type", "agreement_code", "agreement_name", "business_type"
        # ]
        # for field in required_fields:
        #     value = request_dict.get(field)
        #     if value is None or (isinstance(value, str) and value.strip() == ""):
        #         abort(400, description=f"{field} は必須項目です。")

        with get_scoped_session() as session:
            # 企業組織情報既存チェック
            corporate_organization_info = (
                session.query(MUserOrganizationInfo)
                .filter_by(org_id=request_dict["org_id"])
                .all()
            )

            # 既存情報存在の場合、エラー
            if len(corporate_organization_info) > 0:
                abort(409, description=get_message("REGISTERED", data="企業の組織情報"))

            # 組織種別コードで支店 or 本店を判断（org_type_code は数字）
            org_type_code = request_dict.get("org_type_code")

            # 本店情報が先に存在する場合 → 支店登録時に親組織IDを設定
            parent_org_id = None
            if org_type_code == "03":  # 地銀・支店
                bank_code = request_dict.get("bank_code")
                if bank_code:
                    honten = (
                        session.query(MUserOrganizationInfo)
                        .filter_by(
                            bank_code=bank_code, org_type_code="02"  # 地銀・本店
                        )
                        .first()
                    )
                    if honten:
                        parent_org_id = honten.org_id

            # 登録処理
            self.user_organization_info_insert(
                session, request_dict, user_context, parent_org_id
            )

            # 本店登録時 → 所属支店に親組織IDを設定する
            if org_type_code == "02":  # 地銀・本店
                bank_code = request_dict.get("bank_code")
                new_honten_org_id = request_dict.get("org_id")
                if bank_code:
                    session.query(MUserOrganizationInfo).filter(
                        MUserOrganizationInfo.bank_code == bank_code,
                        MUserOrganizationInfo.org_type_code == "03",  # 地銀・支店
                        MUserOrganizationInfo.parent_org_id.is_(None),
                    ).update(
                        {
                            MUserOrganizationInfo.parent_org_id: new_honten_org_id,
                            MUserOrganizationInfo.created_by: user_context.get(
                                "user_id"
                            ),  # 作成者
                        },
                        synchronize_session=False,
                    )

            session.commit()

    def user_organization_info_insert(
        self, session, df_orgCorpAuth, user_context, parent_org_id=None
    ):
        """
        企業組織基本情報登録処理
        """
        mUserOrganizationInfo = MUserOrganizationInfo()
        mUserOrganizationInfo.org_id = df_orgCorpAuth["org_id"]  # 組織ID（前端设置済）
        mUserOrganizationInfo.org_name = df_orgCorpAuth[
            "org_name"
        ]  # 組織名（前端设置済）
        mUserOrganizationInfo.parent_org_id = parent_org_id  # 親組織ID（支店时设定）
        mUserOrganizationInfo.company_name = df_orgCorpAuth["company_name"]  # 会社名
        mUserOrganizationInfo.company_code = df_orgCorpAuth[
            "company_code"
        ]  # 会社コード
        mUserOrganizationInfo.bank_code = df_orgCorpAuth["bank_code"]  # 銀行コード
        mUserOrganizationInfo.branch_code = df_orgCorpAuth["branch_code"]  # 支店コード
        mUserOrganizationInfo.branch_name = df_orgCorpAuth["branch_name"]  # 支店名
        mUserOrganizationInfo.org_type_code = df_orgCorpAuth[
            "org_type_code"
        ]  # 組織種別コード
        mUserOrganizationInfo.org_type = df_orgCorpAuth["org_type"]  # 組織種別
        # mUserOrganizationInfo.agreement_code = df_orgCorpAuth['agreement_code']             # 同意書取得経路コード（前端设置済）
        # mUserOrganizationInfo.agreement_name = df_orgCorpAuth['agreement_name']             # 同意書取得経路（前端设置済）
        mUserOrganizationInfo.business_type = df_orgCorpAuth[
            "business_type"
        ]  # 事業者区分
        mUserOrganizationInfo.delete_flg = False  # 削除フラグ
        mUserOrganizationInfo.created_by = user_context.get("user_id")  # 作成者

        session.add(mUserOrganizationInfo)
