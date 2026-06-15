"""Assemble the L10 always-on heartbeat panel into a freeze-gateable report.

The panel runs the soaks the predicates need (an uninterrupted idle baseline for H1/H2/H3
and a reboot leg for H4), evaluates every predicate, and emits a structured report with
per-predicate PASS/FAIL, metrics, the explicitly *not-covered* legs (no silent skips —
CLAUDE.md), and a **deterministic digest**.

The digest is a SHA-256 over only the hardware-stable evidence: the per-beat SHAPE
(``did_work`` / ``field_valid`` / learning counts / vault size — all deterministic ints &
bools) and each predicate's ``(name, passed)`` verdict. It deliberately EXCLUDES the raw
``versor_condition`` float (machine-variant; only the ``field_valid`` comparison against the
ceiling is stable). Pin the digest once the lane is trusted and a regression flips it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import RuntimeConfig

from evals.l10_always_on.predicates import (
    PredicateOutcome,
    evaluate_h1_closure,
    evaluate_h2_bounded_idle,
    evaluate_h3_convergence,
    evaluate_h4_reboot_resume,
)
from evals.l10_always_on.runner import HeartbeatSoakResult, run_heartbeat_soak

# Legs this lane does NOT cover, recorded so a PASS is never read as "everything checked".
NOT_COVERED: tuple[tuple[str, str], ...] = (
    (
        "H5_learning_life_resource_cost",
        "This lane proves the IDLE (converged) life is resource-bounded. The cost of a "
        "continuously-LEARNING life under a sustained NEW-fact stream (the full-snapshot "
        "checkpoint is O(n^2) in facts; lived_life.json is per-run) is out of scope until "
        "an afferent/intake feed and incremental persistence exist; deferred.",
    ),
)


@dataclass(frozen=True)
class L10AlwaysOnReport:
    n_beats: int
    reboot_beat: int
    predicates: tuple[PredicateOutcome, ...]
    not_covered: tuple[tuple[str, str], ...]
    deterministic_digest: str

    def all_gates_pass(self) -> bool:
        return all(p.passed for p in self.predicates)

    def to_dict(self) -> dict:
        return {
            "n_beats": self.n_beats,
            "reboot_beat": self.reboot_beat,
            "all_gates_pass": self.all_gates_pass(),
            "deterministic_digest": self.deterministic_digest,
            "predicates": [asdict(p) for p in self.predicates],
            "not_covered": [{"leg": leg, "reason": reason} for leg, reason in self.not_covered],
        }


def deterministic_digest(
    baseline: HeartbeatSoakResult, predicates: tuple[PredicateOutcome, ...]
) -> str:
    """SHA-256 over hardware-stable evidence: the per-beat shape + the verdicts."""
    payload = {
        "beat_shape": [
            [r.did_work, r.field_valid, r.facts_consolidated, r.proposals_created, r.vault_size]
            for r in baseline.records
        ],
        "verdicts": [[p.name, p.passed] for p in predicates],
        "not_covered": [leg for leg, _ in NOT_COVERED],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_report(
    *,
    n_beats: int = 24,
    reboot_beat: int = 12,
    engine_state_root: Path,
    config: RuntimeConfig | None = None,
) -> L10AlwaysOnReport:
    """Run the full idle panel and assemble the report.

    Soaks: an uninterrupted idle ``baseline`` (H1/H2/H3) and a ``reboot`` leg (H4)."""
    root = engine_state_root
    baseline = run_heartbeat_soak(n_beats, engine_state_dir=root / "baseline", config=config)
    reboot = run_heartbeat_soak(
        n_beats, engine_state_dir=root / "reboot", reboot_at=(reboot_beat,), config=config
    )
    predicates: tuple[PredicateOutcome, ...] = (
        evaluate_h1_closure(baseline),
        evaluate_h2_bounded_idle(baseline),
        evaluate_h3_convergence(baseline),
        evaluate_h4_reboot_resume(reboot),
    )
    return L10AlwaysOnReport(
        n_beats=n_beats,
        reboot_beat=reboot_beat,
        predicates=predicates,
        not_covered=NOT_COVERED,
        deterministic_digest=deterministic_digest(baseline, predicates),
    )
