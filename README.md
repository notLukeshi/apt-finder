# APT-Finder

APT-Finder is a Python apartment search tool for Japanese housing sites, commute analysis, and a lightweight React dashboard.

## Highlights

- Scrapes multiple Japanese monthly housing sites through dedicated scraper classes.
- Stores listings, addresses, targets, and commute data in SQLite.
- Calculates commute time using OpenTripPlanner, with optional Google Maps or Nominatim geocoding.
- Exposes a FastAPI backend and a Vite/React dashboard.
- Keeps local-only OTP data and private configuration out of Git.

## Repository policy

This repository is public, but some files are intentionally **local-only**:

- `.env`
- `config.yaml`
- `otp-routing/assets/`
- `otp-routing/gtfs_backup/`
- raw scrape fixtures in `docs/scrape/`

Use the example files instead:

- `.env.example`
- `config.example.yaml`

## OTP assets

Before running the launcher, make sure these local files exist:

- `otp-routing/assets/otp.jar`
- at least one `otp-routing/assets/*.osm.pbf`
- one or more GTFS `.zip` files in `otp-routing/gtfs_backup/`

Download sources:

- **OTP JAR**: download a shaded release from <https://github.com/opentripplanner/OpenTripPlanner/releases>, rename it to `otp.jar`, and place it in `otp-routing/assets/`.
- **OSM PBF**: download a regional extract from <https://download.geofabrik.de/asia/japan/kanto.html> or another region, then save it in `otp-routing/assets/` with any filename ending in `.osm.pbf` such as `kanto.osm.pbf`.
- **GTFS ZIP files**: register at <https://developer.odpt.org/>, copy your access token from <https://developer.odpt.org/editkeys>, then download the `.zip` files from <https://ckan.odpt.org/dataset> and place them in `otp-routing/gtfs_backup/`.

Keep the original GTFS `.zip` filenames exactly as downloaded, and do not unzip them.

For the full step-by-step OTP setup, see `docs/otp-routing/route_setup.md`.

## Distance and geocoding setup

The distance engine now supports two independent switches in `config.yaml`:

- `distance.use_google_maps_bike_calculation`
  - `true`: the bike-only time is calculated from Google Maps and OTP, then averaged when both are available
  - `false`: the bike-only time uses OTP only
- `distance.geocoding.provider`
  - `google`: geocoding uses Google Maps Platform
  - `nominatim`: geocoding uses the public OpenStreetMap Nominatim service
  - `jageocoder`: geocoding uses a Japanese address dictionary (offline or remote server)

### When using Google Maps Platform

You need a Google Cloud project with billing enabled and the following APIs turned on:

- **Geocoding API**
- **Directions API (Legacy)**

The backend uses Google Maps web services directly, so you do **not** need the Maps JavaScript API for these features.

Recommended setup steps:

1. Create or select a Google Cloud project.
2. Enable billing for that project.
3. Enable the Geocoding API and the Directions API (Legacy).
4. Create an API key under **APIs & Services > Credentials**.
5. Restrict the key to the backend machine or IP addresses that will run the scraper.
6. Put the key in your local `.env` as `GOOGLE_MAPS_API_KEY`.

### When using Nominatim

Nominatim is API-free, but the public service has strict fair-use expectations. Use it carefully:

- Set `distance.geocoding.provider: nominatim`
- Provide a meaningful `User-Agent` string in `distance.geocoding.nominatim.user_agent`
- Keep `distance.geocoding.nominatim.min_delay_seconds` at **1.0 or higher**
- Keep `distance.geocoding.nominatim.max_requests_per_run` small, such as **25** or another contained batch size

If you use Nominatim, the scraper can run without a Google Maps API key.

### When using jageocoder

jageocoder is a Python library that geocodes Japanese addresses using a dictionary database derived from government data (Address Base Registry + GSI). It has the best coverage for Japanese addresses among the free options.

Two modes are supported:

- **Local database** (default, `server_url: null`): no network, no rate limit, fastest. Requires a one-time dictionary download.
- **Remote server** (`server_url: https://...`): connects to a jageocoder-server instance. The public demo server has a rate limit.

