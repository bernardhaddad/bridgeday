import json

from bridgeday.data import (
    country_year,
    generate,
    library_countries,
    load_countries,
    load_holidays,
    load_population,
    population,
    pretty,
)


def test_pretty_names():
    assert pretty("BosniaAndHerzegovina") == "Bosnia and Herzegovina"
    assert pretty("IsleOfMan") == "Isle of Man"
    assert pretty("SaintVincentAndTheGrenadines") == "Saint Vincent and the Grenadines"
    assert pretty("DRCongo") == "DR Congo"


def test_library_countries_have_names_and_real_weekends():
    by = {c["countryCode"]: c for c in library_countries()}
    assert len(by) > 200
    assert by["DE"] == {"countryCode": "DE", "name": "Germany", "weekend": [6, 7]}
    assert by["SA"]["weekend"] == [5, 6]  # Friday-Saturday
    assert by["HK"]["weekend"] == [6, 7]  # office weekend, not the legal rest day
    assert "AQ" not in by and "LB" in by


def test_country_year_splits_national_and_regional():
    rows = {(r["date"], r["name"]): r for r in country_year("DE", 2027)}
    asc = rows[("2027-05-06", "Ascension Day")]
    assert (
        asc["global"] and asc["types"] == ["Public"] and asc["localName"] == "Christi Himmelfahrt"
    )
    epiphany = rows[("2027-01-06", "Epiphany")]
    assert not epiphany["global"] and "DE-BY" in epiphany["counties"]


def test_population_keeps_countries_only():
    payload = [
        {"page": 1},
        [
            {"country": {"id": "ZH"}, "countryiso3code": "AFE", "value": 769280888},
            {"country": {"id": "DE"}, "countryiso3code": "DEU", "value": 83510950},
            {"country": {"id": "FR"}, "countryiso3code": "FRA", "value": None},
        ],
    ]
    assert population({"DE", "FR", "ZZ"}, get=lambda url: payload) == {"DE": 83510950}


def test_generate_writes_snapshot_and_survives_population_outage(tmp_path):
    (tmp_path / "population.json").write_text('{"DE": 1}')

    def down(url):
        raise RuntimeError("world bank down")

    stats = generate(tmp_path, [2027], get=down)
    assert stats["files"] + len(stats["skipped"]) == stats["countries"] > 200
    assert "LK 2027" in stats["skipped"]  # the library's Sri Lanka rules end in 2026
    assert load_population(tmp_path) == {"DE": 1}  # old snapshot kept
    assert any(c["countryCode"] == "DE" for c in load_countries(tmp_path))
    de = load_holidays(tmp_path, 2027, "DE")
    assert any(h.name == "Ascension Day" and h.day_off for h in de)
    assert json.loads((tmp_path / "2027" / "SA.json").read_text())


def test_load_holidays_flags(data_dir):
    hols = load_holidays(data_dir, 2027, "DE")
    by = {h.name: h for h in hols}
    assert by["Ascension Day"].day_off and by["Ascension Day"].local_name == "Christi Himmelfahrt"
    assert not by["Women's Day"].day_off and by["Women's Day"].regions == ("DE-BE",)
    assert not by["Reformation Day"].day_off  # an observance, not a day off
    assert load_holidays(data_dir, 2030, "DE") is None


def test_empty_population_answer_keeps_snapshot(tmp_path):
    (tmp_path / "population.json").write_text('{"DE": 1}')
    generate(tmp_path, [], get=lambda url: [{}, []])  # answers fine, but with no rows
    assert load_population(tmp_path) == {"DE": 1}
