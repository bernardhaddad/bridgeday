"""Holiday data for every country, generated offline by the MIT-licensed `holidays` library,
plus population from the World Bank (CC BY 4.0). Both allow commercial use with attribution.

Nager.Date was the first source; its terms forbid running a holiday portal on its data and
require sponsorship for commercial use, so it is no longer used anywhere.

`generate` writes the same JSON shape the rest of the code reads, so the snapshot in `data/`
stays reviewable in git and the site builds without any network access.
"""

from __future__ import annotations

import http.client
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CC_RE = re.compile(r"[A-Z]{2}")
MAX_BODY = 5_000_000
MIN_POPULATION_COUNTRIES = 150  # the World Bank covers about 215 of ours
WORLD_BANK = (
    "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
    "?format=json&per_page=400&mrnev=1"
)
# Class names from the library are CamelCase; these read better written out.
NAME_FIXES = {
    "AlandIslands": "Åland Islands",
    "CuracaoNetherlands": "Curaçao",
    "Curacao": "Curaçao",
    "SaintBarthelemy": "Saint Barthélemy",
    "SaoTomeAndPrincipe": "São Tomé and Príncipe",
    "Reunion": "Réunion",
    "TimorLeste": "Timor-Leste",
    "GuineaBissau": "Guinea-Bissau",
    "CocosIslands": "Cocos (Keeling) Islands",
    "HongKong": "Hong Kong",
    "UnitedStates": "United States",
    "DRCongo": "DR Congo",
    "HeardIslandAndMcDonaldIslands": "Heard Island and McDonald Islands",
    "IvoryCoast": "Côte d'Ivoire",
    "SyrianArabRepublic": "Syria",
    "UnitedStatesVirginIslands": "U.S. Virgin Islands",
}
# Nobody lives here permanently; a holiday page would be noise.
UNINHABITED = {"AQ", "BV", "GS", "HM", "TF", "UM"}
# The library's weekend is the legal rest day used for "observed" rules. Where most offices
# keep a different weekend, the planner should follow the offices.
# Sources: national labour practice; confidence noted in docs/decisions.md.
WEEKEND_OVERRIDES = {
    "HK": [6, 7],
    "AI": [6, 7],
    "CD": [6, 7],
    "KN": [6, 7],
    "NE": [6, 7],
    "PY": [6, 7],
    "TK": [6, 7],
    "VE": [6, 7],
    "MR": [6, 7],  # Saturday-Sunday since 2014
    "AF": [5],  # government week Saturday-Thursday noon (mfa.gov.af, anea.gov.af)
    "LY": [5, 6],
    "PS": [5, 6],
    "SO": [5],
    "NP": [6],
}
# Library categories read per country (default: public). Hong Kong's "optional" category holds
# its gazetted general holidays (Good Friday, the day after...), the days offices actually close.
CATEGORIES = {"HK": ("public", "optional")}
# Hand-kept fixes the library gets wrong, each with the official or reliable source it rests on;
# applied after the library so a rebuild keeps them. See docs/decisions.md (2026-11-02).
CORRECTIONS = Path(__file__).with_name("corrections.json")
# Share of a country's subdivisions that must observe a regional holiday for it to count
# as a day off nationally (Australia's Christmas substitutes, Malaysia's Diwali).
NEAR_NATIONWIDE = 0.9


