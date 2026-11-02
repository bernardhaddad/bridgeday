"""Hand-kept corrections over the holidays library (src/bridgeday/corrections.json)."""

import json
from pathlib import Path

from bridgeday.data import (
    CORRECTIONS,
    apply_corrections,
    check_corrections,
    country_year,
    load_corrections,
)

SNAPSHOT = Path(__file__).resolve().parents[1] / "data"
ROWS = [
    {
        "date": "2026-01-01",
        "name": "New Year",
        "localName": "",
        "global": True,
        "types": ["Public"],
        "counties": None,
    },
    {
        "date": "2026-03-08",
        "name": "Old Day",
        "localName": "",
        "global": True,
        "types": ["Public"],
        "counties": None,
    },
    {
        "date": "2026-04-03",
        "name": "Good Friday",
        "localName": "",
        "global": True,
        "types": ["Public"],
        "counties": None,
    },
    {
        "date": "2026-06-16",
        "name": "Feast (estimated)",
        "localName": "",
        "global": True,
        "types": ["Public"],
        "counties": None,
    },
]


def fix(op, **kw):
    return {"cc": "XX", "op": op, "source": "https://example.gov/notice", **kw}


def test_each_operation():
    corrections = [
        fix("add", date="2026-02-02", name="New Day", regions=None),
        fix("add", date="2026-05-05", name="Local Day", regions=["XX-A"]),
        fix("remove", date="2026-03-08", name="Old Day"),
        fix("move", date="2026-06-16", name="Feast (estimated)", to="2026-06-17", to_name="Feast"),
        fix("rename", date="2026-01-01", name="New Year", to_name="New Year's Day"),
        fix("observance", date="2026-04-03", name="Good Friday"),
        fix("add", date="2027-01-01", name="Other year", regions=None),  # not this year
        fix("add", date="2026-01-01", name="Elsewhere", cc="YY"),  # not this country
    ]
    rows, unmatched = apply_corrections("XX", 2026, ROWS, corrections)
    by = {(r["date"], r["name"]): r for r in rows}
    assert unmatched == []
    assert (
        by[("2026-02-02", "New Day")]["global"]
        and by[("2026-02-02", "New Day")]["counties"] is None
    )
    local = by[("2026-05-05", "Local Day")]
    assert not local["global"] and local["counties"] == ["XX-A"]
    assert ("2026-03-08", "Old Day") not in by
    assert ("2026-06-17", "Feast") in by and ("2026-06-16", "Feast (estimated)") not in by
    assert ("2026-01-01", "New Year's Day") in by
    assert by[("2026-04-03", "Good Friday")]["types"] == ["Observance"]
    assert all(r["source"] == "https://example.gov/notice" for r in rows)  # every row touched
    assert [r["date"] for r in rows] == sorted(r["date"] for r in rows)
    assert ROWS[1]["name"] == "Old Day"  # the input rows are not mutated


def test_corrections_that_match_nothing_are_reported():
    stale = [
        fix("remove", date="2026-03-09", name="Old Day"),
        fix("add", date="2026-01-01", name="New Year", regions=None),  # already there
    ]
    rows, unmatched = apply_corrections("XX", 2026, ROWS, stale)
    assert unmatched == stale and len(rows) == len(ROWS)


def test_shipped_corrections_are_well_formed():
    corrections = load_corrections()
    assert len(corrections) > 200
    ops = {"add", "remove", "move", "rename", "scope", "observance"}
    for c in corrections:
        assert c["op"] in ops and len(c["cc"]) == 2 and c["date"][:2] == "20", c
        assert c["source"].startswith(("https://", "http://")), c
        assert c["op"] != "move" or c["to"][:4] == c["date"][:4], c


def test_corrections_take_effect_on_generated_rows():
    # Hong Kong general holidays come from the library's "optional" category.
    hk = {(r["date"], r["name"]) for r in country_year("HK", 2026)}
    assert ("2026-04-03", "Good Friday") in hk
    # Burkina Faso's 2026 law dropped Easter Monday and added 15 May.
    bf = {(r["date"], r["name"]) for r in country_year("BF", 2026)}
    assert ("2026-04-06", "Easter Monday") not in bf
    assert ("2026-05-15", "Day of Customs and Traditions") in bf
    # Syria's Decree 188 of 2025.
    sy = {r["date"] for r in country_year("SY", 2027)}
    assert "2027-03-18" in sy and "2027-03-08" not in sy


def test_committed_snapshot_has_every_correction():
    assert check_corrections(SNAPSHOT) == []
    assert json.loads(CORRECTIONS.read_text())
