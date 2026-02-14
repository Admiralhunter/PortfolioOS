#!/usr/bin/env python3
"""Pre-commit hook: enforce maximum function length (effective lines).

Parses source files and checks that no function exceeds the line limit.
For Python files, uses the ast module. For JS/TS files, uses brace-depth
tracking with regex-based function detection.

Thresholds:
    Functions/methods: 100 effective lines (excluding comments, blank lines)

Usage:
    python scripts/check-function-length.py [FILES...]
    python scripts/check-function-length.py --threshold 80 [FILES...]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 100
PYTHON_EXTENSIONS = {".py"}
JS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}
SUPPORTED_EXTENSIONS = PYTHON_EXTENSIONS | JS_EXTENSIONS

# Patterns for JS/TS function detection
_JS_FUNC_PATTERNS = [
    # function declarations: function name(
    re.compile(r"^.*\bfunction\s+(\w+)\s*\("),
    # arrow functions assigned to const/let/var: const name = (...) =>
    re.compile(r"^.*\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(.*\)\s*=>"),
    # method definitions in classes/objects: name( or async name(
    re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{"),
]

# JS block comment state tracking
_JS_BLOCK_OPEN = re.compile(r"/\*")
_JS_BLOCK_CLOSE = re.compile(r"\*/")


def _is_python_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _is_js_comment_or_blank(line: str, in_block_comment: bool) -> tuple[bool, bool]:
    """Return (is_ignorable, still_in_block_comment)."""
    stripped = line.strip()

    if in_block_comment:
        if "*/" in stripped:
            return True, False
        return True, True

    if not stripped:
        return True, False
    if stripped.startswith("//"):
        return True, False
    if stripped.startswith("/*"):
        if "*/" in stripped[2:]:
            return True, False
        return True, True

    return False, False


def check_python_functions(
    filepath: Path,
    threshold: int,
) -> list[tuple[str, str, int, int]]:
    """Check Python function lengths using AST.

    Returns list of (filepath, func_name, line_number, effective_lines).
    """
    source = filepath.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    lines = source.splitlines()
    violations: list[tuple[str, str, int, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_name = node.name
        start_line = node.lineno
        end_line = node.end_lineno or node.lineno

        # Count effective lines within the function body
        effective = 0
        for line in lines[start_line - 1 : end_line]:
            if not _is_python_comment_or_blank(line):
                effective += 1

        if effective > threshold:
            violations.append((str(filepath), func_name, start_line, effective))

    return violations


def check_js_functions(
    filepath: Path,
    threshold: int,
) -> list[tuple[str, str, int, int]]:
    """Check JS/TS function lengths using brace-depth tracking.

    Returns list of (filepath, func_name, line_number, effective_lines).
    """
    source = filepath.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    violations: list[tuple[str, str, int, int]] = []

    # Track functions by finding declarations and matching braces
    i = 0
    while i < len(lines):
        line = lines[i]
        func_name = None

        for pattern in _JS_FUNC_PATTERNS:
            match = pattern.match(line)
            if match:
                func_name = match.group(1)
                break

        if func_name and "{" in line:
            # Track brace depth to find function end
            start_line = i
            depth = 0
            in_block_comment = False
            effective = 0

            for j in range(i, len(lines)):
                current_line = lines[j]
                stripped = current_line.strip()

                # Track block comments for brace counting
                if in_block_comment:
                    if "*/" in stripped:
                        in_block_comment = False
                    i = j + 1
                    continue
                if "/*" in stripped and "*/" not in stripped:
                    in_block_comment = True

                # Count effective lines
                is_ignorable, in_block_comment = _is_js_comment_or_blank(
                    current_line, False
                )
                if not is_ignorable:
                    effective += 1

                # Track brace depth (simplified — doesn't handle braces in strings)
                for char in stripped:
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1

                if depth == 0 and j > start_line:
                    if effective > threshold:
                        violations.append(
                            (str(filepath), func_name, start_line + 1, effective)
                        )
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1

    return violations


def main() -> int:
    """Check function lengths and return non-zero if any exceed the threshold."""
    parser = argparse.ArgumentParser(description="Check function length limits")
    parser.add_argument("files", nargs="*", help="Files to check")
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Max effective lines per function (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    all_violations: list[tuple[str, str, int, int]] = []

    for filepath_str in args.files:
        filepath = Path(filepath_str)
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if not filepath.is_file():
            continue

        if filepath.suffix in PYTHON_EXTENSIONS:
            all_violations.extend(check_python_functions(filepath, args.threshold))
        else:
            all_violations.extend(check_js_functions(filepath, args.threshold))

    if all_violations:
        print(f"Function length violations (>{args.threshold} effective lines):")
        for fpath, fname, lineno, count in sorted(all_violations):
            print(f"  {fpath}:{lineno} — {fname}(): {count} lines (limit: {args.threshold})")
        print(
            "\nEffective lines = total lines minus blank lines and comment-only lines."
        )
        print("Extract logical blocks into helper functions and use early returns.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
