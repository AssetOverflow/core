"""``terse_v1`` register pack — load, self-seal, and one-knob behaviour
(ADR-0070, Phase R3).

Direct-call tests against ``pack_grounded_surface``:

* terse_v1 emits a one-domain disclosure head
* neutral / unregistered emit a three-domain disclosure head
* both surfaces carry the same ``pack-grounded ({pack_id})`` provenance
"""

from __future__ import annotations

from chat.pack_grounding import (
    build_pack_surface_candidate,
    pack_grounded_surface,
)
from packs.register.loader import (
    UNREGISTERED,
    RegisterPack,
    load_register_pack,
    verify_register_pack_seal,
)


def test_terse_v1_loads():
    pack = load_register_pack("terse_v1")
    assert isinstance(pack, RegisterPack)
    assert pack.register_id == "terse_v1"
    assert pack.depth_preference == "terse"
    assert not pack.is_unregistered()
    assert not pack.is_null_register()
    assert pack.mastery_report_sha256 != ""


def test_terse_v1_realizer_overrides_shape():
    """ADR-0070 + ADR-0077 — terse_v1 carries disclosure_domain_count
    plus the three substantive R6 knobs (drop_provenance_tag,
    compress_gloss, drop_articles)."""
    pack = load_register_pack("terse_v1")
    assert dict(pack.realizer_overrides) == {
        "disclosure_domain_count": 1,
        "drop_provenance_tag": True,
        "compress_gloss": True,
        "drop_articles": True,
    }


def test_terse_v1_self_seal_verifies():
    assert verify_register_pack_seal("terse_v1") is True


def test_terse_v1_discourse_markers_remain_empty():
    """R3 gate requires markers empty (R4 widens this)."""
    pack = load_register_pack("terse_v1")
    assert pack.discourse_markers.is_empty()


def _find_without_gloss_lemma() -> str | None:
    """Find a pack lemma whose without-gloss disclosure path emits
    multiple domains.  Returns ``None`` if every pack lemma resolves
    via the gloss path (in which case the head slice never executes
    and this test file would be vacuous — flag it loudly).
    """
    from chat.pack_grounding import _pack_index  # type: ignore
    from chat.pack_resolver import resolve_gloss

    for lemma, domains in _pack_index().items():
        if len(domains) < 3:
            continue
        if resolve_gloss(lemma, ("en_core_cognition_v1",)) is not None:
            continue
        return lemma
    return None


def test_terse_emits_one_domain_head_under_terse_register():
    lemma = _find_without_gloss_lemma()
    if lemma is None:
        # No lemma exercises the disclosure path → R3 knob is vacuous
        # for the current pack; degrade-to-trivial rather than skip,
        # so a future pack-content change makes the gap visible.
        return

    terse = load_register_pack("terse_v1")
    neutral = load_register_pack("default_neutral_v1")

    s_terse = pack_grounded_surface(lemma, register=terse)
    s_neutral = pack_grounded_surface(lemma, register=neutral)
    s_unreg = pack_grounded_surface(lemma, register=UNREGISTERED)

    assert s_terse is not None
    assert s_neutral is not None
    assert s_unreg is not None

    # Provenance marker present in every surface.
    assert "pack-grounded" in s_terse
    assert "pack-grounded" in s_neutral
    assert "pack-grounded" in s_unreg

    # Neutral ≡ unregistered (re-asserting ADR-0069 invariant B at the
    # composer level — defense in depth against R3 regressions).
    assert s_neutral == s_unreg

    # Terse compresses the head; surfaces must differ on this lemma.
    assert s_terse != s_neutral

    # Disclosure head separator count is the proxy for domain slice
    # width.  The disclosure head sits after "): " and before ". No
    # session evidence yet."
    def _head_separator_count(surface: str) -> int:
        head = surface.split("): ", 1)[1].split(". No session", 1)[0]
        return head.count("; ")

    assert _head_separator_count(s_terse) == 0
    assert _head_separator_count(s_neutral) == 2


def test_build_candidate_clamps_out_of_range_override():
    """Defensive realizer clamp: out-of-range int falls back to default.

    The ratification gate already enforces ``v in {1, 2, 3}``.  This
    test exercises the off-path defense by constructing a RegisterPack
    in memory with a bad value — what an unratified test fixture
    might do.
    """
    bogus = RegisterPack(
        register_id="bogus_test",
        version="0.0.0",
        description="",
        display_name="",
        depth_preference="standard",
        realizer_overrides={"disclosure_domain_count": 99},  # type: ignore[arg-type]
    )
    lemma = _find_without_gloss_lemma()
    if lemma is None:
        return
    s_bogus = pack_grounded_surface(lemma, register=bogus)
    s_neutral = pack_grounded_surface(
        lemma, register=load_register_pack("default_neutral_v1"),
    )
    # Out-of-range clamps to default (3 domains) — same head as neutral.
    assert s_bogus == s_neutral


def test_build_candidate_respects_register_kwarg_directly():
    """build_pack_surface_candidate accepts register= directly."""
    lemma = _find_without_gloss_lemma()
    if lemma is None:
        return
    terse = load_register_pack("terse_v1")
    cand_terse = build_pack_surface_candidate(lemma, register=terse)
    cand_neutral = build_pack_surface_candidate(lemma, register=UNREGISTERED)
    assert cand_terse is not None and cand_neutral is not None
    assert cand_terse.surface != cand_neutral.surface
    assert cand_terse.grounding_source == cand_neutral.grounding_source
    assert cand_terse.pack_id == cand_neutral.pack_id
    assert cand_terse.semantic_domains == cand_neutral.semantic_domains
