# Bridgeday: a website that runs itself

A static site with every country's public holidays and the best days to take off
("take 1 day of leave, get 4 days off"). It covers 244 countries, this year and next.
A GitHub Actions job rebuilds it every day from free data and publishes it for free.
Money comes from travel affiliate links placed under each plan (the reader has just picked
dates, so booking is the next step) and, optionally, ads.

**Who it helps:** anyone with a job and a few days of leave, which is almost everyone. They get
free, specific advice ("book Fri 7 May off and get four days with your family") and a calendar
they can import. Revenue only comes when they choose to book a trip they already wanted.

**Running cost: $0** (plus about $10 a year if you add a domain, which is recommended).
**Your time after setup: none.** The data refreshes, the years roll over, the site redeploys.

## What earns money, honestly

Income = visitors × the share who click a booking link × commission. Nothing pays until
search engines send traffic, and new sites usually take **3 to 9 months** to rank. Holiday
searches are huge and recurring ("public holidays 2027", "bridge days 2027 Germany"), and
peak every October to January, when people plan next year's leave. The site's edge over the
big holiday lists is the leave optimizer and the year calendar, which they mostly lack.

A realistic range for a site like this is anywhere from nothing (if it never ranks) to a few
hundred dollars a month (if a few dozen country pages rank well). Treat it as an asset that
compounds, not a salary. Every page is computed from real data rather than AI filler, which
is what keeps it within search-engine spam policies.

## Turn on the money (one time, about an hour)

Each step is one line in [`config.toml`](config.toml). Empty values are simply not shown.

1. **Publish it (free).** GitHub Pages is free only on public repositories, and this
   workspace is private. So give the site its own public repository:
   - Create an empty public repository named `bridgeday` on GitHub.
   - Copy the *contents* of this folder to its root and push (`.github/workflows/site.yml`
     comes with it and runs the whole thing daily).
   - In that repository: *Settings → Pages → Source: GitHub Actions*, then *Settings → Secrets
     and variables → Actions → Variables →* `BRIDGEDAY_DEPLOY` = `pages`.
   - *Actions → site → Run workflow*. The site is live at
     `https://bernardhaddad.github.io/bridgeday/` (already the `base_url` in config.toml).
   Ask Claude to do this for you; it needs your go-ahead to create a public repository.
2. **Domain (recommended).** Buy one (e.g. `bridgedays.net`), point it at GitHub Pages
   ([docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)),
   then set `base_url = "https://yourdomain"` and `cname = "yourdomain"`.
