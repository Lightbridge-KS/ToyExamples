#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  CI gate: is <revision> a backward-compatible evolution of <base>?
#
#  Run this in the CONTRACT's CI on every pull request. A breaking
#  change must either be reverted or shipped as a new MAJOR version
#  (a new file + a new /api/vN path), never as a minor.
#
#  Usage:
#    ./scripts/check-breaking.sh <base.yaml> <revision.yaml>
#    ./scripts/check-breaking.sh            # runs the two demo cases
#
#  Team policy — contracts/oasdiff-severity.txt:
#    oasdiff treats "new enum value in a response" as an ERROR by default,
#    because strict readers crash on it (see ACT 3 of the client). Our
#    contracts declare every enum as an OPEN set and our clients are
#    Kiota-generated tolerant readers, so we downgrade it to a WARNING.
#    A policy you write down beats a rule you silently ignore.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

OASDIFF="${OASDIFF:-oasdiff}"
command -v "$OASDIFF" >/dev/null || {
  echo "oasdiff not found. Install: https://github.com/oasdiff/oasdiff#installation"; exit 2; }

check() { # <base> <revision>
  echo "▶ $1  →  $2"
  if "$OASDIFF" breaking "$1" "$2" \
       --fail-on ERR \
       --severity-levels contracts/oasdiff-severity.txt; then
    echo "✔ Compatible: OK to release as a MINOR / PATCH."
  else
    echo "✘ BREAKING: revert, or ship it as a new MAJOR (new file, new /api/vN path)."
    return 1
  fi
}

if [[ $# -eq 2 ]]; then
  check "$1" "$2"
  exit
fi

echo "═══ Case 1: the real 1.1.0 release (additive) ═══"
check contracts/studies-api.v1.0.0.yaml contracts/studies-api.v1.1.0.yaml
echo
echo "═══ Case 2: a 'minor' that renames a field (expected to FAIL) ═══"
check contracts/studies-api.v1.1.0.yaml contracts/rejected/studies-api.v1.2.0.yaml \
  || echo "  (expected — this is what the gate is for)"
