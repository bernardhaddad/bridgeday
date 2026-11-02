"""Command line: generate the data, build the site and products, serve it locally."""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from . import build, config, data, intent, products

ROOT = Path(__file__).resolve().parents[2]
INTENT_FILE = ROOT / "private" / "intent.json"  # the paid first-party data: never commit


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bridgeday")
    p.add_argument("--config", type=Path, default=ROOT / "config.toml")
    p.add_argument("--data", type=Path, default=ROOT / "data")
    p.add_argument("--out", type=Path, default=ROOT / "dist")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data", help="regenerate data/ (holidays library + World Bank population)")
    b = sub.add_parser("build", help="write the site into --out")
    b.add_argument("--base-url", help="override site.base_url (e.g. for local preview)")
    sub.add_parser("intent", help="pull Leave Intent counts from GoatCounter into private/")
    pr = sub.add_parser("products", help="build the paid PDF planners (never published)")
    pr.add_argument("--year", type=int, help="default: next year from October, else this year")
    pr.add_argument("--products-out", type=Path, default=ROOT / "products")
    s = sub.add_parser("serve", help="serve --out on localhost")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    try:
        cfg = config.load(args.config)
    except config.ConfigError as e:
        print(f"config.toml: {e}", file=sys.stderr)
        return 2
    if args.cmd == "data":
        years = build.years_to_fetch(date.today(), cfg)
        stats = data.generate(args.data, years)
        print(
            f"generated {stats['files']} country-years for {stats['countries']} countries {years}"
        )
        return 0
    if args.cmd == "build":
        if args.base_url:
            try:
                url = config.check_base_url(args.base_url)
            except config.ConfigError as e:
                print(e, file=sys.stderr)
                return 2
            cfg = config.Config(**{**cfg.__dict__, "base_url": url})
        stats = build.build(cfg, args.data, args.out, intents=intent.load(INTENT_FILE))
        print(f"built {stats['pages']} pages for {stats['countries']} countries {stats['years']}")
        print(f"output: {args.out}")
        return 0
    if args.cmd == "intent":
        token = os.environ.get("GOATCOUNTER_TOKEN", "")
        if not (cfg.goatcounter and token):
            print("intent: needs analytics.goatcounter in config.toml and GOATCOUNTER_TOKEN")
            return 0  # not configured yet is not a failure of the daily job
        today = date.today()
        try:
            counts = intent.pull(cfg.goatcounter, token, today - timedelta(days=500), today)
        except (OSError, RuntimeError, ValueError) as e:
            # Optional data must never stop the site from publishing: keep the last counts.
            print(f"::warning::intent: kept previous counts ({e})")
            return 0
        intent.save(INTENT_FILE, counts)
        print(f"intent: {len(counts)} breaks, {sum(counts.values())} planners -> {INTENT_FILE}")
        return 0
    if args.cmd == "products":
        today = date.today()
        year = args.year or build.primary_year(today, build.years_for(today, cfg))
        stats = products.build_products(cfg, args.data, args.products_out, year)
        print(f"built {stats['planners']} planners for {year}")
        print(f"catalog: {stats['catalog']}\nbundle: {stats['bundle']}")
        ds = products.build_dataset(
            cfg, args.data, args.products_out, year, intent.load(INTENT_FILE)
        )
        print(f"dataset: {ds}")
        return 0
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.out))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as srv:
        print(f"serving {args.out} at http://127.0.0.1:{args.port}/")
        srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
