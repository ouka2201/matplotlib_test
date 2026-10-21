"""顧客情報と30分値データ連携用のテストデータ投入PGを検証する。"""

from sqlalchemy import create_engine, text
import pytest

from cndx_corp_batch.test.insert_link_customer_30min_data import (
    SeedOptions,
    seed_database,
)


def settings_for(tmp_path):
    return {"url": f"sqlite:///{tmp_path / 'seed.db'}", "schema": None}


def rows(engine, query):
    with engine.connect() as connection:
        return connection.execute(text(query)).mappings().all()


def test_seed_creates_all_source_rows(tmp_path):
    settings = settings_for(tmp_path)
    result = seed_database(
        settings,
        SeedOptions(
            target_month="2026-03",
            count=2,
            days=2,
            init_sqlite=True,
        ),
    )

    assert result["tables"]["management"]["inserted"] == 2
    assert result["tables"]["daily"]["inserted"] == 4
    engine = create_engine(settings["url"])
    try:
        management = rows(
            engine,
            "SELECT * FROM t_30min_import_mng ORDER BY supply_point_number",
        )
        daily = rows(
            engine,
            "SELECT * FROM t_ep_electricity_data_30min ORDER BY t01_get_ymd",
        )
        assert [row["CREATE_STATUS"] for row in management] == ["3", "3"]
        assert len(daily) == 4
        assert daily[0]["T01_30T_SYR01"] == "1.2511"
        assert daily[0]["T01_KSKJ_KSU"] == "0"
        assert daily[0]["CREATED_BY"] == "customer_30min_test_seed"
        assert daily[0]["CREATED_AT"] is not None
    finally:
        engine.dispose()


def test_existing_rows_can_be_skipped(tmp_path):
    settings = settings_for(tmp_path)
    options = SeedOptions(
        target_month="2026-03",
        count=1,
        days=1,
        init_sqlite=True,
    )
    seed_database(settings, options)

    result = seed_database(
        settings,
        SeedOptions(
            target_month="2026-03",
            count=1,
            days=1,
            on_existing="skip",
        ),
    )

    assert all(
        counts == {"inserted": 0, "skipped": 1}
        for counts in result["tables"].values()
    )


def test_dry_run_does_not_insert_rows(tmp_path):
    settings = settings_for(tmp_path)
    result = seed_database(
        settings,
        SeedOptions(
            target_month="2026-02",
            count=1,
            days=1,
            dry_run=True,
            init_sqlite=True,
        ),
    )

    assert result["tables"]["daily"]["inserted"] == 1
    engine = create_engine(settings["url"])
    try:
        assert rows(engine, "SELECT * FROM t_30min_import_mng") == []
        assert rows(engine, "SELECT * FROM t_ep_electricity_data_30min") == []
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "options",
    [
        SeedOptions(target_month="2026/03"),
        SeedOptions(target_month="2026-02", days=30),
        SeedOptions(target_month="2026-03", point_prefix="x"),
    ],
)
def test_invalid_options_are_rejected(options):
    with pytest.raises(ValueError):
        options.period()
