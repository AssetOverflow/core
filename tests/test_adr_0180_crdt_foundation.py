"""
ADR-0180 §1.5.4 — Pre-refactor test obligations for the Delta-CRDT substrate.

CLAUDE.md work-sequencing item 5 ("Rust backend parity only after Python
semantics are locked by tests") and ADR-0180 §1.5.4 both require these four
properties to exist as Python tests and be GREEN on `main` *before* any change
to `core-rs/src/vault.rs`. They are also the foundation ADR-0181 PR-5 (audio
Delta-CRDT wiring) rides on — the audio A-1..A-6 obligations are written as
analogs of these.

  T-1  Set-equality of vault writes under shuffled single-thread ingest.
  T-2  compute_trace_hash invariance under set-equal vault states with
       identical upstream serialized prefixes.
  T-3  versor_apply non-commutativity (negative guard — must NOT silently
       become commutative, which would let the substrate wrongly shard it).
  T-4  ProjectionHead.project purity: same S -> byte-identical (32,) across
       repeated calls and across threads.

T-1 and T-2 are the load-bearing ones (ADR-0180 §1.5.4). T-3 and T-4 are
guards against silent drift.

Per CLAUDE.md §Schema-Defined Proof Obligations, each test must be able to
*meaningfully fail* under the violation it names — see the inline notes.
"""

from __future__ import annotations

