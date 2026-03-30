# Security Policy

## Supported releases

APT-Finder is maintained from the latest `main` branch and tagged releases only.

## Reporting a vulnerability

Please do not open a public issue for:

- Exposed secrets or API keys
- Sensitive local data accidentally committed
- Security issues in scraping or routing workflows

Instead, report the problem privately to the repository maintainers and include:

- A clear description of the issue
- The affected file or endpoint
- Reproduction steps, if safe to share
- Whether any secret or private data may have been exposed

## Operational guidance

- Keep `.env` local and out of Git.
- Do not commit OTP/GTFS data, raw scrape fixtures, or local database files.
- Rotate any secrets that may have been exposed before publishing a fix.
