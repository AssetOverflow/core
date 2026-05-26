"""Reader-level tests for CORE Workbench artifact safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.readers import read_artifact


@pytest.mark.parametrize(
    "artifact_id",
    [
        "../../pyproject.toml",
        "../engine_state/manifest.json",
        "/etc/passwd",
    ],
)
def test_read_artifact_rejects_path_traversal(artifact_id: str) -> None:
    with pytest.raises(ValueError):
        read_artifact(artifact_id)


def test_read_artifact_missing_file_raises_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        read_artifact("evals/does-not-exist.json")


def test_read_known_allowed_artifact_when_present() -> None:
    path = Path("evals/contemplation_quality/contract.md")
    if not path.exists():
        return
    detail = read_artifact(path.as_posix())
    assert detail.path == path.as_posix()
    assert detail.digest
