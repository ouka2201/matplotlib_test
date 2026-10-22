from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from cndx_corp_back.logic.report.pdf_create_component import ReportPdfCreateComponent


@pytest.fixture
def component():
    return ReportPdfCreateComponent()


@pytest.fixture
def creation_info():
    return {
        "bank_code": "001",
        "branch_code": "002",
        "corporate_number": "1234567890",
        "fiscal_year": "2023",
        "registration_seq": 1,
        "current_status": "0",
    }


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
@patch("cndx_corp_back.logic.report.pdf_create_component.TSC.Server")
@patch("cndx_corp_back.logic.report.pdf_create_component.TSC.TableauAuth")
def test_execute_success(
    mock_tableau_auth, mock_server, mock_db_manager, component, creation_info
):

    mock_session = MagicMock()
    mock_db_manager.return_value.session_scope.return_value.__enter__.return_value = (
        mock_session
    )
    mock_query = SimpleNamespace(
        status="0",
        number_offices=1,
        bank_code="001",
        branch_code="002",
        corporate_number="1234567890",
        fiscal_year="2023",
        registration_seq=1,
        current_status="0",
    )
    mock_session.query.return_value.filter_by.return_value.first.return_value = (
        mock_query
    )

    mock_server_instance = mock_server.return_value
    mock_server_instance.auth.sign_in.return_value.__enter__.return_value = None
    mock_server_instance.auth.sign_in.return_value.__exit__ = Mock(return_value=None)
    mock_server_instance.workbooks.get.return_value = ([], None)
    mock_server_instance.views.populate_pdf.return_value = None

    result = component.excute(creation_info)
    assert result == "xxx://test/123.pdf"


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
def test_execute_record_not_found(mock_db_manager, component, creation_info):
    mock_session = MagicMock()
    mock_db_manager.return_value.session_scope.return_value.__enter__.return_value = (
        mock_session
    )
    mock_session.query.return_value.filter_by.return_value.first.return_value = None

    with pytest.raises(Exception) as context:
        component.excute(creation_info)
    assert str(context.value) == "該当レコードが見つかりませんでした。"


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
def test_execute_status_conflict(mock_db_manager, component, creation_info):
    mock_session = MagicMock()
    mock_db_manager.return_value.session_scope.return_value.__enter__.return_value = (
        mock_session
    )
    mock_query = SimpleNamespace(status="1")
    mock_session.query.return_value.filter_by.return_value.first.return_value = (
        mock_query
    )

    with pytest.raises(Exception) as context:
        component.excute(creation_info)
    assert (
        str(context.value)
        == "他のリクエストによりステータスが更新されたので、処理できませんでした。"
    )


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
@patch("cndx_corp_back.logic.report.pdf_create_component.TSC.Server")
@patch("cndx_corp_back.logic.report.pdf_create_component.TSC.TableauAuth")
def test_execute_tableau_error(
    mock_tableau_auth, mock_server, mock_db_manager, component, creation_info
):
    mock_session = MagicMock()
    mock_db_manager.return_value.session_scope.return_value.__enter__.return_value = (
        mock_session
    )
    mock_query = SimpleNamespace(status="0", number_offices=1)
    mock_session.query.return_value.filter_by.return_value.first.return_value = (
        mock_query
    )

    mock_server_instance = mock_server.return_value
    mock_server_instance.auth.sign_in.return_value = None
    mock_server_instance.workbooks.get.side_effect = Exception("TableauError")

    with pytest.raises(Exception) as context:
        component.excute(creation_info)
    assert str(context.value) == "レポートの生成が失敗しました。"


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
def test_execute_db_connection_error(mock_db_manager, component, creation_info):
    mock_db_manager.return_value.session_scope.side_effect = Exception(
        "データベース接続エラーが発生しました。"
    )

    with pytest.raises(Exception) as context:
        component.excute(creation_info)
    assert str(context.value) == "データベース接続エラーが発生しました。"


@patch("cndx_corp_back.common.database_manager.DatabaseManager")
def test_execute_unexpected_error(mock_db_manager, component, creation_info):
    mock_session = MagicMock()
    mock_db_manager.return_value.session_scope.return_value.__enter__.return_value = (
        mock_session
    )
    mock_session.query.side_effect = Exception("予想外のエラーが発生しました。")

    with pytest.raises(Exception) as context:
        component.excute(creation_info)
    assert str(context.value) == "レポートの生成が失敗しました。"
