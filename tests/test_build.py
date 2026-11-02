import json
from datetime import date

import pytest

from bridgeday.build import build
from bridgeday.config import Affiliate, Config

TODAY = date(2027, 4, 30)


def cfg(**kw):
    return Config(base_url="https://ex.github.io/Site", **kw)


def test_builds_every_page(data_dir, tmp_path):
    out = tmp_path / "dist"
    stats = build(cfg(), data_dir, out, today=TODAY)
    assert stats["countries"] == 2 and stats["years"] == [2027, 2028]
    de = (out / "de" / "2027" / "index.html").read_text()
    assert "Germany public holidays 2027" in de
    assert "Fri 7 May" in de  # the Ascension bridge day
    assert 'href="/Site/style.css"' in de
    assert '<link rel="canonical" href="https://ex.github.io/Site/de/2027/">' in de
    assert "FAQPage" in de and "Women&#x27;s Day" in de
    assert (out / "de" / "2027" / "holidays.ics").exists()
    assert (out / "de" / "2028" / "index.html").exists()
    assert not (out / "eg" / "2028").exists()  # no data, no page
    assert "url=https://ex.github.io/Site/de/2027/" in (out / "de" / "index.html").read_text()
    sitemap = (out / "sitemap.xml").read_text()
    assert "https://ex.github.io/Site/eg/2027/" in sitemap
    assert "Sitemap: https://ex.github.io/Site/sitemap.xml" in (out / "robots.txt").read_text()
    index = (out / "index.html").read_text()
    assert "Ascension Day" in index  # coming up within two weeks
    for name in ("404.html", "style.css", "about/index.html", "privacy/index.html", ".nojekyll"):
        assert (out / name).exists()


def test_monetization_off_by_default(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=TODAY)
    de = (out / "de" / "2027" / "index.html").read_text()
    assert "sponsored" not in de and "adsbygoogle" not in de and "goatcounter" not in de
    assert not (out / "ads.txt").exists() and not (out / "CNAME").exists()


def test_monetization_on(data_dir, tmp_path):
    out = tmp_path / "dist"
    c = cfg(
        adsense_client="ca-pub-1234567890123456",
        goatcounter="mysite",
        cname="holidays.example.com",
        affiliates=(Affiliate("Flights", "https://fly.example/?from={start}&to={end}"),),
    )
    build(c, data_dir, out, today=TODAY)
    de = (out / "de" / "2027" / "index.html").read_text()
    assert 'rel="sponsored nofollow noopener"' in de
    assert "https://fly.example/?from=2027-05-06&amp;to=2027-05-09" in de
    assert "commission" in de  # disclosure shown with affiliate links
    assert "client=ca-pub-1234567890123456" in de and "mysite.goatcounter.com" in de
    assert (out / "ads.txt").read_text().startswith("google.com, pub-1234567890123456, DIRECT")
    assert (out / "CNAME").read_text().strip() == "holidays.example.com"
    assert "AdSense" in (out / "privacy" / "index.html").read_text()


def test_untrusted_names_are_escaped(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=TODAY)
    eg = (out / "eg" / "2027" / "index.html").read_text()
    assert "<script>alert(1)</script>" not in eg
    assert "&lt;script&gt;" in eg
    for block in eg.split('<script type="application/ld+json">')[1:]:
        json.loads(block.split("</script>")[0])  # JSON-LD stays parseable


def test_refuses_to_wipe_a_foreign_directory(data_dir, tmp_path):
    out = tmp_path / "precious"
    out.mkdir()
    (out / "notes.txt").write_text("mine")
    with pytest.raises(SystemExit):
        build(cfg(), data_dir, out, today=TODAY)
    assert (out / "notes.txt").exists()


def test_rebuild_replaces_previous_output(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=TODAY)
    (out / "stale.html").write_text("old")
    build(cfg(), data_dir, out, today=TODAY)
    assert not (out / "stale.html").exists()


def test_from_october_the_index_points_at_next_year(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=date(2027, 10, 30))
    assert 'href="/Site/de/2028/"' in (out / "index.html").read_text()
    assert "/Site/de/2028/" in (out / "de" / "index.html").read_text()
    assert 'href="/Site/eg/2027/"' in (out / "index.html").read_text()  # no 2028 data for EG


def test_current_year_only_offers_plans_still_ahead(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=date(2027, 6, 1))  # after Ascension, before Christmas
    de = (out / "de" / "2027" / "index.html").read_text()
    plans = de.split("Best days to take off")[1].split("Make the most")[0]
    assert "Fri 7 May" not in plans  # Christmas 2027 is a weekend: nothing left to bridge
    assert "No weekday holidays left to bridge in 2027" in plans
    assert "Plans below start from today, Tue 1 Jun" in de
    assert 'href="/Site/de/2028/">Plan 2028 now' in de
    nxt = (out / "de" / "2028" / "index.html").read_text()
    assert "start from today" not in nxt


def test_json_ld_has_no_markup_characters():
    from bridgeday.render import json_ld

    out = json_ld({"a": "<!--<script></script>&"})
    assert "<" not in out and ">" not in out and "&" not in out
    assert json.loads(out) == {"a": "<!--<script></script>&"}


def test_refuses_to_wipe_a_repository(data_dir, tmp_path):
    out = tmp_path / "repo"
    (out / ".git").mkdir(parents=True)
    (out / ".bridgeday-build").write_text("")
    with pytest.raises(SystemExit):
        build(cfg(), data_dir, out, today=TODAY)
    assert (out / ".git").exists()


def test_sitemap_has_one_url_per_line(data_dir, tmp_path):
    out = tmp_path / "dist"
    stats = build(cfg(), data_dir, out, today=TODAY)
    lines = [ln for ln in (out / "sitemap.xml").read_text().splitlines() if "<loc>" in ln]
    assert len(lines) == stats["pages"]  # the workflow's smoke test counts lines


def test_fetch_covers_the_january_after_the_last_page():
    from bridgeday.build import years_for, years_to_fetch

    assert years_for(TODAY, cfg()) == [2027, 2028]
    assert years_to_fetch(TODAY, cfg()) == [2027, 2028, 2029]


def test_coming_up_crosses_new_year(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(cfg(), data_dir, out, today=date(2027, 12, 22))
    up = (out / "index.html").read_text().split("Coming up")[1]
    assert "Christmas Day" in up and "Sat 1 Jan" in up


def test_shop_box_only_for_countries_on_sale(data_dir, tmp_path):
    from bridgeday.config import Shop

    out = tmp_path / "dist"
    shop = Shop(
        url="https://s.example/products/{slug}-{year}-leave-planner",
        price="$4.99",
        countries=frozenset({"DE"}),
        bundle_url="https://s.example/products/all",
        bundle_price="$19",
    )
    build(cfg(shop=shop), data_dir, out, today=TODAY)
    de = (out / "de" / "2027" / "index.html").read_text()
    assert 'href="https://s.example/products/germany-2027-leave-planner"' in de
    assert "Get the planner · $4.99" in de
    assert "Get the planner" not in (out / "eg" / "2027" / "index.html").read_text()
    assert "Get the bundle · $19" in (out / "index.html").read_text()
    assert not list(out.rglob("*.pdf"))  # the product never ships with the free site
