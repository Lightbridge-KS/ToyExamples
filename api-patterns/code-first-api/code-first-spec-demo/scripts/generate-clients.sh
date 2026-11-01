#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  Generate the typed C# clients from the COMMITTED spec snapshot.
#  The client repo never needs the gateway source, only contracts/.
#
#  Usage:   dotnet tool restore && ./scripts/generate-clients.sh
#  Override the Kiota binary with:  KIOTA=/path/to/kiota ./scripts/generate-clients.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

KIOTA="${KIOTA:-dotnet kiota}"

for doc in v1 v2; do
  ns="StudiesV${doc#v}"
  echo "▶ contracts/studies-$doc.json  →  client/Generated/$ns"
  $KIOTA generate \
    --language CSharp \
    --openapi "contracts/studies-$doc.json" \
    --class-name "${ns}Client" \
    --namespace-name "ClientApp.Generated.$ns" \
    --output "client/Generated/$ns" \
    --exclude-backward-compatible \
    --clean-output \
    --log-level Warning
done
rm -f client/Generated/*/.kiota.log
