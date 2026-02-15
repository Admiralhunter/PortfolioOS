# Agent PR Guide — PortfolioOS

This document defines the pull request process for AI coding agents working on PortfolioOS. It is the authoritative reference for tag definitions, quality gates, and enforcement rules.

Human reviewers: use this guide to evaluate whether an agent has done its due diligence.

---

## Tag System

Every PR must include tags from three categories. Tags serve as structured metadata so reviewers (human or automated) can quickly assess what a PR does, where it touches, and how risky it is.

### Change Type (exactly 1 required)

| Tag | When to use |
|-----|-------------|
| `type:feat` | Adding a new user-facing feature or capability that did not exist before. |
| `type:fix` | Correcting a bug — something that was working incorrectly. Must reference the issue or describe the broken behavior. |
| `type:refactor` | Restructuring existing code without changing its external behavior. No new features, no bug fixes. Tests should remain unchanged. |
| `type:docs` | Changes limited to documentation files (`.md`, JSDoc, docstrings, comments). No functional code changes. |
| `type:test` | Adding, updating, or fixing tests. No production code changes beyond what's needed to make tests possible (e.g., exporting a function). |
| `type:chore` | Build config, CI/CD, dependency updates, tooling, formatting. No production logic changes. |
| `type:perf` | Performance optimization. Must describe the bottleneck and the improvement (ideally with measurements). |
| `type:security` | Security fix or hardening. Must describe the vulnerability or attack vector addressed. |

**Rule:** If a PR spans multiple types (e.g., a feature that also fixes a bug), pick the *primary* intent. If genuinely split, break it into separate PRs.

### Scope (1 or more required)

| Tag | What it covers |
|-----|----------------|
| `scope:frontend` | React components, hooks, stores, styles, renderer-process code under `src/`. |
| `scope:backend` | Electron main process code under `electron/`, IPC handlers, Node.js services. |
| `scope:database` | DuckDB or SQLite schemas, queries, migrations, database access layer under `electron/db/`. |
| `scope:python` | Python sidecar code under `python/`, including simulation, market data, and analysis modules. |
| `scope:llm` | LLM provider integration, prompt engineering, model configuration under `electron/llm/`. |
| `scope:config` | Project configuration: `package.json`, `tsconfig.json`, `pyproject.toml`, Vite config, Tailwind config, environment files. |
| `scope:ci` | GitHub Actions workflows, CI/CD pipelines, release automation under `.github/workflows/`. |

**Rule:** Pick all scopes that apply. A PR touching React components and Electron IPC handlers should have both `scope:frontend` and `scope:backend`.

### Risk (exactly 1 required)

| Tag | Criteria |
|-----|----------|
| `risk:low` | Change is isolated to a single module. No shared interfaces modified. No data schema changes. Easily reversible. |
| `risk:medium` | Touches shared utilities, modifies interfaces used by multiple modules, or changes behavior that other code depends on. |
| `risk:high` | Breaking API changes, database schema migrations, security-sensitive changes, changes to financial calculation logic, or modifications to the IPC contract between renderer and main process. |

**Rule:** When in doubt, round up. A `risk:medium` wrongly tagged as `risk:low` is worse than the reverse.

---

## Quality Gates

These are hard limits. A PR that violates them should not be merged without explicit justification.

### 1. File Size: 700 Lines Maximum

Every source file (`.ts`, `.tsx`, `.py`, `.js`, `.jsx`) must be under 700 effective lines (excluding blank lines and comments).

**Enforcement:** Pre-commit hooks (`file-size-check`) and CI quality gates both enforce this automatically. Commits that violate this limit will be rejected.

**If a file approaches 700 lines:** Split it into focused modules with single responsibilities before it hits the limit.

### 2. Function Length: 100 Lines Maximum

Every function, method, or arrow function must be under 100 effective lines.

**Enforcement:** Pre-commit hooks (`function-length-check`) and CI quality gates both enforce this automatically. Commits that violate this limit will be rejected.

**If a function approaches 100 lines:**
1. Extract logical blocks into named helper functions.
2. Use early returns to reduce nesting.

### 3. DRY Compliance

Before writing new utility functions, helpers, or abstractions:

1. **Search the codebase** for existing implementations.
2. **Check `src/lib/`** for shared utilities.
3. **Check `src/hooks/`** for shared React hooks.
4. **Check `electron/services/`** for shared backend logic.

