# BUILD_TODO.md — Build & Development Process Issues

Audit date: 2026-02-14
Audited from: commit `d818f61` (main)

---

## Oversights

### 1. No Root `.gitignore`

- **Severity:** High
- **Fix effort:** Trivial
- **Status:** Open

Only `python/.gitignore` exists. The repo root has no `.gitignore`. Once the Electron/React frontend is scaffolded, `node_modules/`, `dist/`, `.vite/`, `.env`, and OS artifacts will get committed on the first careless `git add .`.

**Action:** Create a root `.gitignore` covering Node, Electron, Vite, OS artifacts, IDE files, and environment secrets.

---

### 2. `pnpm` Commands Referenced Everywhere but Don't Exist

- **Severity:** High
- **Fix effort:** Medium (blocked on Phase 0 frontend scaffolding)
- **Status:** Open

`CLAUDE.md`, `pull_request_template.md` (lines 154-156), and `AGENT_PR_GUIDE.md` all list `pnpm lint`, `pnpm test`, `pnpm build` as **mandatory** pre-PR verification steps. No `package.json` exists. These commands will fail.

The PR template checkboxes are unconditional — there's no "N/A if no JS changes" escape hatch. An agent doing Python-only work cannot honestly check those boxes.

**Action:**
- [ ] Scaffold `package.json` with at minimum stub scripts (Phase 0)
- [ ] Or: make PR template checkboxes conditional — "if applicable" language

---

### 3. No CI/CD Workflows

- **Severity:** High
- **Fix effort:** Medium
- **Status:** Open

`docs/ARCHITECTURE.md` and `AGENT_PR_GUIDE.md` reference `.github/workflows/ci.yml` and `.github/workflows/release.yml`. Neither file exists. There is **zero automated enforcement** of any quality gate — the entire PR quality system is honor-based.

**Action:**
- [ ] Create `.github/workflows/ci.yml` — run Python lint/typecheck/test on push and PR
- [ ] Create `.github/workflows/release.yml` — build and package on tag (later phase)
- [ ] Add branch protection rules requiring CI to pass before merge

---

### 4. `master` vs `main` Branch Name Inconsistency

- **Severity:** Medium
- **Fix effort:** Trivial
- **Status:** Open

The local default branch may be `master`, but `AGENT_PR_GUIDE.md` tells agents to target `main`. Agents that diff or rebase against `main` locally without fetching will get unexpected errors.

**Action:**
- [ ] Ensure the repo's default branch is `main` on GitHub
- [ ] Run `git branch -m master main` if needed locally
- [ ] Add `init.defaultBranch=main` to repo-level `.gitconfig` or document in CLAUDE.md

---

### 5. Coverage Threshold Permanently Set to 0

- **Severity:** Medium
- **Fix effort:** Trivial
- **Status:** Open

`python/pyproject.toml` line 118: `fail_under = 0` with comment "Raise to 80 once implementations land." There's no mechanism (CI check, script, reminder) to trigger that raise. This will silently stay at 0 as real code accumulates, and the CI scripts will report `PASS` with 0% coverage indefinitely.

**Action:**
- [ ] Add a CI step or script that warns if `fail_under` is 0 and source line count exceeds a threshold (e.g., 500 lines of non-test Python)
- [ ] Or: raise to 80 as soon as the first real module has tests

---

### 6. No Root-Level Unified Build/Check Script

- **Severity:** Medium
- **Fix effort:** Low
- **Status:** Open

The Python sidecar has `scripts/ci.py` for orchestration. There's nothing equivalent at the project root. An agent must remember to run two separate toolchains in two different directories:

```bash
cd python && uv run python -m scripts.ci   # Python checks
cd .. && pnpm lint && pnpm test && pnpm build  # JS checks (once they exist)
```

Agents frequently lose track of their working directory.

**Action:**
- [ ] Create a root-level `Makefile` or `scripts/check-all.sh` with targets: `check-python`, `check-js`, `check-all`
- [ ] Or: add a root `package.json` script that orchestrates both

---

### 7. Python Sidecar Has Zero Actual Tests

- **Severity:** Medium
- **Fix effort:** Medium
- **Status:** Open

