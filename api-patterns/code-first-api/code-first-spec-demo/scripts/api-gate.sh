#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  CI gate for a CODE-FIRST API. Run on every pull request.
#
#    1. Export the spec from the code in this PR        → .spec-out/
#    2. BREAKING?  committed contracts/ → fresh export   (oasdiff)
#    3. DRIFT?     fresh export ≠ committed contracts/   (someone forgot
#                  to run export-spec.sh, so reviewers never saw it)
#
#  In real CI the baseline is contracts/ on the target branch (or the
#  last release tag). Here the committed contracts/ folder plays that role.
#
#  Team policy (contracts/oasdiff-severity.txt): enums are OPEN sets, so a
#  new response enum value is a warning, not an error (all clients are
#  Kiota-generated tolerant readers).
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

OASDIFF="${OASDIFF:-oasdiff}"
command -v "$OASDIFF" > /dev/null || {
  echo "oasdiff not found. Install: https://github.com/oasdiff/oasdiff#installation"; exit 2; }

FRESH=.spec-out
rm -rf "$FRESH"
./scripts/export-spec.sh "$FRESH" > /dev/null

status=0
for doc in v1 v2; do
  base="contracts/studies-$doc.json"
  fresh="$FRESH/studies-$doc.json"
  echo "▶ $doc: committed snapshot → spec exported from current code"

  if ! "$OASDIFF" breaking "$base" "$fresh" --fail-on ERR \
         --severity-levels contracts/oasdiff-severity.txt; then
    echo "  ✘ BREAKING change in $doc. Revert it, or ship it as a new major (/api/v3 + a new document)."
    status=1
  elif ! cmp -s "$base" "$fresh"; then
    echo "  ⚠ Compatible change in $doc, but contracts/ is stale."
    echo "    Bump the MINOR in gateway/Api/OpenApiSetup.cs, run ./scripts/export-spec.sh, commit contracts/."
    status=1
  else
    echo "  ✔ No API change."
  fi
done
exit $status
