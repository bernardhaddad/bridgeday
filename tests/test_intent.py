import json
import zipfile
from datetime import date

from bridgeday import intent
from bridgeday.build import build
from bridgeday.config import Config
from bridgeday.products import build_dataset

ASC = ("DE", date(2027, 5, 6), date(2027, 5, 9))


def test_event_paths_round_trip_and_reject_junk():
    p = intent.event_path("DE", ASC[1], ASC[2])
    assert p == "intent-de-2027-05-06_2027-05-09" and intent.parse(p) == ASC
    assert intent.parse("/" + p) == ASC  # GoatCounter may report a leading slash
    for bad in (
        "intent-de-2027-05-09_2027-05-06",
        "intent-xx-2027-13-01_2027-13-02",
        "intent-de-2027-01-01_2027-06-01",
        "de/2027/",
        "intent-DE-2027-05-06_2027-05-09",
    ):
        assert intent.parse(bad) is None


def test_pull_follows_pages_and_keeps_intent_events_only():
    pages = [
        {
            "hits": [
                {"path_id": 1, "path": "intent-de-2027-05-06_2027-05-09", "count": 7},
                {"path_id": 2, "path": "/de/2027/", "count": 900},
            ],
            "more": True,
        },
        {
            "hits": [{"path_id": 3, "path": "intent-fr-2027-05-06_2027-05-09", "count": 2}],
            "more": False,
        },
    ]
    seen = []

    def get(code, token, params):
        seen.append(params.get("exclude_paths"))
        return pages[len(seen) - 1]

    counts = intent.pull("site", "tok", date(2026, 1, 1), date(2027, 1, 1), get=get)
    assert counts == {"intent-de-2027-05-06_2027-05-09": 7, "intent-fr-2027-05-06_2027-05-09": 2}
    assert seen == [None, [1, 2]]


def test_badge_needs_enough_people(tmp_path):
    p = tmp_path / "intent.json"
    intent.save(p, {"intent-de-2027-05-06_2027-05-09": 4})
    assert intent.most_chosen(intent.load(p), "DE", 2027) is None
    intent.save(p, {"intent-de-2027-05-06_2027-05-09": 5, "intent-de-2027-12-24_2027-12-27": 3})
    assert intent.most_chosen(intent.load(p), "de", 2027) == (ASC[1], ASC[2])


def test_dataset_rows_drop_small_counts():
    intents = {
        ASC: 6,
        ("DE", date(2027, 12, 24), date(2027, 12, 27)): 2,
        ("FR", date(2027, 5, 6), date(2027, 5, 9)): 3,
    }
    rows = intent.dataset_rows(intents, 2027, {"DE": 83_000_000})
    assert [(r["country"], r["planners"]) for r in rows] == [("DE", 6), ("FR", 3)]
    assert rows[0]["share_of_country_planners"] == 0.75 and rows[1]["country_population"] == ""


def test_site_badge_and_counting_hook(data_dir, tmp_path):
    out = tmp_path / "dist"
    cfg = Config(base_url="https://ex.github.io/Site", goatcounter="mysite")
    build(cfg, data_dir, out, today=date(2027, 4, 30), intents={ASC: 9})
    de = (out / "de" / "2027" / "index.html").read_text()
    assert "🔥 Most chosen by planners" in de and "goatcounter.count({path: &#x27;" not in de
    assert "window.goatcounter.count({path: 'intent-'" in de
    assert 'data-start="2027-05-06" data-end="2027-05-09"' in de
    plain = tmp_path / "plain"
    build(Config(base_url="https://ex.github.io/Site"), data_dir, plain, today=date(2027, 4, 30))
    assert "goatcounter" not in (plain / "de" / "2027" / "index.html").read_text()


def test_dataset_carries_intent_file(data_dir, tmp_path):
    (data_dir / "population.json").write_text(json.dumps({"DE": 83_000_000}))
    path = build_dataset(Config(), data_dir, tmp_path, 2027, intents={ASC: 6})
    with zipfile.ZipFile(path) as z:
        assert "leave_intent_2027.csv" in z.namelist()
        assert (
            "DE,2027-05-06,2027-05-09,4,6,1.0,83000000" in z.read("leave_intent_2027.csv").decode()
        )
