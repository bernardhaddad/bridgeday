"""Build the paid planners. Output stays out of the public site (it is what people buy)."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from . import insights, intent
from .calendars import country_calendar
from .config import Config, slug
from .data import load_countries
from .optimizer import BUDGETS, best_budget, best_plans, weekend_label
from .planner import Planner


def title(country: str, year: int) -> str:
    return f"{country} {year} Leave Planner"


def planner_pdf(
    cfg: Config, data_dir: Path, cc: str, country: str, year: int, weekend: list[int] | None = None
) -> bytes | None:
    country = {"countryCode": cc, "name": country, "weekend": weekend}
    loaded, cal = country_calendar(data_dir, country, range(year - 1, year + 2))
    hols = loaded[year]
    if hols is None:
        return None
    country = country["name"]
    host = cfg.base_url.split("://", 1)[-1]
    return Planner(
        cc=cc,
        country=country,
        year=year,
        holidays=hols,
        cal=cal,
        weekend=weekend_label(cc, weekend),
        plans=best_plans(cal, year),
        budgets=[best_budget(cal, year, b) for b in BUDGETS],
        site=cfg.name,
        url=host,
    ).bytes()


def build_products(cfg: Config, data_dir: Path, out: Path, year: int) -> dict:
    folder = out / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.pdf"):  # a country can disappear from the source
        old.unlink()
    rows, files = [], []
    for c in load_countries(data_dir):
        cc, name = c["countryCode"], c["name"]
        pdf = planner_pdf(cfg, data_dir, cc, name, year, c.get("weekend"))
        if pdf is None:
            continue
        path = folder / f"{slug(name)}-{year}-leave-planner.pdf"
        path.write_bytes(pdf)
        files.append(path)
        rows.append(
            {
                "cc": cc,
                "title": title(name, year),
                "handle": slug(title(name, year)),
                "price": cfg.shop.price,
                "file": str(path.relative_to(out)),
                "description": (
                    f"A 17+ page printable planner for {year} in {name}: every public holiday, "
                    "the best days to take leave already worked out, a year-at-a-glance "
                    "calendar, a page per month and a leave tracker. A4 landscape PDF."
                ),
            }
        )
    with (out / f"catalog-{year}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["cc"])
        w.writeheader()
        w.writerows(rows)
    bundle = out / f"all-countries-{year}-leave-planners.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.name)
    return {"planners": len(files), "bundle": bundle, "catalog": out / f"catalog-{year}.csv"}


DATASET_README = """# Global Long-Weekend & Absence Index {year}

Built by {name} ({url}) from:
- Holidays: the open-source `holidays` project (MIT licence), nationwide public holidays;
  regional ones count when at least 90% of regions observe them. Future dates are the library's
  projections: lunar and Islamic dates and late-announced transfers (China) can move.
- Weekends: each country's standard office weekend; declared weekend workdays count as open.
- No nationwide public holidays in the source for {year}: {no_holidays}.
- Population: World Bank, World Development Indicators, SP.POP.TOTL, latest year (CC BY 4.0).
  No World Bank figure, so not in the population totals: {missing}.

## Files
- `daily_world_{year}.csv`: one row per day. people_on_public_holiday (any day of the week),
  people_on_weekday_holiday (the ones that close offices), people_in_long_break,
  people_on_bridge_day, share_of_world_open (population-weighted), and the country codes behind
  each figure. Totals use countries with a population figure only.
- `daily_country_{year}.csv`: one row per day and every country (population blank where the
  World Bank has none). weekend, declared_workday, public_holiday, weekday_holiday,
  holiday_name, open, long_break_days (length of the break this day is in, 0 if none),
  bridge_day_unlocks (days off one or two leave days around here unlock, 0 if not a bridge day).
- `country_pairs_{year}.csv`: for every pair of countries, days both are open, only one is open,
  and both are closed.
- `biggest_long_weekends_{year}.csv`: the ranked events shown on the website.
- `leave_intent_{year}.csv` (when collected): first-party data from the website's planner.
  For each break, how many distinct people pressed "I'm taking this break", and its share of
  that country's planners. Breaks with fewer than 3 planners are left out. Nobody else has this:
  it is a forward-looking signal of when people intend to be away, months before they book.

## Definitions
- long break: 3+ consecutive days off that include a nationwide public holiday.
- bridge day: a working day between a public holiday and the weekend (or another holiday),
  so that 1 or 2 days of leave join them into a break of 4+ days with at least 3 days off per
  leave day.

## Licence
You may use this data inside your organisation and in derived analyses and products. You may
not resell or republish the raw files. Attribution for the sources above is required where you
publish figures derived from them.
"""


def build_dataset(
    cfg: Config, data_dir: Path, out: Path, year: int, intents: dict | None = None
) -> Path:
    ix = insights.compute(data_dir, year)
    path = out / f"global-leave-intelligence-{year}.zip"
    events = [
        {
            "rank": i,
            "start": e["start"].isoformat(),
            "end": e["end"].isoformat(),
            "peak_day": e["peak_day"].isoformat(),
            "peak_people_in_long_break": e["peak"],
            "countries": ";".join(c.cc for c in e["countries"]),
            "holidays": "; ".join(e["reason"]),
        }
        for i, e in enumerate(ix.biggest_breaks(50), 1)
    ]
    readme = DATASET_README.format(
        year=year,
        name=cfg.name,
        url=cfg.base_url,
        missing=", ".join(ix.missing_population) or "none",
        no_holidays=", ".join(ix.no_holidays) or "none",
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", readme)
        z.writestr(f"daily_world_{year}.csv", insights.to_csv(ix.daily()))
        z.writestr(f"daily_country_{year}.csv", insights.to_csv(insights.country_daily(ix)))
        z.writestr(f"country_pairs_{year}.csv", insights.to_csv(ix.pairs()))
        z.writestr(f"biggest_long_weekends_{year}.csv", insights.to_csv(events))
        rows = intent.dataset_rows(intents or {}, year, {c.cc: c.weight for c in ix.weighted})
        if rows:
            z.writestr(f"leave_intent_{year}.csv", insights.to_csv(rows))
    return path
