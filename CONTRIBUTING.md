# Contributing to APT-Finder

Thanks for helping improve APT-Finder. This project is kept intentionally small and predictable, so please favor simple changes over clever ones.

## Local setup

- Install Python dependencies from `pyproject.toml` or `requirements.txt`.
- Create a local `.env` from `.env.example` and add your `GOOGLE_MAPS_API_KEY` only if you enable Google geocoding or Google bike calculations.
- Keep private OTP/GTFS assets on disk, but do not commit them.

## Before opening a pull request

- Run the Python checks and tests relevant to your change.
- Run the frontend build if you touched `web/`.
- Make sure your changes do not expose secrets, local datasets, or personal addresses.
- Update documentation when behavior changes.

## Code style

- Follow DRY and KISS principles.
- Prefer small functions, clear names, and explicit error handling.
- Keep imports at the top of the file.
- Preserve backwards compatibility where practical.

## Pull request checklist

- [ ] Description explains the user-facing change
- [ ] Tests were added or updated
- [ ] Existing behavior still works
- [ ] Documentation was updated
- [ ] No local-only data or secrets were added to the repository
