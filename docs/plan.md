# Plan: bridgeday

Tasks in dependency order. Tick with `[x]` when observed working.

## 2026-10-30 — v1, fully automated

- [x] T1 Walking skeleton: `make setup && make check && make run` pass.
- [x] T2 Optimizer: bridges, free long weekends, exact best-use of 5/10/15 leave days; tests.
- [x] T3 Data: computed offline by the `holidays` library (Nager.Date dropped: its terms forbid portals).
- [x] T4 Site: country/year pages, year calendar, .ics, index with search, sitemap, robots,
  JSON-LD, about, privacy, 404. All external text escaped (tested with a `<script>` name).
- [x] T5 Monetization from `config.toml`: affiliate templates (https only), AdSense + ads.txt,
  GoatCounter, CNAME, contact, automatic disclosure.
- [x] T6 Daily workflow `.github/workflows/bridgeday-site.yml`: test, data, build, smoke-test,
  deploy behind `vars.BRIDGEDAY_DEPLOY == 'pages'`.
- [x] T8 Paid product: stdlib PDF writer, 17+ page planner per country/year, `make products`
  (204 planners, bundle zip, catalog csv), "Get the planner" box from `[shop]` config.
- [x] T10 Global Long-Weekend & Absence Index: public `/global/<year>/` page (Dataset JSON-LD) and
  the paid dataset zip (daily world, day x country, country pairs, ranked breaks, README).
- [x] T11 Dataset audit: 12 findings fixed with real-data regression tests.
- [x] T12 Leave Intent Index: take-this-break button (.ics + anonymous event), `make intent`,
  most-chosen badge, `leave_intent_<year>.csv` in the dataset.
- [x] T14 Holiday corrections: 234 sourced fixes over the library (corrections.json), HK general
  holidays, AF weekend; regression tests in tests/test_corrections.py.
- [x] T15 `generate()` writes `{}` over population.json when the World Bank answer is empty but
  raises nothing (seen 2026-11-02 behind a proxy); keep the snapshot unless most countries come back. Fixed: fewer than 150 keeps the snapshot.
- [x] T7a Published 2026-11-02: https://bernardhaddad.github.io/bridgeday/ from the public repo
  bernardhaddad/bridgeday (daily workflow site.yml, BRIDGEDAY_DEPLOY=pages, GoatCounter on).
- [x] T7b Google Search Console verified (HTML tag), sitemap processed: 492 URLs discovered.
  Bing tag live (msvalidate.01). Both codes live in config.toml; never remove them.
- [ ] T7c Owner: affiliate ids (Travelpayouts), optional own domain.
- [x] T13 GoatCounter account `bridgeday`; GOATCOUNTER_TOKEN secret set in bernardhaddad/bridgeday.
- [ ] T9 Owner: list the top countries + bundle + dataset in a shop, fill `[shop]` (README "Sell the planner").

## Later / parked
- Team/HR edition: one calendar across several countries for remote teams (subscription).
- Preview images of the planner on each country page.
- Regional (state) optimizer pages, e.g. Germany per Bundesland: more long-tail pages.
- Language versions (de, fr, es) of the country pages: the searches are mostly local-language.
- "Bridge days {year}" roundup page across countries for the October–January peak.
- Workspace: the `new-project` scaffolder writes a mis-indented python `ci.yml` (steps at column 0).
