<!--
  PortfolioOS — Pull Request Template for AI Agents
  ==================================================
  This template is designed for GenAI coding agents (Claude Code, Copilot, etc.).
  All sections are REQUIRED unless marked [optional].
  See .github/AGENT_PR_GUIDE.md for full tag definitions and enforcement rules.
-->

## Tags

<!--
  REQUIRED: Select ALL applicable tags. You MUST pick at least one from each category.
  Delete the tags that do NOT apply. Keep only the ones that describe this PR.
-->

### Change Type (pick exactly 1)

- `type:feat` — New feature or capability
- `type:fix` — Bug fix (include issue ref)
- `type:refactor` — Code restructuring, no behavior change
- `type:docs` — Documentation only
- `type:test` — Test additions or corrections
- `type:chore` — Build, CI, deps, tooling
- `type:perf` — Performance improvement
- `type:security` — Security fix or hardening

### Scope (pick 1 or more)

- `scope:frontend` — React renderer, UI components, styles
- `scope:backend` — Electron main process, IPC handlers
- `scope:database` — DuckDB or SQLite schema, queries, migrations
- `scope:python` — Python sidecar, analytics engine
- `scope:llm` — LLM provider integration
- `scope:config` — Configuration, build system, environment
- `scope:ci` — CI/CD pipelines, GitHub Actions

### Risk (pick exactly 1)

- `risk:low` — Isolated change, no shared-code side effects
- `risk:medium` — Touches shared modules or multiple features
- `risk:high` — Breaking change, data migration, or security-sensitive

---

## Summary

<!--
  Write 2-5 sentences explaining:
  1. WHAT changed and WHY
  2. The approach taken and any alternatives considered
  3. Any trade-offs made
-->



---

## Changes

<!--
  List every file touched with a one-line description of the change.
  Group by directory. Use the format:
    - `path/to/file.ts` — Description of change
-->



---

## Code Quality Self-Review

<!--
  REQUIRED: The agent MUST verify each item and check the box.
  Unchecked boxes indicate the agent did NOT complete due diligence.
  DO NOT check a box unless you have actually verified the claim.
-->

### DRY (Don't Repeat Yourself)

- [ ] No duplicated logic — searched for existing utilities/helpers before writing new ones
- [ ] Shared code is extracted into reusable functions or modules
- [ ] No copy-paste blocks across files (3+ similar lines should be abstracted)

### File Size

- [ ] **Every modified/created file is under 700 lines** (report any exceptions below)
- [ ] Large files were split into focused modules with single responsibilities

### Function Length

- [ ] **Every modified/created function is under 100 lines** (report any exceptions below)
- [ ] Long functions were decomposed into smaller, named helper functions
- [ ] Each function does one thing and does it well

### Documentation

- [ ] Public functions and interfaces have clear JSDoc/docstring comments
- [ ] Complex logic has inline comments explaining *why*, not *what*
- [ ] Any new configuration options are documented
- [ ] README or relevant docs updated if user-facing behavior changed

### Security

- [ ] No secrets, API keys, or credentials in code or comments
- [ ] User input is validated and sanitized at system boundaries
- [ ] No `eval()`, `innerHTML`, `dangerouslySetInnerHTML`, or equivalent unsafe patterns
- [ ] IPC channels follow least-privilege principle
- [ ] No new `any` types introduced in TypeScript
- [ ] Dependencies checked for known vulnerabilities (if new deps added)
- [ ] No telemetry, tracking, or data exfiltration (per project policy)

### Maintainability

- [ ] Naming is clear and consistent with project conventions (camelCase JS/TS, PascalCase components, snake_case Python)
- [ ] No dead code, commented-out blocks, or TODO-without-issue references left behind
- [ ] Error handling is explicit — no swallowed errors or empty catch blocks
- [ ] Types are specific — no `any`, `object`, or `unknown` without justification
- [ ] Code follows existing patterns in the codebase rather than introducing new ones

### Testing

- [ ] New code has corresponding tests
- [ ] Existing tests still pass after changes
- [ ] Edge cases are covered (null, empty, boundary values)
- [ ] Tests are colocated with source files per project convention (`*.test.ts`, `*_test.py`)

---

## Size Violations

<!--
  If ANY file exceeds 700 lines or ANY function exceeds 100 lines,
  you MUST list them here with justification for why they cannot be split.
  Leave "None" if all limits are met.
-->

**Files over 700 lines:** None

**Functions over 100 lines:** None

---

## Testing Done

<!--
  REQUIRED: Describe how you verified this PR works.
  Include commands run and their output summary.
-->

- [ ] `pnpm lint` — passes
- [ ] `pnpm test` — passes
- [ ] `pnpm build` — passes
- [ ] `cd python && uv run pytest` — passes (if Python changes)
- [ ] `cd python && uv run ruff check .` — passes (if Python changes)
- [ ] Manual verification: (describe what you tested manually)

---

## Dependency Changes

<!--
  [optional] If you added, removed, or updated dependencies, list them here.
  Include license compatibility check per project policy (PolyForm NC 1.0.0).
-->

- No dependency changes

---

## Screenshots / Recordings

<!--
  [optional] If this PR includes UI changes, attach before/after screenshots.
-->

N/A

---

## Related Issues

<!--
  [optional] Link related issues. Use closing keywords where appropriate.
  Format: Closes #123, Relates to #456
-->

---

## Agent Attestation

<!--
  REQUIRED for AI agents. This section confirms the agent performed
  genuine verification rather than rubber-stamping checkboxes.
-->

- [ ] I have **read every file** I modified before making changes
- [ ] I have **searched the codebase** for existing patterns before introducing new ones
- [ ] I have **run the test suite** and confirmed it passes (not just claimed it)
- [ ] I have **verified file sizes** and **function lengths** against the limits above
- [ ] I have **reviewed my own diff** for unintended changes, debug code, or leftover artifacts
- [ ] I confirm this PR follows the [PortfolioOS coding conventions](../CLAUDE.md)
