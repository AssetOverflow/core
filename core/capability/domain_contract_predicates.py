"""ADR-0091 / ADR-0093 — Domain Pack Contract v1 predicate evaluation.

Wires the five follow-up items from ADR-0091 §"Follow-up Work" into a
single evidence-bearing report. The existing parser
(:func:`language_packs.domain_contract.parse_domain_contract`) handles
structural validation; this module layers the nine semantic predicates
from ADR-0091 §"Validation Semantics" on top.

The predicates are pure functions over already-available data:

- Manifest checksums and gloss closure are checked by existing
  pack-validation paths and surfaced via :func:`_predicate_p1` /
  :func:`_predicate_p2`.
- Chain coverage (P4/P5/P6) consults :func:`core.capability.chain_report`.
- Reviewer resolution (P8) consults the ADR-0092 registry.
- Gap state (P9) consults ``docs/gaps.md``.

Nothing mutates pack state. The validator remains proposal-only.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.capability.domains import DOMAIN_OPERATOR_CLAIMS, DOMAIN_PACKS
from core.capability.reporting import chain_report
from core.capability.reviewers import (
    ReviewerRegistry,
    ReviewerRegistryError,
    load_reviewer_registry,
)
from core.capability.sources import LEDGER_SOURCES
from language_packs.domain_contract import (
    DomainContractValidation,
    DomainPackContract,
    validate_domain_contract_pack,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REQUIRED_SPLITS: frozenset[str] = frozenset({"dev", "public", "holdout"})
_MIN_CHAINS_PER_OPERATOR = 8
_MIN_INTENT_SHAPES = 3


@dataclass(frozen=True, slots=True)
class PredicateResult:
    """Outcome of a single ADR-0091 predicate evaluation."""

    predicate_id: str
    title: str
    passed: bool
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "predicate_id": self.predicate_id,
            "title": self.title,
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class DomainContractPredicateReport:
    """Per-pack ADR-0091 nine-predicate report."""

    pack_id: str
    domain_id: str
    contract_present: bool
    contract_valid: bool
    contract_errors: tuple[str, ...]
    predicates: tuple[PredicateResult, ...]
    eval_lane_artifacts: tuple[dict[str, Any], ...] = field(default=())

    @property
    def all_passed(self) -> bool:
        return (
            self.contract_present
            and self.contract_valid
            and all(p.passed for p in self.predicates)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "domain_id": self.domain_id,
            "contract_present": self.contract_present,
            "contract_valid": self.contract_valid,
            "contract_errors": list(self.contract_errors),
            "predicates": [p.as_dict() for p in self.predicates],
            "eval_lane_artifacts": [dict(a) for a in self.eval_lane_artifacts],
            "all_passed": self.all_passed,
        }


# ---------------------------------------------------------------------------
# Predicate implementations
# ---------------------------------------------------------------------------


def _predicate_p1_manifest_valid(
    pack_id: str, *, data_root: Path  # noqa: ARG001 - reserved for future overrides
) -> PredicateResult:
    """P1: base manifest valid and checksums match bytes on disk.

    Re-runs the existing pack-validation entry point. We do not
    duplicate the checksum logic here; if a stronger pack validator
    lands, this predicate inherits the improvement.
    """
    try:
        from language_packs import compiler as pack_compiler

        loader = getattr(pack_compiler, "load_pack", None)
        if loader is None:
            return PredicateResult(
                predicate_id="P1",
                title="manifest/checksum valid",
                passed=False,
                notes="language_packs.compiler.load_pack not available",
            )
        loader(pack_id)
    except Exception as exc:  # pylint: disable=broad-except
        return PredicateResult(
            predicate_id="P1",
            title="manifest/checksum valid",
            passed=False,
            notes=f"pack load failed: {type(exc).__name__}: {exc}",
        )
    return PredicateResult(
        predicate_id="P1",
        title="manifest/checksum valid",
        passed=True,
    )


def _predicate_p2_gloss_closure(
    pack_id: str, *, data_root: Path
) -> PredicateResult:
    """P2: gloss checksum and definitional closure pass when present.

    A pack without glosses passes vacuously. A pack with glosses must
    have its declared checksum match the on-disk bytes.
    """
    pack_dir = data_root / pack_id
    glosses = pack_dir / "glosses.jsonl"
    manifest_path = pack_dir / "manifest.json"
    if not glosses.exists():
        return PredicateResult(
            predicate_id="P2",
            title="gloss/definition checksum valid",
            passed=True,
            notes="no glosses.jsonl; vacuously passes",
        )
    if not manifest_path.exists():
        return PredicateResult(
            predicate_id="P2",
            title="gloss/definition checksum valid",
            passed=False,
            notes="manifest.json missing alongside glosses",
        )
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Canonical location is the top-level ``glosses_checksum`` field
    # (in-tree packs use that form). ``checksums.glosses_sha256`` is
    # accepted as an alternate location for forward compatibility.
    declared = manifest.get("glosses_checksum") or manifest.get(
        "checksums", {}
    ).get("glosses_sha256")
    if not declared:
        return PredicateResult(
            predicate_id="P2",
            title="gloss/definition checksum valid",
            passed=True,
            notes="manifest does not declare a gloss checksum; vacuously passes",
        )
    actual = hashlib.sha256(glosses.read_bytes()).hexdigest()
    if actual != declared:
        return PredicateResult(
            predicate_id="P2",
            title="gloss/definition checksum valid",
            passed=False,
            notes=f"checksum mismatch: declared={declared[:12]}.., actual={actual[:12]}..",
        )
    return PredicateResult(
        predicate_id="P2",
        title="gloss/definition checksum valid",
        passed=True,
    )


def _predicate_p3_domain_known(contract: DomainPackContract) -> PredicateResult:
    """P3: ``domain_id`` maps to a known ledger domain."""
    if contract.domain_id in DOMAIN_PACKS:
        return PredicateResult(
            predicate_id="P3",
            title="domain_id maps to known ledger domain",
            passed=True,
        )
    return PredicateResult(
        predicate_id="P3",
        title="domain_id maps to known ledger domain",
        passed=False,
        notes=f"unknown domain_id: {contract.domain_id!r}",
    )


def _predicate_p4_chains_registered(
    contract: DomainPackContract,
) -> PredicateResult:
    """P4: every ``teaching_chains`` corpus is registered and read-only."""
    from chat.teaching_grounding import TEACHING_CORPORA

    registered_ids: set[str] = {spec.corpus_id for spec in TEACHING_CORPORA}
    # Domain capability corpora are also registered for capability purposes
    # via core.capability.domains.DOMAIN_CAPABILITY_CORPORA — extend the
    # registered set without auto-mounting them at runtime.
    from core.capability.domains import DOMAIN_CAPABILITY_CORPORA

    registered_ids |= set(DOMAIN_CAPABILITY_CORPORA.keys())

    unregistered = [c for c in contract.teaching_chains if c not in registered_ids]
    if unregistered:
        return PredicateResult(
            predicate_id="P4",
            title="teaching_chains entries registered",
            passed=False,
            notes=f"unregistered corpora: {unregistered}",
        )
    return PredicateResult(
        predicate_id="P4",
        title="teaching_chains entries registered",
        passed=True,
        notes=f"all {len(contract.teaching_chains)} corpora registered",
    )


def _predicate_p5_operator_chain_coverage(
    contract: DomainPackContract, *, chain_inv: dict[str, Any]
) -> PredicateResult:
    """P5: each claimed operator family has ≥ 8 reviewed active chains.

    Operator families are pinned per domain in
    :data:`DOMAIN_OPERATOR_CLAIMS`. Counts come from
    :func:`chain_report` which already aggregates by_domain_operator_family.
    """
    expected_ops = DOMAIN_OPERATOR_CLAIMS.get(contract.domain_id, ())
    if not expected_ops:
        return PredicateResult(
            predicate_id="P5",
            title="≥8 reviewed chains per claimed operator family",
            passed=False,
            notes=f"no operator claims registered for domain {contract.domain_id!r}",
        )
    by_op = chain_inv.get("by_domain_operator_family", {}).get(contract.domain_id, {})
    shortfalls = [
        (op, int(by_op.get(op, 0)))
        for op in expected_ops
        if int(by_op.get(op, 0)) < _MIN_CHAINS_PER_OPERATOR
    ]
    if shortfalls:
        return PredicateResult(
            predicate_id="P5",
            title="≥8 reviewed chains per claimed operator family",
            passed=False,
            notes="shortfalls: " + ", ".join(f"{op}={n}" for op, n in shortfalls),
        )
    counts = ", ".join(f"{op}={int(by_op.get(op, 0))}" for op in expected_ops)
    return PredicateResult(
        predicate_id="P5",
        title="≥8 reviewed chains per claimed operator family",
        passed=True,
        notes=counts,
    )


def _predicate_p6_intent_shapes(
    contract: DomainPackContract, *, chain_inv: dict[str, Any]
) -> PredicateResult:
    """P6: at least 3 intent shapes present before reasoning-capable."""
    by_intent = chain_inv.get("by_domain_intent_shape", {}).get(contract.domain_id, {})
    shape_count = sum(1 for v in by_intent.values() if int(v) > 0)
    if shape_count < _MIN_INTENT_SHAPES:
        return PredicateResult(
            predicate_id="P6",
            title="≥3 intent shapes present",
            passed=False,
            notes=f"only {shape_count} intent shape(s) populated",
        )
    return PredicateResult(
        predicate_id="P6",
        title="≥3 intent shapes present",
        passed=True,
        notes=f"{shape_count} intent shape(s) populated",
    )


def _predicate_p7_eval_splits(contract: DomainPackContract) -> PredicateResult:
    """P7: every ``eval_lanes`` entry has dev/public/holdout splits."""
    if not contract.eval_lanes:
        return PredicateResult(
            predicate_id="P7",
            title="eval_lanes entries cover dev/public/holdout",
            passed=False,
            notes="no eval_lanes declared",
        )
    incomplete = [
        lane.lane
        for lane in contract.eval_lanes
        if not _REQUIRED_SPLITS.issubset(set(lane.splits))
    ]
    if incomplete:
        return PredicateResult(
            predicate_id="P7",
            title="eval_lanes entries cover dev/public/holdout",
            passed=False,
            notes=f"incomplete splits on: {incomplete}",
        )
    return PredicateResult(
        predicate_id="P7",
        title="eval_lanes entries cover dev/public/holdout",
        passed=True,
        notes=f"{len(contract.eval_lanes)} lane(s) cover all required splits",
    )


def _predicate_p8_reviewers_resolve(
    contract: DomainPackContract, *, registry: ReviewerRegistry | None
) -> PredicateResult:
    """P8: every ``reviewers`` entry resolves to reviewer metadata."""
    if not contract.reviewers:
        return PredicateResult(
            predicate_id="P8",
            title="reviewers resolve via ADR-0092 registry",
            passed=False,
            notes="no reviewers declared on contract",
        )
    if registry is None:
        return PredicateResult(
            predicate_id="P8",
            title="reviewers resolve via ADR-0092 registry",
            passed=False,
            notes="reviewer registry failed to load",
        )
    unresolved: list[str] = []
    out_of_scope: list[str] = []
    for reviewer_id in contract.reviewers:
        if registry.resolve(reviewer_id) is None:
            unresolved.append(reviewer_id)
            continue
        if not registry.can_review(
            reviewer_id, domain_id=contract.domain_id, scope="pack"
        ):
            out_of_scope.append(reviewer_id)
    if unresolved or out_of_scope:
        parts: list[str] = []
        if unresolved:
            parts.append(f"unresolved: {unresolved}")
        if out_of_scope:
            parts.append(f"out_of_scope: {out_of_scope}")
        return PredicateResult(
            predicate_id="P8",
            title="reviewers resolve via ADR-0092 registry",
            passed=False,
            notes="; ".join(parts),
        )
    return PredicateResult(
        predicate_id="P8",
        title="reviewers resolve via ADR-0092 registry",
        passed=True,
        notes=f"{len(contract.reviewers)} reviewer(s) resolved",
    )


def _predicate_p9_gap_state(contract: DomainPackContract) -> PredicateResult:
    """P9: every open ``known_gaps`` entry blocks promotion."""
    if not contract.known_gaps:
        return PredicateResult(
            predicate_id="P9",
            title="no open known_gaps block promotion",
            passed=True,
            notes="no gaps referenced on contract",
        )
    gaps_path = _REPO_ROOT / LEDGER_SOURCES.gaps
    if not gaps_path.exists():
        return PredicateResult(
            predicate_id="P9",
            title="no open known_gaps block promotion",
            passed=False,
            notes="docs/gaps.md not found",
        )
    gap_state = _parse_gap_states(gaps_path.read_text(encoding="utf-8"))
    open_gaps = [g for g in contract.known_gaps if not gap_state.get(g, False)]
    if open_gaps:
        return PredicateResult(
            predicate_id="P9",
            title="no open known_gaps block promotion",
            passed=False,
            notes=f"open: {open_gaps}",
        )
    return PredicateResult(
        predicate_id="P9",
        title="no open known_gaps block promotion",
        passed=True,
        notes=f"{len(contract.known_gaps)} gap(s) all closed",
    )


_GAP_LINE_RE = re.compile(r"^- \[(?P<mark>[ x])\] `(?P<gap_id>gap:[^`]+)`")


def _parse_gap_states(text: str) -> dict[str, bool]:
    """Return ``{gap_id: closed?}`` parsed from gaps.md markdown."""
    result: dict[str, bool] = {}
    for line in text.splitlines():
        match = _GAP_LINE_RE.match(line.strip())
        if match:
            result[match.group("gap_id")] = match.group("mark") == "x"
    return result


# ---------------------------------------------------------------------------
# Eval lane artifact resolution (ADR-0093 item 4)
# ---------------------------------------------------------------------------


def _resolve_eval_lane_artifacts(
    contract: DomainPackContract,
) -> tuple[dict[str, Any], ...]:
    """For each declared eval lane, surface the most recent report SHA per split."""
    results: list[dict[str, Any]] = []
    for lane in contract.eval_lanes:
        lane_dir = _REPO_ROOT / "evals" / lane.lane / "results"
        entry: dict[str, Any] = {
            "lane": lane.lane,
            "version": lane.version,
            "splits": {},
        }
        for split in lane.splits:
            candidate = lane_dir / f"{lane.version}_{split}.json"
            if candidate.exists():
                entry["splits"][split] = {
                    "path": str(candidate.relative_to(_REPO_ROOT)),
                    "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    "exists": True,
                }
            else:
                entry["splits"][split] = {
                    "path": str(candidate.relative_to(_REPO_ROOT)),
                    "sha256": None,
                    "exists": False,
                }
        results.append(entry)
    return tuple(results)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_domain_contract(
    pack_id: str,
    *,
    data_root: Path | None = None,
    chain_inventory: dict[str, Any] | None = None,
    reviewer_registry: ReviewerRegistry | None = None,
) -> DomainContractPredicateReport:
    """Run all nine ADR-0091 predicates against ``pack_id``.

    Returns a structured report. Never raises on predicate failure —
    failures are recorded in :attr:`PredicateResult.passed`. Reads only;
    no pack mutation.

    Optional injection points:

    - ``data_root`` overrides the language-pack data directory (used by
      tests to point at a synthetic pack tree).
    - ``chain_inventory`` injects a pre-computed chain report (avoids
      re-running it across many packs in a single ledger pass).
    - ``reviewer_registry`` injects a parsed registry (avoids re-loading
      from disk per pack).
    """
    root = data_root or (_REPO_ROOT / "language_packs" / "data")

    validation: DomainContractValidation = validate_domain_contract_pack(
        pack_id, data_root=root
    )

    if not validation.present:
        return DomainContractPredicateReport(
            pack_id=pack_id,
            domain_id="",
            contract_present=False,
            contract_valid=validation.valid,
            contract_errors=validation.errors,
            predicates=(),
            eval_lane_artifacts=(),
        )

    contract = validation.contract
    assert contract is not None  # narrowed by present=True

    if not validation.valid:
        return DomainContractPredicateReport(
            pack_id=pack_id,
            domain_id=contract.domain_id,
            contract_present=True,
            contract_valid=False,
            contract_errors=validation.errors,
            predicates=(),
            eval_lane_artifacts=(),
        )

    inv = chain_inventory if chain_inventory is not None else chain_report()
    registry = reviewer_registry
    if registry is None:
        try:
            registry = load_reviewer_registry(
                _REPO_ROOT / LEDGER_SOURCES.reviewers
            )
        except ReviewerRegistryError:
            registry = None

    predicates: tuple[PredicateResult, ...] = (
        _predicate_p1_manifest_valid(pack_id, data_root=root),
        _predicate_p2_gloss_closure(pack_id, data_root=root),
        _predicate_p3_domain_known(contract),
        _predicate_p4_chains_registered(contract),
        _predicate_p5_operator_chain_coverage(contract, chain_inv=inv),
        _predicate_p6_intent_shapes(contract, chain_inv=inv),
        _predicate_p7_eval_splits(contract),
        _predicate_p8_reviewers_resolve(contract, registry=registry),
        _predicate_p9_gap_state(contract),
    )

    artifacts = _resolve_eval_lane_artifacts(contract)

    return DomainContractPredicateReport(
        pack_id=pack_id,
        domain_id=contract.domain_id,
        contract_present=True,
        contract_valid=True,
        contract_errors=(),
        predicates=predicates,
        eval_lane_artifacts=artifacts,
    )
