# bridgeday

## Objective
A static website that earns money with no ongoing work. For every country the open-source
`holidays` library covers (244 inhabited countries), and for this year and next, it publishes the public holidays and
works out the best days to take off ("take 3 days of leave, get 9 days off in a row").
A scheduled GitHub Actions run rebuilds and redeploys it, and the year rolls over without
anyone touching it. Revenue comes from travel affiliate links placed beside each plan
(the reader has just picked dates, so booking is the next step) and an optional ad slot.
All monetization lives in `config.toml`.

## Users and the job they hire this for
- Employees planning leave: "when should I take my days off in 2027 to get the most rest?"
- Travellers and HR people checking "is X a public holiday in country Y?"
- Anyone who wants the holidays in their own calendar (.ics download).

## Must-haves (v1)
- One page per country per year: nationwide and regional holidays, free long weekends,
  the best short plans (1 to 5 leave days), and the best way to spend 5, 10 and 15 leave days.
- The correct weekend per country (Friday-Saturday where that applies), shown on the page.
- An .ics calendar per country and year.
- An index page with search, plus sitemap.xml, robots.txt, canonical URLs, JSON-LD and a 404 page.
- Monetization from config only: affiliate URL templates with dates filled in, an AdSense
  client id (ads.txt is generated), and GoatCounter analytics. Empty means nothing is rendered.
  An affiliate disclosure appears automatically whenever an affiliate link does.
- Never down because of a third party: holidays are computed offline; population falls back to the committed snapshot.
- Paid products: a printable planner per country and the Global Long-Weekend & Absence Index dataset.

## Non-goals
- No server, database, accounts or paid services. No AI-generated filler text: every page
  is computed from data, which is what keeps it on the right side of search-engine spam policies.
- No regional (state-level) optimizer in v1; regional holidays are listed, not optimized.

## Constraints
- Runtime / platform: Python 3.11+; one runtime dependency, `holidays`, pinned exactly (MIT).
  Hosting: GitHub Pages (free).
- Data and privacy: public data only; no cookies unless the owner switches ads on.
- Budget / cost ceiling: $0 a month. A custom domain (~$10 a year) is optional but needed for AdSense.

## Success criteria (observable)
- `make check` passes; `make run` builds the site from the snapshot and serves it.
  `/de/2027/` shows the holidays, plans and budget table in a browser.
- The scheduled workflow builds the site without a human; with deploy switched on, it publishes it.

## Open questions (owner)
- Custom domain? It strongly helps ad approval and brand. Set `site.base_url` and `site.cname`.
- Which affiliate programs to join (see README "Turn on the money").
