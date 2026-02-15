"""TODO Scanner agent — extracts TODO/FIXME/HACK/XXX comments from the codebase.

Reads all source files, extracts marked comments, deduplicates against
existing findings in the blackboard, and queues new items.

Usage:
    python -m agents.agents.todo_scanner [--repo-root /path/to/repo]
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import time
from pathlib import Path
from typing import Any

# Allow running as a module from the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.blackboard.db import Blackboard  # noqa: E402

AGENT_NAME = "todo_scanner"

# File extensions to scan
SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".sql", ".yaml", ".yml", ".toml", ".md",
    ".sh", ".bash",
}

# Directories to skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "dist", "out", "release", ".vite", ".reports",
}

# Regex for TODO-style markers in comments
# Matches: # TODO: text, // FIXME: text, /* HACK: text */, <!-- XXX: text -->
_MARKER_PATTERN = re.compile(
    r"(?:#|//|/\*|<!--|--|%)\s*"      # comment prefix
    r"(TODO|FIXME|HACK|XXX|NOTE)"     # marker
    r"\s*[:(\s]\s*"                   # separator (colon, paren, or space)
    r"(.+?)$",                        # description (rest of line)
    re.IGNORECASE | re.MULTILINE,
)

# Priority mapping per the design spec
PRIORITY_MAP: dict[str, int] = {
    "FIXME": 2,
    "HACK": 2,
    "XXX": 3,
    "TODO": 3,
    "NOTE": 5,
}

SEVERITY_MAP: dict[str, str] = {
    "FIXME": "high",
    "HACK": "high",
    "XXX": "medium",
    "TODO": "medium",
    "NOTE": "info",
}


def _load_ignore_patterns(repo_root: Path) -> list[str]:
    """Load glob patterns from .todoscanignore if it exists."""
    ignore_file = repo_root / ".todoscanignore"
    if not ignore_file.is_file():
        return []
    patterns: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def _should_scan(path: Path, ignore_patterns: list[str] | None = None) -> bool:
    """Check if a file should be scanned."""
    if path.suffix not in SOURCE_EXTENSIONS:
        return False
    if not all(part not in SKIP_DIRS for part in path.parts):
        return False
    if ignore_patterns:
        path_str = str(path)
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return False
    return True


def _collect_source_files(repo_root: Path) -> list[Path]:
    """Walk the repo and collect scannable source files."""
    ignore_patterns = _load_ignore_patterns(repo_root)
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if path.is_file() and _should_scan(
            path.relative_to(repo_root), ignore_patterns
        ):
            files.append(path)
    return sorted(files)


def _extract_todos(file_path: Path) -> list[dict[str, Any]]:
    """Extract TODO-style markers from a single file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    results: list[dict[str, Any]] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        match = _MARKER_PATTERN.search(line)
        if match:
            marker = match.group(1).upper()
            raw = match.group(2).strip()
            for suffix in ("-->", "*/"):
                raw = raw.removesuffix(suffix)
            description = raw.strip()
            if not description:
                continue
            results.append({
                "marker": marker,
                "description": description,
                "line_number": line_num,
            })
    return results


def run(repo_root: Path, db_path: Path | None = None) -> dict[str, int]:
    """Run the TODO scanner and write findings to the blackboard.

    Returns a summary dict with counts per marker type.
    """
    bb = Blackboard(db_path) if db_path else Blackboard()
    start_ms = time.monotonic_ns() // 1_000_000

    bb.log_event(agent_name=AGENT_NAME, event_type="start")

    source_files = _collect_source_files(repo_root)
    counts: dict[str, int] = {}
    total_queued = 0

    for fpath in source_files:
        todos = _extract_todos(fpath)
        rel_path = str(fpath.relative_to(repo_root))

        for item in todos:
            marker = item["marker"]
            counts[marker] = counts.get(marker, 0) + 1

            # NOTE markers are informational — log but don't queue
            if marker == "NOTE":
                continue

            title = f"{marker}: {item['description'][:120]}"
            finding_id = bb.add_finding(
                agent_name=AGENT_NAME,
                severity=SEVERITY_MAP[marker],
                category="todo",
                title=title,
                description=item["description"],
                file_path=rel_path,
                line_number=item["line_number"],
                metadata={"marker": marker},
            )

            # add_task uses deterministic IDs and is idempotent,
            # so duplicates are handled automatically.
            bb.add_task(
                source_agent=AGENT_NAME,
                title=title,
                description=(
                    f"Address {marker} in {rel_path}:{item['line_number']}\n\n"
                    f"{item['description']}"
                ),
                priority=PRIORITY_MAP[marker],
                source_finding_id=finding_id,
            )
            total_queued += 1

    elapsed = (time.monotonic_ns() // 1_000_000) - start_ms
    summary_msg = (
        f"Scanned {len(source_files)} files. "
        f"Found {sum(counts.values())} markers "
        f"({', '.join(f'{k}:{v}' for k, v in sorted(counts.items()))}). "
        f"{total_queued} tasks queued."
    )
    bb.log_event(
        agent_name=AGENT_NAME,
        event_type="complete",
        message=summary_msg,
        duration_ms=elapsed,
    )
    bb.update_last_run(AGENT_NAME)

    print(summary_msg)
    return counts


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="PortfolioOS TODO Scanner Agent")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Root of the repository to scan",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to the blackboard database",
    )
    args = parser.parse_args()

    from agents.log_config import setup as setup_logging

    setup_logging()
    run(args.repo_root, args.db_path)


if __name__ == "__main__":
    main()
