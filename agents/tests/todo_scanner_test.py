"""Tests for the TODO Scanner agent."""

import textwrap
from pathlib import Path

from agents.agents.todo_scanner import (
    _collect_source_files,
    _extract_todos,
    _should_scan,
    run,
)
from agents.blackboard.db import Blackboard


class TestShouldScan:
    def test_python_file(self) -> None:
        assert _should_scan(Path("src/foo.py"))

    def test_typescript_file(self) -> None:
        assert _should_scan(Path("src/App.tsx"))

    def test_binary_file(self) -> None:
        assert not _should_scan(Path("image.png"))

    def test_node_modules(self) -> None:
        assert not _should_scan(Path("node_modules/pkg/index.js"))

    def test_git_directory(self) -> None:
        assert not _should_scan(Path(".git/objects/pack/data.py"))

    def test_pycache(self) -> None:
        assert not _should_scan(Path("src/__pycache__/mod.py"))


class TestExtractTodos:
    def test_python_todo(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# TODO: implement this\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "TODO"
        assert result[0]["description"] == "implement this"
        assert result[0]["line_number"] == 1

    def test_python_fixme(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("x = 1\n# FIXME: broken logic\ny = 2\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "FIXME"
        assert result[0]["line_number"] == 2

    def test_typescript_todo(self, tmp_path: Path) -> None:
        f = tmp_path / "test.ts"
        f.write_text("// TODO: add validation\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "TODO"

    def test_hack_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# HACK: workaround for upstream bug\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "HACK"

    def test_xxx_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# XXX: needs review\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "XXX"

    def test_note_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# NOTE: this is intentional\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "NOTE"

    def test_case_insensitive(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# todo: lowercase works too\n")
        result = _extract_todos(f)
        assert len(result) == 1
        assert result[0]["marker"] == "TODO"

    def test_multiple_markers(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text(textwrap.dedent("""\
            # TODO: first item
            x = 1
            # FIXME: second item
            y = 2
            # NOTE: just a note
        """))
        result = _extract_todos(f)
        assert len(result) == 3
        markers = [r["marker"] for r in result]
        assert markers == ["TODO", "FIXME", "NOTE"]

    def test_empty_description_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("# TODO:\n")
        result = _extract_todos(f)
        assert len(result) == 0

    def test_no_markers(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("x = 1\ny = 2\n# Regular comment\n")
        result = _extract_todos(f)
        assert len(result) == 0


class TestCollectSourceFiles:
    def test_finds_python_files(self, tmp_path: Path) -> None:
        (tmp_path / "foo.py").write_text("")
        (tmp_path / "bar.ts").write_text("")
        (tmp_path / "baz.png").write_text("")
        files = _collect_source_files(tmp_path)
        names = {f.name for f in files}
        assert "foo.py" in names
        assert "bar.ts" in names
        assert "baz.png" not in names

    def test_skips_git_dir(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("")
        (tmp_path / "real.py").write_text("")
        files = _collect_source_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "real.py"


class TestRun:
    def test_scans_and_populates_blackboard(self, tmp_path: Path) -> None:
        # Create a mini project
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text(
            "# TODO: implement feature\n"
            "# FIXME: critical bug\n"
        )
        (src / "utils.py").write_text("# NOTE: informational\n")

        db_path = tmp_path / "test.db"
        counts = run(tmp_path, db_path)

        assert counts["TODO"] == 1
        assert counts["FIXME"] == 1
        assert counts["NOTE"] == 1

        # Verify blackboard state
        bb = Blackboard(db_path)
        findings = bb.get_findings(agent_name="todo_scanner")
        # NOTE markers create findings but not tasks
        assert len(findings) == 2  # TODO + FIXME (not NOTE)

        tasks = bb.get_tasks(status="pending")
        assert len(tasks) == 2

        # FIXME should be higher priority
        fixme_tasks = [t for t in tasks if "FIXME" in t["title"]]
        assert fixme_tasks[0]["priority"] == 2

    def test_idempotent_rerun(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("# TODO: do something\n")

        db_path = tmp_path / "test.db"
        run(tmp_path, db_path)
        run(tmp_path, db_path)  # second run

        bb = Blackboard(db_path)
        findings = bb.get_findings(agent_name="todo_scanner")
        assert len(findings) == 1  # no duplicates
        tasks = bb.get_tasks()
        assert len(tasks) == 1  # no duplicate tasks

    def test_deterministic_ids_across_fresh_databases(
        self, tmp_path: Path
    ) -> None:
        """Same TODO produces same finding/task IDs in independent DBs."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("# TODO: do something\n")

        db1 = tmp_path / "db1.db"
        db2 = tmp_path / "db2.db"
        run(tmp_path, db1)
        run(tmp_path, db2)

        bb1 = Blackboard(db1)
        bb2 = Blackboard(db2)

        findings1 = bb1.get_findings(agent_name="todo_scanner")
        findings2 = bb2.get_findings(agent_name="todo_scanner")
        assert findings1[0]["id"] == findings2[0]["id"]

        tasks1 = bb1.get_tasks()
        tasks2 = bb2.get_tasks()
        assert tasks1[0]["id"] == tasks2[0]["id"]