def http_json(url: str, retries: int = 3, timeout: float = 60) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "bridgeday-site/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                raise ValueError("response too large")
            return json.loads(body) if body.strip() else []
        # OSError covers URLError, timeouts and dropped connections (ConnectionResetError).
        except (OSError, http.client.HTTPException, ValueError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    tmp.replace(path)


def pretty(class_name: str) -> str:
    if class_name in NAME_FIXES:
        return NAME_FIXES[class_name]
    words = re.findall(r"[A-Z][a-z]*|[a-z]+|\d+", class_name)
    small = {"And", "Of", "The"}
    return " ".join(w.lower() if i and w in small else w for i, w in enumerate(words))


def library_countries() -> list[dict]:
    import holidays
    from holidays.registry import COUNTRIES

    out = {}
    for class_name, cc, *_ in COUNTRIES.values():
        if not CC_RE.fullmatch(cc) or cc in out or cc in UNINHABITED:
            continue
        h = holidays.country_holidays(cc)
        out[cc] = {
            "countryCode": cc,
            "name": pretty(class_name),
            "weekend": WEEKEND_OVERRIDES.get(cc) or sorted(d + 1 for d in h.weekend),  # ISO Mon=1
        }
    return sorted(out.values(), key=lambda c: c["name"])


def _language(h) -> str | None:
    langs = getattr(h, "supported_languages", ()) or ()
    for lang in ("en_US", "en_GB", "en"):
        if lang in langs:
            return lang
    return None


def country_year(cc: str, year: int) -> list[dict]:
    """Nationwide holidays, then regional ones tagged with their subdivision codes."""
    import holidays

    cats = {"categories": CATEGORIES[cc]} if cc in CATEGORIES else {}
    base = holidays.country_holidays(cc, years=year, **cats)
    lang, local_lang = _language(base), getattr(base, "default_language", None)
    national = holidays.country_holidays(cc, years=year, language=lang, **cats)
    local = holidays.country_holidays(cc, years=year, language=local_lang, **cats)
    rows: dict[tuple[str, str], dict] = {}
    for d, names in sorted(national.items()):
        english, local_names = names.split("; "), (local.get(d) or "").split("; ")
        for name in english:
            # The library sorts several names on one date alphabetically per language, so
            # pairing by position would mismatch them; only a single name pairs safely.
            single = len(english) == 1 and len(local_names) == 1 and local_names[0]
            rows[(d.isoformat(), name)] = {
                "date": d.isoformat(),
                "name": name,
                "localName": local_names[0] if single else "",
                "global": True,
                "types": ["Public"],
                "counties": None,
            }
    national_keys = set(rows)
    for sub in getattr(base, "subdivisions", ()) or ():
        try:
            regional = holidays.country_holidays(cc, subdiv=sub, years=year, language=lang, **cats)
        except (NotImplementedError, KeyError, ValueError):
            continue
        for d, names in regional.items():
            for name in names.split("; "):
                key = (d.isoformat(), name)
                if key in national_keys:
                    continue
                row = rows.setdefault(
                    key,
                    {
                        "date": d.isoformat(),
                        "name": name,
                        "localName": name,
                        "global": False,
                        "types": ["Public"],
                        "counties": [],
                    },
                )
                row["counties"].append(f"{cc}-{sub}")
    # A date counts nationally when nearly every region is off, even under different names
    # (Australia, 28 Dec: Boxing Day observed, Boxing Day, Proclamation Day).
    subs = len(getattr(base, "subdivisions", ()) or ())
    by_date: dict[str, list[dict]] = {}
    for row in rows.values():
        by_date.setdefault(row["date"], []).append(row)
    for day_rows in by_date.values():
        if not subs or any(r["global"] for r in day_rows):
            continue
        regions = {c for r in day_rows for c in r["counties"]}
        if len(regions) / subs >= NEAR_NATIONWIDE:
            main = max(day_rows, key=lambda r: len(r["counties"]))
            main["global"] = True
            main["nearNationwide"] = True
    out, _ = apply_corrections(cc, year, list(rows.values()))
    return out


def load_corrections(path: Path = CORRECTIONS) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def apply_corrections(
    cc: str, year: int, rows: list[dict], corrections: list[dict] | None = None
) -> tuple[list[dict], list[dict]]:
    """Apply this country-year's corrections; return the rows and the corrections that matched
    nothing (the library changed upstream, so the entry needs a look rather than silent drift)."""
    if corrections is None:
        corrections = load_corrections()
    rows = [dict(r) for r in rows]
    unmatched = []
    for c in corrections:
        if c["cc"] != cc or not c["date"].startswith(f"{year}-"):
            continue
        if c["op"] == "add":
            if any(r["date"] == c["date"] and r["name"] == c["name"] for r in rows):
                unmatched.append(c)
                continue
            regions = c.get("regions")
            rows.append(
                {
                    "date": c["date"],
                    "name": c["name"],
                    "localName": c.get("localName") or "",
                    "global": not regions,
                    "types": ["Public"],
                    "counties": list(regions) if regions else None,
                    "source": c["source"],
                }
            )
            continue
        hit = next((r for r in rows if r["date"] == c["date"] and r["name"] == c["name"]), None)
        if hit is None:
            unmatched.append(c)
            continue
        if c["op"] == "remove":
            rows.remove(hit)
            continue
        if c["op"] == "move":
            hit["date"] = c["to"]
            hit["name"] = c.get("to_name", hit["name"])
        elif c["op"] == "rename":
            hit["name"] = c["to_name"]
            hit["localName"] = ""
        elif c["op"] == "scope":
            hit["global"] = not c["regions"]
            hit["counties"] = list(c["regions"]) or None
            hit.pop("nearNationwide", None)
        elif c["op"] == "observance":
            hit["types"] = ["Observance"]
        else:
            raise ValueError(f"unknown correction op {c['op']!r}")
        hit["source"] = c["source"]
    rows.sort(key=lambda r: (r["date"], not r["global"], r["name"]))
    return rows, unmatched


def covers(cc: str, year: int) -> bool:
    """Whether the library has rules for this country in this year (Sri Lanka stops at 2026)."""
    import holidays

    h = holidays.country_holidays(cc)
    return getattr(h, "start_year", 0) <= year <= getattr(h, "end_year", 9999)


def weekend_workdays(cc: str, year: int) -> list[str]:
    """Weekend days declared working days (China's make-up Saturdays, Russia's transfers)."""
    import holidays

    h = holidays.country_holidays(cc, years=year)
    return sorted(d.isoformat() for d in getattr(h, "weekend_workdays", ()) if d.year == year)


def population(codes: set[str], get=http_json) -> dict[str, int]:
    """Latest World Bank total population per ISO2 code (aggregates such as 'World' dropped)."""
    _, rows = get(WORLD_BANK)
    out = {}
    for r in rows or []:
        iso2 = (r.get("country") or {}).get("id", "")
        # Aggregates ("Africa Eastern" is ZH, AFE) look like countries; only membership in our
        # country list tells them apart.
        if iso2 in codes and isinstance(r.get("value"), int | float):
            out[iso2] = int(r["value"])
    return out


def generate(data_dir: Path, years: list[int], get=http_json) -> dict:
    countries = library_countries()
    try:
        pop = population({c["countryCode"] for c in countries}, get)
        # An empty or truncated answer (seen behind a proxy) must not wipe the snapshot.
        if len(pop) < MIN_POPULATION_COUNTRIES:
            raise ValueError(f"only {len(pop)} countries with a population")
        _write(data_dir / "population.json", pop)
    except (RuntimeError, KeyError, TypeError, ValueError) as e:
        print(f"population: keeping snapshot ({e})", file=sys.stderr)
    _write(data_dir / "countries.json", countries)
    n, skipped = 0, []
    for year in years:
        folder = data_dir / str(year)
        for old in folder.glob("*.json"):  # a country can lose coverage; never keep stale files
            old.unlink()
        workdays = {}
        for c in countries:
            cc = c["countryCode"]
            if not covers(cc, year):
                skipped.append(f"{cc} {year}")
                continue
            _write(folder / f"{cc}.json", country_year(cc, year))
            if wd := weekend_workdays(cc, year):
                workdays[cc] = wd
            n += 1
        _write(folder / "_workdays.json", workdays)
    stale = check_corrections(data_dir)
    for problem in stale:
        print(f"correction no longer applies: {problem}", file=sys.stderr)
    return {"countries": len(countries), "files": n, "skipped": skipped, "stale": stale}


def check_corrections(data_dir: Path, corrections: list[dict] | None = None) -> list[str]:
    """Every correction's intended result must be visible in the generated data."""
    if corrections is None:
        corrections = load_corrections()
    problems = []
    for c in corrections:
        path = data_dir / c["date"][:4] / f"{c['cc']}.json"
        if not path.exists():
            continue  # the library stopped covering this country-year
        rows = json.loads(path.read_text())

        def has(day: str, name: str, rows=rows) -> bool:
            return any(r["date"] == day and r["name"] == name for r in rows)

        if c["op"] == "remove":
            ok = not has(c["date"], c["name"])
        elif c["op"] == "move":
            ok = has(c["to"], c.get("to_name", c["name"]))
        elif c["op"] == "rename":
            ok = has(c["date"], c["to_name"])
        else:  # add, scope, observance keep their date and name
            ok = has(c["date"], c["name"])
        if not ok:
            problems.append(f"{c['cc']} {c['op']} {c['date']} {c['name']}")
    return problems


def load_workdays(data_dir: Path, year: int) -> dict[str, set[date]]:
    path = data_dir / str(year) / "_workdays.json"
    if not path.exists():
        return {}
    return {
        cc: {date.fromisoformat(d) for d in ds} for cc, ds in json.loads(path.read_text()).items()
    }


def load_population(data_dir: Path) -> dict[str, int]:
    path = data_dir / "population.json"
    return json.loads(path.read_text()) if path.exists() else {}


@dataclass(frozen=True)
class Holiday:
    day: date
    name: str
    local_name: str
    nationwide: bool
    day_off: bool  # nationwide and a public holiday, so it counts in the optimizer
    regions: tuple[str, ...]
    types: tuple[str, ...]


def load_countries(data_dir: Path) -> list[dict]:
    path = data_dir / "countries.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text())
    return sorted(
        (r for r in rows if CC_RE.fullmatch(str(r.get("countryCode", "")))), key=lambda r: r["name"]
    )


def load_holidays(data_dir: Path, year: int, cc: str) -> list[Holiday] | None:
    path = data_dir / str(year) / f"{cc}.json"
    if not path.exists():
        return None
    out = []
    for h in json.loads(path.read_text()):
        try:
            day = date.fromisoformat(h["date"])
        except (KeyError, TypeError, ValueError):
            continue
        types = tuple(str(t) for t in (h.get("types") or []))
        nationwide = bool(h.get("global"))
        out.append(
            Holiday(
                day=day,
                name=str(h.get("name") or h.get("localName") or "Holiday"),
                local_name=str(h.get("localName") or ""),
                nationwide=nationwide,
                day_off=nationwide and "Public" in types,
                regions=tuple(str(r) for r in (h.get("counties") or [])),
                types=types,
            )
        )
    return sorted(out, key=lambda h: (h.day, not h.nationwide, h.name))
