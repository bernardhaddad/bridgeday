import pytest

from bridgeday.config import Affiliate, ConfigError, load


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_missing_file_gives_defaults(tmp_path):
    cfg = load(tmp_path / "nope.toml")
    assert cfg.affiliates == () and cfg.adsense_client == ""


def test_base_path_from_url(tmp_path):
    cfg = load(write(tmp_path, '[site]\nbase_url = "https://x.github.io/Repo/"\n'))
    assert cfg.base_url == "https://x.github.io/Repo" and cfg.base_path == "/Repo"


@pytest.mark.parametrize(
    "text",
    [
        '[[affiliate]]\nlabel = "x"\nurl = "javascript:alert(1)"\n',
        '[[affiliate]]\nlabel = "x"\nurl = "http://plain.example"\n',
        '[ads]\nadsense_client = "pub-123"\n',
        '[analytics]\ngoatcounter = "bad code"\n',
        '[site]\ncname = "not a domain"\n',
        "[site]\nyears_ahead = 9\n",
        '[site]\ncontact = "javascript:alert(1)"\n',
    ],
)
def test_rejects_bad_values(tmp_path, text):
    with pytest.raises(ConfigError):
        load(write(tmp_path, text))


def test_affiliate_placeholders_are_encoded():
    a = Affiliate("Go", "https://ex.com/?d={start}&c={country}&r={end}")
    url = a.url(start="2027-05-06", end="2027-05-09", country="Bosnia & Herzegovina")
    assert url == "https://ex.com/?d=2027-05-06&c=Bosnia%20%26%20Herzegovina&r=2027-05-09"


def test_shipped_config_is_valid():
    from bridgeday.main import ROOT

    cfg = load(ROOT / "config.toml")
    assert cfg.base_url.startswith("https://")


@pytest.mark.parametrize(
    "url",
    ['https://x.test/a"><script>', "javascript:alert(1)//", "https://x.test/?q=1", "https://"],
)
def test_base_url_is_strict(url):
    from bridgeday.config import check_base_url

    with pytest.raises(ConfigError):
        check_base_url(url)


def test_affiliate_host_cannot_come_from_data(tmp_path):
    with pytest.raises(ConfigError):
        load(write(tmp_path, '[[affiliate]]\nlabel = "x"\nurl = "https://{country}/p"\n'))


def test_search_verification_tags(tmp_path, data_dir):
    from datetime import date

    from bridgeday.build import build

    cfg = load(write(tmp_path, '[site]\nbing_verification = "FD80ACADDD5990ADCBE29D1B200308BD"\n'))
    out = tmp_path / "dist"
    build(cfg, data_dir, out, today=date(2027, 4, 30))
    home = (out / "index.html").read_text()
    head = home.split("<body>")[0]
    assert '<meta name="msvalidate.01" content="FD80ACADDD5990ADCBE29D1B200308BD">' in head
    assert "google-site-verification" not in home
    with pytest.raises(ConfigError):
        load(write(tmp_path, '[site]\ngoogle_verification = "x\\" onload=alert(1)"\n'))
