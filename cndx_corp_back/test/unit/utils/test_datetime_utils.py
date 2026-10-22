import unittest
from copy import deepcopy
from datetime import datetime

from cndx_corp_back.utils.datetime_utils import format_datetimes


class TestDatetimeUtils(unittest.TestCase):

    def setUp(self):
        self.datetime_str = "2023-10-01 12:00:00"
        self.datetime_obj = datetime.strptime(self.datetime_str, "%Y-%m-%d %H:%M:%S")

    def test_format_datetimes_simple_dict(self):
        data = {"date": self.datetime_obj}
        data_before = deepcopy(data)
        expected = {"date": self.datetime_str}
        self.assertEqual(format_datetimes(data, in_place=False), expected)
        self.assertEqual(data, data_before)

    def test_format_datetimes_nested_dict(self):
        data = {"level1": {"level2": {"date": self.datetime_obj}}}
        data_before = deepcopy(data)
        expected = {"level1": {"level2": {"date": self.datetime_str}}}
        self.assertEqual(format_datetimes(data, in_place=False), expected)
        self.assertEqual(data, data_before)

    def test_format_datetimes_simple_list(self):
        data = [self.datetime_obj, {"date": self.datetime_obj}]
        data_before = deepcopy(data)
        expected = [self.datetime_str, {"date": self.datetime_str}]
        self.assertEqual(format_datetimes(data, in_place=False), expected)
        self.assertEqual(data, data_before)

    def test_format_datetimes_nested_list(self):
        data = [{"date": self.datetime_obj}, {"nested": {"date": self.datetime_obj}}]
        data_before = deepcopy(data)
        expected = [
            {"date": self.datetime_str},
            {"nested": {"date": self.datetime_str}},
        ]
        self.assertEqual(format_datetimes(data, in_place=False), expected)
        self.assertEqual(data, data_before)

    def test_format_datetimes_tuple(self):
        data = (self.datetime_obj, "test")
        expected = (self.datetime_str, "test")
        self.assertEqual(format_datetimes(data, in_place=False), expected)

    def test_format_datetimes_set(self):
        data = {self.datetime_obj, "test"}
        expected = {self.datetime_str, "test"}
        self.assertEqual(format_datetimes(data, in_place=False), expected)

    def test_format_datetimes_in_place_dict(self):
        data = {"date": self.datetime_obj}
        expected = {"date": self.datetime_str}
        self.assertEqual(format_datetimes(data), expected)
        self.assertEqual(data, expected)

    def test_format_datetimes_in_place_list(self):
        data = [{"date": self.datetime_obj}, {"nested": {"date": self.datetime_obj}}]
        expected = [
            {"date": self.datetime_str},
            {"nested": {"date": self.datetime_str}},
        ]
        self.assertEqual(format_datetimes(data, in_place=True), expected)
        self.assertEqual(data, expected)

    def test_format_datetimes_custom_format(self):
        custom_format = "%d-%m-%Y %H:%M:%S"
        data = {"date": self.datetime_obj}
        expected = {"date": self.datetime_obj.strftime(custom_format)}
        self.assertEqual(
            format_datetimes(data, fmt=custom_format, in_place=False), expected
        )


if __name__ == "__main__":
    unittest.main()