If similar logic exists in 3+ places, extract it. If you're writing something that feels generic (date formatting, validation, error handling), it probably already exists or should be shared.

### 4. Documentation Standards

| What | Requirement |
|------|-------------|
| Public functions | JSDoc (TS/JS) or docstring (Python) with description, params, and return type |
| Interfaces/types | JSDoc describing purpose and when to use |
| Complex algorithms | Inline comments explaining the *why* behind non-obvious logic |
| Financial calculations | Citation to methodology (e.g., "Bengen 1994", "Trinity Study 1998") |
| Configuration options | Document in relevant config section or README |
| IPC channels | Document message format and expected response |

**Do not over-document.** Self-explanatory code (`getUserById(id)`) does not need a comment. Reserve comments for non-obvious decisions, trade-offs, and domain-specific logic.

### 5. Security Checklist

Every PR must verify:

| Check | Details |
|-------|---------|
| No hardcoded secrets | No API keys, passwords, tokens, or credentials anywhere in code, comments, or test fixtures |
| Input validation | All user input and external data is validated at system boundaries |
| No unsafe patterns | No `eval()`, `new Function()`, `innerHTML`, `dangerouslySetInnerHTML`, or `shell: true` without sanitization |
| IPC least-privilege | New IPC channels expose minimal necessary functionality |
| Type safety | No `any` types introduced without documented justification |
| Dependency audit | New dependencies checked for known CVEs and license compatibility (PolyForm NC 1.0.0) |
| Privacy compliance | No telemetry, tracking, analytics, or data exfiltration. Cloud LLM calls require explicit consent flow. |
| SQL injection | All database queries use parameterized statements, never string concatenation |

### 6. Maintainability Standards

| Standard | Enforcement |
|----------|-------------|
| Consistent naming | camelCase (JS/TS vars/functions), PascalCase (components/types), snake_case (Python) |
| No dead code | Remove commented-out code, unused imports, unreachable branches |
| Explicit errors | No empty `catch {}` blocks, no swallowed promises, no silent failures |
| Single responsibility | Each module, class, and function has one clear purpose |
| Follow existing patterns | Match the codebase's existing approach before introducing new patterns |
| Conventional commits | Commit messages follow `type: description` format |

---

## GitHub Operations — `curl` Only (No `gh` CLI)

> **The `gh` CLI is NOT available in this project's development environment.** This project is developed using Claude Code on the web, which does not have `gh` installed. **Do not attempt to use `gh` commands.** All GitHub API interactions must use `curl` against the [GitHub REST API](https://docs.github.com/en/rest).

Authenticate with the `GITHUB_TOKEN` environment variable, which is automatically available in Claude Code web sessions and CI.

> **Tip:** A helper script `scripts/create-pr.sh` is available to simplify PR creation. See `scripts/create-pr.sh --help` for usage.

### Creating a Pull Request via `curl`

After pushing your branch, create the PR using the GitHub REST API:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -d "$(cat <<'EOF'
{
  "title": "feat: your PR title here",
  "body": "## Tags\n\n- type:feat\n- scope:frontend\n- risk:low\n\n## Summary\n\nDescription of changes.\n\n## Changes\n\n- `path/to/file.ts` — Description\n",
  "head": "your-branch-name",
  "base": "main"
}
EOF
)"
```

**Important notes:**
- Replace `OWNER/REPO` with the actual repository path (e.g., `Admiralhunter/PortfolioOS`)
- The PR body should follow the [PR template](pull_request_template.md) format
- Use `$GITHUB_TOKEN` for authentication — never hardcode tokens
- Use a heredoc for the JSON body to handle multi-line content and special characters

### Other Common GitHub API Operations

```bash
# Get PR details
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER

# Add a comment to a PR or issue
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/issues/PR_NUMBER/comments \
  -d '{"body": "Comment text here"}'

# List PR review comments
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/comments

# Check CI status for a commit
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/commits/COMMIT_SHA/check-runs

# Merge a pull request
curl -s -X PUT \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/merge \
  -d '{"merge_method": "squash"}'