`tests/conftest.py` defines fixtures (`reproducible_rng`, `sample_returns`, `sample_portfolio_value`) but no test files exist. The CI pipeline reports `PASS: 0 passed, 0 failed`, which provides zero safety. Combined with `fail_under = 0`, the Python CI is a no-op.

**Action:**
- [ ] Add tests for `portfolioos/main.py` (dispatch, message loop, error handling)
- [ ] Add tests for `scripts/_report.py` (report generation, summary aggregation)

---

### 8. `run_command()` Has No Timeout

- **Severity:** Medium
- **Fix effort:** Trivial
- **Status:** Open

`python/scripts/_report.py` line 59: `subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)` — no `timeout` parameter. If `mypy`, `pytest`, or `ruff` hangs (infinite import loop, network stall on a `yfinance` import), the entire CI run blocks forever with no feedback.

**Action:**
- [ ] Add a `timeout` parameter to `run_command()`, default 120 seconds
- [ ] Handle `subprocess.TimeoutExpired` and report it as a failure

---

### 9. Sphinx Docs Build in Critical CI Path Without `conf.py`

- **Severity:** Low
- **Fix effort:** Trivial
- **Status:** Open

`scripts/ci.py` runs: `lint -> typecheck -> test -> docs -> build`. The Sphinx docs step sits between tests and package build. But there's no `docs/conf.py` checked in — the `docs.py` script will fail immediately, blocking the package build.

For a pre-alpha project with no published docs, this adds friction for no benefit.

**Action:**
- [ ] Either add a minimal `docs/conf.py` so Sphinx doesn't error
- [ ] Or: move docs out of the critical CI path (make it optional / non-blocking)

---

### 10. No Pre-Commit Hooks or Commit-Time Validation

- **Severity:** Medium
- **Fix effort:** Low
- **Status:** Open

No `.pre-commit-config.yaml`, no `.husky/`, no `.git/hooks/`. An agent can commit malformatted code and push without any guardrail. Given that CI workflows also don't exist, there is **zero automated quality enforcement** at any point in the pipeline.

**Action:**
- [ ] Add `.pre-commit-config.yaml` with ruff, mypy, and (later) eslint hooks
- [ ] Or: add a `Makefile` target / npm script that agents run before committing

---

## Agent/LLM-Unfriendly Patterns

### 11. PR Template Requires Manual Tag Deletion

- **Severity:** Medium
- **Fix effort:** Low
- **Status:** Open

`pull_request_template.md` lines 20-45 ask agents to "Delete the tags that do NOT apply." LLMs are much better at **selecting/filling** than **deleting lines** from a template. Most LLM-generated PRs will either leave all tags in place or mangle the markdown formatting.

**Action:**
- [ ] Change to a fill-in-the-blank format: `**Change type:** ___` (agent writes one value)
- [ ] Or: use structured YAML frontmatter that agents can populate

---

### 12. Agent Attestation Section Is Unverifiable

- **Severity:** Medium
- **Fix effort:** Medium
- **Status:** Open

`pull_request_template.md` lines 193-206 ask agents to self-certify claims like "I have **run the test suite** and confirmed it passes." With no CI enforcement, this is purely performative. Every LLM will check the box regardless.

**Action:**
- [ ] Replace with CI-verified status checks (once CI exists)
- [ ] Or: require agents to paste actual command output (stdout) as evidence
- [ ] Or: have CI comment on the PR with verified results

---

### 13. `curl`-Only GitHub API Is Error-Prone for Agents

- **Severity:** Medium
- **Fix effort:** Medium
- **Status:** Open

The project forbids `gh` CLI and requires raw `curl` with heredocs and JSON escaping. Constructing multi-line JSON bodies with proper escaping inside `curl -d` is one of the most fragile operations for an LLM. Nested quotes, newlines, and special characters in PR descriptions cause silent failures.

**Action:**
- [ ] Create a helper script (`scripts/create-pr.py` or `scripts/create-pr.sh`) that takes structured arguments (title, body-file, base, head) and handles JSON construction internally
- [ ] Or: install `gh` CLI in the development environment

---

### 14. Verbose Output Is Opt-In — Failures Require Two Runs

