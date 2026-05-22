"""Domain-aware expert-demo promotion gate (ADR-0106).

Replaces the cognition-lane-only predicate previously embedded in
``core.capability.reporting``. A domain ``D`` is promoted to
``expert_demo=true`` iff:

1. ``D`` already passes the ``reasoning_capable`` predicate.
2. A signed ``ExpertDemoClaim`` exists in the reviewer registry for ``D``.
3. The reviewer named in ``claim.signed_by`` may review evals for ``D``
   (ADR-0092 ``can_review`` check, scope ``"eval"``).
4. Every lane listed in ``claim.evidence_lanes`` is attached to at least
   one of ``D``'s ratified packs (no cross-domain bleed).
5. Every named lane's threshold metrics meet the ADR-0106 §1 bar on both
   ``public`` and ``holdout``.
6. The canonical evidence-bundle digest reproduces ``claim.claim_digest``
   byte-for-byte.

Any failure leaves the ledger row at ``reasoning-capable``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.capability.reviewers import ReviewerRegistry

_LaneResults = Mapping[str, Mapping[str, Mapping[str, Any]]]


SURFACE_GROUNDEDNESS_MIN: float = 0.95
TERM_CAPTURE_RATE_MIN: float = 0.85
INTENT_ACCURACY_MIN: float = 0.95
VERSOR_CLOSURE_RATE_MIN: float = 1.0
FABRICATION_PASSED_MIN: float = 1.0

FABRICATION_CONTROL_LANE: str = "fabrication_control"


@dataclass(frozen=True, slots=True)
class ExpertDemoVerdict:
    passed: bool
    reason: str
    derived_digest: str | None


def derive_evidence_digest(
    domain_id: str,
    evidence_revision: str,
    evidence_lanes: Sequence[str],
    lane_results: _LaneResults,
) -> str:
    """Compute the canonical evidence-bundle SHA-256.

    ``lane_results`` maps ``lane_id -> split -> result_dict`` where the
    result_dict is the raw JSON ``metrics`` block from
    ``evals/<lane>/results/v1_<split>.json``.

    The bundle is deterministic in field order (sorted keys, compact
    separators) so re-derivation reproduces the digest byte-for-byte.
    """
    sorted_lanes = sorted(evidence_lanes)
    bundle = {
        "domain_id": domain_id,
        "evidence_revision": evidence_revision,
        "evidence_lanes": sorted_lanes,
        "lane_metrics": {
            lane: {
                "public": dict(lane_results.get(lane, {}).get("public", {})),
                "holdout": dict(lane_results.get(lane, {}).get("holdout", {})),
            }
            for lane in sorted_lanes
        },
    }
    body = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _meets_thresholds(lane_id: str, metrics: Mapping[str, Any]) -> tuple[bool, str]:
    if lane_id == FABRICATION_CONTROL_LANE:
        passed = float(metrics.get("passed_rate", metrics.get("accuracy", 0)) or 0)
        if passed < FABRICATION_PASSED_MIN:
            return False, (
                f"lane {lane_id!r} passed_rate={passed} below "
                f"threshold {FABRICATION_PASSED_MIN}"
            )
        return True, ""
    checks = (
        ("surface_groundedness", SURFACE_GROUNDEDNESS_MIN),
        ("term_capture_rate", TERM_CAPTURE_RATE_MIN),
        ("intent_accuracy", INTENT_ACCURACY_MIN),
        ("versor_closure_rate", VERSOR_CLOSURE_RATE_MIN),
    )
    for key, minimum in checks:
        if key not in metrics:
            return False, (
                f"lane {lane_id!r} missing required metric {key!r}"
            )
        value = float(metrics[key] or 0)
        if value < minimum:
            return False, (
                f"lane {lane_id!r} {key}={value} below threshold {minimum}"
            )
    return True, ""


def evaluate_expert_demo(
    *,
    domain_id: str,
    reasoning_capable: bool,
    registry: ReviewerRegistry,
    domain_lanes: Sequence[str],
    lane_results: Mapping[str, Mapping[str, Mapping[str, object]]],
) -> ExpertDemoVerdict:
    """Decide whether ``domain_id`` may carry ``expert_demo=true``.

    ``domain_lanes`` is the union of ``eval_lanes`` declared by the
    ratified packs for ``domain_id`` — the only lanes legal as evidence
    sources for this promotion.

    ``lane_results`` is the materialised per-split metrics; the caller
    is responsible for resolving each lane id to its on-disk result.
    """
    if not reasoning_capable:
        return ExpertDemoVerdict(
            passed=False,
            reason="domain not yet reasoning-capable",
            derived_digest=None,
        )

    claim = registry.expert_demo_claim_for(domain_id)
    if claim is None:
        return ExpertDemoVerdict(
            passed=False,
            reason="no expert_demo_claims entry for this domain",
            derived_digest=None,
        )

    if not registry.can_review(claim.signed_by, domain_id=domain_id, scope="eval"):
        return ExpertDemoVerdict(
            passed=False,
            reason=(
                f"signer {claim.signed_by!r} cannot review eval-scope "
                f"artifacts for domain {domain_id!r}"
            ),
            derived_digest=None,
        )

    domain_lane_set = set(domain_lanes)
    cross_domain = [
        lane for lane in claim.evidence_lanes if lane not in domain_lane_set
    ]
    if cross_domain:
        return ExpertDemoVerdict(
            passed=False,
            reason=(
                f"claim cites lanes not attached to domain {domain_id!r}: "
                f"{sorted(cross_domain)}"
            ),
            derived_digest=None,
        )

    for lane_id in claim.evidence_lanes:
        for split in ("public", "holdout"):
            metrics = lane_results.get(lane_id, {}).get(split)
            if not metrics:
                return ExpertDemoVerdict(
                    passed=False,
                    reason=(
                        f"lane {lane_id!r} split {split!r} has no results"
                    ),
                    derived_digest=None,
                )
            ok, why = _meets_thresholds(lane_id, metrics)
            if not ok:
                return ExpertDemoVerdict(
                    passed=False,
                    reason=f"{why} (split={split})",
                    derived_digest=None,
                )

    derived = derive_evidence_digest(
        domain_id=domain_id,
        evidence_revision=claim.evidence_revision,
        evidence_lanes=claim.evidence_lanes,
        lane_results=lane_results,
    )
    if derived != claim.claim_digest:
        return ExpertDemoVerdict(
            passed=False,
            reason=(
                "evidence-bundle digest does not match claim_digest "
                "(replay drift)"
            ),
            derived_digest=derived,
        )

    return ExpertDemoVerdict(
        passed=True,
        reason="all expert-demo predicates satisfied",
        derived_digest=derived,
    )


def collect_domain_lanes(
    pack_manifests: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Return the union of ``eval_lanes[].lane`` across pack manifests."""
    lanes: list[str] = []
    seen: set[str] = set()
    for manifest in pack_manifests:
        entries = manifest.get("eval_lanes") or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            lane_id = entry.get("lane")
            if isinstance(lane_id, str) and lane_id not in seen:
                seen.add(lane_id)
                lanes.append(lane_id)
    return tuple(lanes)


def materialise_lane_results(
    lane_ids: Sequence[str],
    *,
    fetch_split: Callable[[str, str], Mapping[str, Any]],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    """Materialise ``lane -> split -> metrics`` for the named lanes.

    ``fetch_split(lane_id, split)`` returns the parsed ``metrics``
    sub-dict from the latest result file (or ``{}`` if absent).
    """
    out: dict[str, dict[str, Mapping[str, object]]] = {}
    for lane_id in lane_ids:
        out[lane_id] = {
            "public": dict(fetch_split(lane_id, "public") or {}),
            "holdout": dict(fetch_split(lane_id, "holdout") or {}),
        }
    return out
