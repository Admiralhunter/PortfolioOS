#!/usr/bin/env bash
# create-pr.sh — Create a GitHub PR via the REST API.
#
# Usage:
#   scripts/create-pr.sh \
#     --title "feat: add rebalancing calculator" \
#     --body-file /tmp/pr-body.md \
#     --head my-branch \
#     --base main
#
# Or with inline body:
#   scripts/create-pr.sh \
#     --title "fix: correct CAGR formula" \
#     --body "Short description here" \
#     --head my-branch
#
# Requires: GITHUB_TOKEN environment variable
# Repo: auto-detected from git remote, or override with --repo owner/name

set -euo pipefail

REPO=""
TITLE=""
BODY=""
BODY_FILE=""
HEAD=""
BASE="main"

usage() {
  cat <<'USAGE'
Usage: scripts/create-pr.sh [OPTIONS]

Required:
  --title TEXT       PR title
  --head BRANCH      Source branch name

Body (one of):
  --body TEXT        Inline PR body
  --body-file PATH   Read PR body from file

Optional:
  --base BRANCH      Target branch (default: main)
  --repo OWNER/NAME  Repository (default: auto-detect from git remote)
  -h, --help         Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)   TITLE="$2";     shift 2 ;;
    --body)    BODY="$2";      shift 2 ;;
    --body-file) BODY_FILE="$2"; shift 2 ;;
    --head)    HEAD="$2";      shift 2 ;;
    --base)    BASE="$2";      shift 2 ;;
    --repo)    REPO="$2";      shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# Validate required args
if [[ -z "$TITLE" ]]; then echo "Error: --title is required" >&2; exit 1; fi
if [[ -z "$HEAD" ]];  then echo "Error: --head is required" >&2;  exit 1; fi

# Resolve body
if [[ -n "$BODY_FILE" ]]; then
  if [[ ! -f "$BODY_FILE" ]]; then
    echo "Error: body file not found: $BODY_FILE" >&2; exit 1
  fi
  BODY="$(cat "$BODY_FILE")"
elif [[ -z "$BODY" ]]; then
  BODY="$TITLE"
fi

# Resolve repo from git remote
if [[ -z "$REPO" ]]; then
  REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$REMOTE_URL" ]]; then
    echo "Error: cannot detect repo — set --repo or add a git remote" >&2; exit 1
  fi
  # Handle both HTTPS and SSH remote URLs
  REPO="$(echo "$REMOTE_URL" | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')"
fi

# Check token
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN environment variable is not set" >&2; exit 1
fi

# Build JSON payload using python to handle escaping correctly
JSON_PAYLOAD="$(python3 -c "
import json, sys
print(json.dumps({
    'title': sys.argv[1],
    'body': sys.argv[2],
    'head': sys.argv[3],
    'base': sys.argv[4],
}))
" "$TITLE" "$BODY" "$HEAD" "$BASE")"

# Create the PR
RESPONSE="$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/pulls" \
  -d "$JSON_PAYLOAD")"

HTTP_CODE="$(echo "$RESPONSE" | tail -1)"
BODY_RESPONSE="$(echo "$RESPONSE" | sed '$d')"

if [[ "$HTTP_CODE" == "201" ]]; then
  PR_URL="$(echo "$BODY_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['html_url'])")"
  echo "PR created: $PR_URL"
else
  echo "Error: API returned HTTP $HTTP_CODE" >&2
  echo "$BODY_RESPONSE" >&2
  exit 1
fi
