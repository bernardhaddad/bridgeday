"""Write the whole static site into one directory."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime, timedelta
from importlib import resources
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from . import ics, insights, intent, render, render_global
from .calendars import country_calendar
from .config import Config
from .data import load_countries
from .optimizer import BUDGETS, best_budget, best_plans, weekend_label

MARKER = ".bridgeday-build"


def years_for(today: date, cfg: Config) -> list[int]:
    return list(range(today.year, today.year + cfg.years_ahead + 1))


def years_to_fetch(today: date, cfg: Config) -> list[int]:
    """One year beyond the last page: its December windows run into the next January."""
    years = years_for(today, cfg)
    return years + [years[-1] + 1]


def primary_year(today: date, years: list[int]) -> int:
    """From October on, people plan next year; send them there first."""
    nxt = today.year + 1
    return nxt if today.month >= 10 and nxt in years else today.year


def _prepare(out: Path) -> None:
    if out.exists():
        if (out / ".git").exists() or out.resolve() in (Path.home(), Path.cwd(), Path("/")):
            raise SystemExit(f"refusing to wipe {out}: it looks like a repository or home")
        if any(out.iterdir()) and not (out / MARKER).exists():
            raise SystemExit(f"refusing to wipe {out}: it was not made by bridgeday")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("generated; safe to delete\n")


def _write(out: Path, rel: str, text: str) -> None:
    path = out / rel.lstrip("/")
    if rel.endswith("/"):
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def build(
    cfg: Config,
    data_dir: Path,
    out: Path,
    today: date | None = None,
    intents: dict | None = None,
) -> dict:
    today = today or date.today()
    stamp = datetime.now(UTC).replace(microsecond=0)
    years = years_for(today, cfg)
    countries = load_countries(data_dir)
    if not countries:
        raise SystemExit(f"no countries in {data_dir}; run `bridgeday data` first")
    main_year = primary_year(today, years)
    _prepare(out)
    urls: list[str] = ["/"]
    upcoming = []
    built = []
    for c in countries:
        cc, name = c["countryCode"], c["name"]
        loaded, cal = country_calendar(data_dir, c, range(years[0] - 1, years[-1] + 2))
        have = [y for y in years if loaded[y] is not None]
        if not have:
            continue
        for y in have:
            hols = loaded[y] or []
            after = today if y == today.year else None  # past plans help nobody
            path = f"/{cc.lower()}/{y}/"
            html = render.country_page(
                cfg,
                cc=cc,
                country=name,
                year=y,
                years=have,
                holidays=hols,
                cal=cal,
                weekend=weekend_label(cc, c.get("weekend")),
                plans=best_plans(cal, y, after=after),
                budgets=[best_budget(cal, y, b, after) for b in BUDGETS],
                breaks=cal.free_breaks(y, after=after),
                today=today,
                chosen=intent.most_chosen(intents or {}, cc, y),
            )
            _write(out, path, html)
            _write(out, f"{path}holidays.ics", ics.calendar(cc, name, y, hols, stamp))
            urls.append(path)
        _write(
            out,
            f"/{cc.lower()}/",
            render.redirect_page(
                cfg, f"/{cc.lower()}/{main_year if main_year in have else have[0]}/"
            ),
        )
        built.append({**c, "year": main_year if main_year in have else have[0]})
        soon = today + timedelta(days=14)
        seen = set()
        for h in (loaded[today.year] or []) + (loaded.get(today.year + 1) or []):
            if h.day_off and today <= h.day <= soon and h.day not in seen:
                seen.add(h.day)
                upcoming.append((h.day, cc, name, h.name))
    for y in years:
        ix = insights.compute(data_dir, y)
        if ix.countries:
            _write(out, f"/global/{y}/", render_global.global_page(cfg, ix))
            urls.append(f"/global/{y}/")
    _write(out, "/global/", render.redirect_page(cfg, f"/global/{main_year}/"))
    upcoming.sort()
    _write(out, "/", render.index_page(cfg, built, main_year, upcoming[:40]))
    for rel, html in (
        ("/about/", render.about_page(cfg)),
        ("/privacy/", render.privacy_page(cfg)),
        ("/404.html", render.not_found_page(cfg)),
    ):
        _write(out, rel, html)
    urls += ["/about/", "/privacy/"]
    _write(out, "/style.css", resources.files("bridgeday").joinpath("style.css").read_text())
    _write(out, "/sitemap.xml", sitemap(cfg, urls, today))
    _write(out, "/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {cfg.base_url}/sitemap.xml\n")
    _write(out, "/.nojekyll", "")
    if cfg.adsense_client:
        pub = cfg.adsense_client.removeprefix("ca-")
        _write(out, "/ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    if cfg.cname:
        _write(out, "/CNAME", cfg.cname + "\n")
    return {"countries": len(built), "pages": len(urls), "years": years}


def sitemap(cfg: Config, urls: list[str], today: date) -> str:
    body = "".join(
        f"<url><loc>{xml_escape(cfg.base_url + u)}</loc><lastmod>{today}</lastmod></url>\n"
        for u in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n'
    )
