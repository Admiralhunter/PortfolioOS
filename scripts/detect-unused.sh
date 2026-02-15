#!/usr/bin/env bash
# detect-unused.sh — Find unused code, exports, files, and dependencies
#
# Runs vulture (Python) and knip (TypeScript/Node) to surface dead code
# that accumulates as agents make changes over time.
#
# Usage:
#   scripts/detect-unused.sh          # run all checks
#   scripts/detect-unused.sh python   # Python only (vulture)
#   scripts/detect-unused.sh node     # Node/TS only (knip)
#   scripts/detect-unused.sh agents   # agents/ only (vulture)
#
# Exit codes:
#   0  — no unused code found
#   1  — unused code detected (review output above)
#   2  — tool not installed or misconfigured

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCOPE="${1:-all}"
EXIT_CODE=0

# ── Colors (disabled if not a terminal) ──
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

header() { printf "\n${BLUE}══ %s ══${NC}\n\n" "$1"; }
pass()   { printf "${GREEN}✓ %s${NC}\n" "$1"; }
warn()   { printf "${YELLOW}⚠ %s${NC}\n" "$1"; }
fail()   { printf "${RED}✗ %s${NC}\n" "$1"; }

# ── Python sidecar (vulture) ──
run_python() {
    header "Python sidecar — vulture (unused functions, classes, variables)"

    if ! (cd "$REPO_ROOT/python" && uv run vulture --version) >/dev/null 2>&1; then
        warn "vulture not installed.  Run:  cd python && uv sync --group dev"
        return 2
    fi

    if (cd "$REPO_ROOT/python" && uv run vulture portfolioos tests vulture_whitelist.py --min-confidence 80); then
        pass "No unused Python code found in python/"
    else
        fail "Unused Python code detected in python/ (see above)"
        EXIT_CODE=1
    fi
}

# ── Agent system (vulture) ──
run_agents() {
    header "Agent system — vulture (unused functions, classes, variables)"

    if ! (cd "$REPO_ROOT/agents" && uv run vulture --version) >/dev/null 2>&1; then
        warn "vulture not installed.  Run:  cd agents && uv sync --group dev"
        return 2
    fi

    if (cd "$REPO_ROOT/agents" && uv run vulture agents tests vulture_whitelist.py --min-confidence 80); then
        pass "No unused Python code found in agents/"
    else
        fail "Unused Python code detected in agents/ (see above)"
        EXIT_CODE=1
    fi
}

# ── Node / TypeScript (knip) ──
run_node() {
    header "TypeScript / Node — knip (unused exports, files, dependencies)"

    if ! (cd "$REPO_ROOT" && pnpm knip --version) >/dev/null 2>&1; then
        warn "knip not installed.  Run:  pnpm install"
        return 2
    fi

    if (cd "$REPO_ROOT" && pnpm knip); then
        pass "No unused TypeScript/Node code found"
    else
        fail "Unused TypeScript/Node code detected (see above)"
        EXIT_CODE=1
    fi
}

# ── Dispatch ──
case "$SCOPE" in
    python)  run_python ;;
    agents)  run_agents ;;
    node|js|ts)  run_node ;;
    all)
        run_python  || true
        run_agents  || true
        run_node    || true
        ;;
    *)
        echo "Usage: $0 [all|python|agents|node]"
        exit 2
        ;;
esac

if [ "$EXIT_CODE" -eq 0 ]; then
    printf "\n${GREEN}All dead-code checks passed.${NC}\n"
else
    printf "\n${YELLOW}Dead code detected — review the output above and remove what is no longer needed.${NC}\n"
fi

exit "$EXIT_CODE"
