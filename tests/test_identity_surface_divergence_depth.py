"""ADR-0030 — verify pack swap affects Hebrew and Koine Greek surfaces.

ADR-0028 wired identity-pack ``surface_preferences`` into English
assembly only.  ADR-0030 extends the same algorithm to Hebrew and Greek
with language-appropriate hedge phrases (canonical defaults baked into
``generate/surface.py`` until a future schema bump allows per-pack
overrides).

These tests prove the depth-language surfaces:

* Hedge bands fire correctly at the same thresholds as English.
* Hebrew hedges use Hebrew phrases (``"נראה ש"`` / ``"אולי"``); Greek
  hedges use Greek phrases (``"δοκεῖ ὅτι"`` / ``"ἴσως"``).
* Pack swap → different hedge band entry points across languages.
* Claim-strength "qualified" prepends the language-specific qualifier
  in the marginal band.
"""

from __future__ import annotations

import pytest

from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SurfaceContext
from packs.identity.loader import load_identity_manifold

_ASSEMBLER = SentenceAssembler()

# Hebrew hedge phrases (must match ``_DEPTH_HEDGE_PHRASES["he"]`` in surface.py).
_HE_HEDGE_STRONG = "נראה ש"
_HE_HEDGE_SOFT = "אולי"
_HE_QUALIFIER = "במקרים מסוימים,"

# Greek hedge phrases (must match ``_DEPTH_HEDGE_PHRASES["grc"]``).
_GRC_HEDGE_STRONG = "δοκεῖ ὅτι"
_GRC_HEDGE_SOFT = "ἴσως"
_GRC_QUALIFIER = "ἐνίοτε,"


def _plan(lang: str) -> ArticulationPlan:
    return ArticulationPlan(
        subject="logos" if lang == "grc" else "truth" if lang == "en" else "אמת",
        predicate="reveals" if lang == "en" else "מגלה" if lang == "he" else "ἀποκαλύπτει",
        object="reality" if lang == "en" else "מציאות" if lang == "he" else "πραγματικότητα",
        surface="",
        output_language=lang,
        frame_id="default",
    )


def _ctx_from_pack(pack_id: str, alignment: float) -> SurfaceContext:
    prefs = load_identity_manifold(pack_id).surface_preferences
    return SurfaceContext(
        identity_alignment=alignment,
        hedge_threshold_strong=prefs.hedge_threshold_strong,
        hedge_threshold_soft=prefs.hedge_threshold_soft,
        preferred_hedge_strong=prefs.preferred_hedge_strong,
        preferred_hedge_soft=prefs.preferred_hedge_soft,
        claim_strength=prefs.claim_strength,
        qualified_band_high=prefs.qualified_band_high,
        preferred_qualifier=prefs.preferred_qualifier,
    )


def _surface(pack_id: str, alignment: float, lang: str) -> str:
    return _ASSEMBLER.assemble(
        _plan(lang), tokens=[], role="assert", context=_ctx_from_pack(pack_id, alignment),
    ).surface


# ---------- Hebrew hedge bands ----------


class TestHebrewHedgeBands:
    def test_high_alignment_is_bare(self) -> None:
        s = _surface("default_general_v1", 0.9, "he")
        assert _HE_HEDGE_STRONG not in s
        assert _HE_HEDGE_SOFT not in s

    def test_strong_hedge_under_default(self) -> None:
        s = _surface("default_general_v1", 0.3, "he")
        assert s.startswith(_HE_HEDGE_STRONG), s

    def test_soft_hedge_under_default(self) -> None:
        s = _surface("default_general_v1", 0.45, "he")
        assert s.startswith(_HE_HEDGE_SOFT), s

    def test_precision_pushes_hedges_to_higher_alignment(self) -> None:
        # alignment=0.60 is bare under default (soft=0.50) but in
        # precision's soft band (strong=0.55, soft=0.70).
        default_surface = _surface("default_general_v1", 0.60, "he")
        precision_surface = _surface("precision_first_v1", 0.60, "he")
        # Default leaves bare; precision applies soft hedge "אולי" (default
        # phrase, since v1 packs don't override per-language).
        assert _HE_HEDGE_SOFT not in default_surface
        assert precision_surface.startswith(_HE_HEDGE_SOFT)

    def test_generosity_pulls_hedges_to_lower_alignment(self) -> None:
        # alignment=0.45 is in default's soft band but above generosity's
        # soft (0.30).
        default_surface = _surface("default_general_v1", 0.45, "he")
        generosity_surface = _surface("generosity_first_v1", 0.45, "he")
        assert default_surface.startswith(_HE_HEDGE_SOFT)
        assert _HE_HEDGE_SOFT not in generosity_surface


