"""
ユーザー権限情報取得モジュールのテスト
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from cndx_corp_back.api.auth.util.user_permissions import get_user_permissions
from cndx_corp_back.entity.m_organization_authority_info_entity import (
    MOrganizationAuthorityInfo,
)
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo


@pytest.fixture
def mock_session():
    """モックセッション"""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_org_info():
    """モック組織情報"""
    org_info = MagicMock()
    org_info.org_type_code = "01"
    org_info.org_name = "テスト組織"
    return org_info


@pytest.fixture
def mock_authorities():
    """モック権限情報"""
    auth1 = MagicMock()
    auth1.authority_id = 1
    auth1.authority_code = "A"
    auth2 = MagicMock()
    auth2.authority_id = 2
    auth2.authority_code = "B"
    return [auth1, auth2]


def test_get_user_permissions_success(mock_session, mock_org_info, mock_authorities):
    """正常系: ユーザー権限情報を取得できる"""
    # 組織情報のクエリをモック
    org_query = MagicMock()
    org_filter = MagicMock()
    org_filter.first.return_value = mock_org_info
    org_query.filter.return_value = org_filter
    mock_session.query.return_value = org_query

    # 権限情報のクエリをモック
    auth_query = MagicMock()
    auth_filter = MagicMock()
    auth_filter.all.return_value = mock_authorities
    auth_query.filter.return_value = auth_filter

    # query()が呼ばれたときに、MUserOrganizationInfoの場合はorg_query、MOrganizationAuthorityInfoの場合はauth_queryを返す
    def query_side_effect(*args):
        if args and args[0] == MUserOrganizationInfo:
            return org_query
        elif args and args[0] == MOrganizationAuthorityInfo:
            return auth_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    # テスト実行
    result = get_user_permissions(mock_session, "ORG01", "admin")

    # 検証
    assert result["role"] == "admin"
    assert result["org_type_code"] == "01"
    assert result["org_name"] == "テスト組織"
    assert result["authority_code_map"] == [(1, "A"), (2, "B")]


def test_get_user_permissions_org_not_found(mock_session):
    """異常系: 組織情報が存在しない場合"""
    # 組織情報のクエリをモック（Noneを返す）
    org_query = MagicMock()
    org_filter = MagicMock()
    org_filter.first.return_value = None
    org_query.filter.return_value = org_filter

    def query_side_effect(*args):
        if args and args[0] == MUserOrganizationInfo:
            return org_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    # テスト実行
    with pytest.raises(ValueError, match="利用者組織情報"):
        get_user_permissions(mock_session, "ORG01", "admin")


def test_get_user_permissions_empty_authorities(mock_session, mock_org_info):
    """正常系: 権限情報が空の場合"""
    # 組織情報のクエリをモック
    org_query = MagicMock()
    org_filter = MagicMock()
    org_filter.first.return_value = mock_org_info
    org_query.filter.return_value = org_filter

    # 権限情報のクエリをモック（空のリストを返す）
    auth_query = MagicMock()
    auth_filter = MagicMock()
    auth_filter.all.return_value = []  # 空のリスト
    auth_query.filter.return_value = auth_filter

    def query_side_effect(*args):
        if args and args[0] == MUserOrganizationInfo:
            return org_query
        elif args and args[0] == MOrganizationAuthorityInfo:
            return auth_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    # テスト実行
    result = get_user_permissions(mock_session, "ORG01", "admin")

    # 検証
    assert result["role"] == "admin"
    assert result["org_type_code"] == "01"
    assert result["org_name"] == "テスト組織"
    assert result["authority_code_map"] == []  # 空のリスト


def test_get_user_permissions_authority_code_filtered(mock_session, mock_org_info):
    """正常系: authority_code='2'の権限は除外される"""
    # 組織情報のクエリをモック
    org_query = MagicMock()
    org_filter = MagicMock()
    org_filter.first.return_value = mock_org_info
    org_query.filter.return_value = org_filter

    # 権限情報のクエリをモック（authority_code='2'を含む）
    auth1 = MagicMock()
    auth1.authority_id = 1
    auth1.authority_code = "A"
    auth2 = MagicMock()
    auth2.authority_id = 2
    auth2.authority_code = "2"  # 除外されるべき権限コード
    auth3 = MagicMock()
    auth3.authority_id = 3
    auth3.authority_code = "B"

    auth_query = MagicMock()
    auth_filter = MagicMock()
    # filter()でauthority_code != '2'が適用されるため、auth2は除外される
    auth_filter.all.return_value = [auth1, auth3]
    auth_query.filter.return_value = auth_filter

    def query_side_effect(*args):
        if args and args[0] == MUserOrganizationInfo:
            return org_query
        elif args and args[0] == MOrganizationAuthorityInfo:
            return auth_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    # テスト実行
    result = get_user_permissions(mock_session, "ORG01", "admin")

    # 検証
    assert result["authority_code_map"] == [(1, "A"), (3, "B")]
    # authority_code='2'は除外されていることを確認
    assert (2, "2") not in result["authority_code_map"]
