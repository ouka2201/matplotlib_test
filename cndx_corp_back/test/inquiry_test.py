# tests/test_inquiry_api.py

import unittest

from cndx_corp_back.app import app


class InquiryApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_submit_inquiry(self):
        response = self.app.post(
            "/api/inquiry",
            json={
                "reportingYear": "1",
                "companyName": "1",
                "deploymentName": "1",
                "reptName": "1",
                "internalNumber": "1",
                "industryClassification": "1",
                "electricitySupply": "1",
                "gasBusinessName": "1",
                "otherGasBusinessName": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json)
        self.assertEqual(response.json["status"], "success")

    def test_inquiry_components(self):

        from cndx_corp_back.logic.energyinfo.inquiry_insert_component import (
            process_inquiry,
        )

        data = {
            "reportingYear": "1",
            "companyName": "1",
            "deploymentName": "1",
            "reptName": "1",
            "internalNumber": "1",
            "industryClassification": "1",
            "electricitySupply": "1",
            "gasBusinessName": "1",
            "otherGasBusinessName": "1",
        }
        result = process_inquiry(data)

        self.assertEqual(result["reportingYear"], "1")
        self.assertEqual(result["companyName"], "1")
        self.assertEqual(result["deploymentName"], "1")


if __name__ == "__main__":
    unittest.main(exit=False)
