#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  Regenerate the typed C# clients from PINNED contract versions.
#
#  Two things are pinned, so generation is reproducible:
#    1. the contract file   (which version of the API we build against)
#    2. the generator       (Kiota 1.36.1, in .config/dotnet-tools.json)
#
#  Usage:   dotnet tool restore && ./scripts/generate-clients.sh
#  Override the Kiota binary with:  KIOTA=/path/to/kiota ./scripts/generate-clients.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

KIOTA="${KIOTA:-dotnet kiota}"

generate() { # <contract> <client-class> <namespace> <output-dir>
  echo "▶ $1  →  $4"
  $KIOTA generate \
    --language CSharp \
    --openapi "$1" \
    --class-name "$2" \
    --namespace-name "$3" \
    --output "$4" \
    --exclude-backward-compatible \
    --clean-output \
    --log-level Warning
}

# Simulates client release 1.4.x — built against contract 1.0.0 and NEVER regenerated.
# It is the "old client still in the field" that must keep working.
generate contracts/studies-api.v1.0.0.yaml \
         StudiesV1Client ClientApp.Generated.StudiesV1 client/Generated/StudiesV1

# Client release 2.0.x — built against the new major contract.
generate contracts/studies-api.v2.0.0.yaml \
         StudiesV2Client ClientApp.Generated.StudiesV2 client/Generated/StudiesV2

echo "✔ Done. Lock files (contract hash + Kiota version) live next to the generated code:"
ls client/Generated/*/kiota-lock.json
