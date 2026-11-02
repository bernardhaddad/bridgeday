"""Site and monetization settings, read from config.toml. Empty values switch a feature off."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

PLACEHOLDERS = ("start", "end", "country", "cc", "year", "slug")
ADSENSE_RE = re.compile(r"^ca-pub-\d{10,20}$")
GOATCOUNTER_RE = re.compile(r"^[a-z0-9-]{1,63}$")
VERIFY_RE = re.compile(r"[A-Za-z0-9_-]{10,100}")  # search-console verification codes
CNAME_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$")


def slug(s: str) -> str:
    """The URL handle Shopify derives from a title: lowercase words joined by hyphens."""
    import unicodedata

    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Affiliate:
    label: str
    template: str

    def url(self, **values: str) -> str:
        out = self.template
        for k in PLACEHOLDERS:
            out = out.replace("{" + k + "}", quote(values.get(k, ""), safe=""))
        return out


@dataclass(frozen=True)
class Shop:
    """Where the printable planner is sold. url may use {cc} {year} {country}."""

    url: str = ""
    price: str = ""
    countries: frozenset[str] = frozenset()  # {"*"} means every country
    bundle_url: str = ""
    bundle_price: str = ""
    dataset_url: str = ""
    dataset_price: str = ""

    def sells(self, cc: str) -> bool:
        return bool(self.url) and ("*" in self.countries or cc.upper() in self.countries)

    def link(self, cc: str, year: int, country: str) -> str:
        vals = {"cc": cc.lower(), "year": str(year), "country": country, "slug": slug(country)}
        return Affiliate("shop", self.url).url(**vals)


@dataclass(frozen=True)
class Config:
    name: str = "Bridgeday"
    tagline: str = "More time with the people you love, from the same days of leave"
    base_url: str = "http://localhost:8000"
    cname: str = ""
    google_verification: str = ""
    bing_verification: str = ""
    contact: str = ""
    years_ahead: int = 1
    goatcounter: str = ""
    adsense_client: str = ""
    affiliates: tuple[Affiliate, ...] = field(default_factory=tuple)
    shop: Shop = field(default_factory=Shop)
    disclosure: str = (
        "Some links are affiliate links: if you book through them we may earn a commission, "
        "at no extra cost to you."
    )

    @property
    def base_path(self) -> str:
        return urlsplit(self.base_url).path.rstrip("/")


PATH_RE = re.compile(r"(/[A-Za-z0-9._~-]+)*")
HOST_RE = re.compile(r"[A-Za-z0-9.-]+(:\d{1,5})?")


def check_base_url(url: str) -> str:
    """http(s)://host[/plain/path] and nothing else: it is pasted into every page."""
    url = url.strip().rstrip("/")
    p = urlsplit(url)
    if (
        p.scheme not in ("http", "https")
        or not HOST_RE.fullmatch(p.netloc)
        or p.query
        or p.fragment
        or not PATH_RE.fullmatch(p.path)
    ):
        raise ConfigError(f"site.base_url must look like https://host/path, got {url!r}")
    return url


def _https(url: str, what: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ConfigError(f"{what} must be an https:// URL, got {url!r}")
    return url


def load(path: Path) -> Config:
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text())
    site, ads, an = raw.get("site", {}), raw.get("ads", {}), raw.get("analytics", {})
    base_url = check_base_url(str(site.get("base_url") or Config.base_url))
    cname = str(site.get("cname") or "").strip().lower()
    google_v = str(site.get("google_verification") or "").strip()
    bing_v = str(site.get("bing_verification") or "").strip()
    for key, val in (("google_verification", google_v), ("bing_verification", bing_v)):
        if val and not VERIFY_RE.fullmatch(val):
            raise ConfigError(f"site.{key} must be the content value of the meta tag, got {val!r}")
    if cname and not CNAME_RE.match(cname):
        raise ConfigError(f"site.cname is not a domain: {cname!r}")
    contact = str(site.get("contact") or "").strip()
    if contact and not (contact.startswith("mailto:") and "@" in contact):
        contact = _https(contact, "site.contact")
    adsense = str(ads.get("adsense_client") or "").strip()
    if adsense and not ADSENSE_RE.match(adsense):
        raise ConfigError(f"ads.adsense_client must look like ca-pub-1234567890, got {adsense!r}")
    gc = str(an.get("goatcounter") or "").strip().lower()
    if gc and not GOATCOUNTER_RE.match(gc):
        raise ConfigError(f"analytics.goatcounter must be your site code, got {gc!r}")
    affiliates = []
    for item in raw.get("affiliate", []):
        template = str(item.get("url") or "").strip()
        label = str(item.get("label") or "").strip()
        if template and label:
            _https(template, f"affiliate {label!r}")
            if "{" in urlsplit(template).netloc:
                raise ConfigError(f"affiliate {label!r}: placeholders are not allowed in the host")
            affiliates.append(Affiliate(label, template))
    raw_shop = raw.get("shop", {})
    shop_url = str(raw_shop.get("url") or "").strip()
    if shop_url:
        _https(shop_url, "shop.url")
        if "{" in urlsplit(shop_url).netloc:
            raise ConfigError("shop.url: placeholders are not allowed in the host")
    bundle_url = str(raw_shop.get("bundle_url") or "").strip()
    if bundle_url:
        _https(bundle_url, "shop.bundle_url")
    dataset_url = str(raw_shop.get("dataset_url") or "").strip()
    if dataset_url:
        _https(dataset_url, "shop.dataset_url")
    codes = frozenset(str(c).strip().upper() for c in raw_shop.get("countries", []))
    if any(c != "*" and not re.fullmatch(r"[A-Z]{2}", c) for c in codes):
        raise ConfigError('shop.countries must be two-letter codes or "*"')
    shop = Shop(
        url=shop_url,
        price=str(raw_shop.get("price") or "").strip(),
        countries=codes,
        bundle_url=bundle_url,
        bundle_price=str(raw_shop.get("bundle_price") or "").strip(),
        dataset_url=dataset_url,
        dataset_price=str(raw_shop.get("dataset_price") or "").strip(),
    )
    years = int(site.get("years_ahead", Config.years_ahead))
    if not 0 <= years <= 3:
        raise ConfigError("site.years_ahead must be 0..3")
    return Config(
        name=str(site.get("name") or Config.name),
        tagline=str(site.get("tagline") or Config.tagline),
        base_url=base_url,
        cname=cname,
        google_verification=google_v,
        bing_verification=bing_v,
        contact=contact,
        years_ahead=years,
        goatcounter=gc,
        adsense_client=adsense,
        affiliates=tuple(affiliates),
        shop=shop,
        disclosure=str(raw.get("disclosure") or Config.disclosure),
    )
