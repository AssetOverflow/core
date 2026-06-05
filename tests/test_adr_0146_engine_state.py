from __future__ import annotations

import json

import pytest

from chat.runtime import ChatRuntime
from engine_state import EngineStateStore
from recognition.anti_unifier import Constant, DerivedRecognizer, TypedSlot
from recognition.registry import RecognizerRegistry
from teaching.discovery import DiscoveryCandidate, EvidencePointer, SubQuestion


def _recognizer(teaching_set_id: str = "set-1") -> DerivedRecognizer:
    return DerivedRecognizer(
        pattern=(
            Constant("light"),
            TypedSlot(
                feature_name="object",
                slot_type="noun",
                min_width=1,
                max_width=2,
                ignored_prefix_tokens=("the",),
            ),
        ),
        teaching_set_id=teaching_set_id,
        constant_features={"intent": "definition"},
        absent_features={"negated": 0},
    )


def _candidate() -> DiscoveryCandidate:
    evidence = EvidencePointer(
        source="pack",
        ref="en_core_cognition_v1:light",
        polarity="affirms",
        epistemic_status="ratified",
    )
    sub_question = SubQuestion(
        sub_id="sub-1",
        proposed_subject="light",
        proposed_intent="verification",
        outcome="grounded",
        evidence=(evidence,),
    )
    return DiscoveryCandidate(
        candidate_id="candidate-1",
        proposed_chain={"subject": "light", "intent": "verification"},
        trigger="would_have_grounded",
        source_turn_trace="trace-1",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(evidence,),
        sub_questions=(sub_question,),
        contemplation_depth=1,
    )


def test_engine_state_store_round_trips_recognizers(tmp_path) -> None:
    store = EngineStateStore(tmp_path)
    recognizer = _recognizer()

    store.save_recognizers([recognizer])

    assert store.load_recognizers() == [recognizer]


def test_engine_state_store_round_trips_empty(tmp_path) -> None:
    store = EngineStateStore(tmp_path)

    store.save_recognizers([])
    store.save_discovery_candidates([])

    assert store.load_recognizers() == []
    assert store.load_discovery_candidates() == []
    assert (tmp_path / "recognizers.jsonl").read_text(encoding="utf-8") == ""
    assert (tmp_path / "discovery_candidates.jsonl").read_text(encoding="utf-8") == ""


def test_engine_state_store_manifest_written(tmp_path) -> None:
    store = EngineStateStore(tmp_path)

    store.save_manifest(turn_count=7)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["turn_count"] == 7
    assert isinstance(manifest["written_at_revision"], str)


def test_recognizer_registry_register_and_get() -> None:
    registry = RecognizerRegistry()
    recognizer = _recognizer()

    registry.register(recognizer)

    assert len(registry) == 1
    assert registry.get("set-1") == recognizer
    assert registry.get("missing") is None
    assert registry.all() == [recognizer]


def test_recognizer_registry_from_recognizers() -> None:
    first = _recognizer("set-1")
    second = _recognizer("set-2")

    registry = RecognizerRegistry.from_recognizers([first, second])

    assert len(registry) == 2
    assert registry.get("set-1") == first
    assert registry.get("set-2") == second


def test_chat_runtime_creates_store_by_default(tmp_path) -> None:
    runtime = ChatRuntime(engine_state_path=tmp_path)

    assert runtime._engine_state_store is not None
    assert runtime._engine_state_store.path == tmp_path
    assert len(runtime._recognizer_registry) == 0


def test_chat_runtime_no_load_state_skips_load(tmp_path) -> None:
    store = EngineStateStore(tmp_path)
    store.save_recognizers([_recognizer()])
    store.save_manifest(turn_count=3)

    runtime = ChatRuntime(no_load_state=True, engine_state_path=tmp_path)

    assert runtime._engine_state_store is None
    assert len(runtime._recognizer_registry) == 0
    assert runtime._turn_count == 0


def test_discovery_candidate_from_dict_round_trips() -> None:
    candidate = _candidate()

    roundtrip = DiscoveryCandidate.from_dict(candidate.as_dict())

    assert roundtrip == candidate


# --- ADR-0146 byte-stability + store-path coverage (added 2026-06-05) ----------
# The round-trip tests above prove OBJECT equality. The cross-reboot identity the
# telos needs (the shelved EngineIdentity content-hash) additionally requires the
# on-disk serialization to be IDEMPOTENT (save->load->save reproduces the bytes)
# and DETERMINISTIC (same logical state -> same bytes across independent stores).
# These lock that. They are deliberately NOT golden-format pins: a *deterministic*
# format change is harmless for a content hash (it changes consistently), so the
# real hazards are non-idempotence, run-to-run nondeterminism, and a broken store
# path -- not the exact byte layout (which must stay free to evolve under a
# versioned schema, lest every legitimate field-add become a death-and-rebirth).


def test_recognizers_save_load_save_is_idempotent(tmp_path) -> None:
    store = EngineStateStore(tmp_path)
    recs = [_recognizer("set-1"), _recognizer("set-2")]

    store.save_recognizers(recs)
    first = (tmp_path / "recognizers.jsonl").read_bytes()
    store.save_recognizers(store.load_recognizers())

    assert (tmp_path / "recognizers.jsonl").read_bytes() == first


def test_recognizers_save_is_deterministic_across_instances(tmp_path) -> None:
    recs = [_recognizer("set-1"), _recognizer("set-2")]

    EngineStateStore(tmp_path / "a").save_recognizers(recs)
    EngineStateStore(tmp_path / "b").save_recognizers(recs)

    assert (
        (tmp_path / "a" / "recognizers.jsonl").read_bytes()
        == (tmp_path / "b" / "recognizers.jsonl").read_bytes()
    )


def test_discovery_store_round_trips_nonempty_candidate(tmp_path) -> None:
    # The only existing non-empty discovery test bypasses EngineStateStore
    # (as_dict -> from_dict in memory); this exercises the STORE's save+load
    # path for a non-empty candidate, which was previously untested.
    store = EngineStateStore(tmp_path)
    candidate = _candidate()

    store.save_discovery_candidates([candidate])

    assert store.load_discovery_candidates() == [candidate]


def test_discovery_store_save_load_save_is_idempotent(tmp_path) -> None:
    store = EngineStateStore(tmp_path)

    store.save_discovery_candidates([_candidate()])
    first = (tmp_path / "discovery_candidates.jsonl").read_bytes()
    store.save_discovery_candidates(store.load_discovery_candidates())

    assert (tmp_path / "discovery_candidates.jsonl").read_bytes() == first


# --- L10 step-2: schema-version migration discipline (added 2026-06-05) --------
# Versioned additive-optional migration: tolerate schema_version <= current
# (older/equal checkpoints read any missing newer fields via defaults), REFUSE
# schema_version > current (never silently mis-load a checkpoint written by code
# we don't understand). A version bump is a recorded lineage transition, not a
# death-and-rebirth.


def test_load_manifest_refuses_newer_schema_version(tmp_path) -> None:
    from engine_state import IncompatibleEngineStateError

    store = EngineStateStore(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {"schema_version": 999, "turn_count": 3, "written_at_revision": "deadbeef"}
        ),
        encoding="utf-8",
    )

    with pytest.raises(IncompatibleEngineStateError):
        store.load_manifest()


def test_load_manifest_tolerates_older_schema_version(tmp_path) -> None:
    store = EngineStateStore(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {"schema_version": 0, "turn_count": 5, "written_at_revision": "unknown"}
        ),
        encoding="utf-8",
    )

    manifest = store.load_manifest()

    assert manifest is not None
    assert manifest["turn_count"] == 5
