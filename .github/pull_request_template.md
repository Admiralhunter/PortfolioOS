<!--
  PortfolioOS — Pull Request Template
  Fill in each section. See .github/AGENT_PR_GUIDE.md for full tag definitions.

  NOTE: The `gh` CLI is NOT available. PRs must be created via `curl`.
  See AGENT_PR_GUIDE.md for curl examples.
-->

## Tags

**Change type:** <!-- Write one: feat / fix / refactor / docs / test / chore / perf / security -->

**Scope:** <!-- Write one or more, comma-separated: frontend / backend / database / python / llm / config / ci -->

**Risk:** <!-- Write one: low / medium / high -->

---

## Summary

<!-- 2-5 sentences: WHAT changed, WHY, approach taken, trade-offs. -->



---

## Changes

<!-- List every file touched:
  - `path/to/file.ts` — Description of change
-->



---

## Self-Review Checklist

- [ ] No duplicated logic — searched for existing utilities before writing new ones
- [ ] Every file under 700 lines, every function under 100 lines
- [ ] Public functions have JSDoc/docstrings; complex logic has "why" comments
- [ ] No secrets, `eval()`, `innerHTML`, `any` types, or telemetry added
- [ ] New code has tests; existing tests still pass
- [ ] Naming follows project conventions (camelCase JS, PascalCase components, snake_case Python)
- [ ] No dead code, commented-out blocks, or debug statements

---

## Testing Done

<!-- REQUIRED: Paste actual command output (abbreviated is fine). -->

**Python** (if applicable):
```
$ cd python && uv run pytest
<paste output here>
```

**Frontend** (if applicable):
```
$ pnpm test
<paste output here>
```

---

## Size Violations

<!-- If any file > 700 lines or function > 100 lines, list with justification. Otherwise "None". -->

None

---

## Related Issues

<!-- Closes #123, Relates to #456 — or leave blank. -->

