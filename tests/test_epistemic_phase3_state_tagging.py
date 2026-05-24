from __future__ import annotations

import numpy as np

from chat.telemetry import serialize_turn_event
from core.epistemic_state import EpistemicState, NormativeClearance
from core.physics.identity import TurnEvent
from language_packs.compiler import compile_entries_to_manifold
from language_packs.loader import lookup_unit
from language_packs.schema import LexicalEntry
from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore, epistemic_state_for_vault_status


def test_turn_event_telemetry_serializes_state_axes() -> None:
    event = TurnEvent(
        turn=7,
        input_tokens=("truth",),
        surface="Truth is grounded.",
        walk_surface="Truth is grounded.",
        articulation_surface="Truth is grounded.",
        dialogue_role="assert",
        identity_score=None,
        cycle_cost_total=0.0,
        vault_hits=1,
        versor_condition=0.0,
        flagged=False,
        grounding_source="pack",
        epistemic_state=EpistemicState.DECODED.value,
        normative_clearance=NormativeClearance.CLEARED.value,
        normative_detail="all runtime-checkable verdicts upheld",
    )

    payload = serialize_turn_event(event)

    assert payload["epistemic_state"] == "decoded"
    assert payload["normative_clearance"] == "cleared"
    assert payload["normative_detail"] == "all runtime-checkable verdicts upheld"


def test_lookup_unit_tags_curated_and_composed_entries() -> None:
    curated = lookup_unit("dollar")
    # "euro per hour" is not a curated lexicon entry; it is dynamically
    # composed from decoded primitives (euro × hour) by the per-unit rule.
    inferred = lookup_unit("euro per hour")

    assert curated is not None
    assert curated.epistemic_state == EpistemicState.DECODED.value
    assert inferred is not None
    assert inferred.epistemic_state == EpistemicState.INFERRED.value


def test_compile_entries_to_manifold_preserves_entry_status_mapping() -> None:
    entries = [
        LexicalEntry(
            entry_id="coherent-1",
            surface="alpha",
            lemma="alpha",
            language="en",
            semantic_domains=("test.domain",),
            provenance_ids=("fixture",),
            epistemic_status="coherent",
        ),
        LexicalEntry(
            entry_id="speculative-1",
            surface="beta",
            lemma="beta",
            language="en",
            semantic_domains=("test.domain",),
            provenance_ids=("fixture",),
            epistemic_status="speculative",
        ),
        LexicalEntry(
            entry_id="falsified-1",
            surface="gamma",
            lemma="gamma",
            language="en",
            semantic_domains=("test.domain",),
            provenance_ids=("fixture",),
            epistemic_status="falsified",
        ),
    ]

    manifold, _ = compile_entries_to_manifold(entries)

    assert manifold.epistemic_state_for_word("alpha") == EpistemicState.DECODED.value
    assert manifold.epistemic_state_for_word("beta") == EpistemicState.UNVERIFIED_POSSIBLE.value
    assert manifold.epistemic_state_for_word("gamma") == EpistemicState.CONTRADICTED.value


def test_vault_statuses_map_to_distinct_epistemic_states() -> None:
    assert epistemic_state_for_vault_status(EpistemicStatus.COHERENT) is EpistemicState.DECODED
    assert epistemic_state_for_vault_status(EpistemicStatus.FALSIFIED) is EpistemicState.CONTRADICTED
    assert epistemic_state_for_vault_status(EpistemicStatus.SPECULATIVE) is EpistemicState.UNVERIFIED_POSSIBLE
    assert epistemic_state_for_vault_status(EpistemicStatus.CONTESTED) is EpistemicState.AMBIGUOUS


def test_vault_recall_exposes_epistemic_state_metadata() -> None:
    vault = VaultStore(reproject_interval=0)
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0

    vault.store(v, epistemic_status=EpistemicStatus.FALSIFIED)

    hits = vault.recall(v, top_k=1)

    assert len(hits) == 1
    assert hits[0]["epistemic_state"] == EpistemicState.CONTRADICTED.value
    assert hits[0]["metadata"]["epistemic_state"] == EpistemicState.CONTRADICTED.value


def test_refusal_reason_materialized_in_cognitive_turn_result() -> None:
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig
    from core.cognition import CognitiveTurnPipeline
    from chat.refusal import TYPED_REFUSAL_PREFIX
    from packs.safety.check import SafetyCheckResult
    from core.cognition.trace import trace_hash_from_result
    import dataclasses

    runtime = ChatRuntime(config=RuntimeConfig())
    pipeline = CognitiveTurnPipeline(runtime)

    # 1. Normal turn: refusal_reason must be empty
    result_normal = pipeline.run("light logos", max_tokens=8)
    assert result_normal.refusal_reason == ""
    normal_hash = result_normal.trace_hash

    # 2. Force safety violation to trigger refusal
    boundary_id = "preserve_versor_closure"
    def _failing(ctx) -> SafetyCheckResult:
        return SafetyCheckResult(
            boundary_id=boundary_id,
            upheld=False,
            reason="forced for test",
            runtime_checkable=True,
        )

    runtime.safety_check.register(boundary_id, _failing)

    # 3. Refusal turn: refusal_reason must be populated
    result_refusal = pipeline.run("light logos", max_tokens=8)
    refusal_reason = result_refusal.refusal_reason
    assert refusal_reason != ""
    assert refusal_reason.startswith(TYPED_REFUSAL_PREFIX)
    assert boundary_id in refusal_reason

    # 4. Check trace hash is different due to refusal_reason fold
    refusal_hash = result_refusal.trace_hash
    assert refusal_hash != normal_hash

    # 5. Verify trace hashing conditional fold explicitly
    # If we compute the trace hash from a modified result with empty refusal_reason,
    # it must differ from the refusal_hash.
    modified_result = dataclasses.replace(result_refusal, refusal_reason="")
    recomputed_without_reason = trace_hash_from_result(modified_result)
    assert recomputed_without_reason != refusal_hash

