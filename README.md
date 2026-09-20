# Loadshedding BD · লোডশেডিং বিডি

A plain-language website about power cuts in Bangladesh, for people who are not engineers.

It answers the questions people actually ask during a power cut: **Is the power on? Is it my area?
Who do I call? Why is this happening? When will it hit next? What will my bill be?** Every number
comes from a report the government itself publishes, copied as published and refreshed every
time someone opens the page. English and বাংলা, light and dark, phone first.

## What you see

Five tabs, each with its own link.

| Tab | What it tells you |
|---|---|
| **Today** `#today` | How many homes out of 100 have no power right now. The next 12 hours, hour by hour. Your area: how it compares, tomorrow's temperature, planned shutdowns, **tap-to-call hotlines** and local complaint offices. A weather-warning banner appears only while a Met Office (BMD) warning covers your district. A share button sends tonight's outlook through the phone's own share sheet. |
| **Map** `#map` | Bangladesh coloured by loadshedding in each of the 9 grid regions. Search about 7,600 places (district, upazila, union, pourashava, city ward, neighbourhood) to see which region you are in. DESCO customers can look up the hours their own street is due for cuts. |
| **Why** `#why` | Which power plants could not run yesterday and why (no gas, coal trouble, down for repairs), with the plant names one tap away. How much power is coming from India and Nepal right now. Gas needed vs delivered, idle capacity, and what the fuel costs per unit. |
| **Forecast** `#outlook` | The next 24 hours and the next 30 days: how likely cuts are, for how long, and at what time of day. Each forecast is shown next to how wrong it has been in the past. |
| **Costs** `#data` | An **electricity bill calculator** from the official slab rates (slide your units, see the bill and how close you are to the next, dearer slab). Petrol, octane, diesel, kerosene and government LPG prices. Below that, every chart, table and downloadable file behind the site. |

Design rules the page follows:

- **Sentence first, number second, chart last.** Charts stay folded until asked for.
- **Pick your place once**; it is remembered on the device and every tab then talks about your area.
- **Never colour alone**: every status has an icon and words. Checked with axe on every tab, in
  both languages and both themes.
- **Nothing stale is shown as new.** Every card says how fresh it is, and hides itself when its
  source goes quiet (idle plants after 7 days, the DESCO schedule after 14, warnings at their
  expiry, shutdown notices once their day has passed).

## How it works

```
visitor ─▶ app.py (FastAPI) ─▶ data/*.csv, *.json ─▶ index.html + static/*.js
              │
              ├─ every request: Power Grid (PGB) checked if the last check is over 2 minutes old
              │                 (one fetch, shared by all visitors, never blocks other requests)
              ├─ hourly, in the background: BPDB, Petrobangla, BPC, SREDA, DPDC tariff, BMD forecast
              │                 and warnings, DESCO schedule, NESCO notices, weather
              └─ after new PGB hours arrive: the forecast is rebuilt in the background
```

- Government sites send no CORS headers, so a browser cannot read them directly. The server does.
- Data can't be fresher than the source: PGB publishes hourly; BPDB, Petrobangla and the regions
  daily (regions about 5 days late). The page shows when PGB last published and when the server
  last checked.
- If PGB is unreachable, the page serves the stored data and says so.
- One failing source never stops the others, and a changed page layout is an error, never a guess.
- A GitHub Action runs the same scrapers every hour and commits `data/`, so a fresh deploy starts
  from recent data even on hosts that wipe their disk.

**Stack:** Python 3.12 standard library for scraping (`urllib`, `html.parser`, `xml.etree`),
`pdfplumber` for PDFs, `numpy` for the forecasts, FastAPI + uvicorn to serve. The page is plain
HTML, CSS and JavaScript with Chart.js and Leaflet from a CDN. No build step, no database.

## Project layout

```
app.py                   the server: serves the page and keeps data/ fresh
index.html               the page
static/app.js            rendering          static/tools.js   pure logic (bill, hotlines, warnings…)
static/i18n.js           all text, English and বাংলা          static/app.css    styles, light and dark
static/geo/              places.json, offices.json, district and upazila outlines
scraper/pgb.py           Power Grid Bangladesh: hourly generation, demand, supply, loadshedding
scraper/sources.py       BPDB regions, BPC fuel prices, SREDA capacity, DPDC tariff
scraper/pdf_sources.py   BPDB daily report (totals, idle plants), Petrobangla gas report
scraper/bmd.py           Met Office station forecast and CAP weather warnings
scraper/utilities.py     DESCO feeder schedule, NESCO planned shutdowns
scraper/weather.py       Open-Meteo history, forecast and normals (for the forecast model)
scraper/forecast.py      next 24 hours, next 30 days, and their backtests
tools/build_places.py    builds static/geo/places.json      tools/build_offices.py   builds offices.json
geo/                     region-to-district mapping and hand-curated Bangla names
data/                    everything the scrapers write; committed hourly by the Action
tests/                   Python tests with saved real pages and PDFs; tests/js for the page logic
```

