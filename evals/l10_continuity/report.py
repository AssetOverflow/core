"""Assemble the L10 continuity panel into a structured, freeze-gateable report.

The panel runs the soaks the predicates need (an uninterrupted baseline, a
reboot leg, and two crash-recoveries), evaluates every predicate, and emits a
structured report with per-predicate PASS/FAIL, metrics, the explicitly
*not-covered* legs (no silent skips — CLAUDE.md), and a **deterministic digest**.

The digest is a SHA-256 over only the hardware-stable evidence: the canonical
``trace_hash`` sequence (``core.cognition.trace`` already rounds floats so the
hash is stable across hardware) and each predicate's ``(name, passed)`` verdict.
It deliberately EXCLUDES RSS, wall-clock, and raw float metrics, which are not
reproducible across machines. The digest is the freeze handle: pin it once the
lane is trusted and a regression flips it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import RuntimeConfig

from evals.l10_continuity.predicates import (
    PredicateOutcome,
    evaluate_p1_closure,
    evaluate_p2a_determinism,
    evaluate_p2b_reboot_transparency,
    evaluate_p3_bounded_resources,
    evaluate_p4_commit_point,
    evaluate_p4_recovery_determinism,
    evaluate_p5b_anchor_stability,
    evaluate_p5c_coherence,
)
from evals.l10_continuity.runner import (
    SoakResult,
    _inject_orphan_tmp,
    read_recovered_turn_count,
    run_soak,
)

# Legs the spec names but this lane does not yet cover, recorded explicitly so a
# PASS is never read as "everything was checked".
NOT_COVERED: tuple[tuple[str, str], ...] = (
    (
        "P5a_recall_stability",
        "recall precision@k over a held-out probe set requires a probe set with "
        "known-relevant entries and a metric grounded in the vault's scoring "
        "semantics (the raw recall score is not a clean similarity); deferred.",
    ),
)


@dataclass(frozen=True)
class L10ContinuityReport:
    n_turns: int
    reboot_turn: int
    predicates: tuple[PredicateOutcome, ...]
    not_covered: tuple[tuple[str, str], ...]
    deterministic_digest: str

    def all_gates_pass(self) -> bool:
        return all(p.passed for p in self.predicates)

    def to_dict(self) -> dict:
        return {
            "n_turns": self.n_turns,
            "reboot_turn": self.reboot_turn,
            "all_gates_pass": self.all_gates_pass(),
            "deterministic_digest": self.deterministic_digest,
            "predicates": [asdict(p) for p in self.predicates],
            "not_covered": [
                {"leg": leg, "reason": reason} for leg, reason in self.not_covered
            ],
        }


def deterministic_digest(
    baseline: SoakResult, predicates: tuple[PredicateOutcome, ...]
) -> str:
    """SHA-256 over hardware-stable evidence: trace_hash sequence + verdicts."""
    payload = {
        "trace_hashes": list(baseline.trace_hashes()),
        "verdicts": [[p.name, p.passed] for p in predicates],
        "not_covered": [leg for leg, _ in NOT_COVERED],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_report(
    *,
    n_turns: int = 12,
    reboot_turn: int = 3,
    engine_state_root: Path,
    config: RuntimeConfig | None = None,
) -> L10ContinuityReport:
    """Run the full panel and assemble the report.

    Soaks: an uninterrupted ``baseline``; a second independent ``run_b`` (P2a);
    a ``reboot`` leg (P2b); and two orphan-crash recoveries (P4).
    """
    config = config or RuntimeConfig()
    root = engine_state_root

    baseline = run_soak(n_turns, engine_state_dir=root / "baseline", config=config)
    run_b = run_soak(n_turns, engine_state_dir=root / "run_b", config=config)
    reboot = run_soak(
        n_turns, engine_state_dir=root / "reboot", reboot_at=(reboot_turn,), config=config
    )
    rec_a = run_soak(
        n_turns,
        engine_state_dir=root / "rec_a",
        reboot_at=(reboot_turn,),
        inject_orphan_tmp_at_reboot=True,
        config=config,
    )
    rec_b = run_soak(
        n_turns,
        engine_state_dir=root / "rec_b",
        reboot_at=(reboot_turn,),
        inject_orphan_tmp_at_reboot=True,
        config=config,
    )
    # Commit-point probe: run exactly ``reboot_turn`` turns, simulate the torn
    # write, and read the recovered turn_count AT the crash boundary (not after
    # the recovery continues and re-checkpoints).
    probe_dir = root / "commit_probe"
    run_soak(reboot_turn, engine_state_dir=probe_dir, config=config)
    _inject_orphan_tmp(probe_dir)
    recovered = read_recovered_turn_count(probe_dir)

    p2b_outcome, _ = evaluate_p2b_reboot_transparency(reboot, baseline)
    predicates: tuple[PredicateOutcome, ...] = (
        evaluate_p1_closure(baseline),
        evaluate_p2a_determinism(baseline, run_b),
        p2b_outcome,
        evaluate_p3_bounded_resources(baseline),
        evaluate_p4_recovery_determinism(rec_a, rec_b),
        evaluate_p4_commit_point(recovered, expected_turn_count=reboot_turn),
        evaluate_p5b_anchor_stability(baseline),
        evaluate_p5c_coherence(baseline),
    )
    digest = deterministic_digest(baseline, predicates)
    return L10ContinuityReport(
        n_turns=n_turns,
        reboot_turn=reboot_turn,
        predicates=predicates,
        not_covered=NOT_COVERED,
        deterministic_digest=digest,
    )
