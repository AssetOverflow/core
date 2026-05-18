"""ADR-0031 — score decomposition: per-axis hedge phrases.

When a hedge band fires AND ``IdentityScore.deviation_axes`` names an
axis for which the pack supplies an ``axis_hedges`` entry, the
assembler uses that axis's phrase instead of the generic
``preferred_hedge_*``.  These tests prove:

* Per-axis phrases fire when the score reports the axis as deviating.
* Generic phrase still fires when no specific axis matches.
* Pack swap produces different axis-specific phrases on the same
  trajectory + deviation.
* Lex tie-break is deterministic when multiple axes deviate.
* Depth languages (he, grc) still use canonical ADR-0030 phrases
  regardless of which axis deviates (English-only at v1).
* Backward compatibility: ``deviation_axes=frozenset()`` falls back to
  ADR-0028 generic behavior byte-for-byte.
"""

from __future__ import annotations

from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SurfaceContext
from packs.identity.loader import load_identity_manifold

_ASSEMBLER = SentenceAssembler()


def _plan(lang: str = "en") -> ArticulationPlan:
    if lang == "he":
        return ArticulationPlan(
            "אמת", "מגלה", "מציאות", "", "he", "default",
        )
    if lang == "grc":
        return ArticulationPlan(
            "logos", "ἀποκαλύπτει", "πραγματικότητα", "", "grc", "default",
        )
    return ArticulationPlan(
        "truth", "reveals", "reality", "", "en", "default",
    )


def _ctx(
    pack_id: str, alignment: float, deviation_axes: set[str], lang: str = "en",
) -> SurfaceContext:
    prefs = load_identity_manifold(pack_id).surface_preferences
    axis_hedges = tuple(
        (aid, h.strong, h.soft, h.qualifier) for aid, h in prefs.axis_hedges
    )
    return SurfaceContext(
        identity_alignment=alignment,
        hedge_threshold_strong=prefs.hedge_threshold_strong,
        hedge_threshold_soft=prefs.hedge_threshold_soft,
        preferred_hedge_strong=prefs.preferred_hedge_strong,
        preferred_hedge_soft=prefs.preferred_hedge_soft,
        claim_strength=prefs.claim_strength,
        qualified_band_high=prefs.qualified_band_high,
        preferred_qualifier=prefs.preferred_qualifier,
        deviation_axes=frozenset(deviation_axes),
        axis_hedges=axis_hedges,
    )


def _surface(
    pack_id: str, alignment: float, deviation_axes: set[str], lang: str = "en",
) -> str:
    return _ASSEMBLER.assemble(
        _plan(lang),
        tokens=[],
        role="assert",
        context=_ctx(pack_id, alignment, deviation_axes, lang),
    ).surface


# ---------- per-axis phrases under default pack ----------


class TestAxisSpecificPhrases:
    def test_truthfulness_deviation_uses_truthfulness_phrase(self) -> None:
        s = _surface("default_general_v1", 0.30, {"truthfulness"})
        assert s.startswith("Evidence is thin that"), s

    def test_coherence_deviation_uses_coherence_phrase(self) -> None:
        s = _surface("default_general_v1", 0.30, {"coherence"})
        assert s.startswith("This does not yet cohere:"), s

    def test_reverence_deviation_uses_reverence_phrase(self) -> None:
        s = _surface("default_general_v1", 0.30, {"reverence"})
        assert s.startswith("Reports suggest"), s

    def test_no_deviation_falls_back_to_generic(self) -> None:
        s = _surface("default_general_v1", 0.30, set())
        assert s.startswith("It seems that"), s

    def test_deviation_outside_pack_axis_hedges_falls_back(self) -> None:
        # An axis_id that the pack doesn't provide an axis_hedge for.
        s = _surface("default_general_v1", 0.30, {"unfamiliar_axis"})
        assert s.startswith("It seems that"), s


# ---------- band gating still applies ----------