- **Severity:** Low
- **Fix effort:** Trivial
- **Status:** Open

Python CI scripts default to one-line summaries: `[lint] FAIL: 3 errors`. To see details, agents must re-run with `--verbose`. Every failure requires two command invocations to diagnose.

**Action:**
- [ ] Auto-escalate to verbose on failure: if exit code != 0, print full output
- [ ] Keep quiet mode for passes — only show details when something goes wrong

---

### 15. `.reports/` Is Gitignored — No Cross-Session State

- **Severity:** Low
- **Fix effort:** Low
- **Status:** Open

`.reports/` is in `python/.gitignore`. Each agent session starts cold with no build history. If an agent runs CI, the session ends, and a new session picks up the work, the new session has zero visibility into what previously passed or failed.

**Action:**
- [ ] Consider committing `summary.json` (but not full reports) to a known location
- [ ] Or: document that agents should re-run full CI at the start of every session

---

### 16. No `.env.example` or Bootstrap Documentation

- **Severity:** Low
- **Fix effort:** Trivial
- **Status:** Open

No inventory of required environment variables, tool versions, or system prerequisites. An agent must read `CLAUDE.md`, `ARCHITECTURE.md`, and `pyproject.toml` to piece together what's needed.

**Action:**
- [ ] Create `.env.example` with placeholders for `GITHUB_TOKEN`, LM Studio endpoint, optional API keys
- [ ] Or: add a "Prerequisites" section to the root README with exact version requirements

---

### 17. 206-Line PR Template via JSON Escaping

- **Severity:** High
- **Fix effort:** Medium
- **Status:** Open

When an agent creates a PR via `curl`, it must construct a JSON body string containing most of the 206-line template, filled in. That's ~150 lines of markdown being passed through JSON escaping inside a heredoc inside a shell command. The probability of a correctly formatted PR body approaches zero as template length increases.

**Action:**
- [ ] Shorten the template significantly — move the checklists into CI or a bot comment
- [ ] Or: create a script that generates the PR body from simple key-value arguments
- [ ] Or: split the template into required (short) and extended (CI-generated) sections

---

### 18. Test File Naming Convention Mismatch Risk

- **Severity:** Low
- **Fix effort:** Trivial
- **Status:** Open

`pyproject.toml` specifies `python_files = ["*_test.py"]` (suffix pattern). An agent coming from the TypeScript world (where `*.test.ts` is the norm) might create `test_something.py` (prefix pattern — the pytest default). The strict `python_files` setting would **silently ignore** those test files.

**Action:**
- [ ] Add `"test_*.py"` to `python_files` to accept both patterns
- [ ] Or: add a comment in `pyproject.toml` explicitly warning about this
- [ ] Or: add a CI check that detects test-like files not matching the naming pattern

---

## Priority Matrix

| # | Issue | Severity | Effort | Priority |
|---|-------|----------|--------|----------|
| 1 | No root `.gitignore` | High | Trivial | **P0** |
| 2 | `pnpm` commands don't exist | High | Medium | **P0** |
| 3 | No CI/CD workflows | High | Medium | **P0** |
| 17 | PR template too long for JSON | High | Medium | **P0** |
| 4 | `master`/`main` mismatch | Medium | Trivial | **P1** |
| 5 | Coverage threshold at 0 | Medium | Trivial | **P1** |
| 6 | No unified build command | Medium | Low | **P1** |
| 7 | Zero actual Python tests | Medium | Medium | **P1** |
| 8 | `run_command()` no timeout | Medium | Trivial | **P1** |
| 10 | No pre-commit hooks | Medium | Low | **P1** |
| 11 | PR template tag deletion | Medium | Low | **P1** |
| 12 | Unverifiable attestation | Medium | Medium | **P1** |
| 13 | `curl`-only PR creation | Medium | Medium | **P1** |
| 9 | Sphinx in critical CI path | Low | Trivial | **P2** |
| 14 | Verbose output opt-in | Low | Trivial | **P2** |
| 15 | `.reports/` gitignored | Low | Low | **P2** |
| 16 | No `.env.example` | Low | Trivial | **P2** |
| 18 | Test naming mismatch risk | Low | Trivial | **P2** |
