"""
Lab Eval: Vault EpistemicStatus Lifecycle Trace

Traces the full EpistemicStatus lifecycle across a simulated session:

  Phase 1 — Writes: every store() call records status, turn, role
  Phase 2 — Recall tiers: compares min_status=None vs min_status=COHERENT
             to show which entries are visible at each tier
  Phase 3 — Promotion: shows that a promoted entry (with_status(COHERENT))
             appears in COHERENT-filtered recall; un-promoted entries don't
  Phase 4 — Contamination isolation proof: SPECULATIVE benchmark/test
             writes never appear in COHERENT-filtered recall

This is the structural argument for why per-session non-persistent vaults
preserve the integrity of the pack geometry — and why this is deliberate
design, not a missing feature.

Outputs JSON to stdout.  Exits 0.

To run:
    python -m evals.lab.vault_epistemic_trace
"""

from __future__ import annotations

import json
import sys

import numpy as np


def _random_versor(seed: int) -> np.ndarray:
    from algebra.versor import unitize_versor
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal(32).astype(np.float32)
    return unitize_versor(raw)


def run() -> dict:
    from vault.store import VaultStore
    from teaching.epistemic import EpistemicStatus

    vault = VaultStore()
    write_log = []

    # Phase 1: simulate a session — user + assistant turns (SPECULATIVE)
    # interspersed with benchmark writes (also SPECULATIVE)
    session_versors = [_random_versor(i) for i in range(6)]
    for i, v in enumerate(session_versors):
        role = "user" if i % 2 == 0 else "assistant"
        idx = vault.store(v, {"turn": i // 2, "role": role}, epistemic_status=EpistemicStatus.SPECULATIVE)
        write_log.append({"index": idx, "role": role, "status": "speculative", "source": "session"})

    # Simulate benchmark writes — same SPECULATIVE tier
    bench_versors = [_random_versor(100 + i) for i in range(3)]
    for i, v in enumerate(bench_versors):
        idx = vault.store(v, {"turn": -1, "role": "benchmark"}, epistemic_status=EpistemicStatus.SPECULATIVE)
        write_log.append({"index": idx, "role": "benchmark", "status": "speculative", "source": "benchmark"})

    total_entries = len(vault)

    # Phase 2: recall tier comparison — query with one of the session versors
    query = session_versors[0]
    hits_unfiltered = vault.recall(query, top_k=10, min_status=None)
    hits_coherent_filtered = vault.recall(query, top_k=10, min_status=EpistemicStatus.COHERENT)

    tier_comparison = {
        "unfiltered_count": len(hits_unfiltered),
        "coherent_filtered_count": len(hits_coherent_filtered),
        "all_entries_visible_unfiltered": len(hits_unfiltered) == min(10, total_entries),
        "nothing_visible_coherent_before_promotion": len(hits_coherent_filtered) == 0,
    }

    # Phase 3: promote one entry to COHERENT and re-query
    # (simulates curator ratification of a teaching proposal)
    # We re-store the same versor with COHERENT status (immutable store —
    # promotion is a new store, not a mutation)
    promoted_v = session_versors[2]
    vault.store(
        promoted_v,
        {"turn": 1, "role": "assistant", "ratified": True},
        epistemic_status=EpistemicStatus.COHERENT,
    )
    hits_after_promotion = vault.recall(query, top_k=10, min_status=EpistemicStatus.COHERENT)
    promotion_result = {
        "coherent_entries_after_promotion": len(hits_after_promotion),
        "promotion_visible": len(hits_after_promotion) > 0,
        "only_ratified_visible": all(
            h["metadata"].get("epistemic_status") == "coherent"
            for h in hits_after_promotion
        ),
    }

    # Phase 4: contamination isolation proof
    # Benchmark versors are SPECULATIVE — they must NEVER appear in COHERENT recall
    bench_query = bench_versors[0]
    bench_hits_coherent = vault.recall(bench_query, top_k=10, min_status=EpistemicStatus.COHERENT)
    contamination_proof = {
        "benchmark_entries_in_coherent_recall": sum(
            1 for h in bench_hits_coherent
            if h["metadata"].get("role") == "benchmark"
        ),
        "contamination_isolated": not any(
            h["metadata"].get("role") == "benchmark"
            for h in bench_hits_coherent
        ),
        "explanation": (
            "Per-session non-persistent vault + SPECULATIVE default ensures "
            "benchmark/test writes never contaminate COHERENT-tier inference. "
            "This is deliberate design: packs carry the durable geometry; "
            "the vault carries ephemeral session context."
        ),
    }

    return {
        "eval": "vault_epistemic_trace",
        "total_entries_written": total_entries,
        "write_log": write_log,
        "phase_2_tier_comparison": tier_comparison,
        "phase_3_promotion": promotion_result,
        "phase_4_contamination_isolation": contamination_proof,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    sys.exit(0)
