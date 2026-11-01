# ─────────────────────────────────────────────────────────────────────
#  Sourced by api-gate.sh and generate-clients.sh (not run on its own).
#  Call it from the toy root, after `cd`.
#
#  Resolves SPEC_FORMAT, the contract format the gate and Kiota read:
#    1. environment variable   SPEC_FORMAT=yaml ./scripts/api-gate.sh
#    2. contracts/spec.env     the committed default
#    3. json
#  Exits with status 2 on any value except "json" or "yaml".
# ─────────────────────────────────────────────────────────────────────
if [ -z "${SPEC_FORMAT:-}" ] && [ -f contracts/spec.env ]; then
  SPEC_FORMAT=$(. contracts/spec.env && echo "${SPEC_FORMAT:-}")
fi
SPEC_FORMAT="${SPEC_FORMAT:-json}"

case "$SPEC_FORMAT" in
  json|yaml) export SPEC_FORMAT ;;
  *) echo "SPEC_FORMAT must be 'json' or 'yaml' (got '$SPEC_FORMAT')." >&2
     echo "Set it in contracts/spec.env or in the environment." >&2
     exit 2 ;;
esac