## Data

| File | Source | Grain | History |
|---|---|---|---|
| `generation.csv` | [PGB generation report](https://erp.powergrid.gov.bd/w/generations/view_generations_bn) | hourly, MW by fuel, imports by line | 12 months (PGB has 2015→) |
| `demand.csv` | [PGB demand/supply/loadshed](https://erp.powergrid.gov.bd/web/generations/view_demand_supply_loadshed_bn) | hourly, MW | 2026-04-23→ (PGB has nothing older) |
| `zones.csv` | [BPDB area-wise demand](https://misc.bpdb.gov.bd/area-wise-demand) | daily, 9 regions, at the 21:00 evening peak | 12 months |
| `bpdb_daily.csv` | BPDB daily generation report PDF | daily: shortfall by cause, energy, fuel cost, gas supplied, max temperature | 12 months |
| `bpdb_forecast.csv` | same PDF | BPDB's own next-day forecast | 12 months |
| `plants.csv` | same PDF | each plant that lost output: MW lost, reason (gas, coal, oil, water, repair), BPDB's remark, restart date | latest report only |
| `gas.csv` | [Petrobangla daily gas report](https://petrobangla.org.bd/pages/reports) PDF | daily MMCFD: production, R-LNG, gas needed vs delivered to power plants | 12 months |
| `fuel_prices.csv` | [BPC](https://bpc.gov.bd/) | price changes with effective dates (petrol, octane, diesel, kerosene, government LPG cylinder, furnace oil, LDO) | builds up over time |
| `tariff.csv` | [DPDC retail tariff](https://dpdc.gov.bd/pages/static-pages/6922de6f933eb65569e1a9c4) (the BERC order, same for every utility) | home slabs, Tk per unit, demand charge, effective month | current order only |
| `bmd_forecast.csv` | [BMD](https://bmd.gov.bd/) station forecast (`home_all_json`) | max/min °C for 46 stations with coordinates | current days only |
| `alerts.json` | [BMD CAP feed](https://cap.bmd.gov.bd/api/cap/rss.xml) | weather warnings in English and Bangla, expiry, and the districts they cover | the 5 in BMD's feed |
| `desco_schedule.json` | [DESCO feeder schedule](https://desco.gov.bd/pages/static-pages/69db2a3c6a42b12e9344d1f1) PDF | per 11 kV feeder: areas served and the hours it is cut | latest upload only |
| `nesco_notices.csv` | [NESCO shutdown notices](https://nesco.gov.bd/) | planned shutdowns: days, hours, town, official PDF | the 10 newest |
| `capacity.csv` | [SREDA](https://www.renewableenergy.gov.bd/index.php?id=7) | installed MW by fuel, appended when it changes | builds up over time |
| `weather*.csv` | [Open-Meteo](https://open-meteo.com/) (not a government source) | hourly Dhaka temperature/humidity, 16-day forecast, 2021–2025 daily normals | 12 months |
| `forecast.json` | computed | next 24 hours, next 30 days, and their measured error | — |

Values are MW unless named otherwise. A blank cell means the source published nothing; it is never
filled with 0. Timestamps are Bangladesh time (UTC+6).

## Forecasts and how good they are

Both forecasts are replayed on past days and the page shows the result next to them.

| | Method | Error (backtest) | Naive baseline |
|---|---|---|---|
| Next 24 h demand | least squares on hour, weekday, temperature, humidity, last week's level, anchored to the latest actual hours | 3.5% (2.4% at 21:00) | 4.8% (same hour yesterday) |
| Next 24 h loadshed | ½ yesterday's loadshed that hour + ½ (forecast demand − last 3 days' supply) | 603 MW | 757 MW |
| Next 30 days peak demand | last 14 days' average peak, adjusted for temperature difference | 4.35% | 5.9% (last 14 days' average) |
| Hours without power per day | 24 × unserved ÷ demand, blended with the 14-day average | about 1.1 h | — |
| Time of day cuts are likeliest | model gap plus the recent loadshedding profile | right about 6 days in 10 | — |

The 30-day range is the 10th–90th percentile of the backtest's own misses. Backtests use actual
weather, so live forecasts (which rely on predicted or typical weather) miss by somewhat more.
Loadshed depends on how much fuel arrives, which no weather model can see; treat it as the least
certain number on the page. BPDB's own evening-peak forecast is scored the same way for comparison.

### Tried and not adopted (2026-09-19)

Each was replayed on the same past days as the forecasts above and dropped because it did not
clearly beat the current method:

| Idea | Result | Current |
|---|---|---|
| Gas delivered to power plants (Petrobangla) as an input to daily outage hours | 1.32 h (ridge), 1.16 h (gradient boosting) | 1.08 h |
| Gradient boosting for 24 h demand | 4.03% alone, 3.45% averaged with current | 3.51% |
| 12 months of BPDB evening-peak demand to learn the heat effect for the 30-day outlook | 4.42% | 4.35% |

Gas does track loadshedding (correlation −0.46 with daily outage hours), but yesterday's outage
hours track it more closely (+0.82), and gas figures arrive 1–2 days late, so by the time they
are known the shortage already shows in the loadshedding the model uses. The real limit is
history: hourly loadshedding data only starts on 2026-04-23 and grows every day.

## Places and the map

Search covers about 7,600 places (`static/geo/places.json`, built by `python3 tools/build_places.py`):
64 districts, 544 upazilas/thanas, 4,566 unions, 309 pourashavas and 284 city-corporation wards
(geoBoundaries / BBS 2020, CC BY 3.0 IGO), plus 1,838 neighbourhoods and towns such as Mirpur 2,
Uttara and Agrabad (© OpenStreetMap contributors, ODbL). Bangla names come from bangladesh-geocode
(MIT), OpenStreetMap, and `geo/upazila_bn_extra.csv` for 48 city thanas neither source names.
Every place is assigned to its upazila and district by where it sits on the map.

Wards don't say which city corporation they belong to, so they are shown with their thana
("Ward 12, Mirpur"); the list is from 2020, so newer or renumbered wards may be missing.
Loadshedding is only published for BPDB/NLDC's **9 regions**, so every place shows its region's
figures, labelled as region-level.

`geo/zone_districts.csv` maps each district to its region. No official district list is published;
each row is marked `verified` (plants BPDB's own daily report groups under that region, or officials
quoted in the press) or `inferred` (substation-load arithmetic). Note Greater Faridpur (Faridpur,
Gopalganj, Madaripur, Shariatpur, Rajbari) is in the **Khulna** region, not Dhaka. The page says
when a district's region is inferred.

## Hotlines and complaint offices

Short codes are from the Power Division circular of 18 Sep 2026: Power Division 16999, DPDC 16116,
DESCO 16120, Palli Bidyut (BREB) 16899, NESCO 16603, WZPDCL 16117, BPDB 16200. Which utility serves
a place follows each utility's published service area (DPDC and DESCO: Dhaka, Narayanganj, Gazipur;
NESCO: Rajshahi and Rangpur regions; WZPDCL: Khulna and Barishal regions; BPDB: the other four;
Palli Bidyut: villages everywhere).

`static/geo/offices.json` holds 176 local complaint offices of DESCO, DPDC, NESCO and WZPDCL,
rebuilt by hand with `python3 tools/build_offices.py`. Each office is tied to one district when it
is built; a name that fits two districts (one "ফুলবাড়ী" office) is never shown, and an office is
only offered when its name contains the place, upazila or district as whole words, so নবাবগঞ্জ
(Dinajpur) never gets a চাঁপাইনবাবগঞ্জ number. A mobile number is preferred; 7 offices publish
only a landline.

The bill calculator shows the energy charge only. Demand charge (Tk 42 per kW), VAT and meter rent
are left out because no official page states the VAT rate as text.

## Known quirks in the sources

- ~2% of PGB generation rows don't sum exactly to the total, almost always by a few MW. One row is
  mistyped at source (2025-09-26 13:00: parts 26,014 MW vs total 13,609 MW). Kept as published.
- PGB's generation page has deficit/loadshed columns commented out in its HTML; loadshed comes only
  from the demand table. Each day also has an extra 19:30 row; daily averages use on-the-hour rows.
- Several gov.bd HTTPS servers omit their intermediate certificates.
  `scraper/missing-intermediates.pem` supplies them so verification stays on.
- Petrobangla's listing sometimes shows the wrong date; the date is read from inside each PDF.
- BPDB's daily report often prints the wrong year for "yesterday" (e.g. "31.12.24" on the
  01-01-2026 report). The date is taken from the report's own header instead.
- 14 of the last 365 BPDB reports use different wording for a label (e.g. the coal line in July
  2026) and are skipped and logged rather than guessed. Malformed archived PDFs likewise.
- BMD draws warning areas with coarse outlines that clip neighbouring districts, so a district
  counts as covered only when at least half of its upazilas fall inside; a port-sized area keeps
  whatever it touches.
- BMD's per-station `weather` text is the same for every row, so only temperatures are used.
- BMD's feed carries Update and (possibly) Cancel or Test messages. Only `Actual` messages are
  shown, and a warning named in a later message's `references` is treated as withdrawn. A warning
  with no outline is shown to everyone rather than to no one.
- NESCO writes times loosely ("রাত ২ ঘটিকা", "০১:৩০ টা", or no part of day at all). "রাত" before 6
  is read as after midnight; a notice naming two dates stays listed until the last one.
- DESCO's schedule is one PDF replaced in place at a new link each time; a cell holds the load to
  shed in that hour, and 0 means nothing is shed.
- Government portal file links change on every upload, so the list page is always read first.

## Sources checked and not used

| Source | Why not |
|---|---|
| BERC monthly private LPG price; household gas tariffs | published only as scanned images (the page links to BERC's notice instead) |
| Bangladesh Bank (fuel imports, exchange rate) | blocks scripts; would need a full browser |
| BRTA vehicle numbers | irregular yearly PDF; does not help a household decide anything |
| BPDB, DPDC and Palli Bidyut loadshedding schedules | stale (2022–2025) or phone-camera scans |
| WZPDCL shutdown feed | clean JSON, but not updated since Feb 2025 |
| BCMCL / BAPEX | scanned monthly PDFs |
| data.gov.bd | energy datasets last updated 2016–2018 |
| FFWC river levels and flood alerts | works only with a key copied from their website's code; needs FFWC's permission first |
| Coal stock, LNG cargo arrivals, Rooppur status, subsidy figures | not published in any readable form |

## Run locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -p '*_test.py'
node --test tests/js/*.test.js             # page logic; Node's built-in runner, no packages
.venv/bin/uvicorn app:app --port 8000        # open http://localhost:8000
```

Scrapers can also run on their own (`--days N` sets the backfill for an empty CSV):

```sh
.venv/bin/python scraper/pgb.py
.venv/bin/python scraper/sources.py
.venv/bin/python scraper/pdf_sources.py
.venv/bin/python scraper/weather.py
.venv/bin/python scraper/bmd.py
.venv/bin/python scraper/utilities.py
.venv/bin/python scraper/forecast.py
```

Tests use saved copies of the real pages and PDFs (`tests/fixtures/`), so they need no network.

## Deploy

**Live site (GitHub Pages):** https://dhrupo.github.io/loadshedding-bd/

The `scrape` Action runs every hour (and on every push to `main`): tests, scrapers, commit
`data/`, then publish `index.html`, `static/` and `data/` to GitHub Pages. The page works as plain
static files; on Pages the data is as fresh as the last hourly run, and the "checked N seconds
ago" line is simply absent. One-time setup: Settings → Pages → Source: **GitHub Actions**.

**Vercel:** `vercel.json` makes Vercel serve the same three things as plain static files (`index.html`, `static/`, `data/`),
and tells it not to run `app.py`. Vercel's disk is read-only and keeps nothing between requests, so the live server could not
save what it fetches there. Each hourly `data:` commit to `main` redeploys the site, so Vercel is as fresh as Pages.
One-time setup: import the repository at vercel.com/new and leave every setting as it is.

**With the live check (any Python host):** `uvicorn app:app --host 0.0.0.0 --port $PORT`, single
worker (the refresh locks are per process). The server then re-checks Power Grid Bangladesh
whenever a visitor arrives and the last check is over 2 minutes old.

## Credits

Data: Power Grid Bangladesh, Bangladesh Power Development Board, Petrobangla, Bangladesh Petroleum
Corporation, SREDA, Bangladesh Meteorological Department, DPDC, DESCO, NESCO, WZPDCL and the Power
Division, all from their public websites. Weather history from Open-Meteo. Boundaries from
geoBoundaries (CC BY 3.0 IGO, BBS 2020); place names from bangladesh-geocode (MIT) and
© OpenStreetMap contributors (ODbL). Charts by Chart.js, maps by Leaflet.

This is an independent civic project, not a government service. Figures are copied from official
reports, and the forecasts are estimates; for an actual outage, call your electricity company.
