#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$PROJECT_ROOT/web"
OTP_SCRIPT="$PROJECT_ROOT/otp-routing/start_otp.sh"
VENV_DIR="$PROJECT_ROOT/.venv"
API_PORT="${APT_FINDER_API_PORT:-8000}"
WEB_PORT="${APT_FINDER_WEB_PORT:-5173}"
API_BIND_HOST="${APT_FINDER_API_HOST:-0.0.0.0}"
BOOTSTRAP_PYTHON="${PYTHON:-}"

if [ -z "$BOOTSTRAP_PYTHON" ]; then
  BOOTSTRAP_PYTHON="$(command -v python3 || command -v python || true)"
fi

if [ -z "$BOOTSTRAP_PYTHON" ]; then
  echo "ERROR: python3 or python was not found in PATH." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm was not found in PATH. Install Node.js before starting the web app." >&2
  exit 1
fi

supports_color() {
  [ -t 1 ] && [ "${TERM:-}" != "dumb" ]
}

if supports_color; then
  C_RESET='\033[0m'
  C_RED='\033[31m'
  C_GREEN='\033[32m'
  C_YELLOW='\033[33m'
  C_BLUE='\033[34m'
  C_MAGENTA='\033[35m'
  C_CYAN='\033[36m'
else
  C_RESET=''
  C_RED=''
  C_GREEN=''
  C_YELLOW=''
  C_BLUE=''
  C_MAGENTA=''
  C_CYAN=''
fi

log_section() {
  printf '%b\n' "${C_MAGENTA}============================================================${C_RESET}"
  printf '%b\n' "${C_MAGENTA}$1${C_RESET}"
  printf '%b\n' "${C_MAGENTA}============================================================${C_RESET}"
}

log_step() {
  printf '%b\n' "${C_CYAN}[$1]${C_RESET} $2"
}

log_success() {
  printf '%b\n' "${C_GREEN}[OK]${C_RESET} $1"
}

log_warn() {
  printf '%b\n' "${C_YELLOW}[WARN]${C_RESET} $1"
}

log_error() {
  printf '%b\n' "${C_RED}[ERROR]${C_RESET} $1" >&2
}

detect_launch_host() {
  if [ -n "${APT_FINDER_HOST:-}" ]; then
    printf '%s' "$APT_FINDER_HOST"
    return 0
  fi

  local host=""
  if command -v hostname >/dev/null 2>&1; then
    host="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | grep -v '^127\.' | grep -v '^169\.254\.' | head -n 1 || true)"
  fi
  if [ -z "$host" ] && command -v ip >/dev/null 2>&1; then
    host="$(ip route get 1.1.1.1 2>/dev/null | awk '/src / {for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}' || true)"
  fi

  if [ -z "$host" ]; then
    host="127.0.0.1"
  fi

  printf '%s' "$host"
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local pid="${3:-}"
  local timeout_seconds="${4:-60}"
  local elapsed=0

  while true; do
    if python -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)' "$url" >/dev/null 2>&1; then
      log_success "$label is ready at $url"
      return 0
    fi

    if [ -n "$pid" ] && ! kill -0 "$pid" >/dev/null 2>&1; then
      log_error "$label exited before it became ready."
      return 1
    fi

    if [ "$elapsed" -ge "$timeout_seconds" ]; then
      log_error "Timed out waiting for $label at $url"
      return 1
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done
}

cleanup() {
  local exit_code=$?

  if [ -n "${WEB_PID:-}" ] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${OTP_PID:-}" ] && kill -0 "$OTP_PID" >/dev/null 2>&1; then
    kill "$OTP_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi

  if [ -n "${WEB_PID:-}" ]; then wait "$WEB_PID" >/dev/null 2>&1 || true; fi
  if [ -n "${OTP_PID:-}" ]; then wait "$OTP_PID" >/dev/null 2>&1 || true; fi
  if [ -n "${API_PID:-}" ]; then wait "$API_PID" >/dev/null 2>&1 || true; fi

  if [ "$exit_code" -eq 0 ]; then
    log_success "Launcher finished cleanly."
  else
    log_warn "Launcher stopped (exit code $exit_code). Background services were asked to shut down."
  fi
}

