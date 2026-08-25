#!/usr/bin/env bash
# Launch Drone Maintenance Assistant as a desktop app window.
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
PYTHON="$APP_ROOT/.venv/bin/python"
LOG_FILE="${XDG_RUNTIME_DIR:-/tmp}/drone-maintenance-assistant.log"

fail() {
  local msg="$1"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --width=420 --title="Drone Maintenance Assistant" --text="$msg" || true
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "Drone Maintenance Assistant" "$msg" || true
  fi
  echo "$msg" >&2
  exit 1
}

if [[ ! -x "$PYTHON" ]]; then
  fail "The app environment is missing.\n\nFrom the project folder, run:\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"
fi

cd "$APP_ROOT"
: >"$LOG_FILE"
if ! "$PYTHON" -c "import PySide6" >>"$LOG_FILE" 2>&1; then
  fail "PySide6 is not installed in the app environment.\n\nFrom the project folder, run:\nsource .venv/bin/activate\npip install -r requirements.txt"
fi

exec "$PYTHON" "$APP_ROOT/main.py" >>"$LOG_FILE" 2>&1
