# Rextech Studios — Event Monitoring Dashboard

Automatically discovers conferences, hackathons, webinars, expos, demo days,
funding programmes and networking events across game development, mobile apps,
AR/VR/XR, AI, software, the startup ecosystem and digital innovation.

Nobody searches manually. The system visits 74 trusted websites **every 6 hours**,
extracts events, ignores anything it has already seen, and flags the rest as new.

Rextech Studios builds **games, AR/VR experiences and apps**, so every event is
scored against those three areas. Focus events are marked ★, ranked above
everything else, given their own section on the home page, and can be isolated
with the **★ Game · AR/VR · Apps** filter. Nothing is hidden — the rest of the
tech, AI, startup and funding events stay available underneath.

Free to run end to end — no paid services, no API keys, no accounts.

---

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

The dashboard opens at **http://127.0.0.1:8000**.

The first crawl starts immediately, so the dashboard fills up within a minute or two.

### Other ways to run it

```bash
python main.py --crawl      # run one crawl and exit (no web server)
python main.py --no-crawl   # start the server without the startup crawl
python -m scraper.runner    # crawl directly, for testing
```

### Optional: JavaScript-only sources

Six sources (Unity, Unreal, GDG, Startup India, F6S, MachineHack) build their
event lists in the browser. To include them:

```bash
pip install playwright
playwright install chromium
```

Without Playwright those six are skipped and the other 49 work normally.

---

## Project structure

```
events finder/
├── main.py                  entry point — database + scheduler + server
├── requirements.txt
│
├── config/
│   ├── settings.py          paths, port, 6-hour interval, timeouts
│   ├── sources.py           the 74 websites that are crawled
│   └── categories.py        the 13 categories, focus rules, keyword rules
│
├── database/
│   ├── db.py                SQLite schema, inserts, filtered queries
│   └── events.db            created on first run
│
├── scraper/
│   ├── fetcher.py           requests (default) / Playwright (only if needed)
│   ├── extractor.py         HTML → events, via BeautifulSoup
│   ├── dateparser.py        recognises the many date formats sites use
│   ├── classifier.py        category, location, online/offline, noise filter
│   └── runner.py            the crawl itself
│
├── scripts/
│   └── backfill_focus.py    re-scores an existing database after rule changes
│
├── scheduler/
│   └── scheduler.py         background thread, fires every 6 hours
│
├── server/
│   └── app.py               http.server routes + JSON API
│
├── frontend/
│   ├── index.html           home page
│   ├── events.html          new events + all events
│   └── static/
│       ├── style.css        dark theme
│       ├── app.js           shared helpers + event card
│       ├── home.js          home page logic
│       └── events.js        filters, search, table view
│
└── logs/app.log
```

---

## How the pages work

**Home (`/`)**
- 🔔 notification box — `🔔 12 New Events`, or `No New Events`
- counters: total, upcoming, closing soon, focus, new
- four sections: **★ Game · AR/VR · App Events**, **Recent Events**,
  **Upcoming Events**, **Registration Closing Soon**
- a Refresh button that triggers a crawl on demand

**New Events (`/new`)** — opened by clicking the bell or the notification box.
A table with Event Name, Category, Location, Date, Registration Status, Website
and an **Apply Now** button that opens the official event site in a new tab.

Opening this page clears the badge, but the batch stays on screen. The server
returns the batch's discovery timestamp and the page filters on
`created_at >= cutoff` from then on, so reloading the page or changing a filter
no longer empties the table.

**All Events (`/events`)** — search by title plus filters for category, country,
state, online/offline, registration status, upcoming-only and core focus.
Results are ranked focus-first, then by date, and the list is not paginated —
every match is shown.

No login, no authentication, no user management, no payments, no admin panel.

---

## How an event is found

For every source website:

1. **Fetch** the page — `requests` first, Playwright only where required.
2. **Extract**, using the first strategy that produces results:
   - schema.org JSON-LD `Event` objects (perfect data, no guessing)
   - repeated event cards (`<article>` / `.event` / `.card` …)
   - bare links, for pages that are just lists (government notice boards)
3. **Filter out** navigation text, boilerplate, and news reports about events
   that already happened.
4. **Classify** — category, location, online/offline, and a parsed date.
5. **Compare with SQLite.** Already present → ignore. Otherwise insert with
   `is_new = 1`.

### Duplicate detection

Each event gets a `fingerprint`: a SHA-256 of
`source + normalised title + date`. The title is lower-cased with punctuation
removed, so `AI Summit 2026` and `AI Summit, 2026!` collapse to one entry.
The column has a `UNIQUE` constraint, so a duplicate is rejected by the
database itself and can never be inserted twice.

### Registration status

Recomputed after every crawl from the event date:

| Status | Meaning |
|---|---|
| `Open` | more than 14 days away |
| `Closing Soon` | starts within 14 days |
| `Closed` | date has passed |

---

## Database

SQLite only, one file at `database/events.db`.

| Column | Purpose |
|---|---|
| `id` | primary key |
| `title` | event name |
| `category` | one of the 12 categories |
| `location` | city / country / "Online" |
| `date` | human-readable, exactly as scraped |
| `date_iso` | `YYYY-MM-DD`, used for sorting and status |
| `registration_url` | where **Apply Now** goes |
| `website` | the organisation's site |
| `source` | which website it came from |
| `status` | Open / Closing Soon / Closed |
| `mode` | Online / Offline |
| `country`, `region` | drive the country / state filters |
| `created_at` | when we discovered it |
| `is_new` | 1 until the New Events page is opened |
| `focus` | 2 = title names games / AR-VR / apps, 1 = related, 0 = other |
| `fingerprint` | unique duplicate-detection key |

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/summary` | everything the home page needs, in one call |
| GET | `/api/events` | filtered list — `q`, `category`, `country`, `state`, `mode`, `status`, `upcoming`, `new`, `since`, `focus`, `order`, `limit` |
| GET | `/api/stats` | counters and filter options |
| POST | `/api/mark-seen` | clears the 🔔 badge, returns the batch `cutoff` |
| POST | `/api/refresh` | starts a crawl immediately |

---

## Adding a website

Append one dictionary to `SOURCES` in [config/sources.py](config/sources.py):

```python
{
    "name": "Some Tech Conference",
    "url": "https://example.com/events",   # the page that lists the events
    "website": "https://example.com",
    "category": "Conference",              # fallback if auto-detection is unsure
    "region": "Kerala",
    "country": "India",
    "js_required": False,                  # True only if the list needs a browser
},
```

Nothing else needs to change — the extractor works out the markup on its own.

---

## Current state

A full crawl reaches **47 of 55 sources** and stores around **220 events**.
The 8 that fail either block automated requests or need Playwright; they are
logged as warnings and never stop the crawl.

Everything is logged to `logs/app.log`.
