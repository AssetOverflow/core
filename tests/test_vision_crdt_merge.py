from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from sensorium.vision import VisionCompiler, canonicalize_image
from sensorium.vision.arena import (
    VisionArena,
    VisionDelta,
    merge_vision_deltas,
    reset_thread_local_vision_arena,
    thread_local_vision_arena,
    vision_merge_trace_hash,
)
from sensorium.vision.trace import vision_evidence_trace


def _image(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((32, 32, 3), dtype=np.float32)


def _units():
    compiler = VisionCompiler()
    out = []
    for seed in (1, 2, 3):
        out.extend(compiler.compile_image(canonicalize_image(_image(seed))))
    return out


def test_vision_merge_is_permutation_invariant():
    units = _units()
    base = merge_vision_deltas([VisionDelta.from_units(units)])
    for _ in range(5):
        shuffled = units[:]
        random.shuffle(shuffled)
        merged = merge_vision_deltas([VisionDelta.from_units([u]) for u in shuffled])
        assert merged.merge_keys == base.merge_keys
        assert vision_merge_trace_hash(merged) == vision_merge_trace_hash(base)


def test_vision_sequential_equals_concurrent():
    units = _units()
    seq = VisionArena()
    for unit in units:
        seq.push(unit)
    seq_hash = vision_merge_trace_hash(merge_vision_deltas([seq.snapshot()]))

    def worker(unit):
        reset_thread_local_vision_arena()
        arena = thread_local_vision_arena()
        arena.push(unit)
        return arena.snapshot()

    shuffled = units[:]
    random.shuffle(shuffled)
    with ThreadPoolExecutor(max_workers=4) as pool:
        deltas = list(pool.map(worker, shuffled))
    assert vision_merge_trace_hash(merge_vision_deltas(deltas)) == seq_hash


def test_vision_merge_is_idempotent_and_trace_safe():
    delta = VisionDelta.from_units(_units())
    merged = merge_vision_deltas([delta, delta])
    assert merged.merge_keys == delta.merge_keys
    assert vision_merge_trace_hash(merged) == vision_merge_trace_hash(delta)
    for unit in merged.units:
        trace = vision_evidence_trace(unit)
        assert "pixels" not in trace
        for value in trace.values():
            assert not isinstance(value, (np.ndarray, bytes, bytearray))