trap cleanup EXIT INT TERM

APP_HOST="$(detect_launch_host)"
API_BASE_URL="${VITE_API_BASE_URL:-http://${APP_HOST}:${API_PORT}/api}"
WEB_ORIGIN="http://${APP_HOST}:${WEB_PORT}"

if [ -z "${CORS_ORIGINS:-}" ]; then
  CORS_ORIGINS="http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT},${WEB_ORIGIN}"
fi

export API_HOST="$API_BIND_HOST"
export API_PORT="$API_PORT"
export API_RELOAD="false"
export CORS_ORIGINS
export npm_config_legacy_peer_deps=true
export VITE_API_BASE_URL="$API_BASE_URL"

frontend_dependencies_ready() {
  [ -x "$WEB_DIR/node_modules/.bin/vite" ]
}

log_section "APT-Finder all-in-one launcher"
log_step "INFO" "Project root: $PROJECT_ROOT"
log_step "INFO" "Selected host: $APP_HOST"
log_step "INFO" "API URL: $API_BASE_URL"
log_step "INFO" "Web origin: $WEB_ORIGIN"
log_step "INFO" "Backend port: $API_PORT"
log_step "INFO" "Web port: $WEB_PORT"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  log_step "SETUP" "Creating virtual environment at $VENV_DIR"
  "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
  log_success "Virtual environment created"
else
  log_success "Virtual environment already exists"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
log_success "Virtual environment activated"

log_step "CHECK" "Verifying backend Python dependencies"
if ! python -c 'import importlib.util, sys; modules = ["fastapi", "uvicorn", "requests", "bs4", "yaml", "googlemaps", "dotenv", "tenacity", "pydantic"]; missing = [name for name in modules if importlib.util.find_spec(name) is None]; sys.exit(1 if missing else 0)' >/dev/null 2>&1; then
  log_warn "Backend dependencies are missing; installing them now"
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
  log_success "Backend dependencies installed"
else
  log_success "Backend dependencies are already installed"
fi

if ! frontend_dependencies_ready; then
  if ! command -v npm >/dev/null 2>&1; then
    log_error "npm was not found in PATH. Install Node.js before starting the web app."
    exit 1
  fi
  log_step "SETUP" "Installing frontend dependencies with legacy peer resolution"
  (cd "$WEB_DIR" && npm ci)
  log_success "Frontend dependencies installed"
else
  log_success "Frontend dependencies are already installed"
fi

log_step "START" "Launching API server"
python "$PROJECT_ROOT/run_api.py" &
API_PID=$!
log_success "API server process started (PID $API_PID)"

wait_for_http "http://127.0.0.1:${API_PORT}/health" "API server" "$API_PID" 60

if [ ! -f "$OTP_SCRIPT" ]; then
  log_error "OTP launcher not found: $OTP_SCRIPT"
  exit 1
fi

log_step "START" "Launching OpenTripPlanner routing"
bash "$OTP_SCRIPT" &
OTP_PID=$!
log_success "OTP process started (PID $OTP_PID)"

sleep 5
if ! kill -0 "$OTP_PID" >/dev/null 2>&1; then
  set +e
  wait "$OTP_PID"
  OTP_EXIT_CODE=$?
  set -e
  log_error "OTP launcher exited during startup with exit code $OTP_EXIT_CODE. Check Java 21 installation and OTP logs."
  exit "$OTP_EXIT_CODE"
fi

log_step "BUILD" "Creating the production frontend bundle"
(cd "$WEB_DIR" && npm run build)
log_success "Frontend bundle built"

log_step "START" "Serving the production web build"
log_success "Open the dashboard at $WEB_ORIGIN"
log_warn "Press Ctrl+C to stop the web server, OTP, and API launcher together."
(cd "$WEB_DIR" && npm run preview -- --host 0.0.0.0 --port "$WEB_PORT" --strictPort)
