"""Read-only readers for the CORE Workbench W-026 API."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from engine_state import EngineStateStore, get_git_revision
from evals.framework import discover_lanes, get_lane, run_lane
from teaching.proposals import DEFAULT_PROPOSAL_LOG_PATH, ProposalLog
from workbench.schemas import (
    ArtifactDetail,
    ArtifactRef,
    EvalLaneSummary,
    EvalRunResult,
    ProposalDetail,
    ProposalSummary,
    RuntimeStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAFE_EVAL_LANES = frozenset({"contemplation_quality"})
ALLOWED_ARTIFACT_ROOTS = (
    REPO_ROOT / "engine_state",
    REPO_ROOT / "teaching" / "proposals",
    REPO_ROOT / "evals",
    REPO_ROOT / "contemplation" / "runs",
)


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _validate_artifact_id(artifact_id: str) -> PurePosixPath:
    if not artifact_id or artifact_id.startswith("/"):
        raise ValueError("artifact id must be a repo-relative path")
    rel = PurePosixPath(artifact_id)
    if any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError("artifact id must not contain path traversal")
    return rel


def _is_allowed(path: Path) -> bool:
    resolved = path.resolve()
    for root in ALLOWED_ARTIFACT_ROOTS:
        root_resolved = root.resolve()
        if resolved == root_resolved or root_resolved in resolved.parents:
            return True
    return False


def _resolve_artifact(artifact_id: str) -> Path:
    rel = _validate_artifact_id(artifact_id)
    candidate = (REPO_ROOT / rel.as_posix()).resolve()
    if not _is_allowed(candidate):
        raise ValueError("artifact path is outside allowed roots")
    return candidate


def _artifact_kind(path: Path) -> str:
    rel = _relative(path)
    if rel == "engine_state/manifest.json":
        return "engine_state_manifest"
    if rel.startswith("teaching/proposals/"):
        return "proposal"
    if rel.startswith("evals/") and "/results/" in rel:
        return "eval_result"
    if rel.startswith("contemplation/runs/"):
        return "contemplation_report"
    if path.suffix == ".jsonl":
        return "telemetry"
    return "unknown"


def runtime_status() -> RuntimeStatus:
    store = EngineStateStore()
    manifest = store.load_manifest() or {}
    current_revision = get_git_revision()
    checkpoint_revision = str(manifest.get("written_at_revision") or "unknown")
    backend_raw = os.environ.get("CORE_BACKEND", "numpy")
    backend = backend_raw if backend_raw in {"numpy", "mlx", "rust"} else "unknown"
    return RuntimeStatus(
        backend=backend,  # type: ignore[arg-type]
        git_revision=current_revision,
        engine_state_present=store.exists(),
        checkpoint_revision=checkpoint_revision,
        revision_warning=(
            checkpoint_revision not in {"", "unknown"}
            and current_revision not in {"", "unknown"}
            and checkpoint_revision != current_revision
        ),
        active_session_id=None,
    )


def list_artifacts(*, limit: int = 100) -> list[ArtifactRef]:
    items: list[ArtifactRef] = []
    for root in ALLOWED_ARTIFACT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if len(items) >= limit:
                return items
            if not path.is_file() or path.suffix not in {".json", ".jsonl", ".md", ".txt"}:
                continue
            if not _is_allowed(path):
                continue
            try:
                content = path.read_bytes()
            except OSError:
                continue
            rel = _relative(path)
            items.append(
                ArtifactRef(
                    artifact_id=rel,
                    kind=_artifact_kind(path),  # type: ignore[arg-type]
                    path=rel,
                    digest=_sha256_bytes(content),
                    created_at=None,
                )
            )
    return items


def read_artifact(artifact_id: str) -> ArtifactDetail:
    path = _resolve_artifact(artifact_id)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(artifact_id)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    content_type = "text"
    content: Any = text
    if path.suffix == ".json":
        content_type = "json"
        content = json.loads(text)
    elif path.suffix == ".jsonl":
        content_type = "jsonl"
        rows: list[Any] = []
        for line in text.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        content = rows
    rel = _relative(path)
    return ArtifactDetail(
        artifact_id=rel,
        kind=_artifact_kind(path),  # type: ignore[arg-type]
        path=rel,
        digest=_sha256_bytes(raw),
        created_at=None,
        content_type=content_type,  # type: ignore[arg-type]
        content=content,
    )


def _state_value(value: Any) -> str:
    text = str(value or "unknown")
    return text if text in {"pending", "accepted", "rejected", "withdrawn"} else "unknown"


def _source_kind(source: Any) -> str:
    if isinstance(source, dict):
        return str(source.get("kind") or "unknown")
    return "unknown"


def _replay_equivalent(replay: Any) -> bool | None:
    if isinstance(replay, dict) and isinstance(replay.get("replay_equivalent"), bool):
        return bool(replay["replay_equivalent"])
    return None


def _proposal_summary(proposal_id: str, record: dict[str, Any]) -> ProposalSummary:
    return ProposalSummary(
        proposal_id=proposal_id,
        state=_state_value(record.get("state")),  # type: ignore[arg-type]
        source_kind=_source_kind(record.get("source")),
        replay_equivalent=_replay_equivalent(record.get("replay_evidence")),
        created_at=None,
        downstream_effect="observed" if record.get("accepted_chain_id") else "unknown",
    )


def list_proposals(*, log_path: Path | None = None) -> list[ProposalSummary]:
    log = ProposalLog(path=log_path or DEFAULT_PROPOSAL_LOG_PATH)
    state = log.current_state()
    return [
        _proposal_summary(proposal_id, state[proposal_id])
        for proposal_id in sorted(state)
    ]


def read_proposal(proposal_id: str, *, log_path: Path | None = None) -> ProposalDetail:
    log = ProposalLog(path=log_path or DEFAULT_PROPOSAL_LOG_PATH)
    record = log.find(proposal_id)
    if record is None:
        raise FileNotFoundError(proposal_id)
    proposal = record.get("proposal") if isinstance(record.get("proposal"), dict) else {}
    summary = _proposal_summary(proposal_id, record)
    review_state = summary.state
    return ProposalDetail(
        proposal_id=summary.proposal_id,
        state=review_state,
        source_kind=summary.source_kind,
        replay_equivalent=summary.replay_equivalent,
        created_at=summary.created_at,
        downstream_effect=summary.downstream_effect,
        proposed_chain=proposal.get("proposed_chain"),
        replay_evidence=record.get("replay_evidence"),
        source=record.get("source"),
        evidence=proposal.get("evidence") if isinstance(proposal.get("evidence"), list) else [],
        artifact_refs=[],
        suggested_cli=(
            f"core teaching review {proposal_id} --accept --review-date YYYY-MM-DD"
            if review_state == "pending"
            else None
        ),
    )


def list_eval_lanes() -> list[EvalLaneSummary]:
    return [
        EvalLaneSummary(
            lane=lane.name,
            versions=list(lane.versions),
            read_only=lane.name in SAFE_EVAL_LANES,
            description=None,
        )
        for lane in discover_lanes()
    ]


def read_eval_lane(lane_name: str) -> EvalLaneSummary:
    lane = get_lane(lane_name)
    return EvalLaneSummary(
        lane=lane.name,
        versions=list(lane.versions),
        read_only=lane.name in SAFE_EVAL_LANES,
        description=None,
    )


def run_safe_eval_lane(
    lane_name: str,
    *,
    version: str = "v1",
    split: str = "public",
) -> EvalRunResult:
    if lane_name not in SAFE_EVAL_LANES:
        raise ValueError(f"eval lane is not workbench-safe/read-only: {lane_name}")
    if split == "holdout":
        raise ValueError("holdout execution is disabled in Workbench v1")
    lane = get_lane(lane_name)
    result = run_lane(lane, version=version, split=split, workers=1)
    passed_raw = result.metrics.get("passed") if isinstance(result.metrics, dict) else None
    passed = bool(passed_raw) if isinstance(passed_raw, bool) else None
    return EvalRunResult(
        lane=result.lane,
        version=result.version,
        split=result.split,
        passed=passed,
        metrics=result.metrics,
        cases=result.case_details,
        source_digest=(
            str(result.metrics["source_digest"])
            if isinstance(result.metrics, dict) and "source_digest" in result.metrics
            else None
        ),
    )
