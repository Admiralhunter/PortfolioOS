# BUILD_TODO.md — Build & Development Process Issues

Audit date: 2026-02-14
Audited from: commit `d818f61` (main)

**Status: All 18 items addressed.**

---

## Oversights

### 1. No Root `.gitignore`

- **Severity:** High | **Effort:** Trivial | **Status:** Resolved

Created root `.gitignore` covering Node, Electron, Vite, Python, OS artifacts, IDE files, and environment secrets.

---

### 2. `pnpm` Commands Referenced Everywhere but Don't Exist

- **Severity:** High | **Effort:** Medium | **Status:** Resolved (documentation)

Updated `CLAUDE.md`, `AGENT_PR_GUIDE.md`, and PR template to mark frontend commands as conditional. Added `make check-all` as the unified command. PR template uses "if applicable" language.

---

### 3. No CI/CD Workflows

- **Severity:** High | **Effort:** Medium | **Status:** Resolved

Created `.github/workflows/ci.yml` with Python lint, format check, type check, and tests. Frontend job scaffolded but commented out.

---

### 4. `master` vs `main` Branch Name Inconsistency

- **Severity:** Medium | **Effort:** Trivial | **Status:** Resolved (documented)

Added "Branch Naming" section to `CLAUDE.md`.

---

### 5. Coverage Threshold Permanently Set to 0

- **Severity:** Medium | **Effort:** Trivial | **Status:** Resolved

Raised `fail_under` from 0 to 50 in `pyproject.toml`.

---

### 6. No Root-Level Unified Build/Check Script

- **Severity:** Medium | **Effort:** Low | **Status:** Resolved

Created root `Makefile` with `check-all`, `check-python`, `lint`, `test` targets.

---

### 7. Python Sidecar Has Zero Actual Tests

- **Severity:** Medium | **Effort:** Medium | **Status:** Resolved

Added `tests/main_test.py` with tests for `dispatch()` and `main()` message loop. Existing test files (all skipped) were already in place.

---

### 8. `run_command()` Has No Timeout

- **Severity:** Medium | **Effort:** Trivial | **Status:** Resolved

Added `timeout` parameter (default 120s) to `run_command()`. Handles `subprocess.TimeoutExpired`.

---

### 9. Sphinx Docs Build in Critical CI Path Without `conf.py`

- **Severity:** Low | **Effort:** Trivial | **Status:** Resolved

`docs/conf.py` already existed. Removed docs from critical CI path — now opt-in via `--with-docs`.

---

### 10. No Pre-Commit Hooks or Commit-Time Validation

- **Severity:** Medium | **Effort:** Low | **Status:** Resolved

Created `.pre-commit-config.yaml` with ruff, trailing whitespace, YAML/JSON validation, large file check, and no-commit-to-main guard.

---

## Agent/LLM-Unfriendly Patterns

### 11. PR Template Requires Manual Tag Deletion

- **Severity:** Medium | **Effort:** Low | **Status:** Resolved

Rewrote PR template with fill-in-the-blank format instead of "delete what doesn't apply".

---

### 12. Agent Attestation Section Is Unverifiable

- **Severity:** Medium | **Effort:** Medium | **Status:** Resolved

Replaced attestation checkboxes with "Testing Done" section requiring pasted command output. CI provides automated verification.

---

### 13. `curl`-Only GitHub API Is Error-Prone for Agents

- **Severity:** Medium | **Effort:** Medium | **Status:** Resolved

Created `scripts/create-pr.sh` helper that takes structured arguments and handles JSON via Python's `json.dumps()`.

---

### 14. Verbose Output Is Opt-In — Failures Require Two Runs

- **Severity:** Low | **Effort:** Trivial | **Status:** Resolved

`scripts/ci.py` now auto-escalates to verbose on failure.

---

### 15. `.reports/` Is Gitignored — No Cross-Session State

- **Severity:** Low | **Effort:** Low | **Status:** Resolved (documented)

Added note in `CLAUDE.md`: run `make check-all` at session start.

---

### 16. No `.env.example` or Bootstrap Documentation

- **Severity:** Low | **Effort:** Trivial | **Status:** Resolved

Created `.env.example` with placeholders for all config variables.

---

### 17. 206-Line PR Template via JSON Escaping

- **Severity:** High | **Effort:** Medium | **Status:** Resolved

Shortened PR template from 218 to ~79 lines. Combined with `scripts/create-pr.sh` helper.

---

### 18. Test File Naming Convention Mismatch Risk

- **Severity:** Low | **Effort:** Trivial | **Status:** Resolved

Added `"test_*.py"` to `python_files` in `pyproject.toml` alongside `"*_test.py"`.

---

## Priority Matrix

| # | Issue | Severity | Effort | Status |
|---|-------|----------|--------|--------|
| 1 | No root `.gitignore` | High | Trivial | Resolved |
| 2 | `pnpm` commands don't exist | High | Medium | Resolved |
| 3 | No CI/CD workflows | High | Medium | Resolved |
| 17 | PR template too long for JSON | High | Medium | Resolved |
| 4 | `master`/`main` mismatch | Medium | Trivial | Resolved |
| 5 | Coverage threshold at 0 | Medium | Trivial | Resolved |
| 6 | No unified build command | Medium | Low | Resolved |
| 7 | Zero actual Python tests | Medium | Medium | Resolved |
| 8 | `run_command()` no timeout | Medium | Trivial | Resolved |
| 10 | No pre-commit hooks | Medium | Low | Resolved |
| 11 | PR template tag deletion | Medium | Low | Resolved |
| 12 | Unverifiable attestation | Medium | Medium | Resolved |
| 13 | `curl`-only PR creation | Medium | Medium | Resolved |
| 9 | Sphinx in critical CI path | Low | Trivial | Resolved |
| 14 | Verbose output opt-in | Low | Trivial | Resolved |
| 15 | `.reports/` gitignored | Low | Low | Resolved |
| 16 | No `.env.example` | Low | Trivial | Resolved |
| 18 | Test naming mismatch risk | Low | Trivial | Resolved |