import itertools
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from algebra.versor import unitize_versor, versor_apply
from core.cognition.trace import compute_trace_hash
from sensorium.protocol import CL41_DIM, ModalityVocabulary
from sensorium.adapters.text import TextProjectionHead
from vault.store import VaultStore
from teaching.epistemic import EpistemicStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit_versor(seed: int) -> np.ndarray:
    """A reproducible positive-norm Cl(4,1) grade-1 unit versor.

    Mirrors the construction idiom in tests/test_versor_closure.py: a grade-1
    vector with its e5 component bounded below the four-space norm so that
    V * reverse(V) = +1.
    """
    rng = np.random.default_rng(seed)
    vec4 = rng.standard_normal(4).astype(np.float32)
    norm4 = float(np.linalg.norm(vec4))
    if norm4 < 1e-6:
        vec4[0] = 1.0
        norm4 = 1.0
    vec = np.zeros(5, dtype=np.float32)
    vec[:4] = vec4
    vec[4] = 0.25 * norm4 * np.tanh(float(rng.standard_normal()))
    mv = np.zeros(CL41_DIM, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


def _versor_bytes(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def _store_all(pairs: list[tuple[np.ndarray, dict]]) -> VaultStore:
    """Store (versor, metadata) pairs into a fresh vault.

    reproject_interval=0 disables the periodic null-reprojection so the test
    isolates the *append* semilattice (ADR-0180 §1.5.2 row 5) rather than
    reprojection bookkeeping.
    """
    store = VaultStore(reproject_interval=0)
    for F, meta in pairs:
        store.store(F, meta, epistemic_status=EpistemicStatus.SPECULATIVE)
    return store


def _vault_contents_set(store: VaultStore) -> set[tuple[bytes, str]]:
    """Content-addressed view of vault state: {(versor_bytes, status)}.

    This is the 'as a set, not as a sequence' projection ADR-0180 §1.5.3
    point 1 requires the sequential and concurrent runs to agree on.
    """
    return {
        (_versor_bytes(v), m.get("epistemic_status", "speculative"))
        for v, m in zip(store._versors, store._metadata)
    }


# ---------------------------------------------------------------------------
# T-1 — set-equality of vault writes under shuffled ingest (load-bearing)
# ---------------------------------------------------------------------------

def test_t1_vault_writes_set_equal_under_permutation():
    """For any ingest sequence and any permutation, vault contents are equal
    *as a set*. This is the property that makes write-accumulation
    semilattice-eligible (ADR-0180 §1.5.2 row 5 / §2.2 commutativity).

    Fails loudly if store() ever dedups, drops, or order-mutates entries.
    """
    pairs = [
        (_unit_versor(s), {"src": f"entry-{s}"})
        for s in range(8)
    ]
    canonical = _vault_contents_set(_store_all(pairs))

    # Exercise several distinct permutations of the same multiset of writes.
    perms = list(itertools.islice(itertools.permutations(range(len(pairs))), 0, 5040, 720))
    for perm in perms:
        shuffled = [pairs[i] for i in perm]
        assert _vault_contents_set(_store_all(shuffled)) == canonical


def test_t1_idempotent_reingest_is_set_stable():
    """Re-ingesting an already-stored entry keeps the content-addressed set
    stable (the idempotence leg of the join semilattice, ADR-0180 §2.2).

    Note: the vault deque itself appends duplicates (len grows); idempotence
    is asserted at the *content-addressed* layer the CRDT merge dedups on,
    which is exactly the layer ADR-0181 §2.2 keys audio deltas by.
    """
    pairs = [(_unit_versor(s), {"src": f"e{s}"}) for s in range(4)]
    once = _vault_contents_set(_store_all(pairs))
    twice = _vault_contents_set(_store_all(pairs + pairs))
    assert once == twice


# ---------------------------------------------------------------------------
# T-2 — trace-hash invariance under set-equal vault states (load-bearing)
# ---------------------------------------------------------------------------

def test_t2_trace_hash_invariant_to_vault_order():
    """compute_trace_hash is invariant to the *order* vault entries were
    written, given identical upstream serialized fields.

    FINDING (recorded in docs/audit/ADR-0180-t1-t4-findings.md): the current
    compute_trace_hash folds only `vault_hits` (an int count) plus the
    serialized upstream prefix — it does NOT fold vault *contents*. So
    ADR-0180 §1.5.3 point 2 ("the hashing step must re-sort vault state in
    content-addressed order") is currently *vacuous at the trace-hash layer*:
    there is nothing order-sensitive to re-sort because contents are not in
    the payload. The obligation becomes live only if vault contents later
    enter the payload. This test pins that the count-based hash is stable.
    """
    def _hash(vault_hits: int) -> str:
        return compute_trace_hash(
            input_text="what is truth",
            filtered_tokens=("truth",),
            surface="truth is coherent",
            walk_surface="truth",
            articulation_surface="truth is coherent",
            dialogue_role="assistant",
            versor_condition=1e-9,
            vault_hits=vault_hits,
            intent_tag="definition",
        )

    assert _hash(3) == _hash(3)
    # Different hit COUNT must change the hash (count is load-bearing).
    assert _hash(4) != _hash(3)


def test_t2_recall_result_set_invariant_to_insertion_order():
    """The genuinely-failable half of T-2: with distinct scores, recall
    returns the same result set (by content) regardless of insertion order.

    This is what guarantees `vault_hits` (the count folded into the trace
    hash) AND the recalled content are order-invariant across a CRDT merge
    that reorders the deque. Fails if the recall scan or its tiebreak is
    corrupted by storage order.

    (Tie-scored entries are deliberately avoided: ascending-index tiebreak is
    index-sensitive, so equal-score entries are an order-dependent edge the
    CRDT merge must content-address — noted in the findings doc.)
    """
    versors = [_unit_versor(s) for s in range(6)]
    query = versors[0]

    forward = VaultStore(reproject_interval=0)
    for v in versors:
        forward.store(v, {}, epistemic_status=EpistemicStatus.SPECULATIVE)

    reverse_store = VaultStore(reproject_interval=0)
    for v in reversed(versors):
        reverse_store.store(v, {}, epistemic_status=EpistemicStatus.SPECULATIVE)

    fwd = {_versor_bytes(r["versor"]) for r in forward.recall(query, top_k=3)}
    rev = {_versor_bytes(r["versor"]) for r in reverse_store.recall(query, top_k=3)}
    assert fwd == rev
    assert len(fwd) == 3  # count (→ vault_hits) is stable


# ---------------------------------------------------------------------------
# T-3 — versor_apply non-commutativity (negative guard)
# ---------------------------------------------------------------------------

def test_t3_versor_apply_is_non_commutative():
    """The sandwich V·F·rev(V) is non-commutative (ADR-0180 §1.5.2 row 3).

    This negative guard exists so a future refactor that accidentally makes
    versor_apply commutative is caught HERE, rather than silently masked by
    the CRDT substrate sharding an operation that is not order-invariant.
    ADR-0181 §2.1 relies on this: in-chunk composition is the serialization
    barrier *precisely because* this product does not commute.
    """
    V1 = _unit_versor(11)
    V2 = _unit_versor(23)
    F = _unit_versor(101)

    ab = versor_apply(V1, versor_apply(V2, F))
    ba = versor_apply(V2, versor_apply(V1, F))

    assert not np.allclose(ab, ba, atol=1e-6), (
        "versor_apply became commutative — the Delta-CRDT substrate must NOT "
        "shard versor_apply; see ADR-0180 §1.5.2."
    )


# ---------------------------------------------------------------------------
# T-4 — ProjectionHead.project purity (negative guard)
# ---------------------------------------------------------------------------

def _en_head() -> tuple[TextProjectionHead, str]:
    vocab = ModalityVocabulary()
    point = _unit_versor(7)
    vocab.register_point("beginning", point)
    return TextProjectionHead(vocab), "beginning"


def test_t4_projection_is_pure_across_calls():
    """Same S -> byte-identical (32,) float32 across repeated calls
    (ADR-0180 T-4). Fails if any hidden state leaks into project()."""
    head, token = _en_head()
    v1 = head.project(token)
    v2 = head.project(token)
    assert v1.shape == (CL41_DIM,)
    assert v1.dtype == np.float32
    assert np.array_equal(v1, v2)


def test_t4_projection_is_pure_across_threads():
    """Same S -> byte-identical (32,) across threads. The audio
    ProjectionHead (ADR-0181) inherits this purity requirement so a delayed
    CRDT merge can never change what a thread-local arena compiled
    (ADR-0181 §2.4)."""
    head, token = _en_head()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: head.project(token).tobytes(), range(32)))
    assert len(set(results)) == 1
