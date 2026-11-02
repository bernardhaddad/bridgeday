"""The Leave Intent Index: which breaks people actually plan to take, counted on this site.

This is the part nobody else can reproduce. When a visitor presses "I'm taking this break"
on a plan, the page hands them a calendar event and sends one anonymous GoatCounter event
named `intent-<cc>-<start>_<end>` (no cookie, no personal data). GoatCounter counts unique
visitors per event, and `pull` reads those counts back through its API.

The counts are the paid product. They are kept in `private/` (git-ignored) and never
published raw: the site only marks the most chosen plan per country, and only once at least
MIN_PUBLIC people chose it.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

PATH_RE = re.compile(r"^intent-([a-z]{2})-(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$")
MIN_PUBLIC = 5  # below this a badge would reveal too little data to mean anything
MIN_DATASET = 3  # rows below this are dropped from the paid files (noise and privacy)


def event_path(cc: str, start: date, end: date) -> str:
    return f"intent-{cc.lower()}-{start.isoformat()}_{end.isoformat()}"


def parse(path: str) -> tuple[str, date, date] | None:
    m = PATH_RE.match(path.strip().lstrip("/"))
    if not m:
        return None
    try:
        start, end = date.fromisoformat(m.group(2)), date.fromisoformat(m.group(3))
    except ValueError:
        return None
    if end < start or (end - start).days > 60:
        return None
    return m.group(1).upper(), start, end


def _api(code: str, token: str, params: dict) -> dict:
    url = f"https://{code}.goatcounter.com/api/v0/stats/hits?" + urllib.parse.urlencode(
        params, doseq=True
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "bridgeday-site/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read(5_000_000))
    except urllib.error.HTTPError as e:
        if e.code == 404:  # a new site with no recorded paths answers 404: no data yet
            return {"hits": [], "more": False}
        body = e.read(500).decode("utf-8", "replace")
        raise RuntimeError(f"GoatCounter API {e.code}: {body}") from e


def pull(code: str, token: str, start: date, end: date, get=_api) -> dict[str, int]:
    """Unique visitors per intent event between two dates, following `more` pages."""
    counts: dict[str, int] = {}
    seen: list[int] = []
    for _ in range(200):  # hard stop: 200 pages of 100 paths
        params = {
            "start": f"{start.isoformat()}T00:00:00Z",
            "end": f"{end.isoformat()}T23:00:00Z",
            "limit": 100,
        }
        if seen:
            params["exclude_paths"] = list(seen)
        resp = get(code, token, params)
        for h in resp.get("hits") or []:
            seen.append(int(h.get("path_id", 0)))
            path = str(h.get("path", ""))
            if parse(path):
                counts[path.lstrip("/")] = counts.get(path.lstrip("/"), 0) + int(h.get("count", 0))
        if not resp.get("more"):
            break
    return counts


def save(path: Path, counts: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")


def load(path: Path) -> dict[tuple[str, date, date], int]:
    if not path.exists():
        return {}
    out = {}
    for p, n in json.loads(path.read_text()).items():
        key = parse(p)
        if key and isinstance(n, int) and n > 0:
            out[key] = out.get(key, 0) + n
    return out


def most_chosen(intents: dict, cc: str, year: int) -> tuple[date, date] | None:
    """The plan most people in this country chose this year, if enough did."""
    best = max(
        ((n, k) for k, n in intents.items() if k[0] == cc.upper() and k[1].year == year),
        default=None,
    )
    if not best or best[0] < MIN_PUBLIC:
        return None
    return best[1][1], best[1][2]


def dataset_rows(intents: dict, year: int, population: dict[str, int]) -> list[dict]:
    totals: dict[str, int] = defaultdict(int)
    for (cc, start, _), n in intents.items():
        if start.year == year:
            totals[cc] += n
    rows = []
    for (cc, start, end), n in sorted(intents.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if start.year != year or n < MIN_DATASET:
            continue
        rows.append(
            {
                "country": cc,
                "break_start": start.isoformat(),
                "break_end": end.isoformat(),
                "days": (end - start).days + 1,
                "planners": n,
                "share_of_country_planners": round(n / totals[cc], 4),
                "country_population": population.get(cc, ""),
            }
        )
    return rows
