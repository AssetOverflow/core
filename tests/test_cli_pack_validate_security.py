"""Security tests for the ``core pack validate`` CLI subcommand."""
from __future__ import annotations

import importlib.util

import pytest

from core import cli


def test_pack_validate_requires_allow_arbitrary_code(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["pack", "validate", "en"])

    assert exc.value.code != 0
    captured = capsys.readouterr()
    assert "--allow-arbitrary-code" in captured.err


def test_pack_validate_dry_run_does_not_execute_validator(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_import(*args: object, **kwargs: object) -> None:
        raise AssertionError("validator should not execute during dry-run")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", fail_import)

    rc = cli.main(["pack", "validate", "en", "--dry-run"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "dry-run" in captured.out.lower()


@pytest.mark.parametrize(
    "pack_id",
    ["../foo", "/tmp/foo", "foo/bar", r"foo\bar", ".", "..", ""],
)
def test_pack_validate_rejects_unsafe_pack_ids(pack_id: str) -> None:
    args = ["pack", "validate", pack_id, "--dry-run"] if pack_id else ["pack", "validate", "", "--dry-run"]
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2


def test_pack_validate_rejects_path_traversal(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["pack", "validate", "../foo", "--dry-run"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "path" in captured.err.lower() or "traversal" in captured.err.lower()


def test_pack_validate_rejects_absolute_paths(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["pack", "validate", "/tmp/foo", "--dry-run"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "absolute" in captured.err.lower()


def test_pack_validate_rejects_path_separators(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["pack", "validate", "foo/bar", "--dry-run"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "path" in captured.err.lower()


def test_pack_validate_allows_known_safe_pack_with_explicit_flag() -> None:
    rc = cli.main(["pack", "validate", "en", "--allow-arbitrary-code"])
    assert rc in {0, 1}


def test_pack_validate_dry_run_json(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    rc = cli.main(["pack", "validate", "en", "--dry-run", "--json"])

    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["pack_id"] == "en"
    assert data["would_execute"] is False
    assert data["exists"] is True
