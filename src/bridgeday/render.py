"""HTML for every page. All data that reaches a page goes through esc() or attr()."""

from __future__ import annotations

import calendar
import json
from datetime import date
from html import escape

from .config import Config
from .data import Holiday
from .optimizer import BudgetPlan, Calendar, Window, weekday_holidays

MONTHS = calendar.month_name
SHORT_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def esc(s: object) -> str:
    return escape(str(s), quote=True)


def flag(cc: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in cc.upper())


def fmt(d: date, year: bool = False) -> str:
    s = f"{SHORT_DAYS[d.weekday()]} {d.day} {MONTHS[d.month][:3]}"
    return f"{s} {d.year}" if year else s


def span(w: Window) -> str:
    cross = w.start.year != w.end.year
    return f"{fmt(w.start, cross)} – {fmt(w.end, cross)}"


def window_line(w: Window) -> str:
    return f"{span(w)} ({plural(w.cost, 'day')} → {w.length})"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def json_ld(obj: object) -> str:
    # No <, > or & inside a script block at all: "</script" and "<!--" both change parsing.
    out = json.dumps(obj, ensure_ascii=False)
    return out.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page(
    cfg: Config, *, path: str, title: str, description: str, body: str, ld: list | None = None
) -> str:
    bp = esc(cfg.base_path)
    canonical = cfg.base_url + path
    head_extra = []
    if cfg.adsense_client:
        head_extra.append(
            '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
            f'adsbygoogle.js?client={esc(cfg.adsense_client)}" crossorigin="anonymous"></script>'
        )
    if cfg.goatcounter:
        head_extra.append(
            f'<script data-goatcounter="https://{esc(cfg.goatcounter)}.goatcounter.com/count" '
            'async src="https://gc.zgo.at/count.js"></script>'
        )
    for obj in ld or []:
        head_extra.append(f'<script type="application/ld+json">{json_ld(obj)}</script>')
    extra = "\n".join(head_extra)
    year = date.today().year
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="{bp}/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌉</text></svg>">
{extra}
</head>
<body>
<header class="top"><a class="brand" href="{bp}/">🌉 {esc(cfg.name)}</a>
<nav><a href="{bp}/">Countries</a> <a href="{bp}/global/">World</a> <a href="{bp}/about/">About</a></nav></header>
<main>
{body}
</main>
<footer><p>Holiday data: the open-source <a href="https://github.com/vacanza/holidays">holidays</a> project (MIT).
Population: <a href="https://data.worldbank.org">World Bank</a> (CC BY 4.0).
Always confirm leave with your employer; regional rules can differ.</p>
<p>© {year} {esc(cfg.name)} · <a href="{bp}/privacy/">Privacy</a> · <a href="{bp}/about/">About</a></p></footer>
</body>
</html>
"""


def affiliate_links(cfg: Config, w: Window, country: str, cc: str) -> str:
    if not cfg.affiliates:
        return ""
    vals = {
        "start": w.start.isoformat(),
        "end": w.end.isoformat(),
        "country": country,
        "cc": cc,
        "year": str(w.start.year),
    }
    links = " ".join(
        f'<a class="btn" rel="sponsored nofollow noopener" target="_blank" '
        f'href="{esc(a.url(**vals))}">{esc(a.label)}</a>'
        for a in cfg.affiliates
    )
    return f'<div class="cta">{links}</div>'


# "I'm taking this break": hands the visitor an .ics for the break and, if analytics is on,
# counts one anonymous event. Values come from data attributes, never from markup.
TAKE_SCRIPT = r"""<script>
document.addEventListener('click', function (e) {
  var b = e.target.closest('button.take'); if (!b) return;
  var d = b.dataset, end = new Date(d.end + 'T00:00:00Z');
  end.setUTCDate(end.getUTCDate() + 1);
  var f = function (s) { return s.replace(/-/g, ''); };
  var esc = function (s) { return s.replace(/[\\;,]/g, function (c) { return '\\' + c; }); };
  var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//bridgeday//plan//EN', 'BEGIN:VEVENT',
    'UID:' + d.cc + '-' + d.start + '-' + d.end + '@bridgeday',
    'DTSTAMP:' + new Date().toISOString().replace(/[-:]/g, '').slice(0, 15) + 'Z',
    'DTSTART;VALUE=DATE:' + f(d.start), 'DTEND;VALUE=DATE:' + end.toISOString().slice(0, 10).replace(/-/g, ''),
    'SUMMARY:' + esc(d.title), 'DESCRIPTION:' + esc('Book leave: ' + d.leave),
    'END:VEVENT', 'END:VCALENDAR'].join('\r\n') + '\r\n';
  var a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([ics], {type: 'text/calendar'}));
  a.download = 'my-break-' + d.start + '.ics'; document.body.appendChild(a); a.click(); a.remove();
  /*COUNT*/
  b.textContent = '✓ Added to your calendar'; b.disabled = true;
});
</script>"""


COUNT_JS = r"""if (window.goatcounter && window.goatcounter.count) {
    window.goatcounter.count({path: 'intent-' + d.cc + '-' + d.start + '_' + d.end, title: d.title, event: true});
  }"""


def take_script(cfg: Config) -> str:
    return TAKE_SCRIPT.replace("/*COUNT*/", COUNT_JS if cfg.goatcounter else "")


def plan_card(
    cfg: Config,
    w: Window,
    cal: Calendar,
    hol_names: dict,
    country: str,
    cc: str,
    chosen: tuple[date, date] | None = None,
) -> str:
    leave = ", ".join(fmt(d) for d in w.leave)
    hols = "; ".join(f"{fmt(d)}: {esc(hol_names[d])}" for d in w.holidays if d in hol_names)
    badge = '<p class="hot">🔥 Most chosen by planners</p>' if chosen == (w.start, w.end) else ""
    take = (
        f'<button class="take" type="button" data-cc="{esc(cc.lower())}" '
        f'data-start="{w.start.isoformat()}" data-end="{w.end.isoformat()}" '
        f'data-title="{esc(f"Time off: {w.length} days ({country})")}" '
        f'data-leave="{esc(leave)}">✓ I&#x27;m taking this break</button>'
    )
    return f"""<article class="plan{" is-hot" if badge else ""}">{badge}
