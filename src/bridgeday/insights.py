"""The Global Long-Weekend & Absence Index: every country's calendar joined with population.

It exists only once 240+ calendars, each country's working weekend (including declared
weekend workdays), the leave optimizer and population are combined. Every figure traces back
to the holidays library (MIT) and the World Bank (CC BY 4.0).

Definitions, per country and date:
- public holiday:  a nationwide public holiday, any day of the week. Regional holidays count
  only when at least 90% of the country's regions observe them.
- weekday holiday: a public holiday that falls on a working weekday (the ones that close offices).
- long break: inside a run of 3+ consecutive days off that includes a public holiday. Runs that
  start in the previous year count for the days inside this one.
- bridge day: a working day between a public holiday and the weekend (or another holiday),
  so that 1 or 2 days of leave join them into a break of 4+ days with at least 3 days off
  per leave day. These are the days absence spikes.
- open:       not a weekend (unless declared a working day) and not a public holiday.
Countries with no World Bank population are kept in the per-country files with a blank
population and left out of every population total.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .calendars import country_calendar
from .data import load_countries, load_population
from .optimizer import Calendar, weekday_holidays

DAY = timedelta(days=1)


@dataclass
class CountryYear:
    cc: str
    name: str
    population: int | None
    cal: Calendar
    names: dict[date, str]
    breaks: dict[date, tuple[date, date]] = field(default_factory=dict)  # date -> its break
    bridges: dict[date, int] = field(default_factory=dict)  # date -> days off it unlocks

    @property
    def weight(self) -> int:
        return self.population or 0

    def weekday_holiday(self, d: date) -> bool:
        return d in self.names and not self.cal.is_weekend(d)


@dataclass
class Index:
    year: int
    days: list[date]
    countries: list[CountryYear]  # every country with data, population or not

    @property
    def weighted(self) -> list[CountryYear]:
        return [c for c in self.countries if c.population]

    @property
    def world_population(self) -> int:
        return sum(c.weight for c in self.countries)

    @property
    def missing_population(self) -> list[str]:
        return sorted(c.cc for c in self.countries if not c.population)

    @property
    def no_holidays(self) -> list[str]:
        """Countries whose source lists no nationwide public holiday this year (Ukraine under
        martial law, for example): disclosed, never filled in."""
        return sorted(c.cc for c in self.countries if not c.names)

    def country_rows(self):
        for d in self.days:
            for c in self.countries:
                yield d, c

    def daily(self) -> list[dict]:
        out = []
        world = self.world_population
        for d in self.days:
            ws = self.weighted
            hol = [c for c in ws if d in c.names]
            wk = [c for c in hol if c.weekday_holiday(d)]
            brk = [c for c in ws if d in c.breaks]
            bri = [c for c in ws if d in c.bridges]
            open_pop = sum(c.weight for c in ws if not c.cal.is_off(d))
            out.append(
                {
                    "date": d.isoformat(),
                    "weekday": d.strftime("%a"),
                    "people_on_public_holiday": sum(c.weight for c in hol),
                    "people_on_weekday_holiday": sum(c.weight for c in wk),
                    "people_in_long_break": sum(c.weight for c in brk),
                    "people_on_bridge_day": sum(c.weight for c in bri),
                    "share_of_world_open": round(open_pop / world, 4) if world else 0,
                    "countries_on_public_holiday": ";".join(c.cc for c in hol),
                    "countries_in_long_break": ";".join(c.cc for c in brk),
                    "countries_on_bridge_day": ";".join(c.cc for c in bri),
                }
            )
        return out

    def biggest_breaks(self, limit: int = 15) -> list[dict]:
        """Peak days ranked by people in a long break. A day joins an earlier event when most
        of its people are already counted there (same breaks, same countries), so Nowruz,
        Holi and Easter in one fortnight stay separate events."""
        events: list[dict] = []
        days = sorted(
            self.days, key=lambda d: -sum(c.weight for c in self.weighted if d in c.breaks)
        )
        for d in days:
            off = [c for c in self.weighted if d in c.breaks]
            people = sum(c.weight for c in off)
            if not people:
                break
            covered = 0
            for e in events:
                covered = max(
                    covered,
                    sum(c.weight for c in off if c.cc in e["ccs"] and e["start"] <= d <= e["end"]),
                )
            if covered * 2 > people:
                continue
            spans = [c.breaks[d] for c in off]
            reasons: dict[str, int] = defaultdict(int)
            for c in off:
                s, t = c.breaks[d]
                for h, name in c.names.items():
                    if s <= h <= t:
                        reasons[name] += c.weight
            events.append(
                {
                    "peak_day": d,
                    "peak": people,
                    "start": min(s for s, _ in spans),
                    "end": max(t for _, t in spans),
                    "ccs": {c.cc for c in off},
                    "countries": sorted(off, key=lambda c: -c.weight),
                    "reason": [n for n, _ in sorted(reasons.items(), key=lambda kv: -kv[1])][:3],
                }
            )
            if len(events) == limit:
                break
        return events

    def peak_absence(self, limit: int = 10) -> list[dict]:
        rows = sorted(self.daily(), key=lambda r: -r["people_on_bridge_day"])
        return [r for r in rows if r["people_on_bridge_day"]][:limit]

    def pairs(self) -> list[dict]:
        """For every pair of countries: days both are open, only one is, or neither."""
        masks = {}
        for c in self.countries:
            m = 0
            for i, d in enumerate(self.days):
                if not c.cal.is_off(d):
                    m |= 1 << i
            masks[c.cc] = m
        rows = []
        cs = sorted(self.countries, key=lambda c: c.cc)
        for i, a in enumerate(cs):
            for b in cs[i + 1 :]:
                ma, mb = masks[a.cc], masks[b.cc]
                rows.append(
                    {
                        "country_a": a.cc,
                        "country_b": b.cc,
                        "both_open": (ma & mb).bit_count(),
                        "only_a_open": (ma & ~mb).bit_count(),
                        "only_b_open": (mb & ~ma).bit_count(),
                        "both_closed": len(self.days) - (ma | mb).bit_count(),
                    }
                )
        return rows


def is_bridge(w, cal: Calendar) -> bool:
    """Leave sits strictly inside the break, between days off on both sides."""
    return (
        weekday_holidays(w, cal) > 0
        and w.length >= 4
        and w.ratio >= 3
        and cal.is_off(w.start)
        and cal.is_off(w.end)
    )


def compute(data_dir: Path, year: int) -> Index:
    pop = load_population(data_dir)
    first, last = date(year, 1, 1), date(year, 12, 31)
    countries = []
    for c in load_countries(data_dir):
        cc = c["countryCode"]
        loaded, cal = country_calendar(data_dir, c, range(year - 1, year + 2))
        if loaded[year] is None:
            continue
        names: dict[date, str] = {}
        for h in loaded[year]:
            if h.day_off:
                names.setdefault(h.day, h.name)
        cy = CountryYear(cc, c["name"], pop.get(cc), cal, names)
        # Scan the previous year too, so a break from 31 Dec into January is not lost.
        for scan in (year - 1, year):
            for w in cal.free_breaks(scan):
                for i in range(w.length):
                    d = w.start + i * DAY
                    if first <= d <= last:
                        cy.breaks[d] = (w.start, w.end)
            for w in cal.candidates(scan, 2):
                if is_bridge(w, cal):
                    for d in w.leave:
                        if first <= d <= last:
                            cy.bridges[d] = max(cy.bridges.get(d, 0), w.length)
        countries.append(cy)
    n_days = (date(year + 1, 1, 1) - first).days
    return Index(year, [first + i * DAY for i in range(n_days)], countries)


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return buf.getvalue()


def country_daily(ix: Index) -> list[dict]:
    rows = []
    for d, c in ix.country_rows():
        brk = c.breaks.get(d)
        rows.append(
            {
                "date": d.isoformat(),
                "country": c.cc,
                "country_name": c.name,
                "population": c.population if c.population else "",
                "weekend": int(c.cal.is_weekend(d)),
                "declared_workday": int(d in c.cal.workdays),
                "public_holiday": int(d in c.names),
                "weekday_holiday": int(c.weekday_holiday(d)),
                "holiday_name": c.names.get(d, ""),
                "open": int(not c.cal.is_off(d)),
                "long_break_days": (brk[1] - brk[0]).days + 1 if brk else 0,
                "bridge_day_unlocks": c.bridges.get(d, 0),
            }
        )
    return rows


def millions(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1e9:.2f} billion"
    return f"{n / 1e6:,.0f} million"
