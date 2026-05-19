"""``convivial_v1`` register pack — load, self-seal, runtime threading
(ADR-0071, Phase R4).
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.register.loader import (
    RegisterPack,
    load_register_pack,
    verify_register_pack_seal,
)


def test_convivial_v1_loads():
    pack = load_register_pack("convivial_v1")
    assert isinstance(pack, RegisterPack)
    assert pack.register_id == "convivial_v1"
    assert pack.depth_preference == "standard"
    assert not pack.is_unregistered()
    assert not pack.is_null_register()


def test_convivial_v1_self_seal_verifies():
    assert verify_register_pack_seal("convivial_v1") is True


def test_convivial_v1_markers_populated():
    pack = load_register_pack("convivial_v1")
    assert pack.discourse_markers.openings == ("So,", "Right —", "OK,")
    assert pack.discourse_markers.transitions == ()
    assert pack.discourse_markers.closings == (
        "", " — does that help?", " — make sense?",
    )


def test_runtime_loads_convivial_register():
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="convivial_v1"),
    )
    assert runtime.register_pack.register_id == "convivial_v1"
    assert not runtime.register_pack.is_null_register()


def test_runtime_chat_under_convivial_attaches_a_marker():
    """A pack-grounded chat turn under convivial should produce a
    surface that contains at least one of the configured markers."""
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="convivial_v1"),
    )
    response = runtime.chat("What is light?")
    surface = response.surface
    openings = ("So,", "Right —", "OK,")
    closings = (" — does that help?", " — make sense?")
    has_opening = any(surface.startswith(o + " ") for o in openings)
    has_closing = any(surface.endswith(c) for c in closings)
    # Opening bucket has no empty entry ⇒ every turn gets an opening.
    assert has_opening, f"surface lacks any convivial opening: {surface!r}"
    # Closing may be empty (1/3 of the seed space).
    _ = has_closing


def test_runtime_chat_replay_equivalence_under_convivial():
    """Two fresh runtimes given the same prompt sequence under the
    same register produce byte-identical surfaces.  Load-bearing
    replay-equivalence invariant."""
    prompts = (
        "What is light?",
        "Define knowledge.",
        "What is truth?",
        "Light is illumination, right?",
    )
    surfaces_a: list[str] = []
    surfaces_b: list[str] = []
    for prompts_list, sink in ((prompts, surfaces_a), (prompts, surfaces_b)):
        runtime = ChatRuntime(
            config=RuntimeConfig(register_pack_id="convivial_v1"),
        )
        for p in prompts_list:
            response = runtime.chat(p)
            sink.append(response.surface)
    assert surfaces_a == surfaces_b, (
        "convivial_v1 replay equivalence violated — fresh runtime "
        "produced different surfaces on identical prompt sequence."
    )


def test_runtime_chat_turn_idx_distinct_under_convivial():
    """Same prompt across multiple turns in one session produces at
    least one distinct surface (turn_idx variation is observable)."""
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="convivial_v1"),
    )
    prompt = "What is light?"
    surfaces: list[str] = []
    for _ in range(6):
        response = runtime.chat(prompt)
        surfaces.append(response.surface)
    assert len(set(surfaces)) >= 2, (
        f"convivial register did not vary across 6 same-prompt turns "
        f"in one session: {surfaces}"
    )
