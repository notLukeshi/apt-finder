# Architecture Overview

APT-Finder has three main layers:

## 1. Scraping layer

- `src/scrapers/` contains website-specific scrapers.
- `BaseScraper` provides retry logic, rate limiting, and shared HTTP behavior.
- `ScraperRegistry` maps website names to scraper classes.

## 2. Data and routing layer

- `src/models/` defines the domain dataclasses.
- `src/database/` stores apartments, websites, targets, and commute distances in SQLite.
- `src/distance/` calculates geocoding and route times using configurable Google Maps or Nominatim geocoding plus OpenTripPlanner.

## 3. API and dashboard layer

- `src/api/` exposes apartment, target, website, and stats endpoints.
- `web/` renders the dashboard and talks to the API through the `/api` proxy.

## Local-only data

These items are expected to stay on the developer machine and out of Git:

- `.env`
- `config.yaml`
- `otp-routing/assets/`
- `otp-routing/gtfs_backup/`
- raw scrape fixtures under `docs/scrape/`

The repository ships example files for local setup instead:

- `.env.example`
- `config.example.yaml`
