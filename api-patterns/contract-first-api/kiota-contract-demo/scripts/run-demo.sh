#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  One command: build both repos, start the gateway, run the client,
#  stop the gateway.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

GATEWAY_URL="${GATEWAY_URL:-http://localhost:5080}"

echo "▶ Building gateway and client…"
dotnet build gateway --nologo -v q
dotnet build client  --nologo -v q

echo "▶ Starting Gateway 3.0.0 on $GATEWAY_URL (log: gateway.log)…"
dotnet gateway/bin/Debug/net10.0/Gateway.dll > gateway.log 2>&1 &
GATEWAY_PID=$!
trap 'kill "$GATEWAY_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  curl -fs "$GATEWAY_URL/" >/dev/null && break
  sleep 0.25
done
curl -fs "$GATEWAY_URL/" >/dev/null || { echo "✘ Gateway did not start — see gateway.log"; exit 1; }

echo "▶ Running client…"
GATEWAY_URL="$GATEWAY_URL" dotnet client/bin/Debug/net10.0/ClientApp.dll
