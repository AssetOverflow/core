"""VaultStore round-trip — Shape B+ Phase B.

Exit gate: exact CGA recall is identical after a save/load cycle, and the
restored versors are BIT-IDENTICAL to the originals — which proves the load path
did NOT reproject/normalize them (``vault/store.py`` is a CLAUDE.md forbidden
normalization site; persistence must be pure (de)serialization). The derived
``_exact_index`` is rebuilt on load and the lazy ``_matrix_cache`` stays None.
"""

from __future__ import annotations

import json

import numpy as np

from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore


def _versors(n: int = 6) -> list[np.ndarray]:
    out = []
    for i in range(n):
        v = np.zeros(32, dtype=np.float32)
        v[0] = 1.0
        v[(i % 31) + 1] = 0.1 * (i + 1)  # distinct, near-identity
        out.append(v)
    return out


def _populated_store() -> VaultStore:
    store = VaultStore(reproject_interval=0)  # no auto-reproject; isolate persistence
    for i, v in enumerate(_versors()):
        store.store(
            v,
            {"turn": i, "role": "user" if i % 2 == 0 else "assistant"},
            epistemic_status=EpistemicStatus.SPECULATIVE,
        )
    return store


def test_vaultstore_round_trip_preserves_exact_recall() -> None:
    store = _populated_store()
    query = _versors()[2]
    before = store.recall(query, top_k=5)

    restored = VaultStore.from_dict(store.to_dict())
    after = restored.recall(query, top_k=5)

    assert [(r["index"], r["score"]) for r in before] == [
        (r["index"], r["score"]) for r in after
    ]
    assert [r["metadata"] for r in before] == [r["metadata"] for r in after]
    assert [r["versor"].tobytes() for r in before] == [
        r["versor"].tobytes() for r in after
    ]


def test_vaultstore_restore_does_not_reproject_versors() -> None:
    # Bit-identical versors prove the load path called no null_project/normalizer.
    store = _populated_store()
    restored = VaultStore.from_dict(store.to_dict())
    assert len(restored) == len(store)
    for original, recovered in zip(store._versors, restored._versors):
        assert recovered.tobytes() == original.tobytes()
        assert recovered.dtype == np.float32


def test_vaultstore_round_trip_is_json_safe_and_preserves_scalars() -> None:
    store = _populated_store()
    restored = VaultStore.from_dict(json.loads(json.dumps(store.to_dict())))
    assert len(restored) == len(store)
    assert restored.store_count == store.store_count
    assert restored.reproject_interval == store.reproject_interval


def test_vaultstore_restore_rebuilds_exact_match_index() -> None:
    # The exact-match short-circuit (score == inf) must work after restore,
    # which requires _exact_index to be rebuilt over the restored bytes.
    store = _populated_store()
    restored = VaultStore.from_dict(store.to_dict())
    exact_query = _versors()[3]
    hits = restored.recall(exact_query, top_k=3)
    assert hits[0]["score"] == float("inf")  # exact match found via rebuilt index


def test_vaultstore_round_trips_proposition_valued_metadata() -> None:
    # generate/proposition.py stores {"kind":"proposition","proposition":<Proposition>}
    # into vault metadata — the one structured (non-primitive) metadata value.
    import json

    from generate.proposition import Proposition

    prop = Proposition(
        subject="s", predicate="p", object_="o", surface="s p o",
        frame_id="f", subject_versor=_versors()[0], predicate_versor=_versors()[1],
        relation=_versors()[2],
    )
    store = VaultStore(reproject_interval=0)
    store.store(_versors()[0], {"kind": "proposition", "proposition": prop})

    restored = VaultStore.from_dict(json.loads(json.dumps(store.to_dict())))
    recovered = restored._metadata[0]["proposition"]
    assert isinstance(recovered, Proposition)
    assert recovered.subject == "s"
    assert recovered.relation.tobytes() == prop.relation.tobytes()


def test_empty_vaultstore_round_trips() -> None:
    store = VaultStore(reproject_interval=50, max_entries=10)
    restored = VaultStore.from_dict(store.to_dict())
    assert len(restored) == 0
    assert restored.reproject_interval == 50
    assert restored.recall(_versors()[0], top_k=3) == []
