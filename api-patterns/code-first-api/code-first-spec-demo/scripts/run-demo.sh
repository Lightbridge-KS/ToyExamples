#!/usr/bin/env bash
# Build both, start the gateway, run the client, stop the gateway.
set -euo pipefail
cd "$(dirname "$0")/.."

URL="http://localhost:5080"
dotnet build gateway --nologo -v q -clp:ErrorsOnly
dotnet build client  --nologo -v q -clp:ErrorsOnly

dotnet gateway/bin/Debug/net10.0/Gateway.dll > gateway.log 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do curl -fs "$URL/" > /dev/null && break; sleep 0.25; done
curl -fs "$URL/" > /dev/null || { echo "✘ Gateway did not start — see gateway.log"; exit 1; }

GATEWAY_URL="$URL" dotnet client/bin/Debug/net10.0/ClientApp.dll
