"""
tests/test_architectural_invariants.py

Machine-verified proofs of CORE's architectural claims.

This file tests the claims that distinguish CORE from standard transformer /
attention-based / vector-store architectures. Every test here is either:

  (A) a mathematical invariant that must hold by construction, or
  (B) a structural/type invariant that must hold by design.

If any test in this file fails, a load-bearing architectural claim of CORE
is broken and must be fixed before any other work proceeds.

Claim index
-----------
INV-01  Versor closure under sandwich product (algebraic closure)
INV-02  normalize_to_versor is called once and only at the gate
INV-03  versor_condition < 1e-5 after injection (gate post-condition)
INV-04  versor_apply is algebraically closed (no normalization needed)
INV-05  Holonomy encoding is deterministic (same input → same output)
INV-06  Null-cone membership is preserved under versor_apply
INV-07  D2-D4 frontends cannot claim AUTO_ACCEPT_ELIGIBLE (governance)
INV-08  pressure_id is content-addressed (same content → same id)
INV-09  semantic_key is claim-addressed (same claim, diff provenance → same key)
INV-10  Structural deduplication: duplicate pressure_id rejected
INV-11  Convergent evidence: same semantic_key from N sources → N-1 warnings
INV-12  ReviewDecision does not mutate original packet
INV-13  Segmenter is D0: identical input → identical output (determinism)
INV-14  Segmenter span byte offsets are valid and within source bounds
INV-15  ModalityPack gate_engaged requires checksum_verified
INV-16  ProjectionHead output is always (32,) float32
INV-17  gate_engaged=False structurally prevents projection
INV-18  Null multivector normalization raises (no silent NaN)
INV-19  SourceSpan byte order enforced at construction
INV-20  FieldState versor condition is preserved after versor_apply
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Algebra imports
# ---------------------------------------------------------------------------
from algebra.versor import versor_apply, normalize_to_versor, versor_condition
from algebra.holonomy import holonomy_encode
from algebra.cl41 import geometric_product, reverse

# ---------------------------------------------------------------------------
# Ingest imports
# ---------------------------------------------------------------------------
from core_ingest.types import (
    CandidateGeometricPressure,
    DeterminismClass,
    FrontendTrace,
    GateDisposition,
    Modality,
    ReviewDecision,
    ReviewLevel,
    SourceSpan,
)
from core_ingest.compiler import IngestCompiler
from core_ingest.segmenter import StructuralSegmenter

# ---------------------------------------------------------------------------
# Sensorium imports
# ---------------------------------------------------------------------------
from sensorium.protocol import CL41_DIM, ModalityPack, ModalityVocabulary
from sensorium.registry import ModalityRegistry
from sensorium.adapters.text import TextProjectionHead, english_pack

# ---------------------------------------------------------------------------
# Field / gate imports
# ---------------------------------------------------------------------------
from ingest.gate import inject


# ===========================================================================
# Shared fixtures
# ===========================================================================

SOURCE = b"In the beginning God created the heavens and the earth."
SOURCE_SHA = hashlib.sha256(SOURCE).hexdigest()


def _span(start: int = 0, end: int = 20) -> SourceSpan:
    return SourceSpan(
        byte_start=start, byte_end=end, source_sha256=SOURCE_SHA, region="body"
    )


def _frontend(det: DeterminismClass = DeterminismClass.D0) -> FrontendTrace:
    return FrontendTrace(
        instrument_id="StructuralSegmenter/prose/v1",
        determinism=det,
        version="1.0.0",
    )


def _packet(
    det:    DeterminismClass = DeterminismClass.D0,
    rl:     ReviewLevel      = ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
    lemma:  str              = "beginning",
    s_off:  int              = 0,
    e_off:  int              = 20,
) -> CandidateGeometricPressure:
    return CandidateGeometricPressure(
        kind="assertion",
        modality=Modality.TEXT,
        provenance=(_span(s_off, e_off),),
        frontend=_frontend(det),
        review_level=rl,
        confidence=0.9,
        uncertainty=0.1,
        lemma=lemma,
        payload_json=json.dumps({"text": SOURCE.decode()}),
    )


def _unit_versor(blade: int = 0) -> np.ndarray:
    """A unit versor in Cl(4,1): 1.0 in blade `blade`, 0 elsewhere."""
    v = np.zeros(32, dtype=np.float64)
    v[blade] = 1.0
    return v


# ===========================================================================
# INV-01  Versor closure under sandwich product
# ===========================================================================

class TestINV01VersorClosure:
    """
    Claim: The sandwich product V * F * reverse(V) is algebraically closed
    on the versor manifold. If V and F are versors, the result is a versor
    — no normalization required.

    This is the foundational claim that makes CORE's field evolution
    correct-by-construction rather than correct-by-convention.
    """

    def test_scalar_versor_preserves_condition(self):
        V = _unit_versor(0)  # scalar blade
        F = _unit_versor(0)
        result = versor_apply(V, F)
        assert versor_condition(result) < 1e-5

    def test_bivector_rotor_preserves_condition(self):
        # A rotor in Cl(4,1): scalar + e12 bivector, normalized
        V = np.zeros(32, dtype=np.float64)
        V[0]  = np.cos(np.pi / 8)   # scalar part
        V[5]  = np.sin(np.pi / 8)   # e12 bivector blade
        V = normalize_to_versor(V)
        F = _unit_versor(1)  # e1 vector
        result = versor_apply(V, F)
        assert versor_condition(result) < 1e-5

    def test_closure_holds_after_10_sequential_applications(self):
        """Closure must hold under iterated application — no drift."""
        V = normalize_to_versor(_unit_versor(0))
        F = normalize_to_versor(_unit_versor(1))
        for _ in range(10):
            F = versor_apply(V, F)
        assert versor_condition(F) < 1e-4  # allow mild float accumulation

    def test_closure_is_not_approximate_luck(self):
        """A non-versor does NOT pass the condition check."""
        bad = np.ones(32, dtype=np.float64) * 0.1  # not a versor
        assert versor_condition(bad) > 1e-3


# ===========================================================================
# INV-02  normalize_to_versor called once, at the gate only
# ===========================================================================

class TestINV02SingleNormalizationSite:
    """
    Claim: normalize_to_versor() is the single normalization call in the
    system and it is called at ingest/gate.py and nowhere else in the
    production path.

    Structural test: grep the source tree for normalize_to_versor calls
    outside of ingest/gate.py and algebra/versor.py (definition).
    """

    def test_normalize_not_called_outside_gate(self, tmp_path):
        import ast
        import os

        allowed_files = {
            os.path.join("algebra", "versor.py"),   # definition
            os.path.join("ingest",  "gate.py"),      # sole call site
            os.path.join("tests",   "test_architectural_invariants.py"),  # this file
            os.path.join("tests",   "test_versor_closure.py"),
        }

        violations: list[str] = []
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fname)
                rel  = os.path.relpath(full, root)
                if rel in allowed_files:
                    continue
                try:
                    src  = open(full, encoding="utf-8").read()
                    tree = ast.parse(src, filename=rel)
                except Exception:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        name = ""
                        if isinstance(func, ast.Name):
                            name = func.id
                        elif isinstance(func, ast.Attribute):
                            name = func.attr
                        if name == "normalize_to_versor":
                            violations.append(f"{rel}:{node.lineno}")

        assert violations == [], (
            "normalize_to_versor() called outside the allowed set:\n"
            + "\n".join(violations)
        )


# ===========================================================================
# INV-03  Gate post-condition: versor_condition < 1e-5 after injection
# ===========================================================================

class TestINV03GatePostCondition:
    """
    Claim: Every FieldState produced by ingest/gate.py satisfies
    versor_condition(F) < 1e-5.
    """

    def test_single_token_injection(self):
        """A minimal vocab stub satisfies the gate post-condition."""
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64)
                v[0] = 1.0
                return v

        state = inject(["logos"], _Vocab())
        assert versor_condition(state.F) < 1e-5

    def test_multi_token_injection(self):
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64)
                v[0] = 1.0
                v[1] = 0.1 * hash(t) % 10 * 0.01  # small perturbation per token
                v = v / np.sqrt(abs(v @ v) or 1.0)
                return v

        state = inject(["in", "the", "beginning"], _Vocab())
        assert versor_condition(state.F) < 1e-5


# ===========================================================================
# INV-04  versor_apply is algebraically closed (no post-normalization)
# ===========================================================================

class TestINV04VersorApplyClosed:
    """
    Claim: versor_apply does not call normalize_to_versor internally.
    The closure property is algebraic, not enforced by renormalization.
    """

    def test_no_normalization_in_versor_apply_source(self):
        import inspect
        src = inspect.getsource(versor_apply)
        assert "normalize_to_versor" not in src, (
            "versor_apply must not call normalize_to_versor. "
            "Closure is algebraic, not enforced by renormalization."
        )

    def test_apply_result_passes_condition_without_renormalization(self):
        V = normalize_to_versor(_unit_versor(0))
        F = normalize_to_versor(_unit_versor(1))
        result = versor_apply(V, F)
        # No renormalization — must still pass
        assert versor_condition(result) < 1e-5


# ===========================================================================
# INV-05  Holonomy encoding is deterministic
# ===========================================================================

class TestINV05HolonomyDeterminism:
    """
    Claim: holonomy_encode() is a pure function — given identical inputs it
    produces identical outputs. This is required for D0 classification of
    the gate's encoding step.
    """

    def test_same_versors_same_output(self):
        versors = [_unit_versor(i % 5) for i in range(5)]
        H1 = holonomy_encode(versors)
        H2 = holonomy_encode(versors)
        np.testing.assert_array_equal(H1, H2)

    def test_different_order_different_output(self):
        v1 = _unit_versor(0)
        v2 = _unit_versor(1)
        H_ab = holonomy_encode([v1, v2])
        H_ba = holonomy_encode([v2, v1])
        # Order sensitivity: holonomy is not commutative
        assert not np.allclose(H_ab, H_ba), (
            "Holonomy should be order-sensitive — the geometric product "
            "is non-commutative in Cl(4,1)."
        )

    def test_determinism_across_100_calls(self):
        versors = [normalize_to_versor(_unit_versor(i % 32)) for i in range(4)]
        results = [holonomy_encode(versors) for _ in range(100)]
        for r in results[1:]:
            np.testing.assert_array_equal(r, results[0])


# ===========================================================================
# INV-06  Null-cone membership preserved under versor_apply
# ===========================================================================

class TestINV06NullConePreservation:
    """
    Claim: versor_apply maps null vectors to null vectors.
    A null vector x in Cl(4,1) satisfies x * x = 0 (up to float tolerance).
    This ensures vocabulary tokens (null vectors) remain on the null cone
    after field transitions.
    """

    def _null_vector(self) -> np.ndarray:
        """Construct the canonical o (origin) null vector in CGA Cl(4,1)."""
        # In CGA: o = (e_minus - e_plus) / 2 where e_minus^2=-1, e_plus^2=+1
        # Using the Cl(4,1) blade indexing from algebra/cl41.py:
        # blade 3 = e3, blade 4 = e4 (the extra CGA basis vectors)
        # A simple null vector: e1 + e_inf where e_inf = e4+e3 (metric-dependent)
        # For this test we construct numerically.
        v = np.zeros(32, dtype=np.float64)
        v[1] = 1.0   # e1
        v[2] = 1.0   # e2
        # Make null: x*x = 0 requires careful construction per the metric.
        # Use a known null vector from the CGA embedding instead.
        # e_o = 0.5*(e_minus - e_plus): in our 32-dim basis this is blade index 3+4
        v = np.zeros(32, dtype=np.float64)
        v[3] =  0.5   # e3 component
        v[4] = -0.5   # e4 component (opposite sign for null condition in Cl(4,1))
        return v

    def test_null_vector_self_product_is_zero(self):
        n = self._null_vector()
        nn = geometric_product(n, n)
        assert abs(scalar_part := nn[0]) < 1e-10, (
            f"Null vector self-product scalar part = {scalar_part:.2e}, expected ~0"
        )

    def test_versor_apply_preserves_null_property(self):
        n = self._null_vector()
        V = normalize_to_versor(_unit_versor(0))  # identity-like rotor
        result = versor_apply(V, n)
        rr = geometric_product(result, result)
        assert abs(rr[0]) < 1e-9, (
            f"versor_apply broke null property: x*x scalar = {rr[0]:.2e}"
        )


# ===========================================================================
# INV-07  Governance invariant: D2-D4 cannot claim AUTO_ACCEPT_ELIGIBLE
# ===========================================================================

class TestINV07GovernanceInvariant:
    """
    Claim: The AUTO_ACCEPT_ELIGIBLE status is structurally unavailable to
    D2-D4 frontends. This is enforced at packet construction time by the
    type system, not by a runtime policy check.
    """

    @pytest.mark.parametrize("det", [
        DeterminismClass.D2,
        DeterminismClass.D3,
        DeterminismClass.D4,
    ])
    def test_nondeterministic_frontend_cannot_claim_auto_accept(self, det):
        with pytest.raises(ValueError, match="AUTO_ACCEPT_ELIGIBLE"):
            _packet(det=det, rl=ReviewLevel.AUTO_ACCEPT_ELIGIBLE)

    @pytest.mark.parametrize("det", [
        DeterminismClass.D0,
        DeterminismClass.D1,
    ])
    def test_deterministic_frontend_can_claim_auto_accept(self, det):
        p = _packet(det=det, rl=ReviewLevel.AUTO_ACCEPT_ELIGIBLE)
        assert p.review_level == ReviewLevel.AUTO_ACCEPT_ELIGIBLE


# ===========================================================================
# INV-08  pressure_id is content-addressed
# ===========================================================================

class TestINV08PressureIdContentAddressed:
    """
    Claim: Two packets with identical content have identical pressure_ids.
    Two packets with any field difference have different pressure_ids.
    """

    def test_identical_content_identical_id(self):
        p1 = _packet()
        p2 = _packet()
        assert p1.pressure_id == p2.pressure_id

    def test_different_provenance_different_id(self):
        p1 = _packet(s_off=0,  e_off=20)
        p2 = _packet(s_off=10, e_off=30)
        assert p1.pressure_id != p2.pressure_id

    def test_different_lemma_different_id(self):
        p1 = _packet(lemma="beginning")
        p2 = _packet(lemma="earth")
        assert p1.pressure_id != p2.pressure_id


# ===========================================================================
# INV-09  semantic_key is claim-addressed
# ===========================================================================

class TestINV09SemanticKeyClaimAddressed:
    """
    Claim: Two packets asserting the same semantic claim share a semantic_key
    regardless of provenance, instrument, or confidence values.
    """

    def test_same_claim_different_provenance_same_key(self):
        p1 = _packet(s_off=0,  e_off=20)
        p2 = _packet(s_off=50, e_off=70)
        assert p1.semantic_key == p2.semantic_key

    def test_different_claim_different_key(self):
        p1 = _packet(lemma="beginning")
        p2 = _packet(lemma="darkness")
        assert p1.semantic_key != p2.semantic_key

    def test_semantic_key_stable_across_constructions(self):
        keys = {_packet(lemma="light").semantic_key for _ in range(50)}
        assert len(keys) == 1, "semantic_key must be deterministic"


# ===========================================================================
# INV-10  Structural deduplication
# ===========================================================================

class TestINV10StructuralDeduplication:
    """
    Claim: The IngestCompiler rejects the second submission of a packet with
    an already-seen pressure_id within the same batch.
    """

    def test_duplicate_rejected(self):
        p = _packet()
        compiler = IngestCompiler()
        report, _ = compiler.compile([p, p])
        assert len(report.accepted_ids) == 1
        assert len(report.rejected_ids) == 1
        dup_result = report.results[1]
        assert dup_result.disposition == GateDisposition.REJECTED_PROVENANCE
        assert "duplicate" in (dup_result.failure_reason or "")


# ===========================================================================
# INV-11  Convergent evidence detection
# ===========================================================================

class TestINV11ConvergentEvidence:
    """
    Claim: When N packets share a semantic_key (same claim, N independent
    provenance sources), packets 2..N receive a
    'semantic_convergence:<k>_prior_sources' warning.
    """

    def test_three_independent_sources_two_warnings(self):
        p1 = _packet(s_off=0,  e_off=20)
        p2 = _packet(s_off=30, e_off=50)
        p3 = _packet(s_off=60, e_off=80)
        assert p1.semantic_key == p2.semantic_key == p3.semantic_key
        compiler = IngestCompiler()
        report, _ = compiler.compile([p1, p2, p3])
        warned = [
            r for r in report.results
            if any("semantic_convergence" in w for w in r.warnings)
        ]
        assert len(warned) == 2


# ===========================================================================
# INV-12  ReviewDecision does not mutate original packet
# ===========================================================================

class TestINV12ReviewDecisionImmutability:
    """
    Claim: A ReviewDecision authorizes acceptance of a packet without
    modifying the original packet. The packet's review_level remains
    ARCHITECT_REVIEW_REQUIRED after the override.
    """

    def test_packet_immutable_after_override(self):
        p = _packet(det=DeterminismClass.D4, rl=ReviewLevel.ARCHITECT_REVIEW_REQUIRED)
        original_rl = p.review_level
        decision = ReviewDecision(
            authorized_ids=frozenset({p.pressure_id}),
            authorized_by="joshua.shay",
            reason="Reviewed.",
        )
        compiler = IngestCompiler()
        report, artifacts = compiler.compile([p], review_decision=decision)
        # Accepted via override
        assert p.pressure_id in report.accepted_ids
        # Original packet is unchanged
        assert p.review_level == original_rl
        assert artifacts[0].packet is p


# ===========================================================================
# INV-13  Segmenter is D0: deterministic
# ===========================================================================

class TestINV13SegmenterDeterminism:
    """
    Claim: StructuralSegmenter is a D0 instrument — identical source bytes
    produce identical segments on every call, with no external state.
    """

    @pytest.mark.parametrize("hint", ["prose", "scripture", "code", "math"])
    def test_identical_input_identical_output(self, hint):
        sources = {
            "prose":     b"# Title\n\nFirst paragraph.\n\nSecond.",
            "scripture": b"Gen 1:1 In the beginning.\nGen 1:2 Formless.",
            "code":      b"```python\nprint('logos')\n```",
            "math":      rb"\[E = mc^2\]",
        }
        seg = StructuralSegmenter()
        source = sources[hint]
        results_a = seg.segment(source, modality_hint=hint)
        results_b = seg.segment(source, modality_hint=hint)
        assert len(results_a) == len(results_b)
        for a, b in zip(results_a, results_b):
            assert a.span.byte_start   == b.span.byte_start
            assert a.span.byte_end     == b.span.byte_end
            assert a.span.source_sha256 == b.span.source_sha256
            assert a.text              == b.text

    def test_100_repeated_calls_identical(self):
        seg    = StructuralSegmenter()
        source = b"# Logos\n\nIn the beginning was the Word."
        first  = seg.segment(source, modality_hint="prose")
        for _ in range(99):
            result = seg.segment(source, modality_hint="prose")
            for a, b in zip(first, result):
                assert a.span.byte_start == b.span.byte_start
                assert a.text == b.text


# ===========================================================================
# INV-14  Segmenter byte offsets valid
# ===========================================================================

class TestINV14SegmenterByteOffsets:
    """
    Claim: Every SourceSpan produced by the segmenter has:
    - byte_start >= 0
    - byte_end > byte_start
    - byte_end <= len(source)
    - source_sha256 == sha256(source)
    """

    @pytest.mark.parametrize("hint,source", [
        ("prose",     b"# Title\n\nBody text here."),
        ("scripture", b"Gen 1:1 Beginning.\nGen 1:2 Void."),
        ("code",      b"```py\npass\n```"),
        ("math",      rb"\[x^2\]"),
    ])
    def test_offsets_valid(self, hint, source):
        expected_sha = hashlib.sha256(source).hexdigest()
        seg = StructuralSegmenter()
        for s in seg.segment(source, modality_hint=hint):
            assert s.span.byte_start >= 0
            assert s.span.byte_end > s.span.byte_start
            assert s.span.byte_end <= len(source)
            assert s.span.source_sha256 == expected_sha


# ===========================================================================
# INV-15  ModalityPack gate invariant
# ===========================================================================

class TestINV15ModalityPackGateInvariant:
    """
    Claim: gate_engaged=True cannot be set without checksum_verified=True.
    Structural enforcement at construction time.
    """

    def test_gate_engaged_without_checksum_raises(self):
        vocab = ModalityVocabulary()
        head  = TextProjectionHead(vocab)
        with pytest.raises(ValueError, match="checksum_verified"):
            ModalityPack(
                pack_id="test",
                modality_type=sensorium_modality,
                projection=head,
                decoder=None,
                vocabulary=vocab,
                grammar_scaffold=None,
                checksum_verified=False,
                gate_engaged=True,
            )

    def test_gate_not_engaged_with_unverified_is_ok(self):
        from sensorium.protocol import Modality as SModality
        vocab = ModalityVocabulary()
        pack  = ModalityPack(
            pack_id="ungated",
            modality_type=SModality.TEXT,
            vocabulary=vocab,
            grammar_scaffold=None,
            checksum_verified=False,
            gate_engaged=False,
        )
        assert not pack.gate_engaged


# ---------------------------------------------------------------------------
# local alias to avoid import name collision
# ---------------------------------------------------------------------------
from sensorium.protocol import Modality as sensorium_modality  # noqa: E402
# Reassign after class to satisfy the class body reference above:
TestINV15ModalityPackGateInvariant  # force evaluation


# ===========================================================================
# INV-16  ProjectionHead output is (32,) float32
# ===========================================================================

class TestINV16ProjectionOutputShape:
    """
    Claim: Every projection through the sensorium layer returns a (32,)
    float32 array — the canonical Cl(4,1) multivector shape.
    """

    def test_single_projection_shape_and_dtype(self):
        from sensorium.protocol import ModalityVocabulary
        vocab = ModalityVocabulary()
        rotor = np.zeros(CL41_DIM, dtype=np.float32)
        rotor[0] = 1.0
        vocab.register("logos", rotor)
        head = TextProjectionHead(vocab)
        mv   = head.project("logos")
        assert mv.shape == (CL41_DIM,)
        assert mv.dtype == np.float32

    def test_oov_projection_shape_and_dtype(self):
        head = TextProjectionHead(ModalityVocabulary())
        mv   = head.project("__oov__")
        assert mv.shape == (CL41_DIM,)
        assert mv.dtype == np.float32

    def test_registry_project_enforces_shape(self):
        vocab = ModalityVocabulary()
        r = np.zeros(CL41_DIM, dtype=np.float32); r[0] = 1.0
        vocab.register("word", r)
        registry = ModalityRegistry()
        registry.mount(english_pack(vocab))
        mv = registry.project("en", "word")
        assert mv.shape == (CL41_DIM,)
        assert mv.dtype == np.float32


# ===========================================================================
# INV-17  gate_engaged=False blocks projection
# ===========================================================================

class TestINV17GateEngagedBlocksProjection:
    """
    Claim: A ModalityPack with gate_engaged=False structurally prevents
    projection through the registry. This enforces the Supervised Seeding
    Epoch protocol — Hebrew and Koine Greek cannot be used for inference
    until their seeding epoch completes.
    """

    def test_hebrew_gate_off_blocks_project(self):
        from sensorium.adapters.text import hebrew_pack
        vocab = ModalityVocabulary()
        r = np.zeros(CL41_DIM, dtype=np.float32); r[0] = 1.0
        vocab.register("bereshit", r)
        registry = ModalityRegistry()
        registry.mount(hebrew_pack(vocab))
        with pytest.raises(RuntimeError, match="gate is not engaged"):
            registry.project("he", "bereshit")

    def test_koine_greek_gate_off_blocks_project(self):
        from sensorium.adapters.text import koine_greek_pack
        vocab = ModalityVocabulary()
        r = np.zeros(CL41_DIM, dtype=np.float32); r[0] = 1.0
        vocab.register("logos", r)
        registry = ModalityRegistry()
        registry.mount(koine_greek_pack(vocab))
        with pytest.raises(RuntimeError, match="gate is not engaged"):
            registry.project("grc", "logos")


# ===========================================================================
# INV-18  Null multivector normalization raises
# ===========================================================================

class TestINV18NullNormalizationRaises:
    """
    Claim: normalize_to_versor raises ValueError on a null multivector
    (norm_squared ≈ 0). There is no silent NaN propagation.
    NaN in the manifold would be structurally undetectable and
    catastrophically wrong.
    """

    def test_zero_vector_raises(self):
        with pytest.raises(ValueError, match="null"):
            normalize_to_versor(np.zeros(32, dtype=np.float64))

    def test_near_zero_raises(self):
        v = np.zeros(32, dtype=np.float64)
        v[0] = 1e-15  # effectively zero after squaring
        with pytest.raises(ValueError):
            normalize_to_versor(v)


# ===========================================================================
# INV-19  SourceSpan byte order enforced
# ===========================================================================

class TestINV19SourceSpanByteOrder:
    """
    Claim: SourceSpan enforces byte_end > byte_start at construction.
    A reversed or zero-length span is structurally impossible.
    """

    def test_reversed_offsets_raise(self):
        with pytest.raises(ValueError):
            SourceSpan(byte_start=50, byte_end=10, source_sha256="a" * 64)

    def test_equal_offsets_raise(self):
        with pytest.raises(ValueError):
            SourceSpan(byte_start=10, byte_end=10, source_sha256="a" * 64)

    def test_valid_span_constructs(self):
        span = SourceSpan(byte_start=0, byte_end=1, source_sha256="a" * 64)
        assert span.byte_end > span.byte_start


# ===========================================================================
# INV-20  FieldState versor condition preserved after versor_apply
# ===========================================================================

class TestINV20FieldStateVersorPreserved:
    """
    Claim: Applying versor_apply to a valid FieldState's F array produces
    a result that still satisfies versor_condition < 1e-5. The field
    evolution never leaves the versor manifold.
    """

    def test_field_stays_on_manifold_after_transition(self):
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64); v[0] = 1.0; return v

        state = inject(["logos"], _Vocab())
        V     = normalize_to_versor(_unit_versor(0))
        F_new = versor_apply(V, state.F)
        assert versor_condition(F_new) < 1e-5

    def test_ten_successive_transitions_stay_on_manifold(self):
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64); v[0] = 1.0; return v

        state = inject(["word"], _Vocab())
        F = state.F
        V = normalize_to_versor(_unit_versor(0))
        for _ in range(10):
            F = versor_apply(V, F)
        assert versor_condition(F) < 1e-4
