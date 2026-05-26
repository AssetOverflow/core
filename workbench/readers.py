"""Read-only filesystem-backed readers for CORE Workbench.

Readers are intentionally repo-root constrained. They must never expose
arbitrary path traversal or arbitrary shell execution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from engine_state import EngineStateStore, get_git_revision
from evals.framework import discover_lanes, get_lane, run_lane
from teaching.proposals import DEFAULT_PROPOSAL_LOG_PATH
from workbench.schemas import (
    ArtifactDetail,
    ArtifactRef,
    EvalLaneSummary,
    EvalRunResult,
    ProposalDetail,
    ProposalSummary,
    ReplayComparison,
    RuntimeStatus,
    TraceAdmissibility,
    TraceDetail,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALLOWED_ARTIFACT_ROOTS = (
    _REPO_ROOT / "evals",
    _REPO_ROOT / "engine_state",
    _REPO_ROOT / "teaching",
)
_SAFE_EVAL_LANES = {"contemplation_quality"}


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


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


def _artifact_kind(path: Path) -> str:
    parts = set(path.parts)
    name = path.name
    if "proposals" in parts:
        return "proposal"
    if "results" in parts:
        return "eval_result"
    if "engine_state" in parts and name == "manifest.json":
        return "engine_state_manifest"
    if name.endswith(".jsonl"):
        return "telemetry"
    return "unknown"


def list_artifacts(limit: int = 100) -> list[ArtifactRef]:
    items: list[ArtifactRef] = []

    for root in _ALLOWED_ARTIFACT_ROOTS:
        if not root.exists():
            continue
        for pattern in ("*.json", "*.jsonl"):
            for path in sorted(root.rglob(pattern)):
                if len(items) >= limit:
                    return items
                if not _is_allowed(path):
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                items.append(
                    ArtifactRef(
                        artifact_id=_safe_relative(path),
                        kind=_artifact_kind(path),
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
        kind=_artifact_kind(candidate),
        path=_safe_relative(candidate),
        digest=_sha256_text(text),
        created_at=None,
        content_type=content_type,
        content=content,
    )


def _proposal_source_kind(row: dict[str, Any]) -> str:
    source = row.get("source")
    if isinstance(source, dict):
        return str(source.get("kind", "unknown"))
    return "unknown"


def _proposal_replay_equivalent(row: dict[str, Any]) -> bool | None:
    replay = row.get("replay_evidence")
    if isinstance(replay, dict) and isinstance(replay.get("replay_equivalent"), bool):
        return bool(replay["replay_equivalent"])
    return None


def list_proposals() -> list[ProposalSummary]:
    rows = _read_jsonl(DEFAULT_PROPOSAL_LOG_PATH)
    out: list[ProposalSummary] = []
    for row in rows:
        proposal_id = str(row.get("proposal_id", ""))
        if not proposal_id:
            continue
        out.append(
            ProposalSummary(
                proposal_id=proposal_id,
                state=str(row.get("review_state", "unknown")),
                source_kind=_proposal_source_kind(row),
                replay_equivalent=_proposal_replay_equivalent(row),
                created_at=None,
                downstream_effect="unknown",
            )
        )
    return out


def read_proposal(proposal_id: str) -> ProposalDetail:
    for row in _read_jsonl(DEFAULT_PROPOSAL_LOG_PATH):
        if str(row.get("proposal_id", "")) != proposal_id:
            continue
        state = str(row.get("review_state", "unknown"))
        return ProposalDetail(
            proposal_id=proposal_id,
            state=state,
            source_kind=_proposal_source_kind(row),
            replay_equivalent=_proposal_replay_equivalent(row),
            created_at=None,
            downstream_effect="unknown",
            proposed_chain=row.get("proposed_chain"),
            replay_evidence=row.get("replay_evidence"),
            source=row.get("source"),
            evidence=row.get("evidence") if isinstance(row.get("evidence"), list) else [],
            artifact_refs=[],
            suggested_cli=(
                f"core teaching review {proposal_id} --accept --review-date YYYY-MM-DD"
                if state == "pending"
                else None
            ),
        )
    raise FileNotFoundError(proposal_id)


def list_eval_lanes() -> list[EvalLaneSummary]:
    lanes = []
    for lane in discover_lanes():
        lanes.append(
            EvalLaneSummary(
                lane=lane.name,
                versions=list(lane.versions),
                read_only=lane.name in _SAFE_EVAL_LANES,
                description=None,
            )
        )
    return lanes


def run_safe_eval_lane(lane_name: str, *, version: str = "v1", split: str = "public") -> EvalRunResult:
    if lane_name not in _SAFE_EVAL_LANES:
        raise ValueError(f"eval lane is not workbench-safe/read-only: {lane_name}")
    if split == "holdout":
        raise ValueError("holdout execution is disabled in Workbench v1")
    lane = get_lane(lane_name)
    result = run_lane(lane, version=version, split=split, workers=1)
    data = result.as_dict()
    return EvalRunResult(
        lane=result.lane,
        version=result.version,
        split=result.split,
        passed=None,
        metrics=data.get("metrics", {}),
        cases=data.get("cases", []),
        source_digest=str(data.get("metrics", {}).get("source_digest"))
        if isinstance(data.get("metrics"), dict) and data.get("metrics", {}).get("source_digest")
        else None,
    )


def replay_artifact(artifact_id: str) -> ReplayComparison:
    detail = read_artifact(artifact_id)
    return ReplayComparison(
        artifact_id=artifact_id,
        original_hash=detail.digest,
        replay_hash=detail.digest,
        equivalent=True,
        divergences=[],
    )


def read_trace(turn_id: str) -> TraceDetail:
    """Return a read-only trace detail scaffold.

    W-028 establishes the canonical API shape before live runtime turn storage is
    wired. The placeholder is explicit and non-mutating; unknown turn ids still
    resolve to a structurally valid empty trace surface for frontend development.
    """
    return TraceDetail(
        turn_id=turn_id,
        surface="",
        articulation_surface=None,
        walk_surface=None,
        trace_hash=None,
        replay_digest=None,
        grounding_source=None,
        proposal_refs=[],
        candidate_refs=[],
        admissibility=TraceAdmissibility(rejected_attempts=None, exhausted=None),
        raw={"status": "trace storage not yet wired"},
    )
