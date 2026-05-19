"""Seeded surface variation — selector determinism + decoration shape
(ADR-0071, Plan Phase R4).
"""

from __future__ import annotations

from chat.register_variation import _select_bucket_entry, decorate_surface
from packs.register.loader import UNREGISTERED, load_register_pack


def test_selector_returns_empty_string_for_empty_bucket():
    result = _select_bucket_entry(
        (),
        seed_text="anything",
        register_id="test_v1",
        turn_idx=0,
        bucket_name="openings",
    )
    assert result == ""


def test_selector_is_deterministic():
    bucket = ("a", "b", "c", "d", "e")
    args = dict(
        seed_text="some surface", register_id="test_v1",
        turn_idx=7, bucket_name="openings",
    )
    first = _select_bucket_entry(bucket, **args)
    for _ in range(50):
        assert _select_bucket_entry(bucket, **args) == first


def test_selector_varies_with_turn_idx():
    bucket = ("a", "b", "c", "d", "e")
    seen = set()
    for turn_idx in range(20):
        seen.add(_select_bucket_entry(
            bucket,
            seed_text="constant",
            register_id="test_v1",
            turn_idx=turn_idx,
            bucket_name="openings",
        ))
    # 20 turns over a 5-entry bucket should hit at least 3 entries.
    assert len(seen) >= 3, (
        f"seed is not varying with turn_idx — only saw {seen}"
    )


def test_selector_varies_with_register_id():
    bucket = ("a", "b", "c", "d", "e")
    a = _select_bucket_entry(
        bucket, seed_text="same", register_id="reg_A",
        turn_idx=0, bucket_name="openings",
    )
    b = _select_bucket_entry(
        bucket, seed_text="same", register_id="reg_B",
        turn_idx=0, bucket_name="openings",
    )
    # Not guaranteed for a single bucket size 5 — sweep a few
    # turn_idx values to ensure register_id moves the seed at all.
    diffs = 0
    for t in range(20):
        a_t = _select_bucket_entry(
            bucket, seed_text="same", register_id="reg_A",
            turn_idx=t, bucket_name="openings",
        )
        b_t = _select_bucket_entry(
            bucket, seed_text="same", register_id="reg_B",
            turn_idx=t, bucket_name="openings",
        )
        if a_t != b_t:
            diffs += 1
    assert diffs > 0, (
        f"register_id has no effect on selector across 20 turn_idx "
        f"values (first picks: a={a!r}, b={b!r})"
    )


def test_selector_distributes_across_bucket():
    """Across many distinct seed_text inputs, every entry should be
    selected at least once."""
    bucket = ("a", "b", "c")
    seen: set[str] = set()
    for i in range(300):
        seen.add(_select_bucket_entry(
            bucket,
            seed_text=f"surface_{i}",
            register_id="test",
            turn_idx=0,
            bucket_name="openings",
        ))
    assert seen == {"a", "b", "c"}


def test_selector_uses_bucket_name():
    """Different bucket_name keys produce different seeds."""
    bucket = ("a", "b", "c", "d", "e", "f", "g", "h")
    args = dict(seed_text="x", register_id="r", turn_idx=0)
    o = _select_bucket_entry(bucket, bucket_name="openings", **args)
    c = _select_bucket_entry(bucket, bucket_name="closings", **args)
    diffs = 0
    for t in range(20):
        o_t = _select_bucket_entry(
            bucket, seed_text="x", register_id="r",
            turn_idx=t, bucket_name="openings",
        )
        c_t = _select_bucket_entry(
            bucket, seed_text="x", register_id="r",
            turn_idx=t, bucket_name="closings",
        )
        if o_t != c_t:
            diffs += 1
    # Not strict on (o, c) at turn 0 alone — sweep guards.
    _ = (o, c)
    assert diffs > 0


def test_decorate_surface_empty_buckets_noop():
    """UNREGISTERED / neutral / terse all have empty buckets."""
    surface = "Light is illumination. Pack-grounded (en_core_cognition_v1)."
    out = decorate_surface(surface, UNREGISTERED, turn_idx=0)
    assert out == surface

    neutral = load_register_pack("default_neutral_v1")
    assert decorate_surface(surface, neutral, turn_idx=0) == surface

    terse = load_register_pack("terse_v1")
    assert decorate_surface(surface, terse, turn_idx=0) == surface


def test_decorate_surface_empty_input_noop():
    """Empty input ⇒ empty output regardless of register."""
    convivial = load_register_pack("convivial_v1")
    assert decorate_surface("", convivial, turn_idx=0) == ""


def test_decorate_surface_convivial_attaches_markers():
    """Convivial register has populated openings and closings — at
    least one of them should attach to most surfaces."""
    convivial = load_register_pack("convivial_v1")
    surface = "Light is illumination."
    out = decorate_surface(surface, convivial, turn_idx=0)
    # The opening (3 entries, no empty) is always non-empty.
    # Therefore the surface must change.
    assert out != surface
    assert surface in out


def test_decorate_surface_is_deterministic():
    convivial = load_register_pack("convivial_v1")
    surface = "Light is illumination."
    a = decorate_surface(surface, convivial, turn_idx=0)
    b = decorate_surface(surface, convivial, turn_idx=0)
    assert a == b


def test_decorate_surface_turn_idx_varies_output():
    convivial = load_register_pack("convivial_v1")
    surface = "Light is illumination."
    seen: set[str] = set()
    for t in range(15):
        seen.add(decorate_surface(surface, convivial, turn_idx=t))
    # 15 turns × 3 openings × 3 closings = 9 possible outputs;
    # should see at least 4 distinct.
    assert len(seen) >= 4, f"only {len(seen)} distinct decorations across 15 turns"
