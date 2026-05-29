"""
ADR-0181 PR-5 — audio Delta-CRDT merge proof obligations.

The load-bearing gate is `hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)`
(ADR-0180 §4.3 / ADR-0181 §4.2 A-2, A-3): a set of `AudioCompilationUnit`s folds
to the same merged Vault contribution — and the same trace hash — regardless of
the order arenas were filled or flushed in.

Per CLAUDE.md §Schema-Defined Proof Obligations, each test FAILS LOUDLY under the
violation it names: if `_canonicalize` stopped sorting by `merge_key` (ordered by
arrival instead), the permutation / sequential==concurrent / content-order tests
break; if it stopped deduplicating, the idempotence test breaks.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from evals.audio_sensorium.synth import synthesize
from sensorium.audio.arena import (
    AudioArena,
    AudioDelta,
    audio_merge_trace_hash,
    merge_audio_deltas,
    reset_thread_local_audio_arena,
    thread_local_audio_arena,
)
from sensorium.audio.canonical import canonicalize
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.trace import audio_evidence_trace

SR = 24_000
_EVAL_DIR = Path("evals/audio_sensorium")


def _fixtures() -> list[dict]:
    return json.loads((_EVAL_DIR / "fixtures.json").read_text())["fixtures"]


@pytest.fixture(scope="module")
def units() -> list:
    """Real AudioCompilationUnits — one per eval fixture, distinct merge_keys."""
    compiler = AudioCompiler()
    out = []
    for fx in _fixtures():
        signal = canonicalize(synthesize(fx), SR)
        out.append(compiler.compile_signal(signal))
    return out


# --- the load-bearing property (ADR-0181 §4.2 A-2 / A-3) -------------------


def test_sequential_equals_concurrent(units):
    """hash(Sequential) == hash(Concurrent). Single-arena fixture-order ingest
    vs one unit per thread-local arena flushed under real thread scheduling."""
    seq_arena = AudioArena()
    for unit in units:
        seq_arena.push(unit)
    seq_hash = audio_merge_trace_hash(merge_audio_deltas([seq_arena.snapshot()]))

    def worker(unit) -> AudioDelta:
        # Pools reuse threads; reset so each task gets a fresh share-nothing arena.
        reset_thread_local_audio_arena()
        arena = thread_local_audio_arena()
        arena.push(unit)
        return arena.snapshot()

    for _ in range(5):  # exercise scheduling non-determinism
        order = units[:]
        random.shuffle(order)
        with ThreadPoolExecutor(max_workers=len(order)) as pool:
            deltas = list(pool.map(worker, order))
        conc_hash = audio_merge_trace_hash(merge_audio_deltas(deltas))
        assert conc_hash == seq_hash


def test_merge_is_permutation_invariant(units):
    base = merge_audio_deltas([AudioDelta.from_units(units)])
    for _ in range(8):
        shuffled = units[:]
        random.shuffle(shuffled)
        merged = merge_audio_deltas([AudioDelta.from_units([u]) for u in shuffled])
        assert merged.merge_keys == base.merge_keys
        assert audio_merge_trace_hash(merged) == audio_merge_trace_hash(base)


# --- semilattice legs (ADR-0180 §2.2) -------------------------------------


def test_merge_is_idempotent(units):
    delta = AudioDelta.from_units(units)
    once = merge_audio_deltas([delta])
    twice = merge_audio_deltas([delta, delta])
    assert once.merge_keys == twice.merge_keys
    assert audio_merge_trace_hash(once) == audio_merge_trace_hash(twice)
    # distinct fixtures => no spurious duplicates introduced or dropped
    assert len(twice) == len(units)


def test_join_is_commutative_and_associative(units):
    a = AudioDelta.from_units(units[:2])
    b = AudioDelta.from_units(units[2:4])
    c = AudioDelta.from_units(units[4:])
    assert a.join(b).merge_keys == b.join(a).merge_keys
    assert a.join(b).join(c).merge_keys == a.join(b.join(c)).merge_keys


def test_merge_kernel_equals_semilattice_fold(units):
    deltas = [AudioDelta.from_units([u]) for u in units]
    folded = deltas[0]
    for d in deltas[1:]:
        folded = folded.join(d)
    assert merge_audio_deltas(deltas).merge_keys == folded.merge_keys


# --- content-addressing + dedup correctness --------------------------------


def test_merge_order_is_content_addressed(units):
    delta = AudioDelta.from_units(units)
    assert list(delta.merge_keys) == sorted(delta.merge_keys)
    # all distinct fixtures retained
    assert len(delta) == len({u.merge_key for u in units})


def test_arena_push_order_independent(units):
    forward = AudioArena()
    for u in units:
        forward.push(u)
    backward = AudioArena()
    for u in reversed(units):
        backward.push(u)
    assert forward.snapshot().merge_keys == backward.snapshot().merge_keys


def test_arena_snapshot_non_draining(units):
    arena = AudioArena()
    arena.push(units[0])
    _ = arena.snapshot()
    # flush/GC is the kernel's job; snapshot must not lose the unit across the
    # eventual-consistency window (ADR-0180 §3.2).
    assert len(arena) == 1
    assert len(arena.snapshot()) == 1


# --- trace-hash sensitivity + hygiene (ADR-0181 §4.2 A-6) ------------------


def test_trace_hash_changes_with_content(units):
    """Guards against a vacuous (constant) hash: dropping a unit must change it."""
    full = AudioDelta.from_units(units)
    subset = AudioDelta.from_units(units[:-1])
    assert audio_merge_trace_hash(full) != audio_merge_trace_hash(subset)


def test_merge_trace_hash_no_pcm(units):
    delta = AudioDelta.from_units(units)
    for unit in delta.units:
        trace = audio_evidence_trace(unit)
        for value in trace.values():
            assert not isinstance(value, (np.ndarray, bytes, bytearray))
        assert "samples" not in trace
    # stable across repeated calls
    assert audio_merge_trace_hash(delta) == audio_merge_trace_hash(delta)