```

---

## Agent Workflow

When an AI agent opens a PR on PortfolioOS, it must follow this process:

### Step 1: Read Before Writing

Before modifying any file, **read the entire file** (or at minimum the surrounding context) to understand:
- What the file does
- What patterns it uses
- What other code depends on it

### Step 2: Search Before Creating

Before creating any new function, utility, hook, or module:
- Search the codebase for existing implementations
- Check if the functionality already exists under a different name
- Verify the new code doesn't duplicate logic elsewhere

### Step 3: Write the Code

Follow all conventions in [CLAUDE.md](../CLAUDE.md) and the quality gates above.

### Step 4: Self-Review the Diff

Before opening the PR, review your own changes:

```bash
git diff --stat        # Check which files changed and by how much
git diff               # Read every line of the diff
```

Look for:
- Unintended changes (whitespace, formatting, unrelated modifications)
- Debug code (`console.log`, `print()`, `debugger`)
- Leftover artifacts (TODO comments without issue refs, placeholder text)
- Files that grew too large
- Functions that grew too long

### Step 5: Run Verification

Run the full test and lint suite:

```bash
# Unified check (runs all available checks):
make check-all

# Or run individually:
# Python checks:
cd python && uv run pytest
cd python && uv run ruff check .

# Frontend checks (once package.json exists):
# pnpm lint
# pnpm test
# pnpm build
```

**Do not check the "tests pass" box unless you actually ran the commands and they passed.** Claiming tests pass without running them is a serious trust violation.

### Step 6: Fill Out the PR Template

Complete every section of the [PR template](pull_request_template.md):
1. Select exactly the right tags — do not leave all options listed
2. Write a genuine summary, not a restated diff
3. Check only the boxes you actually verified

### Step 7: Commit Message

Use conventional commit format matching the `type` tag:

```
feat: add portfolio rebalancing calculator

Implements automatic rebalancing suggestions based on target allocation
percentages. Uses threshold-based triggers (5% drift) to minimize
unnecessary trading.

Closes #42
```

### Step 8: Open the PR via `curl`

**Do NOT use `gh` CLI** — it is not available. Use `curl` with the GitHub REST API:

```bash
# Push your branch first
git push -u origin your-branch-name

# Create the PR
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -d "$(cat <<'EOF'
{
  "title": "feat: your PR title",
  "body": "Paste your filled-out PR template here",
  "head": "your-branch-name",
  "base": "main"
}
EOF
)"
```

See the [GitHub Operations](#github-operations--curl-only-no-gh-cli) section above for the full API reference.

---

## Tag Selection Examples

### Example 1: Adding a new chart component

```
type:feat
scope:frontend
risk:low
```

### Example 2: Fixing a Monte Carlo calculation error

```
type:fix
scope:python
risk:high  (financial calculation correctness)
```

### Example 3: Splitting a large service file into modules

```
type:refactor
scope:backend
risk:medium  (touches shared imports)
```

### Example 4: Adding CI pipeline

```
type:chore
scope:ci
risk:low
```

### Example 5: Fixing XSS vulnerability in user input handling

```
type:security
scope:frontend, scope:backend
risk:high
```

### Example 6: Optimizing DuckDB query performance

```
type:perf
scope:database
risk:medium
```

---

## Enforcement

Quality is enforced at two levels:

1. **Pre-commit hooks** (`.pre-commit-config.yaml`): Run locally on every commit. Enforce file size limits (≤700 effective lines), function length limits (≤100 effective lines), test coverage thresholds, Python linting/formatting (ruff), and basic hygiene (trailing whitespace, YAML/JSON validity, no commits to `main`).

2. **CI** (`.github/workflows/ci.yml`): Runs on every push and PR to `main`. Runs Python lint, type check, tests, and quality gates as a backstop for environments where pre-commit hooks aren't installed.

These rules exist because AI agents can generate plausible-looking PRs that pass superficial review but contain subtle issues: duplicated logic, untested edge cases, or security gaps.

The tag system and checklists force agents to slow down, categorize their work, and verify quality before requesting review. Reviewers should:

1. **Check tags match the actual changes** — a `type:refactor` that changes behavior is mislabeled.
2. **Verify checked boxes** — spot-check that the agent actually did what it claims.
3. **Validate test output** — if the agent claims it ran tests, verify the output is consistent with the changes.

PRs that skip required sections, leave all tag options listed (instead of selecting), or have unchecked boxes in critical sections should be sent back for revision.