<p class="gain"><strong>{plural(w.cost, "day")} off</strong> → <strong>{w.length} days</strong> in a row</p>
<p class="when">{span(w)}</p>
<p class="small">Take leave on: {leave}</p>
<p class="small">Thanks to: {hols}</p>
{take}
{affiliate_links(cfg, w, country, cc)}
</article>"""


def year_grid(year: int, cal: Calendar, leave: set[date], names: dict) -> str:
    months = []
    for m in range(1, 13):
        cells = []
        first = date(year, m, 1)
        cells.extend('<span class="d"></span>' for _ in range(first.weekday()))
        for day in range(1, calendar.monthrange(year, m)[1] + 1):
            d = date(year, m, day)
            cls, tip = "d", ""
            if d in names and d in cal.holidays:
                cls, tip = "d hol", names[d]
            elif d in leave:
                cls, tip = "d lv", "Suggested leave day"
            elif cal.is_off(d):
                cls = "d we"
            title = f' title="{esc(fmt(d) + ": " + tip)}"' if tip else ""
            cells.append(f'<span class="{cls}"{title}>{day}</span>')
        head = "".join(f'<span class="h">{s[0]}</span>' for s in SHORT_DAYS)
        months.append(
            f'<div class="month"><h4>{MONTHS[m]}</h4><div class="g">{head}{"".join(cells)}</div></div>'
        )
    return f"""<div class="legend"><span class="d hol">1</span> public holiday
<span class="d lv">1</span> suggested leave (10-day plan) <span class="d we">1</span> weekend</div>
<div class="year">{"".join(months)}</div>"""


def shop_box(cfg: Config, cc: str, country: str, year: int) -> str:
    if not cfg.shop.sells(cc):
        return ""
    price = f" · {esc(cfg.shop.price)}" if cfg.shop.price else ""
    return f"""<aside class="shop"><div><p class="shop-t">📘 The {year} {esc(country)} planner, ready to print</p>
