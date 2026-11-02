import csv
import io
import json
import zipfile
from datetime import date

from bridgeday.build import build
from bridgeday.config import Config, Shop
from bridgeday.insights import compute, country_daily, millions
from bridgeday.products import build_dataset


def with_population(data_dir):
    (data_dir / "population.json").write_text(json.dumps({"DE": 80_000_000, "EG": 100_000_000}))
    return data_dir


def test_index_weights_by_population(data_dir):
    ix = compute(with_population(data_dir), 2027)
    assert ix.world_population == 180_000_000 and len(ix.days) == 365
    day = {r["date"]: r for r in ix.daily()}
    asc = day["2027-05-06"]  # Ascension, Thursday, Germany only
    assert asc["people_on_public_holiday"] == 80_000_000
    assert asc["countries_on_public_holiday"] == "DE"
    assert asc["people_on_weekday_holiday"] == 80_000_000
    assert day["2027-05-07"]["people_on_bridge_day"] == 80_000_000  # Friday bridge
    eg = day["2027-07-01"]  # Egypt's Thursday holiday runs into its Fri-Sat weekend
    assert eg["people_in_long_break"] == 100_000_000
    # Friday: Egypt's weekend (closed), Germany working: 80 of 180 million open.
    assert day["2027-07-02"]["share_of_world_open"] == round(80 / 180, 4)


def test_countries_without_population_are_listed_not_guessed(data_dir):
    (data_dir / "population.json").write_text(json.dumps({"DE": 80_000_000}))
    ix = compute(data_dir, 2027)
    assert ix.missing_population == ["EG"] and ix.world_population == 80_000_000
    assert [c.cc for c in ix.weighted] == ["DE"]
    rows = country_daily(ix)
    assert {r["country"] for r in rows} == {"DE", "EG"}  # kept, with a blank population
    assert next(r for r in rows if r["country"] == "EG")["population"] == ""


def test_pairs_count_shared_working_days(data_dir):
    ix = compute(with_population(data_dir), 2027)
    (pair,) = ix.pairs()
    assert pair["country_a"] == "DE" and pair["country_b"] == "EG"
    assert sum(v for k, v in pair.items() if k.startswith(("both", "only"))) == 365


def test_dataset_zip(data_dir, tmp_path):
    path = build_dataset(Config(), with_population(data_dir), tmp_path, 2027)
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert names == {
            "README.md",
            "daily_world_2027.csv",
            "daily_country_2027.csv",
            "country_pairs_2027.csv",
            "biggest_long_weekends_2027.csv",
        }
        rows = list(csv.DictReader(io.StringIO(z.read("daily_country_2027.csv").decode())))
        assert len(rows) == 365 * 2
        asc = next(r for r in rows if r["date"] == "2027-05-06" and r["country"] == "DE")
        assert asc["holiday_name"] == "Ascension Day" and asc["open"] == "0"
        assert "World Bank" in z.read("README.md").decode()


def test_global_page_published_with_dataset_box(data_dir, tmp_path):
    out = tmp_path / "dist"
    shop = Shop(dataset_url="https://s.example/dataset", dataset_price="$149")
    build(
        Config(base_url="https://ex.github.io/Site", shop=shop),
        with_population(data_dir),
        out,
        today=date(2027, 4, 30),
    )
    page = (out / "global" / "2027" / "index.html").read_text()
    assert "The world&#x27;s long weekends in 2027" in page
    assert "Get the dataset · $149" in page and '"@type": "Dataset"' in page
    assert "https://ex.github.io/Site/global/2027/" in (out / "sitemap.xml").read_text()
    assert not list(out.rglob("*.csv")) and not list(out.rglob("*.zip"))  # paid data stays out


def test_millions():
    assert millions(4_910_000_000) == "4.91 billion" and millions(775_400_000) == "775 million"