class TestBandGating:
    def test_above_hedge_band_leaves_bare_even_with_deviation(self) -> None:
        # alignment=0.90 is above default's hedge_threshold_soft (0.50)
        # and qualified_band_high (0.75).  No phrase prepends.
        s = _surface("default_general_v1", 0.90, {"truthfulness"})
        assert s == "Truth reveals reality."

    def test_soft_band_uses_axis_soft_phrase(self) -> None:
        # alignment=0.45 is in default's soft band [0.40, 0.50).
        s = _surface("default_general_v1", 0.45, {"truthfulness"})
        assert s.startswith("It is hard to confirm that"), s


# ---------- pack swap with same deviation ----------


class TestPackSwapWithDeviation:
    def test_truthfulness_deviation_three_packs_three_phrases(self) -> None:
        a = _surface("default_general_v1", 0.30, {"truthfulness"})
        b = _surface("precision_first_v1", 0.30, {"truthfulness"})
        c = _surface("generosity_first_v1", 0.30, {"truthfulness"})
        assert a.startswith("Evidence is thin that"), a
        assert b.startswith("The evidence does not support that"), b
        # generosity's strong threshold is 0.20; alignment=0.30 is above
        # it, so no hedge fires regardless of deviation.
        assert c == "Truth reveals reality."

    def test_coherence_deviation_three_packs(self) -> None:
        a = _surface("default_general_v1", 0.30, {"coherence"})
        b = _surface("precision_first_v1", 0.30, {"coherence"})
        # default and precision both hedge but with different
        # coherence-specific phrasing.
        assert a.startswith("This does not yet cohere:"), a
        assert b.startswith("This contradicts what is established:"), b


# ---------- lex tie-break ----------


class TestLexTieBreak:
    def test_multiple_deviations_lex_smallest_wins(self) -> None:
        # All three axes deviating — lex-smallest is "coherence" since
        # axis_hedges is in lex order.
        s = _surface(
            "default_general_v1", 0.30,
            {"truthfulness", "coherence", "reverence"},
        )
        assert s.startswith("This does not yet cohere:"), s

    def test_truthfulness_and_reverence_uses_reverence_via_lex(self) -> None:
        # Lex order: "reverence" < "truthfulness", so reverence wins.
        s = _surface(
            "default_general_v1", 0.30,
            {"truthfulness", "reverence"},
        )
        assert s.startswith("Reports suggest"), s


# ---------- depth-language fallback ----------


class TestDepthLanguageFallback:
    def test_hebrew_ignores_axis_hedges(self) -> None:
        s = _surface("default_general_v1", 0.30, {"truthfulness"}, lang="he")
        # Hebrew uses canonical ADR-0030 phrase regardless of deviation.
        assert s.startswith("נראה ש"), s

    def test_greek_ignores_axis_hedges(self) -> None:
        s = _surface("default_general_v1", 0.30, {"coherence"}, lang="grc")
        assert s.startswith("δοκεῖ ὅτι"), s


# ---------- backward compatibility ----------


class TestBackwardCompatibility:
    def test_empty_deviation_axes_matches_adr_0028_behavior(self) -> None:
        # ADR-0028 baseline: default pack at alignment=0.30 with no
        # deviation_axes should produce "It seems that truth reveals reality."
        s = _surface("default_general_v1", 0.30, set())
        assert s == "It seems that truth reveals reality."

    def test_default_surfacecontext_has_empty_decomposition(self) -> None:
        ctx = SurfaceContext()
        assert ctx.deviation_axes == frozenset()
        assert ctx.axis_hedges == ()


# ---------- pack contract: all three v1 packs ship axis_hedges ----------


class TestPackContract:
    def test_all_three_v1_packs_supply_axis_hedges(self) -> None:
        for pack_id in (
            "default_general_v1", "precision_first_v1", "generosity_first_v1",
        ):
            prefs = load_identity_manifold(pack_id).surface_preferences
            # Every v1 pack provides hedges for the three default-pack axes.
            axis_ids = {a for a, _ in prefs.axis_hedges}
            assert {"truthfulness", "coherence", "reverence"} <= axis_ids, (
                f"{pack_id} missing one of the three default-pack axes"
            )

    def test_axis_hedges_in_lex_order(self) -> None:
        prefs = load_identity_manifold("default_general_v1").surface_preferences
        ids = [a for a, _ in prefs.axis_hedges]
        assert ids == sorted(ids)
