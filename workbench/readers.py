"""Read-only readers for the CORE Workbench W-026 API."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, get_args

from engine_state import EngineStateStore, get_git_revision
from evals.framework import discover_lanes, get_lane, run_lane
from teaching.proposals import DEFAULT_PROPOSAL_LOG_PATH, ProposalLog, ReviewState
from workbench.schemas import (
    AuditEvent,
    ArtifactDetail,
    ArtifactRef,
    DemoRunResult,
    DemoScenarioRunResult,
    DemoScenarioSummary,
    DemoSummary,
    EvalLaneSummary,
    EvalRunResult,
    MathProposalDetail,
    MathProposalSummary,
    MathRatifyResult,
    MathReasoningStep,
    PackDetail,
    PackSummary,
    ProposalDetail,
    ProposalSummary,
    RunDetail,
    RunSummary,
    RunTurnRef,
    RuntimeStatus,
    VaultEntry,
    VaultSummary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAFE_EVAL_LANES = frozenset({"contemplation_quality"})
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
SAFE_PACK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
JOURNAL_RUN_ID = "workbench_turn_journal"
ENGINE_STATE_RUN_ID = "engine_state_checkpoint"
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
LANGUAGE_PACK_ROOT = REPO_ROOT / "language_packs" / "data"
RUNTIME_PACK_ROOT = REPO_ROOT / "packs"
WORKBENCH_TELEMETRY_ROOT = REPO_ROOT / "workbench_data"
ENGINE_STATE_ROOT = REPO_ROOT / "engine_state"
DEMOS_ROOT = REPO_ROOT / "demos"
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


@dataclass(frozen=True, slots=True)
class _DemoSpec:
    demo_id: str
    title: str
    description: str
    root: Path
    evidence_class: str
    what_this_proves: str
    what_this_does_not_prove: str
    fixture_paths: Callable[[], list[Path]]
    expected_path: Callable[[str], Path]
    run_fixture: Callable[[Path], dict[str, Any]]


def _pccp_fixture_paths() -> list[Path]:
    from demos.proof_carrying_promotion import run_demo

    return run_demo.fixture_paths()


def _pccp_expected_path(scenario_id: str) -> Path:
    from demos.proof_carrying_promotion import run_demo

    return run_demo.expected_path(scenario_id)


def _pccp_run_fixture(path: Path) -> dict[str, Any]:
    from demos.proof_carrying_promotion import run_demo

    return run_demo.run_fixture(path)


def _deductive_fixture_paths() -> list[Path]:
    from demos.deductive_entailment_authority import run_demo

    return run_demo.fixture_paths()


def _deductive_expected_path(scenario_id: str) -> Path:
    from demos.deductive_entailment_authority import run_demo

    return run_demo.expected_path(scenario_id)


def _deductive_run_fixture(path: Path) -> dict[str, Any]:
    from demos.deductive_entailment_authority import run_demo

    return run_demo.run_fixture(path)


def _truth_state_fixture_paths() -> list[Path]:
    from demos.epistemic_truth_state import run_demo

    return run_demo.fixture_paths()


def _truth_state_expected_path(scenario_id: str) -> Path:
    from demos.epistemic_truth_state import run_demo

    return run_demo.expected_path(scenario_id)


def _truth_state_run_fixture(path: Path) -> dict[str, Any]:
    from demos.epistemic_truth_state import run_demo

    return run_demo.run_fixture(path)


DEMO_SPECS: dict[str, _DemoSpec] = {
    "proof_carrying_promotion": _DemoSpec(
        demo_id="proof_carrying_promotion",
        title="Proof-Carrying Coherence Promotion",
        description="Vault-owned certified promotion with proposer status ignored.",
        root=DEMOS_ROOT / "proof_carrying_promotion",
        evidence_class="substrate_capability",
        what_this_proves=(
            "CORE fresh-reads a curated local arena, recomputes entailment, "
            "and lets the vault owner apply promotion only through a verified certificate."
        ),
        what_this_does_not_prove=(
            "It does not prove broad natural-language reasoning, autonomous curation, "
            "or model authority over epistemic status."
        ),
        fixture_paths=_pccp_fixture_paths,
        expected_path=_pccp_expected_path,
        run_fixture=_pccp_run_fixture,
    ),
    "deductive_entailment_authority": _DemoSpec(
        demo_id="deductive_entailment_authority",
        title="Deductive Entailment Authority",
        description="Formal entailment decided by the pinned engine and an independent oracle.",
        root=DEMOS_ROOT / "deductive_entailment_authority",
        evidence_class="substrate_capability",
        what_this_proves=(
            "CORE serves entailed, refuted, unknown, and refused decisions only when "
            "the pinned ROBDD engine and independent truth-table oracle agree."
        ),
        what_this_does_not_prove=(
            "It does not claim open-domain theorem proving or acceptance of proposer-provided proofs."
        ),
        fixture_paths=_deductive_fixture_paths,
        expected_path=_deductive_expected_path,
        run_fixture=_deductive_run_fixture,
    ),
    "epistemic_truth_state": _DemoSpec(
        demo_id="epistemic_truth_state",
        title="Epistemic Truth-State Authority",
        description="Evidence-bounded state assignment with invalid proposer smuggling refused.",
        root=DEMOS_ROOT / "epistemic_truth_state",
        evidence_class="substrate_capability",
        what_this_proves=(
            "CORE assigns truth-state from bounded evidence and rejects proposer attempts "
            "to smuggle unsupported state."
        ),
        what_this_does_not_prove=(
            "It does not prove universal factual coverage or mutate reviewed memory."
        ),
        fixture_paths=_truth_state_fixture_paths,
        expected_path=_truth_state_expected_path,
        run_fixture=_truth_state_run_fixture,
    ),
}


class ArtifactTooLargeError(OSError):
    """Raised when an artifact is too large for direct Workbench reads."""


class EvidenceUnavailableError(OSError):
    """Raised when a read route has no persisted evidence source to project."""


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


def _display_path(path: Path) -> str:
    try:
        return _relative(path)
    except ValueError:
        return path.resolve().as_posix()


def _check_read_size(path: Path, artifact_id: str | None = None) -> None:
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        label = artifact_id or _display_path(path)
        raise ArtifactTooLargeError(
            f"artifact exceeds {MAX_ARTIFACT_BYTES} byte read limit: {label}"
        )


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _read_json_object(path: Path) -> dict[str, Any]:
    _check_read_size(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {_display_path(path)}")
    return payload


def _read_jsonl_records(path: Path) -> list[tuple[int, dict[str, Any]]]:
    if not path.exists():
        return []
    _check_read_size(path)
    records: list[tuple[int, dict[str, Any]]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append((line_no, payload))
    return records


def _page(items: list[Any], *, limit: int, offset: int) -> list[Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    return items[offset : offset + limit]


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
    _check_read_size(path, artifact_id)
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


def _validate_pack_id(pack_id: str) -> str:
    if not SAFE_PACK_ID_RE.fullmatch(pack_id):
        raise ValueError("pack id contains unsafe characters")
    return pack_id


def _manifest_checksum_fields(manifest: dict[str, Any]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for key in sorted(manifest):
        value = manifest[key]
        if not isinstance(value, str):
            continue
        lowered = key.lower()
        if "checksum" in lowered or lowered.endswith("_sha256") or lowered == "sha256":
            checksums[key] = value
    return checksums


def _pack_source(path: Path) -> str:
    resolved = path.resolve()
    language_root = LANGUAGE_PACK_ROOT.resolve()
    runtime_root = RUNTIME_PACK_ROOT.resolve()
    if language_root == resolved or language_root in resolved.parents:
        return "language_pack"
    if runtime_root == resolved or runtime_root in resolved.parents:
        return "runtime_pack"
    return "runtime_pack"


def _pack_manifest_paths() -> list[Path]:
    paths: list[Path] = []
    if LANGUAGE_PACK_ROOT.exists():
        paths.extend(sorted(LANGUAGE_PACK_ROOT.glob("*/manifest.json")))
    if RUNTIME_PACK_ROOT.exists():
        paths.extend(sorted(RUNTIME_PACK_ROOT.glob("*/*/manifest.json")))
    return paths


def _pack_detail_from_manifest(path: Path) -> PackDetail | None:
    manifest = _read_json_object(path)
    pack_id = str(manifest.get("pack_id") or manifest.get("register_id") or path.parent.name)
    if not SAFE_PACK_ID_RE.fullmatch(pack_id):
        return None
    checksums = _manifest_checksum_fields(manifest)
    return PackDetail(
        pack_id=pack_id,
        source=_pack_source(path),  # type: ignore[arg-type]
        manifest_path=_display_path(path),
        version=(str(manifest["version"]) if "version" in manifest else None),
        language=(str(manifest["language"]) if "language" in manifest else None),
        modality=(str(manifest["modality"]) if "modality" in manifest else None),
        determinism_class=(
            str(manifest["determinism_class"])
            if "determinism_class" in manifest
            else None
        ),
        checksum=(str(manifest["checksum"]) if "checksum" in manifest else None),
        checksums=checksums,
        manifest_digest=_sha256_file(path),
        manifest=manifest,
    )


def _all_pack_details() -> list[PackDetail]:
    details: list[PackDetail] = []
    for path in _pack_manifest_paths():
        detail = _pack_detail_from_manifest(path)
        if detail is not None:
            details.append(detail)
    return sorted(details, key=lambda item: (item.pack_id, item.source, item.manifest_path))


def list_packs(*, limit: int = 100, offset: int = 0) -> list[PackSummary]:
    return [
        PackSummary(
            pack_id=detail.pack_id,
            source=detail.source,
            manifest_path=detail.manifest_path,
            version=detail.version,
            language=detail.language,
            modality=detail.modality,
            determinism_class=detail.determinism_class,
            checksum=detail.checksum,
            checksums=detail.checksums,
        )
        for detail in _page(_all_pack_details(), limit=limit, offset=offset)
    ]


def read_pack(pack_id: str) -> PackDetail:
    safe_id = _validate_pack_id(pack_id)
    for detail in _all_pack_details():
        if detail.pack_id == safe_id:
            return detail
    raise FileNotFoundError(pack_id)


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


def _validate_demo_id(demo_id: str) -> str:
    if not SAFE_PACK_ID_RE.fullmatch(demo_id):
        raise ValueError("demo id contains unsafe characters")
    return demo_id


def _scenario_title(scenario_id: str) -> str:
    return scenario_id.replace("-", " ").replace("_", " ").title()


def _fixture_for_path(path: Path) -> dict[str, Any]:
    _check_read_size(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {_display_path(path)}")
    return payload


def _scenario_id_from_fixture(fixture: dict[str, Any], path: Path) -> str:
    args = fixture.get("arguments")
    if isinstance(args, dict) and isinstance(args.get("scenario_id"), str):
        return args["scenario_id"]
    value = fixture.get("scenario_id")
    if isinstance(value, str):
        return value
    raise ValueError(f"demo fixture has no scenario_id: {_display_path(path)}")


def _proposer_wrong(scenario_id: str, fixture: dict[str, Any], response: Any | None = None) -> bool:
    lowered = scenario_id.lower()
    if "proposer" in lowered or "smuggling" in lowered:
        return True
    source = response if isinstance(response, dict) else fixture.get("arguments")
    if isinstance(source, dict):
        ignored = source.get("proposer_ignored_fields")
        if isinstance(ignored, list) and ignored:
            return True
        trace_summary = source.get("trace_summary")
        if isinstance(trace_summary, dict):
            ignored = trace_summary.get("proposer_fields_ignored")
            if isinstance(ignored, list) and ignored:
                return True
    return False


def _render_demo_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def _demo_spec(demo_id: str) -> _DemoSpec:
    safe_id = _validate_demo_id(demo_id)
    spec = DEMO_SPECS.get(safe_id)
    if spec is None:
        raise FileNotFoundError(demo_id)
    return spec


def _demo_scenario_summaries(spec: _DemoSpec) -> list[DemoScenarioSummary]:
    scenarios: list[DemoScenarioSummary] = []
    for path in spec.fixture_paths():
        fixture = _fixture_for_path(path)
        scenario_id = _scenario_id_from_fixture(fixture, path)
        scenarios.append(
            DemoScenarioSummary(
                scenario_id=scenario_id,
                title=_scenario_title(scenario_id),
                expected_status=str(fixture.get("expected_status") or "unknown"),
                evidence_class=spec.evidence_class,  # type: ignore[arg-type]
                proposer_wrong=_proposer_wrong(scenario_id, fixture),
                what_this_proves=spec.what_this_proves,
                what_this_does_not_prove=spec.what_this_does_not_prove,
            )
        )
    return sorted(scenarios, key=lambda item: item.scenario_id)


def list_demos() -> list[DemoSummary]:
    demos: list[DemoSummary] = []
    for spec in sorted(DEMO_SPECS.values(), key=lambda item: item.demo_id):
        scenarios = _demo_scenario_summaries(spec)
        demos.append(
            DemoSummary(
                demo_id=spec.demo_id,
                title=spec.title,
                description=spec.description,
                evidence_class=spec.evidence_class,  # type: ignore[arg-type]
                scenario_count=len(scenarios),
                read_only=True,
                scenarios=scenarios,
            )
        )
    return demos


def run_demo(demo_id: str) -> DemoRunResult:
    spec = _demo_spec(demo_id)
    results: list[DemoScenarioRunResult] = []
    all_passed = True
    for path in spec.fixture_paths():
        fixture = _fixture_for_path(path)
        scenario_id = _scenario_id_from_fixture(fixture, path)
        expected_status = str(fixture.get("expected_status") or "")
        response = spec.run_fixture(path)
        problems: list[str] = []
        status = str(response.get("status") if isinstance(response, dict) else "unknown")
        if status != expected_status:
            problems.append(f"status {status!r} != expected {expected_status!r}")
        ref = spec.expected_path(scenario_id)
        if not ref.exists():
            problems.append("missing committed expected artifact")
        else:
            _check_read_size(ref)
            if ref.read_text(encoding="utf-8") != _render_demo_payload(response):
                problems.append("response drifted from committed expected artifact")
        passed = not problems
        all_passed = all_passed and passed
        results.append(
            DemoScenarioRunResult(
                scenario_id=scenario_id,
                status=status,
                passed=passed,
                proposer_wrong=_proposer_wrong(scenario_id, fixture, response),
                evidence_class=spec.evidence_class,  # type: ignore[arg-type]
                decision_reason=(
                    str(response.get("decision_reason"))
                    if isinstance(response, dict) and response.get("decision_reason") is not None
                    else None
                ),
                trace_hash=(
                    str(response.get("trace_hash"))
                    if isinstance(response, dict) and response.get("trace_hash") is not None
                    else None
                ),
                problems=problems,
                response=response,
            )
        )
    results.sort(key=lambda item: (item.passed, not item.proposer_wrong, item.scenario_id))
    return DemoRunResult(
        demo_id=spec.demo_id,
        all_passed=all_passed,
        what_this_proves=spec.what_this_proves,
        what_this_does_not_prove=spec.what_this_does_not_prove,
        scenarios=results,
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
    return [_math_proposal_summary(r) for r in records if r.get("domain") == "math"]



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
    if record.get("domain") != "math":
        raise ValueError(f"Partition isolation violation: proposal domain must be 'math', got {record.get('domain')!r}")


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
    category: str | None = None,
    polarity: str | None = None,
    reviewer: str | None = None,
    dry_run: bool = False,
    jsonl_path: Path | None = None,
) -> MathRatifyResult:
    """Dispatch ratification by change_kind.

    If dry_run is False and category is provided, this applies the ratification mutation in-process.
    Otherwise, it validates routing and returns the handler name + suggested CLI.
    """
    path = jsonl_path or MATH_PROPOSALS_JSONL
    records = _load_math_proposals_raw(path)
    record = next((r for r in records if r.get("proposal_id") == proposal_id), None)
    if record is None:
        raise FileNotFoundError(proposal_id)
    if record.get("domain") != "math":
        raise ValueError(f"Partition isolation violation: proposal domain must be 'math', got {record.get('domain')!r}")


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

    if dry_run or category is None:
        return MathRatifyResult(
            proposal_id=proposal_id,
            change_kind=change_kind,
            handler_name=handler_name,
            routing_status="routed",
            message=f"routed to {handler_name} handler",
            suggested_cli=suggested_cli,
            applied=False,
        )

    # In-process application
    from teaching.math_contemplation_proposal import from_jsonl_record
    proposal = from_jsonl_record(record)
    if not proposal.evidence_pointers:
        raise ValueError(f"Proposal {proposal_id} has no evidence pointers")
    claim = proposal.evidence_pointers[0]

    import getpass
    effective_reviewer = reviewer or getpass.getuser()

    if handler_name == "LexicalClaim":
        from teaching.math_lexical_ratification import apply_lexical_claim
        receipt = apply_lexical_claim(
            claim=claim,
            category=category,
            reviewer=effective_reviewer,
            ratifier_kind="workbench",
        )
        return MathRatifyResult(
            proposal_id=proposal_id,
            change_kind=change_kind,
            handler_name=handler_name,
            routing_status="routed",
            message=f"Applied LexicalClaim to {receipt.target_file}",
            suggested_cli=suggested_cli,
            applied=True,
            target_path=receipt.target_file,
            evidence_hash=receipt.evidence_hash,
        )

    elif handler_name == "FrameClaim":
        from teaching.math_frame_ratification import apply_frame_claim
        if not polarity:
            raise ValueError("Polarity is required for FrameClaim ratification")
        receipt = apply_frame_claim(
            claim=claim,
            frame_category=category,
            polarity=polarity,
            reviewer=effective_reviewer,
            ratifier_kind="workbench",
        )
        return MathRatifyResult(
            proposal_id=proposal_id,
            change_kind=change_kind,
            handler_name=handler_name,
            routing_status="routed",
            message=f"Applied FrameClaim to {receipt.target_file}",
            suggested_cli=suggested_cli,
            applied=True,
            target_path=receipt.target_file,
            evidence_hash=receipt.evidence_hash,
        )

    elif handler_name == "CompositionClaim":
        from teaching.math_composition_ratification import apply_composition_claim
        if not polarity:
            raise ValueError("Polarity is required for CompositionClaim ratification")
        receipt = apply_composition_claim(
            claim=claim,
            composition_category=category,
            polarity=polarity,
            reviewer=effective_reviewer,
            ratifier_kind="workbench",
        )
        return MathRatifyResult(
            proposal_id=proposal_id,
            change_kind=change_kind,
            handler_name=handler_name,
            routing_status="routed",
            message=f"Applied CompositionClaim to {receipt.target_file}",
            suggested_cli=suggested_cli,
            applied=True,
            target_path=receipt.target_file,
            evidence_hash=receipt.evidence_hash,
        )

    else:
        raise NotImplementedError(f"handler {handler_name} application not implemented")


def _payload_digest(payload: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(payload))


def _event_timestamp(payload: dict[str, Any]) -> str | None:
    for key in ("timestamp", "created_at", "emitted_at", "reviewed_at", "review_date"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    proposal = payload.get("proposal")
    if isinstance(proposal, dict):
        source = proposal.get("source")
        if isinstance(source, dict):
            value = source.get("emitted_at")
            if isinstance(value, str) and value:
                return value
    return None


def _proposal_ref_id(payload: dict[str, Any]) -> str | None:
    value = payload.get("proposal_id")
    if isinstance(value, str) and value:
        return value
    proposal = payload.get("proposal")
    if isinstance(proposal, dict):
        value = proposal.get("proposal_id")
        if isinstance(value, str) and value:
            return value
    return None


def _audit_event(
    *,
    source: str,
    source_path: Path,
    line_no: int,
    event_type: str,
    payload: dict[str, Any],
    mutation_boundary: bool,
    ref_id: str | None = None,
    summary: str | None = None,
) -> AuditEvent:
    display_path = _display_path(source_path)
    digest = _payload_digest(payload)
    event_id = _sha256_bytes(
        _canonical_json_bytes(
            {
                "digest": digest,
                "event_type": event_type,
                "line_no": line_no,
                "source": source,
                "source_path": display_path,
            }
        )
    )
    label = summary or event_type
    if ref_id:
        label = f"{label}: {ref_id}"
    return AuditEvent(
        event_id=event_id,
        source=source,  # type: ignore[arg-type]
        source_path=display_path,
        timestamp=_event_timestamp(payload),
        event_type=event_type,
        mutation_boundary=mutation_boundary,
        summary=label,
        ref_id=ref_id,
        payload_digest=digest,
        payload=payload,
    )


def _teaching_proposal_audit_events() -> list[AuditEvent]:
    path = DEFAULT_PROPOSAL_LOG_PATH
    events: list[AuditEvent] = []
    for line_no, payload in _read_jsonl_records(path):
        event_type = str(payload.get("event") or "proposal_event")
        ref_id = _proposal_ref_id(payload)
        events.append(
            _audit_event(
                source="teaching_proposal_log",
                source_path=path,
                line_no=line_no,
                event_type=event_type,
                payload=payload,
                mutation_boundary=event_type in {"transition", "accepted_corpus_append"},
                ref_id=ref_id,
                summary="teaching proposal event",
            )
        )
    return events


def _math_proposal_audit_events() -> list[AuditEvent]:
    path = MATH_PROPOSALS_JSONL
    events: list[AuditEvent] = []
    for line_no, payload in _read_jsonl_records(path):
        ref_id = (
            str(payload.get("proposal_id"))
            if isinstance(payload.get("proposal_id"), str)
            else None
        )
        events.append(
            _audit_event(
                source="math_proposal_log",
                source_path=path,
                line_no=line_no,
                event_type="math_proposal_record",
                payload=payload,
                mutation_boundary=False,
                ref_id=ref_id,
                summary="math proposal record",
            )
        )
    return events


def _telemetry_audit_events() -> list[AuditEvent]:
    if not WORKBENCH_TELEMETRY_ROOT.exists():
        return []
    events: list[AuditEvent] = []
    for path in sorted(WORKBENCH_TELEMETRY_ROOT.rglob("*.jsonl")):
        if not path.is_file():
            continue
        for line_no, payload in _read_jsonl_records(path):
            event_name = str(payload.get("event") or "")
            event_type = str(payload.get("type") or event_name or "telemetry_event")
            if event_type == "reboot":
                source = "reboot_telemetry"
                mutation_boundary = False
                summary = "reboot telemetry"
            elif event_name.startswith("operator_"):
                source = "operator_telemetry"
                mutation_boundary = True
                summary = "workbench operator telemetry"
            else:
                continue
            ref_id = (
                str(payload.get("proposal_id"))
                if isinstance(payload.get("proposal_id"), str)
                else None
            )
            events.append(
                _audit_event(
                    source=source,
                    source_path=path,
                    line_no=line_no,
                    event_type=event_type,
                    payload=payload,
                    mutation_boundary=mutation_boundary,
                    ref_id=ref_id,
                    summary=summary,
                )
            )
    return events


def _engine_state_manifest_audit_event() -> list[AuditEvent]:
    path = ENGINE_STATE_ROOT / "manifest.json"
    if not path.exists():
        return []
    manifest = _read_json_object(path)
    return [
        _audit_event(
            source="engine_state_manifest",
            source_path=path,
            line_no=1,
            event_type="engine_state_checkpoint",
            payload=manifest,
            mutation_boundary=True,
            ref_id=str(manifest.get("written_at_revision") or "unknown"),
            summary="engine state checkpoint",
        )
    ]


def list_audit_events(*, limit: int = 100, offset: int = 0) -> list[AuditEvent]:
    events: list[AuditEvent] = []
    events.extend(_engine_state_manifest_audit_event())
    events.extend(_teaching_proposal_audit_events())
    events.extend(_math_proposal_audit_events())
    events.extend(_telemetry_audit_events())
    events.sort(
        key=lambda event: (
            event.timestamp or "",
            event.source,
            event.source_path,
            event.event_type,
            event.event_id,
        )
    )
    return _page(events, limit=limit, offset=offset)


def _artifact_ref_for_path(path: Path, kind: str) -> ArtifactRef | None:
    if not path.exists() or not path.is_file():
        return None
    _check_read_size(path)
    return ArtifactRef(
        artifact_id=_display_path(path),
        kind=kind,  # type: ignore[arg-type]
        path=_display_path(path),
        digest=_sha256_file(path),
        created_at=None,
    )


def _load_engine_manifest() -> tuple[Path, dict[str, Any]] | None:
    path = ENGINE_STATE_ROOT / "manifest.json"
    if not path.exists():
        return None
    return path, _read_json_object(path)


def _journal_entries(journal: Any) -> list[Any]:
    path = getattr(journal, "path", None)
    if isinstance(path, Path) and path.exists():
        _check_read_size(path)
    return list(journal.list_entries(limit=1_000_000, offset=0))


def _engine_run_summary(manifest_item: tuple[Path, dict[str, Any]] | None) -> RunSummary | None:
    if manifest_item is None:
        return None
    path, manifest = manifest_item
    artifact = _artifact_ref_for_path(path, "engine_state_manifest")
    return RunSummary(
        session_id=ENGINE_STATE_RUN_ID,
        source="engine_state_manifest",
        turn_count=int(manifest.get("turn_count") or 0),
        started_at=None,
        updated_at=None,
        checkpoint_present=True,
        checkpoint_revision=str(manifest.get("written_at_revision") or "unknown"),
        artifact_refs=[artifact] if artifact is not None else [],
        evidence_gap="engine_state manifest has no durable per-session id",
    )


def _journal_run_summary(journal: Any, manifest: dict[str, Any] | None) -> RunSummary | None:
    entries = _journal_entries(journal)
    if not entries:
        return None
    path = getattr(journal, "path", None)
    artifact = _artifact_ref_for_path(path, "trace") if isinstance(path, Path) else None
    return RunSummary(
        session_id=JOURNAL_RUN_ID,
        source="turn_journal",
        turn_count=len(entries),
        started_at=str(entries[0].timestamp),
        updated_at=str(entries[-1].timestamp),
        checkpoint_present=manifest is not None,
        checkpoint_revision=(
            str(manifest.get("written_at_revision") or "unknown")
            if manifest is not None
            else None
        ),
        artifact_refs=[artifact] if artifact is not None else [],
        evidence_gap="turn journal is one local grouping; no separate durable session id is recorded",
    )


def list_runs(journal: Any, *, limit: int = 100, offset: int = 0) -> list[RunSummary]:
    manifest_item = _load_engine_manifest()
    manifest = manifest_item[1] if manifest_item is not None else None
    runs = [
        item
        for item in (
            _journal_run_summary(journal, manifest),
            _engine_run_summary(manifest_item),
        )
        if item is not None
    ]
    runs.sort(key=lambda run: (run.updated_at or "", run.session_id))
    return _page(runs, limit=limit, offset=offset)


def _run_detail_from_summary(
    summary: RunSummary,
    *,
    turns: list[RunTurnRef],
    manifest: dict[str, Any] | None,
) -> RunDetail:
    return RunDetail(
        session_id=summary.session_id,
        source=summary.source,
        turn_count=summary.turn_count,
        started_at=summary.started_at,
        updated_at=summary.updated_at,
        checkpoint_present=summary.checkpoint_present,
        checkpoint_revision=summary.checkpoint_revision,
        artifact_refs=summary.artifact_refs,
        evidence_gap=summary.evidence_gap,
        turns=turns,
        manifest=manifest,
    )


def read_run(
    session_id: str,
    journal: Any,
    *,
    turn_limit: int = 100,
    turn_offset: int = 0,
) -> RunDetail:
    manifest_item = _load_engine_manifest()
    manifest = manifest_item[1] if manifest_item is not None else None
    if session_id == JOURNAL_RUN_ID:
        summary = _journal_run_summary(journal, manifest)
        if summary is None:
            raise FileNotFoundError(session_id)
        entries = _journal_entries(journal)
        turns = [
            RunTurnRef(
                turn_id=int(entry.turn_id),
                trace_hash=entry.trace_hash,
                timestamp=str(entry.timestamp),
                trace_path=f"/trace/{entry.turn_id}",
                surface_excerpt=str(entry.surface)[:120],
                trace_integrity=entry.trace_integrity,
            )
            for entry in _page(entries, limit=turn_limit, offset=turn_offset)
        ]
        return _run_detail_from_summary(summary, turns=turns, manifest=manifest)
    if session_id == ENGINE_STATE_RUN_ID:
        summary = _engine_run_summary(manifest_item)
        if summary is None:
            raise FileNotFoundError(session_id)
        return _run_detail_from_summary(summary, turns=[], manifest=manifest)
    raise FileNotFoundError(session_id)


def _load_vault_snapshot() -> tuple[Path, dict[str, Any]]:
    path = ENGINE_STATE_ROOT / "session_state.json"
    if not path.exists():
        raise EvidenceUnavailableError(
            "vault evidence unavailable: engine_state/session_state.json is absent"
        )
    payload = _read_json_object(path)
    vault = payload.get("vault")
    if not isinstance(vault, dict):
        raise EvidenceUnavailableError(
            "vault evidence unavailable: engine_state/session_state.json has no vault snapshot"
        )
    return path, vault


def read_vault_summary() -> VaultSummary:
    path, vault = _load_vault_snapshot()
    metadata = vault.get("metadata")
    entries = metadata if isinstance(metadata, list) else []
    return VaultSummary(
        source_path=_display_path(path),
        entry_count=len(entries),
        store_count=int(vault.get("store_count") or 0),
        reproject_interval=int(vault.get("reproject_interval") or 0),
        max_entries=(
            int(vault["max_entries"])
            if isinstance(vault.get("max_entries"), int)
            else None
        ),
        persisted=True,
    )


def list_vault_entries(*, limit: int = 100, offset: int = 0) -> list[VaultEntry]:
    _path, vault = _load_vault_snapshot()
    metadata_raw = vault.get("metadata")
    versors_raw = vault.get("versors")
    if not isinstance(metadata_raw, list):
        raise ValueError("vault snapshot metadata must be a list")
    versors = versors_raw if isinstance(versors_raw, list) else []
    entries: list[VaultEntry] = []
    for index, metadata_item in enumerate(metadata_raw):
        metadata = metadata_item if isinstance(metadata_item, dict) else {}
        versor = versors[index] if index < len(versors) else None
        entries.append(
            VaultEntry(
                entry_index=index,
                epistemic_status=str(metadata.get("epistemic_status") or "unknown"),
                epistemic_state=str(metadata.get("epistemic_state") or "unknown"),
                metadata=metadata,
                versor_digest=(
                    _sha256_bytes(_canonical_json_bytes(versor))
                    if versor is not None
                    else None
                ),
            )
        )
    return _page(entries, limit=limit, offset=offset)


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
