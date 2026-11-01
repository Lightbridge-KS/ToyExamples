#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  Export the OpenAPI documents FROM the gateway code.
#
#  Usage:  ./scripts/export-spec.sh [out-dir]      (default: contracts/)
#
#  Developer workflow: change C# → run this → commit code AND contracts/
#  together, so reviewers see the API change in the pull request diff.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-contracts}"
URL="http://localhost:5080"
mkdir -p "$OUT"

dotnet build gateway --nologo -v q -clp:ErrorsOnly
dotnet gateway/bin/Debug/net10.0/Gateway.dll > /dev/null 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do curl -fs "$URL/" > /dev/null && break; sleep 0.25; done

for doc in v1 v2; do
  curl -fsS "$URL/openapi/$doc.json" -o "$OUT/studies-$doc.json"
  echo "  exported $OUT/studies-$doc.json"
done
