#!/usr/bin/env bash
# Serve the iOS companion PWA so iPhone/iPad Safari can open it on the LAN.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8765}"
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
HOST_IP="${HOST_IP:-127.0.0.1}"

cd "$ROOT/ios"

echo "Drone Maintenance Assistant — iOS companion"
echo "Serving: $ROOT/ios"
echo
echo "On your iPhone or iPad (same Wi‑Fi), open Safari to:"
echo "  http://${HOST_IP}:${PORT}/"
echo
echo "Then: Share → Add to Home Screen"
echo "Press Ctrl+C to stop."
echo

exec python3 -m http.server "$PORT" --bind 0.0.0.0
