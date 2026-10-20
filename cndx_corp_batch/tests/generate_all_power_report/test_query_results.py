"""DB取得行から帳票入力へ変換する現行サービスを検証する。"""

import pytest

from cndx_corp_batch.domains.generate_all_power_report.services.database_source_service import (
    DATE,
    SLOTS,
    NumericConversionError,
)
from cndx_corp_batch.domains.generate_all_power_report.services.query_result_service import (
    prepare_query_results,
    row_to_dict,
)


POINT = "0000000000000000000001"


def customer():
    return {
        "customer_name": "テスト工場",
        "address": "東京都テスト1番地",
        "customer_number": "0000000000000001",
        "contract_kw": "39",
    }


def daily(day="20260601", value="1.5"):
    return {DATE.lower(): day, **{slot.lower(): value for slot in SLOTS}}


def test_lowercase_columns_are_normalized_and_converted():
    frame, config = prepare_query_results(customer(), [daily()], POINT, "202606")
    assert len(frame) == 48
    assert frame.timestamp.iloc[-1].strftime("%H:%M") == "23:30"
    assert (frame.kw == 3).all()
    assert config["contract_kw"] == 39


def test_alias_mapping_preserves_caller_config():
    aliases = {key: f"SQL_{key.upper()}" for key in customer()}
    aliased_customer = {aliases[key]: value for key, value in customer().items()}
    slot_aliases = [f"ENERGY{i:02d}" for i in range(1, 49)]
    row = {"YMD": "20260601", **{name: str(i) for i, name in enumerate(slot_aliases)}}
    config = {"notes": "共通注記", "contract_kw": 999}
    before = dict(config)
    frame, result = prepare_query_results(
        aliased_customer,
        [row],
        POINT,
        "202606",
        customer_columns=aliases,
        date_column="YMD",
        slot_columns=slot_aliases,
        config=config,
    )
    assert frame.kw.iloc[-1] == 94
    assert result["notes"] == "共通注記"
    assert result["contract_kw"] == 39
    assert config == before


def test_invalid_customer_or_quality_data_is_rejected():
    for updates in ({"contract_kw": "0"}, {"contract_kw": "nan"}):
        invalid = {**customer(), **updates}
        with pytest.raises(ValueError):
            prepare_query_results(invalid, [daily()], POINT, "202606")
    with pytest.raises(ValueError, match="QUALITY"):
        prepare_query_results(
            customer(),
            [{**daily(), "QUALITY": "1"}],
            POINT,
            "202606",
            quality_columns=["QUALITY"],
        )


def test_row_to_dict_accepts_mapping_and_sqlalchemy_style_rows():
    assert row_to_dict({"A": 1}) == {"A": 1}

    class Row:
        _mapping = {"A": 1}

    assert row_to_dict(Row()) == {"A": 1}


def test_bad_slot_keeps_source_date_and_column_for_error_logging():
    row = daily()
    row[SLOTS[4].lower()] = "bad"
    with pytest.raises(NumericConversionError) as caught:
        prepare_query_results(customer(), [row], POINT, "202606")
    assert caught.value.primary_key == "20260601"
    assert caught.value.column == SLOTS[4]
