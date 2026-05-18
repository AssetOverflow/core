"""ADR-0028 — verify pack swap produces visibly different surfaces.

The pre-ADR-0028 hedge logic only consulted ``identity_alignment``.  Now
every band of the hedge / claim-strength decision tree is parameterized
by the loaded identity pack's ``surface_preferences``.  These tests
prove that swapping packs yields different surfaces on identical
trajectories.

The tests bypass the cognitive pipeline and hit ``_apply_hedge`` /
``_assemble_en`` directly: we construct a :class:`SurfaceContext`
populated from each pack's preferences and check the output strings.
This isolates the surface-layer change from upstream non-determinism
(referent state, valence, etc.) so test failures point exactly at the
ADR-0028 logic.
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SurfaceContext
from packs.identity.loader import load_identity_manifold


_ASSEMBLER = SentenceAssembler()


def _plan() -> ArticulationPlan:
    return ArticulationPlan(
        subject="truth",
        predicate="reveals",
        object="reality",
        surface="",
        output_language="en",
        frame_id="default",
    )


def _ctx_from_pack(pack_id: str, alignment: float) -> SurfaceContext:
    manifold = load_identity_manifold(pack_id)
    prefs = manifold.surface_preferences
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


def _surface(pack_id: str, alignment: float) -> str:
    return _ASSEMBLER.assemble(
        _plan(), tokens=[], role="assert", context=_ctx_from_pack(pack_id, alignment),
    ).surface


# ---------- Phase A: hedge bands per pack ----------


class TestHedgeBands:
    def test_default_general_at_high_alignment_is_bare(self) -> None:
        # alignment=0.9 is above every pack's hedge band → bare assertion.
        s = _surface("default_general_v1", 0.9)
        assert s == "Truth reveals reality."

    def test_default_general_strong_hedge(self) -> None:
        # alignment=0.3 is below default's hedge_threshold_strong (0.40).
        s = _surface("default_general_v1", 0.3)
        assert s.startswith("It seems that truth")

    def test_default_general_soft_hedge(self) -> None:
        # alignment=0.45 is between strong (0.40) and soft (0.50).
        s = _surface("default_general_v1", 0.45)
        assert s.startswith("Perhaps truth")

    def test_precision_uses_arguably_at_low_alignment(self) -> None:
        # alignment=0.45 is below precision's strong (0.55).
        s = _surface("precision_first_v1", 0.45)
        assert s.startswith("Arguably, truth"), s

    def test_precision_uses_in_some_cases_in_soft_band(self) -> None:
        # alignment=0.60 is in [0.55, 0.70) for precision.
        s = _surface("precision_first_v1", 0.60)
        assert s.startswith("In some cases, truth"), s

    def test_generosity_skips_hedge_at_default_band(self) -> None:
        # alignment=0.45 would hedge under default; generosity's soft is
        # 0.30, so 0.45 leaves the assertion bare.
        s = _surface("generosity_first_v1", 0.45)
        assert s == "Truth reveals reality."


# ---------- Phase B: claim_strength outside the hedge band ----------


class TestClaimStrength:
    def test_precision_qualified_band_prepends_qualifier(self) -> None:
        # alignment=0.80 is above precision's soft (0.70) but below its
        # qualified_band_high (0.85); claim_strength="qualified" → prepend
        # preferred_qualifier ("Under certain conditions,").
        s = _surface("precision_first_v1", 0.80)
        assert s.startswith("Under certain conditions, truth"), s

    def test_precision_above_qualified_band_is_bare(self) -> None:
        # alignment=0.90 is above qualified_band_high (0.85) → no qualifier.
        s = _surface("precision_first_v1", 0.90)
        assert s == "Truth reveals reality."

    def test_default_balanced_no_qualifier_in_marginal_band(self) -> None:
        # claim_strength="balanced" → no marginal-band qualifier.
        s = _surface("default_general_v1", 0.60)
        assert s == "Truth reveals reality."

    def test_generosity_affirmative_never_qualifies(self) -> None:
        # claim_strength="affirmative" → no marginal-band qualifier.
        s = _surface("generosity_first_v1", 0.40)
        assert s == "Truth reveals reality."


# ---------- pack-swap divergence proof ----------


class TestPackSwapDivergence:
    def test_same_alignment_different_surfaces(self) -> None:
        """The ADR-0028 promise: identical inputs, different packs, different surfaces."""
        alignment = 0.45  # in default's hedge band, outside generosity's
        a = _surface("default_general_v1", alignment)
        b = _surface("precision_first_v1", alignment)
        c = _surface("generosity_first_v1", alignment)
        assert a != b, "default vs precision should differ at alignment=0.45"
        assert a != c, "default vs generosity should differ at alignment=0.45"
        assert b != c, "precision vs generosity should differ at alignment=0.45"

    def test_qualified_band_only_for_precision(self) -> None:
        alignment = 0.80  # above all soft thresholds; only precision qualifies here
        a = _surface("default_general_v1", alignment)
        b = _surface("precision_first_v1", alignment)
        c = _surface("generosity_first_v1", alignment)
        assert a == "Truth reveals reality."
        assert b.startswith("Under certain conditions, truth")
        assert c == "Truth reveals reality."


# ---------- runtime wiring ----------


class TestRuntimeContextWiring:
    def test_default_runtime_context_carries_default_prefs(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        ctx = rt._build_surface_context(None, current_valence=0.0)
        assert ctx.hedge_threshold_strong == 0.40
        assert ctx.preferred_hedge_strong == "It seems that"
        assert ctx.claim_strength == "balanced"

    def test_precision_runtime_context_carries_precision_prefs(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack="precision_first_v1"))
        ctx = rt._build_surface_context(None, current_valence=0.0)
        assert ctx.hedge_threshold_strong == 0.55
        assert ctx.preferred_hedge_strong == "Arguably,"
        assert ctx.claim_strength == "qualified"
        assert ctx.qualified_band_high == 0.85

    def test_generosity_runtime_context_carries_generosity_prefs(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack="generosity_first_v1"))
        ctx = rt._build_surface_context(None, current_valence=0.0)
        assert ctx.hedge_threshold_soft == 0.30
        assert ctx.claim_strength == "affirmative"