Setup for local database:

```bash
pip install jageocoder
```

Download a dictionary file. The `jageocoder download-dictionary` command may fail silently on some networks; use `curl` as a reliable fallback:

```bash
# Full dictionary (住居表示・地番, ~4.5 GB, building-level precision):
curl -L -o jukyo_all_20250423_v22.zip https://www.info-proto.com/static/jageocoder/20250423/v2/jukyo_all_20250423_v22.zip
jageocoder install-dictionary jukyo_all_20250423_v22.zip

# Or the lighter block-level dictionary (~351 MB, sufficient for routing):
# curl -L -o gaiku_all_20250423_v22.zip https://www.info-proto.com/static/jageocoder/20250423/v2/gaiku_all_20250423_v22.zip
# jageocoder install-dictionary gaiku_all_20250423_v22.zip
```

Check <https://www.info-proto.com/static/jageocoder/latest/v2/> for the latest available dictionary versions.

Then set in `config.yaml`:

```yaml
distance:
  geocoding:
    provider: jageocoder
    jageocoder:
      server_url: null
      min_delay_seconds: 0.5
```

If you use jageocoder with a local database, the scraper can run without a Google Maps API key and without any external API registration.

## Quick start

### 1. Prepare local config

Copy `.env.example` to `.env` if you plan to use Google Maps features, and `config.example.yaml` to `config.yaml`, then edit them for your machine, target locations, websites, and distance/geocoding providers.

### 2. Launch the full stack

Run one of the platform launchers from `scripts/`:

```bash
# Linux
bash scripts/start_all.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
```

The launcher will:

- create or reuse `.venv`
- install missing Python dependencies
- install frontend dependencies when `web/node_modules/` is missing
- start the FastAPI server
- start the cached OpenTripPlanner launcher
- build the React app for production and serve it on the preview server

Optional overrides:

- `APT_FINDER_HOST` to force a hostname or LAN IP used by the web build and API URLs
- `APT_FINDER_API_PORT` to change the API port
- `APT_FINDER_WEB_PORT` to change the preview port

### 3. Run the scraper manually, if needed

```bash
python main.py
```

Useful options:

```bash
python main.py --scrape-only
python main.py --website TokyoMonthly
python main.py --start-page 1 --end-page 5
```

For seeing all available options:
```bash
python main.py --help
```

### 4. Manual component start, if needed

```bash
python run_api.py
```

```bash
apt-api
```

```bash
cd web
npm ci
npm run build
npm run preview -- --host 0.0.0.0 --port 5173 --strictPort
```

The frontend now supports a configurable `VITE_API_BASE_URL`, which the launcher sets automatically for production preview. If you build the web app manually, set `VITE_API_BASE_URL` to a reachable API URL first.

## Project layout

```text
apt-finder/
├── main.py                # Scraper CLI entry point
├── run_api.py             # FastAPI server entry point
├── config.example.yaml    # Public config template
├── scripts/               # All-in-one Windows/Linux launchers
├── src/
│   ├── api/               # FastAPI routes and response schemas
│   ├── config/            # YAML config loader
│   ├── database/          # SQLite repository and schema
│   ├── distance/          # Configurable geocoding + OTP logic
│   ├── filters/           # Reusable apartment filters
│   ├── models/            # Dataclasses for domain objects
│   └── scrapers/          # Website-specific scrapers
├── docs/
│   ├── architecture.md
│   ├── scraping-ethics.md
│   └── web/
└── web/                   # React frontend
```

## Testing

```bash
pytest
cd web
npm ci
npm run build
```

For an end-to-end smoke run, use `bash scripts/start_all.sh` or `powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1`.

## Documentation

- `docs/architecture.md` explains the backend/frontend split.
- `docs/scraping-ethics.md` covers safe publishing and responsible scraping.
- `docs/web/local_network_setup.md` explains LAN setup.

## Adding a new scraper

1. Create a new module under `src/scrapers/`.
2. Inherit from `BaseScraper`.
3. Register it with `@ScraperRegistry.register("WebsiteName")`.
4. Add the site to your local `config.yaml`.

## License

MIT License. See `LICENSE`.
