# Local Network & Production Launcher Setup

## 1. Start the full stack

Use the all-in-one launcher in `scripts/`:

- Windows: `powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1`
- Linux: `bash scripts/start_all.sh`

The launcher will:

- create or reuse `.venv`
- install backend dependencies when they are missing
- install frontend dependencies when `web/node_modules/` is missing
- start the FastAPI backend
- start the cached OpenTripPlanner launcher in `otp-routing/`
- build the React app for production and serve it with Vite preview

## 2. Access from other devices

By default, the launcher auto-detects a non-loopback IPv4 address and uses it for the production frontend build.

If you want to force a specific hostname or IP, set `APT_FINDER_HOST` before starting the launcher.

Example URLs:

- API: `http://YOUR_HOST:8000`
- Web: `http://YOUR_HOST:5173`

## 3. Firewall and DNS

If other devices cannot connect, make sure the server firewall allows:

- Port 8000 for the API
- Port 5173 for the web preview server

If you choose a custom hostname via `APT_FINDER_HOST`, make sure DNS or your local hosts file resolves that name on every client device.

## 4. Troubleshooting

- If the web preview fails, run `npm ci` inside `web/` and try again.
- If the API fails, check your local `.env` and `config.yaml` files.
- If OTP fails, verify that the required local assets are still present in `otp-routing/`.
