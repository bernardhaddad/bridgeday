"""Regression tests on real generated data, one per finding of the dataset audit."""

import json
from datetime import date

import pytest

from bridgeday.data import generate, library_countries, load_countries, load_holidays
from bridgeday.insights import compute, country_daily

POP = {
    "RU": 144_000_000,
    "CN": 1_410_000_000,
    "DE": 83_000_000,
    "AU": 27_000_000,
    "GB": 69_000_000,
    "NO": 5_500_000,
    "LK": 22_000_000,
    "VE": 28_000_000,
}


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    # A full-sized answer (a short one is rejected as truncated): POP values for the countries
    # the tests look at, 1,000 people for every other country.
    codes = [c["countryCode"] for c in library_countries()]
    payload = [{}, [{"country": {"id": cc}, "value": POP.get(cc, 1000)} for cc in codes]]
    generate(d, [2026, 2027, 2028], get=lambda url: payload)
    return d


@pytest.fixture(scope="module")
def rows(real):
    ix = compute(real, 2027)
    return {(r["country"], r["date"]): r for r in country_daily(ix)}, ix


def test_countries_outside_the_library_range_are_skipped(real):
    assert load_holidays(real, 2026, "LK") and load_holidays(real, 2027, "LK") is None


def test_breaks_that_start_last_year_count(rows):
    by, _ = rows
    assert by[("RU", "2027-01-01")]["long_break_days"] >= 8


def test_declared_weekend_workdays_are_open(rows):
    by, _ = rows
    sat = by[("RU", "2027-02-20")]
    assert sat["declared_workday"] == 1 and sat["open"] == 1 and sat["weekend"] == 0


def test_near_nationwide_regional_holidays_count(real):
    off = {h.day for h in load_holidays(real, 2027, "AU") if h.day_off}
    assert {date(2027, 12, 27), date(2027, 12, 28)} <= off  # every state, different names
    gb = {h.day for h in load_holidays(real, 2027, "GB") if h.day_off}
    assert date(2027, 3, 29) not in gb  # Easter Monday: Scotland works, 3 of 4 is not 90%


def test_local_names_never_pair_by_position(real):
    for h in load_holidays(real, 2027, "NO"):
        if h.day == date(2027, 5, 17):
            assert h.local_name in ("", "Grunnlovsdag")


def test_bridge_days_sit_between_holiday_and_weekend(rows):
    by, _ = rows
    assert by[("DE", "2027-05-07")]["bridge_day_unlocks"] == 4  # Fri after Ascension Thursday
    assert by[("DE", "2027-01-04")]["bridge_day_unlocks"] == 0  # Mon after New Year Friday


def test_office_weekends(real):
    weekend = {c["countryCode"]: c["weekend"] for c in load_countries(real)}
    assert weekend["VE"] == [6, 7] and weekend["SO"] == [5] and weekend["MR"] == [6, 7]
    assert weekend["SA"] == [5, 6] and weekend["NP"] == [6]


def test_daily_country_covers_every_country(rows, real):
    by, ix = rows
    n = len(
        [c for c in load_countries(real) if load_holidays(real, 2027, c["countryCode"]) is not None]
    )
    assert len(by) == n * 365 and len(ix.weighted) == n  # every country has a figure here
    assert "LK" not in {c.cc for c in ix.countries}  # no 2027 rules in the library


def test_public_holiday_columns_reconcile(rows):
    by, ix = rows
    for r in ix.daily():
        total = sum(
            int(v["population"] or 0)
            for (cc, d), v in by.items()
            if d == r["date"] and v["public_holiday"]
        )
        assert total == r["people_on_public_holiday"]


def test_workdays_file_written(real):
    wd = json.loads((real / "2027" / "_workdays.json").read_text())
    assert "2027-02-20" in wd["RU"]
