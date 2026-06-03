"""CLI tests for curated pytest suite aliases."""

from __future__ import annotations

import pytest

from core import cli


def test_core_test_lists_curated_suites(capsys) -> None:
    rc = cli.main(["test", "--list-suites"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "fast" in captured.out.splitlines()
    assert "smoke" in captured.out.splitlines()
    assert "cognition" in captured.out.splitlines()
    assert "teaching" in captured.out.splitlines()
    assert "packs" in captured.out.splitlines()
    assert "full" in captured.out.splitlines()


def test_core_test_suite_expands_to_expected_pytest_paths(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, check: bool = False, cwd=None) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main(["test", "--suite", "cognition", "-q"])

    assert rc == 0
    assert calls
    command = calls[0]
    assert command[:3] == (cli.sys.executable, "-m", "pytest")
    assert "tests/test_intent_proposition_graph.py" in command
    assert "tests/test_cognitive_turn_pipeline.py" in command
    assert "tests/test_articulation_realizer_v2.py" in command
    assert "-q" in command


def test_core_test_fast_suite_expands_to_iteration_lane(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, check: bool = False, cwd=None) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main(["test", "--suite", "fast", "-q"])

    assert rc == 0
    command = calls[0]
    assert "tests/test_cli_test_suites.py" in command
    assert "tests/test_runtime_config.py" in command
    assert "tests/test_core_semantic_seed_pack.py" in command
    assert "tests/test_cognitive_eval_harness.py" in command
    assert "tests/" not in command


def test_core_test_suite_accepts_pytest_flags_without_separator(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, check: bool = False, cwd=None) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main(["test", "--suite", "packs", "-q"])

    assert rc == 0
    # Assert against the live suite definition rather than re-hardcoding the
    # (growing) packs file list: the contract under test is that a curated
    # suite expands to its files followed by the forwarded "-q", with no "--"
    # separator needed.
    assert calls[0] == (
        cli.sys.executable,
        "-m",
        "pytest",
        *cli._TEST_SUITES["packs"],
        "-q",
    )


def test_core_test_passthrough_still_accepts_arbitrary_pytest_args(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, check: bool = False, cwd=None) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main(["test", "--", "tests/test_core_semantic_seed_pack.py", "-q"])

    assert rc == 0
    assert calls[0] == (
        cli.sys.executable,
        "-m",
        "pytest",
        "tests/test_core_semantic_seed_pack.py",
        "-q",
    )


def test_non_test_commands_still_reject_unknown_args() -> None:
    with pytest.raises(SystemExit):
        cli.main(["pack", "list", "-q"])
