"""The public face of the Global Long-Weekend & Absence Index: the free headline findings.
The full daily, country-level and pair data is the paid dataset."""

from __future__ import annotations

import calendar
from datetime import date

from .config import Config
from .insights import Index, millions
from .render import esc, flag, fmt, page


def _when(start: date, end: date) -> str:
    return fmt(start) if start == end else f"{fmt(start)} – {fmt(end)}"


def dataset_box(cfg: Config, ix: Index) -> str:
    if not cfg.shop.dataset_url:
        return ""
    price = f" · {esc(cfg.shop.dataset_price)}" if cfg.shop.dataset_price else ""
    n = len(ix.countries)
    return f"""<aside class="shop"><div><p class="shop-t">📊 The full {ix.year} dataset</p>
<p class="small">Every day × {n} countries (holiday, long break, bridge day, open or closed,
population), the daily world index, and {n * (n - 1) // 2:,} country-pair overlaps.
CSV, ready for spreadsheets and BI tools. For travel and airline revenue teams, HR and
workforce planning, retail and marketing calendars.</p></div>
<a class="btn big" href="{esc(cfg.shop.dataset_url)}">Get the dataset{price}</a></aside>"""


def global_page(cfg: Config, ix: Index) -> str:
    bp = esc(cfg.base_path)
    year = ix.year
    daily = ix.daily()
    by_date = {r["date"]: r for r in daily}
    breaks = ix.biggest_breaks(15)
    absence = ix.peak_absence(10)
    weekdays = [r for r in daily if r["weekday"] not in ("Sat", "Sun")]
    least_open = min(weekdays, key=lambda r: r["share_of_world_open"])
    top = breaks[0] if breaks else None

    cards = []
    if top:
        cards.append((millions(top["peak"]), f"people in a long weekend on {fmt(top['peak_day'])}"))
    cards.append(
        (
            f"{least_open['share_of_world_open']:.0%}",
            f"of the world open for business on {fmt(date.fromisoformat(least_open['date']))}",
        )
    )
    if absence:
        a = absence[0]
        cards.append(
            (
                millions(a["people_on_bridge_day"]),
                f"people facing a bridge day on {fmt(date.fromisoformat(a['date']))}",
            )
        )
    card_html = "".join(
        f'<div class="stat"><p class="big">{esc(big)}</p><p class="small">{esc(small)}</p></div>'
        for big, small in cards
    )

    def country_links(cs, n=6):
        return ", ".join(
            f'<a href="{bp}/{c.cc.lower()}/{year}/">{flag(c.cc)} {esc(c.name)}</a>' for c in cs[:n]
        )

    def more(cs) -> str:
        return f" and {len(cs) - 6} more" if len(cs) > 6 else ""

    break_rows = "".join(
        f"<tr><td>{i}</td><td><strong>{_when(e['start'], e['end'])}</strong></td>"
        f"<td><strong>{esc(millions(e['peak']))}</strong></td>"
        f"<td>{country_links(e['countries'])}{more(e['countries'])}</td>"
        f"<td class='small'>{esc(', '.join(e['reason']))}</td></tr>"
        for i, e in enumerate(breaks, 1)
    )
    by_cc = {c.cc: c for c in ix.countries}

    def bridged(r) -> list:
        cs = (by_cc[x] for x in r["countries_on_bridge_day"].split(";") if x in by_cc)
        return sorted(cs, key=lambda c: -c.population)

    absence_rows = "".join(
        f"<tr><td><strong>{fmt(date.fromisoformat(r['date']))}</strong></td>"
        f"<td><strong>{esc(millions(r['people_on_bridge_day']))}</strong></td>"
        f"<td>{country_links(bridged(r))}{more(bridged(r))}</td></tr>"
        for r in absence
    )

    months = []
    for m in range(1, 13):
        cells = []
        first = date(year, m, 1)
        cells.extend('<span class="hm"></span>' for _ in range(first.weekday()))
        for day in range(1, calendar.monthrange(year, m)[1] + 1):
            r = by_date[date(year, m, day).isoformat()]
            closed = 1 - r["share_of_world_open"]
            level = min(5, int(closed * 6))
            tip = (
                f"{fmt(date(year, m, day))}: {r['share_of_world_open']:.0%} of the world open; "
                f"{millions(r['people_on_public_holiday'])} on a public holiday"
            )
            cells.append(f'<span class="hm l{level}" title="{esc(tip)}">{day}</span>')
        months.append(
            f'<div class="month"><h4>{calendar.month_name[m]}</h4><div class="g">{"".join(cells)}</div></div>'
        )

    missing = ", ".join(ix.missing_population) or "none"
    body = f"""<nav class="crumbs"><a href="{bp}/">All countries</a> › World</nav>
<h1>🌍 The world's long weekends in {year}</h1>
<p class="lead">Every country's holiday calendar, weighted by how many people live there:
{esc(millions(ix.world_population))} people in {len(ix.weighted)} countries, day by day.
Which dates empty offices across continents, when travel demand peaks, and when your
customers, suppliers and colleagues abroad are really out.</p>
<div class="stats">{card_html}</div>
{dataset_box(cfg, ix)}

<h2>The biggest long weekends on Earth</h2>
<p class="small">Consecutive days on which people are in a break of 3+ days that includes a public holiday,
ranked by the peak number of people off at once.</p>
<div class="scroll"><table><thead><tr><th>#</th><th>When</th><th>Peak people off</th><th>Biggest countries</th><th>Why</th></tr></thead>
<tbody>{break_rows}</tbody></table></div>

<h2>Peak absence days</h2>
<p class="small">Working days that, taken as leave, turn a public holiday into a 4+ day break
(at least 3 days off per leave day). Expect thin offices and slow replies.</p>
<div class="scroll"><table><thead><tr><th>Date</th><th>People facing a bridge day</th><th>Biggest countries</th></tr></thead>
<tbody>{absence_rows}</tbody></table></div>

<h2>{year} heat map: how much of the world is closed</h2>
<div class="legend"><span class="hm l0">1</span> mostly open <span class="hm l2">1</span>
<span class="hm l4">1</span> <span class="hm l5">1</span> mostly closed (weekends and holidays)</div>
<div class="year">{"".join(months)}</div>

<h2>Method and sources</h2>
<p class="small">Holidays: the open-source holidays project (MIT), nationwide public holidays only;
regional holidays count when at least 90% of regions observe them. Future dates are the
library's projections from each country's rules: lunar and Islamic dates, and holiday transfers
that governments announce late (China publishes its schedule each autumn), can move.
Weekends: each country's standard office weekend, with declared weekend workdays counted as open.
Population: World Bank, latest available year (CC BY 4.0). Not in the population totals
because the World Bank has no figure: {esc(missing)}.
No nationwide public holidays in the source for {year}: {esc(", ".join(ix.no_holidays) or "none")}.</p>
"""
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": f"Global Long-Weekend & Absence Index {year}",
            "description": (
                f"Daily, population-weighted index of public holidays, long breaks and bridge "
                f"days for {len(ix.weighted)} countries in {year}, with country-pair overlaps of "
                "working days."
            ),
            "url": f"{cfg.base_url}/global/{year}/",
            "temporalCoverage": f"{year}-01-01/{year}-12-31",
            "spatialCoverage": "World",
            "isAccessibleForFree": False,
            "creator": {"@type": "Organization", "name": cfg.name},
            "variableMeasured": [
                "people on public holiday",
                "people in long break",
                "people on bridge day",
                "share of world open",
            ],
        }
    ]
    title = (
        f"The world's long weekends in {year}: holidays for {millions(ix.world_population)} people"
    )
    desc = (
        f"The biggest long weekends on Earth in {year}, peak absence days and a daily heat map "
        f"of how much of the world is closed, across {len(ix.weighted)} countries."
    )
    return page(cfg, path=f"/global/{year}/", title=title, description=desc, body=body, ld=ld)