# ---------- Greek hedge bands ----------


class TestGreekHedgeBands:
    def test_high_alignment_is_bare(self) -> None:
        s = _surface("default_general_v1", 0.9, "grc")
        assert _GRC_HEDGE_STRONG not in s
        assert _GRC_HEDGE_SOFT not in s

    def test_strong_hedge_under_default(self) -> None:
        s = _surface("default_general_v1", 0.3, "grc")
        assert s.startswith(_GRC_HEDGE_STRONG), s

    def test_soft_hedge_under_default(self) -> None:
        s = _surface("default_general_v1", 0.45, "grc")
        assert s.startswith(_GRC_HEDGE_SOFT), s

    def test_precision_qualified_band_uses_greek_qualifier(self) -> None:
        # alignment=0.80 is in precision's marginal band [0.70, 0.85) and
        # precision's claim_strength is "qualified".  The Greek qualifier
        # "ἐνίοτε," should be prepended.
        s = _surface("precision_first_v1", 0.80, "grc")
        assert s.startswith(_GRC_QUALIFIER), s

    def test_generosity_affirmative_never_qualifies_in_greek(self) -> None:
        s = _surface("generosity_first_v1", 0.40, "grc")
        # No hedge (above soft=0.30), no qualifier (affirmative).
        assert _GRC_QUALIFIER not in s
        assert _GRC_HEDGE_SOFT not in s


# ---------- pack-swap divergence proof ----------


class TestDepthPackSwapDivergence:
    def test_hebrew_pack_swap_visible_at_alignment_0p45(self) -> None:
        a = _surface("default_general_v1", 0.45, "he")
        b = _surface("precision_first_v1", 0.45, "he")
        c = _surface("generosity_first_v1", 0.45, "he")
        assert a != b
        assert a != c
        assert b != c

    def test_greek_pack_swap_visible_at_alignment_0p45(self) -> None:
        a = _surface("default_general_v1", 0.45, "grc")
        b = _surface("precision_first_v1", 0.45, "grc")
        c = _surface("generosity_first_v1", 0.45, "grc")
        assert a != b
        assert a != c
        assert b != c

    def test_all_three_languages_diverge_under_same_pack(self) -> None:
        """English / Hebrew / Greek hedges use language-specific phrases."""
        en = _surface("default_general_v1", 0.3, "en")
        he = _surface("default_general_v1", 0.3, "he")
        grc = _surface("default_general_v1", 0.3, "grc")
        # Each language's strong-hedge phrase appears in its own surface,
        # not in others'.
        assert "It seems that" in en
        assert _HE_HEDGE_STRONG in he
        assert _GRC_HEDGE_STRONG in grc
        assert _HE_HEDGE_STRONG not in en
        assert _GRC_HEDGE_STRONG not in he


# ---------- backward compatibility ----------


class TestBackwardCompatibility:
    def test_he_assembly_without_ctx_unchanged(self) -> None:
        """Hebrew assembly with context=None must match pre-ADR-0030 output."""
        plan = _plan("he")
        result = _ASSEMBLER.assemble(plan, tokens=[], role="assert", context=None)
        # Pre-ADR Hebrew assembly: "predicate subject object."
        assert result.surface == "מגלה אמת מציאות."

    def test_grc_assembly_without_ctx_unchanged(self) -> None:
        """Greek assembly with context=None must match pre-ADR-0030 output."""
        plan = _plan("grc")
        result = _ASSEMBLER.assemble(plan, tokens=[], role="assert", context=None)
        # Pre-ADR Greek assembly: subject object predicate.
        assert result.surface == "Logos πραγματικότητα ἀποκαλύπτει."
