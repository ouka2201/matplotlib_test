import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

from flask import Flask
from flask.testing import FlaskClient

from cndx_corp_back.api.file.check_transfer_api import FileCheckTransferApi


class TestFileCheckTransferApi(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.client = self.app.test_client()
        self.view = FileCheckTransferApi.as_view("check_transfer_api")
        self.app.add_url_rule("/check-transfer", view_func=self.view, methods=["POST"])

    @patch("cndx_corp_back.api.file.check_transfer_api.FileCheckTransferService")
    def test_post_success(self, MockService):
        mock_service_instance = MockService.return_value
        mock_service_instance.execute.return_value = {"error_message_list": []}

        response = self.client.post(
            "/check-transfer", json={"file_base64": "dummy_data"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"error_message_list": []})

    @patch("cndx_corp_back.api.file.check_transfer_api.FileCheckTransferService")
    def test_post_error(self, MockService):
        mock_service_instance = MockService.return_value
        mock_service_instance.execute.return_value = {"error_message_list": ["Error"]}

        response = self.client.post(
            "/check-transfer", json={"file_base64": "dummy_data"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"error_message_list": ["Error"]})

    @patch("cndx_corp_back.api.file.check_transfer_api.FileCheckTransferService")
    def test_post_unexpected_error(self, MockService):
        mock_service_instance = MockService.return_value
        mock_service_instance.execute.side_effect = Exception("Unexpected error")

        response = self.client.post(
            "/check-transfer", json={"file_base64": "dummy_data"}
        )
        self.assertEqual(response.status_code, 500)

    @patch("cndx_corp_back.api.file.check_transfer_api.FileCheckTransferService")
    def test_post_file_upload(self, MockService):
        mock_service_instance = MockService.return_value
        mock_service_instance.execute.return_value = {"error_message_list": []}

        # テスト用のファイルを作成
        data = {"file": (BytesIO(b"dummy file content"), "test_file.xlsx")}

        response = self.client.post(
            "/check-transfer", content_type="multipart/form-data", data=data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"error_message_list": []})


if __name__ == "__main__":
    unittest.main()
