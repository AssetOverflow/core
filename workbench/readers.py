"""Read-only readers for the CORE Workbench W-026 API."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path, PurePosixPath
from typing import Any, get_args

from engine_state import EngineStateStore, get_git_revision
from evals.framework import discover_lanes, get_lane, run_lane
from teaching.proposals import DEFAULT_PROPOSAL_LOG_PATH, ProposalLog, ReviewState
from workbench.schemas import (
    ArtifactDetail,
    ArtifactRef,
    EvalLaneSummary,
    EvalRunResult,
    MathProposalDetail,
    MathProposalSummary,
    MathRatifyResult,
    MathReasoningStep,
    ProposalDetail,
    ProposalSummary,
    RuntimeStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAFE_EVAL_LANES = frozenset({"contemplation_quality"})
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
_EVAL_RUN_LOCK = threading.Lock()
_REVIEW_STATES = frozenset(get_args(ReviewState))
ALLOWED_ARTIFACT_ROOTS = (
    REPO_ROOT / "engine_state",
    REPO_ROOT / "teaching" / "proposals",
    REPO_ROOT / "teaching" / "math_proposals",
    REPO_ROOT / "evals",
    REPO_ROOT / "contemplation" / "runs",
)

MATH_PROPOSALS_JSONL = REPO_ROOT / "teaching" / "math_proposals" / "proposals.jsonl"
_DEFAULT_MATH_AUDIT_PATH = (
    REPO_ROOT
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "audit_brief_11.json"
)

# Dispatch table: proposed_change_kind → handler name.
# Handlers not listed here are not yet implemented.
_HANDLER_DISPATCH: dict[str, str] = {
    "vocabulary_addition": "LexicalClaim",
    "frame_reclassification": "FrameClaim",
    "composition_reclassification": "CompositionClaim",
}


class ArtifactTooLargeError(OSError):
    """Raised when an artifact is too large for direct Workbench reads."""


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(READ_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


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
                digest = _sha256_file(path)
            except OSError:
                continue
            rel = _relative(path)
            items.append(
                ArtifactRef(
                    artifact_id=rel,
                    kind=_artifact_kind(path),  # type: ignore[arg-type]
                    path=rel,
                    digest=digest,
                    created_at=None,
                )
            )
    return items


def read_artifact(artifact_id: str) -> ArtifactDetail:
    path = _resolve_artifact(artifact_id)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(artifact_id)
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ArtifactTooLargeError(
            f"artifact exceeds {MAX_ARTIFACT_BYTES} byte read limit: {artifact_id}"
        )
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
    return text if text in _REVIEW_STATES else "unknown"


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


def _load_math_proposals_raw(jsonl_path: Path) -> list[dict[str, Any]]:
    """Parse proposals.jsonl into self-contained record dicts.

    ADR-0172 tightening follow-up #1: each line is a self-contained record
    written by :func:`teaching.math_contemplation_proposal.to_jsonl_record`
    that carries its own ``proposal_id``, full ``evidence_pointers``, and
    full ``reasoning_trace.steps``.  No decomposer re-run required.
    """
    if not jsonl_path.exists():
        return []
    results: list[dict[str, Any]] = []
    for raw_line in jsonl_path.read_bytes().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        data: dict[str, Any] = json.loads(stripped)
        results.append(data)
    return results


def _math_proposal_summary(record: dict[str, Any]) -> MathProposalSummary:
    evidence_pointers = record.get("evidence_pointers", [])
    evidence_count = len(evidence_pointers) if isinstance(evidence_pointers, list) else 0
    return MathProposalSummary(
        proposal_id=str(record.get("proposal_id", "")),
        domain="math",
        shape_category=str(record.get("shape_category", "")),
        proposed_change_kind=str(record.get("proposed_change_kind", "")),
        structural_commonality=str(record.get("structural_commonality", "")),
        evidence_count=evidence_count,
        replay_equivalence_hash=str(record.get("replay_equivalence_hash", "")),
    )


def list_math_proposals(*, jsonl_path: Path | None = None) -> list[MathProposalSummary]:
    path = jsonl_path or MATH_PROPOSALS_JSONL
    records = _load_math_proposals_raw(path)
    return [_math_proposal_summary(r) for r in records]


def _math_trace_steps_from_record(record: dict[str, Any]) -> list[MathReasoningStep]:
    """Extract 4 reasoning steps from a self-contained JSONL record."""
    trace = record.get("reasoning_trace") or {}
    if not isinstance(trace, dict):
        return []
    steps_raw = trace.get("steps", []) or []
    steps: list[MathReasoningStep] = []
    for step in steps_raw:
        if not isinstance(step, dict):
            continue
        steps.append(
            MathReasoningStep(
                step_index=int(step.get("step_index", 0)),
                step_kind=str(step.get("step_kind", "")),
                claim=str(step.get("claim", "")),
                justification=str(step.get("justification", "")),
                input_pointers=list(step.get("input_pointers", [])),
                output_payload=step.get("output_payload"),
            )
        )
    return steps


def read_math_proposal(
    proposal_id: str,
    *,
    jsonl_path: Path | None = None,
    audit_path: Path | None = None,  # retained for backward-compat; unused
) -> MathProposalDetail:
    """Return full proposal detail loaded entirely from the JSONL record.

    ADR-0172 tightening follow-up #1: no longer re-runs decompose_audit().
    The self-contained JSONL line carries the full reasoning_trace.steps
    and evidence_pointers; the workbench is decoupled from the decomposer.

    The ``audit_path`` keyword is preserved for call-site backward
    compatibility but is unused.
    """
    del audit_path  # decoupled — kept for backward-compat callers

    path = jsonl_path or MATH_PROPOSALS_JSONL
    records = _load_math_proposals_raw(path)
    record = next((r for r in records if r.get("proposal_id") == proposal_id), None)
    if record is None:
        raise FileNotFoundError(proposal_id)

    change_kind = str(record.get("proposed_change_kind", ""))
    handler_name = _HANDLER_DISPATCH.get(change_kind)

    trace_obj = record.get("reasoning_trace") or {}
    trace_id = str(trace_obj.get("trace_id", "")) if isinstance(trace_obj, dict) else ""
    trace_steps = _math_trace_steps_from_record(record)

    evidence_pointers_raw = record.get("evidence_pointers", []) or []
    evidence_hashes = [
        str(ev.get("evidence_hash", ""))
        for ev in evidence_pointers_raw
        if isinstance(ev, dict)
    ]

    suggested_cli: str | None = None
    if handler_name == "LexicalClaim":
        suggested_cli = (
            f"# ratify via Python REPL:\n"
            f"from teaching.math_lexical_ratification import apply_lexical_claim\n"
            f"# apply_lexical_claim(claim=<evidence>, category='drain_token', reviewer='<you>')"
        )
    elif handler_name == "FrameClaim":
        suggested_cli = (
            f"# ratify via Python REPL (ADR-0168):\n"
            f"from teaching.math_frame_ratification import apply_frame_claim\n"
            f"# apply_frame_claim(claim=<evidence>, frame_category='increment_frame', "
            f"polarity='affirms', reviewer='<you>')"
        )
    elif handler_name == "CompositionClaim":
        suggested_cli = (
            f"# ratify via Python REPL (ADR-0169):\n"
            f"from teaching.math_composition_ratification import apply_composition_claim\n"
            f"# apply_composition_claim(claim=<evidence>, "
            f"composition_category='multiplicative_composition', "
            f"polarity='affirms', reviewer='<you>')"
        )

    return MathProposalDetail(
        proposal_id=proposal_id,
        domain="math",
        shape_category=str(record.get("shape_category", "")),
        proposed_change_kind=change_kind,
        structural_commonality=str(record.get("structural_commonality", "")),
        evidence_count=len(evidence_hashes),
        replay_equivalence_hash=str(record.get("replay_equivalence_hash", "")),
        wrong_zero_assertion=str(record.get("wrong_zero_assertion", "")),
        proposed_change_payload=record.get("proposed_change_payload"),
        reasoning_trace_id=trace_id,
        reasoning_trace_steps=trace_steps,
        evidence_hashes=evidence_hashes,
        handler_name=handler_name,
        suggested_ratify_cli=suggested_cli,
    )


def ratify_math_proposal(
    proposal_id: str,
    *,
    jsonl_path: Path | None = None,
) -> MathRatifyResult:
    """Dispatch ratification by change_kind; fail loudly for unimplemented handlers.

    ADR-0160 "Proposal before mutation" doctrine: this function validates
    routing and returns the handler name + suggested CLI without applying
    the change.  Mutation requires an explicit operator action outside the
    workbench (e.g. calling apply_lexical_claim() directly).

    Raises FileNotFoundError if proposal_id not found.
    Raises NotImplementedError with a clear message for unhandled change_kinds.
    """
    path = jsonl_path or MATH_PROPOSALS_JSONL
    records = _load_math_proposals_raw(path)
    record = next((r for r in records if r.get("proposal_id") == proposal_id), None)
    if record is None:
        raise FileNotFoundError(proposal_id)

    change_kind = str(record.get("proposed_change_kind", ""))
    handler_name = _HANDLER_DISPATCH.get(change_kind)

    if handler_name is None:
        raise NotImplementedError(
            f"handler not yet implemented for change_kind={change_kind!r}; "
            f"see docs/handoff/ADR-0167-FOLLOWUPS.md §1 for the scoping ADR required "
            f"before this change_kind can be ratified"
        )

    suggested_cli: str | None = None
    if handler_name == "LexicalClaim":
        suggested_cli = (
            f"from teaching.math_lexical_ratification import apply_lexical_claim\n"
            f"# apply_lexical_claim(claim=<evidence>, category='drain_token', reviewer='<you>')"
        )
    elif handler_name == "FrameClaim":
        suggested_cli = (
            f"from teaching.math_frame_ratification import apply_frame_claim\n"
            f"# apply_frame_claim(claim=<evidence>, frame_category='increment_frame', "
            f"polarity='affirms', reviewer='<you>')"
        )
    elif handler_name == "CompositionClaim":
        suggested_cli = (
            f"from teaching.math_composition_ratification import apply_composition_claim\n"
            f"# apply_composition_claim(claim=<evidence>, "
            f"composition_category='multiplicative_composition', "
            f"polarity='affirms', reviewer='<you>')"
        )

    return MathRatifyResult(
        proposal_id=proposal_id,
        change_kind=change_kind,
        handler_name=handler_name,
        routing_status="routed",
        message=f"routed to {handler_name} handler",
        suggested_cli=suggested_cli,
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
    if version not in lane.versions:
        raise ValueError(f"unsupported eval version for {lane_name}: {version}")
    with _EVAL_RUN_LOCK:
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
