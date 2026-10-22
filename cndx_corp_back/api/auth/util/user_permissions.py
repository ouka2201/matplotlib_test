"""
ユーザー権限情報取得モジュール
"""

from sqlalchemy.orm import scoped_session

from cndx_corp_back.entity.m_organization_authority_info_entity import (
    MOrganizationAuthorityInfo,
)
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.utils.utils import get_message


def get_user_permissions(db_session: scoped_session, user_org_id: str, role: str):
    """
    ユーザーの権限情報を取得

    Args:
        db_session: データベースセッション
        user_org_id: 組織ID
        role: ユーザーロール

    Raises:
        ValueError: 利用者組織情報が存在しない場合

    Returns:
        dict: 権限情報辞書
            - role: ユーザーロール
            - org_type_code: 組織種別コード
            - org_name: 組織名
            - authority_code_map: 権限コードマップ（(authority_id, authority_code)のリスト）
    """
    # 組織情報取得
    org_info = (
        db_session.query(MUserOrganizationInfo)
        .filter(
            MUserOrganizationInfo.org_id == user_org_id,
            MUserOrganizationInfo.delete_flg.is_not(True),
        )
        .first()
    )

    if not org_info:
        raise ValueError(get_message("NOT_EXIST", field="利用者組織情報"))

    org_type_code = org_info.org_type_code

    # 権限情報取得
    authorities = (
        db_session.query(MOrganizationAuthorityInfo)
        .filter(
            MOrganizationAuthorityInfo.org_type_code == org_type_code,
            MOrganizationAuthorityInfo.user_role == role,
            MOrganizationAuthorityInfo.authority_code != "2",  # TODO コードマスタ
            MOrganizationAuthorityInfo.delete_flg.is_not(
                True
            ),  # TODO コンスタンツ化するか
        )
        .all()
    )

    auth_info = {
        "role": role,
        "org_type_code": org_type_code,
        "org_name": org_info.org_name,
        "authority_code_map": [
            (item.authority_id, item.authority_code) for item in authorities
        ],
    }
    return auth_info