<p class="small">17+ pages: your best breaks already worked out, a year-at-a-glance calendar,
a page per month with every holiday and suggested leave day marked, and a leave tracker.
Print it, stick it on the fridge, plan the year together.</p></div>
<a class="btn big" href="{esc(cfg.shop.link(cc, year, country))}">Get the planner{price}</a></aside>"""


def country_page(
    cfg: Config,
    *,
    cc: str,
    country: str,
    year: int,
    years: list[int],
    holidays: list[Holiday],
    cal: Calendar,
    weekend: str,
    plans: list[Window],
    budgets: list[BudgetPlan],
    breaks: list[Window],
    today: date,
    chosen: tuple[date, date] | None = None,
) -> str:
    bp = esc(cfg.base_path)
    path = f"/{cc.lower()}/{year}/"
    in_year = [h for h in holidays if h.day.year == year]
    days_off = sorted({h.day for h in in_year if h.day_off})
    weekday_n = sum(1 for d in days_off if not cal.is_weekend(d))
    names: dict[date, str] = {}
    for h in in_year:
        if h.day_off:
            names.setdefault(h.day, h.name)
    b10 = next((b for b in budgets if b.budget == 10), budgets[0] if budgets else None)
    upcoming = next((h for h in in_year if h.day_off and h.day >= today), None)

    summary = (
        f"{esc(country)} has {plural(len(days_off), 'nationwide public holiday')} in {year}, "
        f"{weekday_n} of them on a working day."
    )
    if b10 and b10.days_off:
        summary += (
            f" Plan well and <strong>{b10.leave_used} days of leave give you "
            f"{b10.days_off} days off</strong>."
        )
    year_links = " ".join(
        f'<a class="pill{" on" if y == year else ""}" href="{bp}/{cc.lower()}/{y}/">{y}</a>'
        for y in years
    )
    later = [y for y in years if y > year]
    nxt = f' <a href="{bp}/{cc.lower()}/{later[0]}/">Plan {later[0]} now →</a>' if later else ""
    plan_html = (
        "".join(plan_card(cfg, w, cal, names, country, cc, chosen) for w in plans)
        or f"<p>No weekday holidays left to bridge in {year}.{nxt}</p>"
    )
    ahead = ""
    if year == today.year and today > date(year, 1, 1):
        ahead = f'<p class="small">Plans below start from today, {fmt(today)}.{nxt}</p>'

    budget_rows = "".join(
        f"<tr><td>{b.budget}</td><td>{b.leave_used}</td><td><strong>{b.days_off}</strong></td>"
        f"<td>{'<br>'.join(window_line(w) for w in b.windows)}</td></tr>"
        for b in budgets
    )
    break_html = (
        "".join(
            f"<li><strong>{span(w)}</strong> · {w.length} days · "
            f"{esc(', '.join(names[d] for d in w.holidays if d in names))}</li>"
            for w in breaks
        )
        or "<li>None this year.</li>"
    )
    rows = []
    for h in in_year:
        scope = "Nationwide" if h.nationwide else f"Regional ({esc(', '.join(h.regions[:6]))}"
        if not h.nationwide:
            scope += "…)" if len(h.regions) > 6 else ")"
        past = ' class="past"' if h.day < today else ""
        local = f'<br><span class="small">{esc(h.local_name)}</span>' if h.local_name else ""
        if h.local_name == h.name:
            local = ""
        rows.append(
            f"<tr{past}><td>{fmt(h.day)}</td><td>{esc(h.name)}{local}</td>"
            f"<td>{scope}</td><td>{esc(', '.join(h.types))}</td></tr>"
        )
    disclosure = f'<p class="small note">{esc(cfg.disclosure)}</p>' if cfg.affiliates else ""
    leave_days = {d for b in budgets if b.budget == 10 for w in b.windows for d in w.leave}

    faq = [
        (
            f"How many public holidays does {country} have in {year}?",
            f"{country} has {len(days_off)} nationwide public holidays in {year}; "
            f"{weekday_n} fall on a working day. The weekend there is {weekend}.",
        )
    ]
    if b10 and b10.days_off:
        faq.append(
            (
                f"How do I get the most days off in {country} in {year}?",
                f"Using {b10.leave_used} days of leave on the right dates gives "
                f"{b10.days_off} days off: "
                + "; ".join(f"{span(w)} ({w.length} days)" for w in b10.windows)
                + ".",
            )
        )
    if upcoming:
        faq.append(
            (
                f"What is the next public holiday in {country}?",
                f"{upcoming.name}, on {fmt(upcoming.day, True)}.",
            )
        )
    faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq
    )
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
                for q, a in faq
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Countries",
                    "item": cfg.base_url + "/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": f"{country} {year}",
                    "item": cfg.base_url + path,
                },
            ],
        },
    ]
    body = f"""<nav class="crumbs"><a href="{bp}/">All countries</a> › {esc(country)}</nav>
