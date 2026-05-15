"""CLI tests for curated pytest suite aliases."""

from __future__ import annotations

from core import cli


def test_core_test_lists_curated_suites(capsys) -> None:
    rc = cli.main(["test", "--list-suites"])

    captured = capsys.readouterr()
    assert rc == 0
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