3. **Analytics.** Make a free [GoatCounter](https://www.goatcounter.com) account and set
   `goatcounter = "yourcode"`, so you can see whether traffic is arriving.
4. **Search engines.** Add the site to [Google Search Console](https://search.google.com/search-console)
   and [Bing Webmaster Tools](https://www.bing.com/webmasters), and submit `/sitemap.xml`.
   This is the single most important step for traffic.
5. **Affiliate links.** Join a travel affiliate network. [Travelpayouts](https://www.travelpayouts.com)
   is one sign-up for many brands (flights, hotels, tours) and accepts new sites. Booking.com
   and GetYourGuide also run their own programmes. Paste each tracking link into a
   `[[affiliate]]` block, using `{start}` and `{end}` where the dates go. The disclosure line
   appears automatically.
6. **Ads (after some traffic).** Apply to Google AdSense with your domain, then set
   `adsense_client = "ca-pub-…"`. Auto ads, `ads.txt` and the privacy-policy text are generated.
   Set `contact` first; reviewers look for one.

Commit `config.toml`; the workflow rebuilds and publishes on the push.

## Sell the printable planner (the product)

The free site draws people in. The planner is what they buy: a 17+ page A4 PDF for their
country and year with their best breaks already worked out, a year-at-a-glance calendar,
a page per month with every holiday and suggested leave day marked, and a leave tracker.
Making more copies costs nothing, and delivery is automatic once it's listed.

1. `make products` builds all 204 planners for next year (about 25 seconds) into `products/`:
   one PDF per country, `all-countries-<year>-leave-planners.zip` and `catalog-<year>.csv`
   (title, handle, description per country). `products/` is git-ignored and never published.
2. List them in a shop that delivers files automatically: Shopify (Digital Downloads),
   Gumroad, Lemon Squeezy or Payhip. Start with the countries that search most (United
   States, United Kingdom, Germany, France, Canada, Australia, Spain, Italy, Netherlands,
   Ireland) plus the all-countries bundle, using the titles and descriptions from the catalog.
   With Shopify, a product titled "Germany 2027 Leave Planner" gets the handle
   `germany-2027-leave-planner`, which is what `{slug}-{year}-leave-planner` produces.
3. In `config.toml` `[shop]`, set `url`, `price`, `countries = ["US", "GB", ...]` (or `["*"]`
   once everything is listed), plus `bundle_url` and `bundle_price`. Each listed country's page
   gets a "Get the planner" box; the home page gets the bundle.
4. Once a year (October, when people plan), run `make products` for the new year and swap the
   files. That's the only recurring job: about 10 minutes, and Claude can do most of it through
   the Shopify connector.

Suggested prices: $4.99 per country and $19 for the bundle (for HR teams and remote companies).

## The premium data product: Global Long-Weekend & Absence Index

To my knowledge, nobody publishes this as a ready-made dataset. It only exists once 240+
holiday calendars, each country's weekend, the leave optimizer and World Bank population are
combined. Every figure is traceable to an open source, so it can be sold.

- **Free and public:** `/global/<year>/`. It shows the biggest long weekends on Earth ranked
  by people off, peak absence days, and a 365-day heat map of how much of the world is closed.
  It is built to be shared and quoted (journalists, travel blogs), and it is marked up as a
  `Dataset`, so Google Dataset Search can list it. That brings links and traffic to the site.
- **Paid:** `make products` also writes `products/global-leave-intelligence-<year>.zip`:
  - daily world index (365 rows)
  - every day × country (about 88,700 rows for 243 countries: holiday, long break, bridge day, open/closed, declared workdays, population)
  - all 29,000+ country pairs (days both open or closed)
  - the ranked long-weekend list
  - a README with definitions, sources and the licence (internal use, no resale)
- **Who buys it:** airline and hotel revenue managers (demand spikes), travel marketers
  (when to run campaigns, and where), HR and workforce planners at multinationals (absence
  peaks), outsourcing and support companies (which teams are reachable), and retail
  and e-commerce calendars.
- **Price:** $149 to $499 a year per company. Sell it on Gumroad or Lemon Squeezy (one
  product, one file, updated yearly), or as a Shopify digital product. Set `dataset_url` and
  `dataset_price` in `[shop]` and the world page shows a "Get the dataset" box.
- **The moat: the Leave Intent Index (first-party data).** Every plan card has an
  "✓ I'm taking this break" button. The visitor gets the break as a calendar event, and the
  site counts one anonymous GoatCounter event for that break (no cookie, no personal data).
  `make intent` (and the daily job, once the `GOATCOUNTER_TOKEN` secret is set) pulls the
  counts into git-ignored `private/intent.json`. The dataset then gains `leave_intent_<year>.csv`:
  which breaks people in each country plan to take, months before they book anything. Nobody
  else has this, and every month of traffic makes it deeper. In public, the site only shows a
  "🔥 Most chosen by planners" badge once 5+ people chose a plan; breaks with fewer than 3
  planners are left out of the paid file.
  Setup: GoatCounter account → `analytics.goatcounter` in config.toml → in GoatCounter,
  *Settings → API → new key* with read statistics → add it as the repository secret
  `GOATCOUNTER_TOKEN`.
- **Next level (future potential):** a monthly-updated feed or API subscription, regional and
  school-holiday layers, and a "your markets" custom report. That's where recurring revenue lives.


## Commands

```bash
make setup   # install (standard library only at runtime; pytest and ruff for dev)
make check   # lint + 78 tests
make data    # regenerate data/: holidays (offline, holidays library) + World Bank population
make build   # production build into dist/
make run     # build for localhost and serve at http://127.0.0.1:8000
make products  # the paid PDF planners + dataset into products/ (never committed)
make intent    # pull Leave Intent counts from GoatCounter into private/ (never committed)
```

## How it works

- `data.py` computes every country's holidays offline with the open-source
  [`holidays`](https://github.com/vacanza/holidays) library (MIT: commercial use and
  redistribution allowed) and takes population from the World Bank (CC BY 4.0). The snapshot
  in `data/` is committed. Nager.Date was the first source and is no longer used: its terms
  forbid running a holiday portal on its data and require sponsorship for commercial use.
- `optimizer.py` finds maximal stretches of days off. `best_plans` ranks bridges by days off per
  leave day. `best_budget` solves "most days off for N leave days" exactly, using weighted interval
  scheduling with a leave budget.
- `render.py` writes the pages (all external text escaped). `build.py` adds the sitemap, robots,
  ads.txt, CNAME, .ics calendars and the 404 page.
- `.github/workflows/bridgeday-site.yml` (repository root) runs it all daily.
