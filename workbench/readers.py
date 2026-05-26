"""Read-only filesystem-backed readers for CORE Workbench.

Readers are intentionally repo-root constrained.  They must never expose
arbitrary path traversal or arbitrary shell execution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from engine_state import EngineStateStore, get_git_revision
from workbench.schemas import ArtifactDetail, ArtifactRef, RuntimeStatus

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALLOWED_ARTIFACT_ROOTS = (
    _REPO_ROOT / "evals",
    _REPO_ROOT / "engine_state",
    _REPO_ROOT / "teaching",
)


def _safe_relative(path: Path) -> str:
    return str(path.resolve().relative_to(_REPO_ROOT.resolve()))


def _is_allowed(path: Path) -> bool:
    resolved = path.resolve()
    return any(
        root.resolve() in resolved.parents or resolved == root.resolve()
        for root in _ALLOWED_ARTIFACT_ROOTS
    )


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def runtime_status() -> RuntimeStatus:
    store = EngineStateStore()
    manifest = store.load_manifest() or {}
    backend = "unknown"

    try:
        import os

        backend = os.environ.get("CORE_BACKEND", "numpy")
    except Exception:
        backend = "unknown"

    checkpoint_revision = str(manifest.get("written_at_revision", "unknown"))
    current_revision = get_git_revision()

    return RuntimeStatus(
        backend=backend,
        git_revision=current_revision,
        engine_state_present=store.exists(),
        checkpoint_revision=checkpoint_revision,
        revision_warning=(
            checkpoint_revision not in ("", "unknown")
            and current_revision not in ("", "unknown")
            and checkpoint_revision != current_revision
        ),
        active_session_id=None,
    )


def list_artifacts(limit: int = 100) -> list[ArtifactRef]:
    items: list[ArtifactRef] = []

    for root in _ALLOWED_ARTIFACT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json"))[:limit]:
            if not _is_allowed(path):
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            items.append(
                ArtifactRef(
                    artifact_id=_safe_relative(path),
                    kind="unknown",
                    path=_safe_relative(path),
                    digest=_sha256_text(content),
                    created_at=None,
                )
            )

    return items


def read_artifact(artifact_id: str) -> ArtifactDetail:
    candidate = (_REPO_ROOT / artifact_id).resolve()

    if not _is_allowed(candidate):
        raise ValueError("artifact path is outside allowed roots")

    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(artifact_id)

    text = candidate.read_text(encoding="utf-8")

    content_type = "text"
    content: Any = text

    if candidate.suffix == ".json":
        content_type = "json"
        try:
            content = json.loads(text)
        except Exception:
            content = text
    elif candidate.suffix == ".jsonl":
        content_type = "jsonl"
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                rows.append(line)
        content = rows

    return ArtifactDetail(
        artifact_id=artifact_id,
        kind="unknown",
        path=_safe_relative(candidate),
        digest=_sha256_text(text),
        created_at=None,
        content_type=content_type,
        content=content,
    )