<h1>{flag(cc)} {esc(country)} public holidays {year}</h1>
<p class="lead">{summary}</p>
<p>{year_links} <a class="pill" href="{bp}/{cc.lower()}/{year}/holidays.ics" download>📅 Add to calendar (.ics)</a></p>
<p class="small">Weekend assumed: {esc(weekend)}. Only nationwide public holidays count as days off below.</p>
{shop_box(cfg, cc, country, year)}

<h2>Best days to take off in {year}</h2>
{ahead}<div class="plans">{plan_html}</div>
{disclosure}

<h2>Make the most of your leave</h2>
<div class="scroll"><table><thead><tr><th>Leave budget</th><th>Used</th><th>Days off</th><th>When</th></tr></thead>
<tbody>{budget_rows}</tbody></table></div>

<h2>{year} at a glance</h2>
{year_grid(year, cal, leave_days, names)}

<h2>Free long weekends</h2>
<ul class="breaks">{break_html}</ul>

<h2>All holidays in {esc(country)} in {year}</h2>
<div class="scroll"><table><thead><tr><th>Date</th><th>Holiday</th><th>Where</th><th>Type</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>

<h2>Questions</h2>
{faq_html}
{take_script(cfg)}
"""
    best = b10.days_off if b10 else 0
    desc = (
        f"All {len(days_off)} public holidays in {country} in {year}, the free long weekends, "
        f"and the best days to take off"
        + (f": {b10.leave_used} days of leave can give you {best} days off." if best else ".")
    )
    return page(
        cfg,
        path=path,
        title=f"{country} public holidays {year} & best days to take off",
        description=desc,
        body=body,
        ld=ld,
    )


def index_page(cfg: Config, countries: list[dict], year: int, upcoming: list[tuple]) -> str:
    bp = esc(cfg.base_path)
    items = "".join(
        f'<li data-n="{esc(c["name"].lower())}"><a href="{bp}/{c["countryCode"].lower()}/{c.get("year", year)}/">'
        f"{flag(c['countryCode'])} {esc(c['name'])}</a></li>"
        for c in countries
    )
    up = "".join(
        f'<li><strong>{fmt(d)}</strong> · <a href="{bp}/{cc.lower()}/{d.year}/">{esc(country)}</a>'
        f" · {esc(name)}</li>"
        for d, cc, country, name in upcoming
    )
    bundle = ""
    if cfg.shop.bundle_url:
        price = f" · {esc(cfg.shop.bundle_price)}" if cfg.shop.bundle_price else ""
        bundle = (
            f'<aside class="shop"><div><p class="shop-t">🌍 Every country, one download</p>'
            f'<p class="small">Printable {year} planners for all {len(countries)} countries: '
            "for remote teams, HR and anyone with family abroad.</p></div>"
            f'<a class="btn big" href="{esc(cfg.shop.bundle_url)}">Get the bundle{price}</a></aside>'
        )
    body = f"""<section class="hero"><h1>{esc(cfg.tagline)}</h1>
