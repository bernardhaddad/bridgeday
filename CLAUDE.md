# bridgeday

Passive-income static site: public holidays and a leave optimizer per country and year,
rebuilt daily by `.github/workflows/bridgeday-site.yml` (repo root) from the `holidays` library
(MIT, offline) and World Bank population (CC BY 4.0), and
monetized from `config.toml` only. Owner guide: README.md.

## Read first
- `docs/spec.md` — what we are building and what is out of scope.
- `docs/plan.md` — ordered tasks with acceptance criteria; tick them as you go.
- `docs/decisions.md` — why things are the way they are. Add a line when you decide something.
- `.claude/rules/verification.md` — what "done" means.

## Commands (the only ones you need)
- `make setup` — install dependencies
- `make check` — lint + tests; must pass before every commit
- `make run` — start the thing so you can observe it
- `make test`, `make lint` — the two halves of `check`
- `make intent` — pull Leave Intent counts (needs `GOATCOUNTER_TOKEN`) into `private/`
- `make products` — the paid PDFs into git-ignored `products/`; never commit or publish them
- `make data` — regenerate `data/` (offline, about 2 s); `make build` — `dist/`

## Invariants
- Data sources must allow commercial use: never Nager.Date (its terms forbid holiday portals).
- Paid outputs (`products/`, `private/intent.json`) never go into `dist/` or git.
- Runtime: stdlib plus pinned `holidays`. Every external string reaches HTML through `esc()`.
- Monetization is config-only; an empty value renders nothing. Affiliate URLs must be https.
- `build()` wipes `--out` only if it carries the `.bridgeday-build` marker.
- Fixes to library data go in `src/bridgeday/corrections.json` with a source URL, never in `data/`
  (regenerated); `check_corrections()` must stay empty.

## Conventions
- Stack: python. Ground any library usage in its current docs (fetch them), not memory.
- Small verified increments; commit after each green `make check`.
- Destructive git and curl-pipe-shell are blocked by a PreToolUse hook; ask instead.
- Lint runs automatically after every edit; fix what it reports before moving on.
