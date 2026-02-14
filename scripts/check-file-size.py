#!/usr/bin/env python3
"""Pre-commit hook: enforce maximum file size (effective lines).

Counts lines excluding comments and blank lines. Exits non-zero if any
staged file exceeds the threshold.

Thresholds:
    Source files (.py, .ts, .tsx, .js, .jsx): 700 effective lines

Usage:
    python scripts/check-file-size.py [FILES...]
    python scripts/check-file-size.py --threshold 500 [FILES...]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 700
SUPPORTED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}

# Regex for JS/TS block comment regions
_JS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def count_effective_lines_python(source: str) -> int:
    """Count non-blank, non-comment lines in Python source."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def count_effective_lines_js(source: str) -> int:
    """Count non-blank, non-comment lines in JS/TS source."""
    # Remove block comments first
    cleaned = _JS_BLOCK_COMMENT_RE.sub("", source)
    count = 0
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        count += 1
    return count


def count_effective_lines(filepath: Path) -> int:
    """Count effective (non-blank, non-comment) lines in a source file."""
    source = filepath.read_text(encoding="utf-8", errors="replace")
    if filepath.suffix == ".py":
        return count_effective_lines_python(source)
    return count_effective_lines_js(source)


def main() -> int:
    """Check file sizes and return non-zero if any exceed the threshold."""
    parser = argparse.ArgumentParser(description="Check file size limits")
    parser.add_argument("files", nargs="*", help="Files to check")
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Max effective lines (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    violations: list[tuple[str, int]] = []

    for filepath_str in args.files:
        filepath = Path(filepath_str)
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if not filepath.is_file():
            continue

        effective = count_effective_lines(filepath)
        if effective > args.threshold:
            violations.append((filepath_str, effective))

    if violations:
        print(f"File size violations (>{args.threshold} effective lines):")
        for name, count in sorted(violations):
            print(f"  {name}: {count} lines (limit: {args.threshold})")
        print(
            "\nEffective lines = total lines minus blank lines and comment-only lines."
        )
        print("Split large files into focused modules with single responsibilities.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