<p class="lead">Everyone gets a handful of days off a year. Placed next to the right holidays,
they become long weekends and real breaks with family and friends.
Pick your country to see every public holiday in {year},
and exactly which days to book off to turn a few days of leave into long breaks.</p>
<input id="q" type="search" placeholder="Search {len(countries)} countries…" aria-label="Search countries" autocomplete="off"></section>
<p><a class="pill on" href="{bp}/global/{year}/">🌍 The world's biggest long weekends in {year} →</a></p>
<ul class="countries" id="list">{items}</ul>
{bundle}
<h2>Coming up around the world</h2>
<ul class="breaks">{up or "<li>Nothing in the next two weeks.</li>"}</ul>
<script>
const q=document.getElementById('q'),li=[...document.querySelectorAll('#list li')];
q.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase();li.forEach(e=>e.hidden=v&&!e.dataset.n.split(/[\\s(),.-]+/).some(w=>w.startsWith(v))&&!e.dataset.n.startsWith(v));}});
</script>"""
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": cfg.name,
            "url": cfg.base_url + "/",
        }
    ]
    return page(
        cfg,
        path="/",
        title=f"{cfg.name}: public holidays {year} & the best days to take off",
        description=(
            f"Public holidays for {len(countries)} countries in {year}, "
            "with the smartest days to take leave for long weekends and longer breaks."
        ),
        body=body,
        ld=ld,
    )


def text_page(cfg: Config, path: str, title: str, paragraphs: list[str]) -> str:
    body = f"<h1>{esc(title)}</h1>" + "".join(f"<p>{p}</p>" for p in paragraphs)
    return page(cfg, path=path, title=f"{title} · {cfg.name}", description=title, body=body)


def about_page(cfg: Config) -> str:
    return text_page(
        cfg,
        "/about/",
        f"About {cfg.name}",
        [
            f"{esc(cfg.name)} lists the public holidays of every country we have data for and works "
            "out which days of leave give the longest breaks. A window counts only nationwide "
            "public holidays and the local weekend; every suggestion is computed, not guessed.",
            "Holiday dates are computed from each country's rules by the open-source "
            '<a href="https://github.com/vacanza/holidays">holidays</a> project (MIT licence); '
            "population figures are from the World Bank (CC BY 4.0). Both are refreshed automatically. Regional holidays are listed but not used "
            "in the plans, because they apply only to part of a country.",
            "Found a mistake? Holiday rules change; check your employer's calendar before booking."
            + (f' <a href="{esc(cfg.contact)}">Contact us</a>.' if cfg.contact else ""),
        ],
    )


def privacy_page(cfg: Config) -> str:
    paras = ["This site has no accounts and stores nothing about you on our side."]
    if cfg.goatcounter:
        paras.append(
            'Visits are counted with <a href="https://www.goatcounter.com">GoatCounter</a>, '
            "which does not use cookies or collect personal data. When you press "
            "\u201cI\u2019m taking this break\u201d we also count that break, anonymously, to "
            "learn which breaks people plan; only totals of several people are ever used."
        )
    if cfg.adsense_client:
        paras.append(
            "We show ads from Google AdSense. Google and its partners use cookies to serve ads "
            "based on your visits to this and other sites. You can opt out of personalised "
            'advertising at <a href="https://adssettings.google.com">Google Ads Settings</a>. '
            'See <a href="https://policies.google.com/technologies/ads">how Google uses data</a>.'
        )
    if cfg.affiliates:
        paras.append(esc(cfg.disclosure))
    return text_page(cfg, "/privacy/", "Privacy policy", paras)


def not_found_page(cfg: Config) -> str:
    return text_page(
        cfg,
        "/404.html",
        "Page not found",
        [f'Try the <a href="{cfg.base_path}/">list of countries</a>.'],
    )


def redirect_page(cfg: Config, target: str) -> str:
    url = esc(cfg.base_url + target)
    return (
        f'<!doctype html><meta charset="utf-8"><link rel="canonical" href="{url}">'
        f'<meta http-equiv="refresh" content="0; url={url}"><a href="{url}">Continue</a>'
    )


__all__ = [
    "about_page",
    "country_page",
    "index_page",
    "not_found_page",
    "privacy_page",
    "redirect_page",
    "weekday_holidays",
]
