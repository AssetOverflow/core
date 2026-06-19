"""Tests for generate/process_frames.py."""
from __future__ import annotations

import pytest

from generate.process_frames import (
    lookup_frame,
    all_frames,
    frame_by_name,
    ProcessFrame,
)


def test_all_frames_registered() -> None:
    frames = all_frames()
    assert len(frames) == 8
    names = {f.name for f in frames}
    expected = {
        "transfer", "consumption", "transaction", "labor_rate", "travel",
        "container_packing", "partition", "comparison"
    }
    assert names == expected


def test_frame_by_name() -> None:
    f = frame_by_name("transfer")
    assert f is not None
    assert f.name == "transfer"
    assert f.candidate_relation == "transfer"

    assert frame_by_name("non_existent_frame") is None


def test_lookup_frame() -> None:
    # Look up by trigger surface
    frames = lookup_frame("give")
    assert len(frames) == 1
    assert frames[0].name == "transfer"

    frames = lookup_frame("buy")
    assert len(frames) == 1
    assert frames[0].name == "transaction"

    frames = lookup_frame("split")
    assert len(frames) == 1
    assert frames[0].name == "partition"

    # Case insensitivity
    assert lookup_frame("GIVE") == lookup_frame("give")

    # Unrecognized trigger
    assert lookup_frame("unknown_trigger_surface") == ()


def test_frame_roles_and_not_licensed() -> None:
    # 1. transfer
    f = frame_by_name("transfer")
    assert f is not None
    assert len(f.required_roles) == 3
    roles = {r.name for r in f.required_roles}
    assert roles == {"agent", "patient", "quantity"}
    assert len(f.not_licensed) > 0

    # 2. transaction
    f = frame_by_name("transaction")
    assert f is not None
    assert len(f.required_roles) == 3
    roles = {r.name for r in f.required_roles}
    assert roles == {"buyer", "quantity", "price"}

    # 3. comparison
    f = frame_by_name("comparison")
    assert f is not None
    assert len(f.required_roles) == 3
    roles = {r.name for r in f.required_roles}
    assert roles == {"reference", "target", "scale_factor"}


def test_deterministic_ordering() -> None:
    # Frames in definition order
    frames = all_frames()
    names = [f.name for f in frames]
    # Check stable order
    assert names == [
        "transfer", "consumption", "transaction", "labor_rate", "travel",
        "container_packing", "partition", "comparison"
    ]

    # Deterministic sorting within lookup results
    # "half" is in partition, and "quarter" in partition.
    # Verb "paid" is in transaction and labor_rate.
    frames = lookup_frame("paid")
    assert len(frames) == 2
    names_lookup = [f.name for f in frames]
    assert names_lookup == sorted(names_lookup)  # labor_rate then transaction
