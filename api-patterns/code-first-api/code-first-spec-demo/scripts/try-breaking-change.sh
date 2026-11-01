#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  Replays "Experiment 2" from the first demo: rename a DTO property.
#  There it broke the old client SILENTLY. Here the gate catches it.
#  The source file is restored afterwards.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

FILE=gateway/Api/V1Endpoints.cs
cp "$FILE" "$FILE.bak"
restore() { cp "$FILE.bak" "$FILE" && rm -f "$FILE.bak"; echo "↺ Restored $FILE"; }
trap restore EXIT

echo "✎ \"Harmless refactor\": PatientName → FullName in the v1 DTO"
sed -i.tmp -e "s/string PatientName,/string FullName,/" \
           -e "s/PatientName: s.Patient.Name/FullName:    s.Patient.Name/" "$FILE"
rm -f "$FILE.tmp"
echo

if ./scripts/api-gate.sh; then
  echo "?! The gate did not catch it."
else
  echo
  echo "→ Caught before merge. In the first demo the same rename shipped and blanked out patient names."
fi
