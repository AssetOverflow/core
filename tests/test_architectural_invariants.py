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
INV-02  normalize_to_versor is called at the gate only (never in construction paths)
INV-02b unitize_versor is never called inside propagation, generation, or vault recall
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

Normalization doctrine (see algebra/versor.py for full rationale):

  unitize_versor()       — CONSTRUCTION primitive.
                           Legitimate call sites: algebra/, persona/, vocab/
                           (pre-add), and construction helpers therein.
                           INV-02b verifies it does NOT appear in propagation,
                           generation, or vault recall paths.

  normalize_to_versor()  — GATE primitive. ingest/gate.py only.
                           INV-02 verifies no other production file calls it.
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
# INV-02  normalize_to_versor called at the gate only
# ===========================================================================

class TestINV02GateOnlyNormalization:
    """
    Claim: normalize_to_versor() is the injection-gate primitive and is
    called ONLY in ingest/gate.py (production) and algebra/versor.py
    (definition). All other normalization at construction sites must use
    unitize_versor() instead.

    Structural test: AST-walk the source tree and assert no file outside
    the allowed set calls normalize_to_versor.

    Note: algebra/rotor.py and persona/motor.py are construction sites
    that legitimately unitize versors — they use unitize_versor(), which
    is the correct primitive. They do NOT appear in this allowed set
    because they must NOT call normalize_to_versor.
    """

    def test_normalize_not_called_outside_gate(self, tmp_path):
        import ast
        import os

        # Only these files may call normalize_to_versor:
        #   algebra/versor.py  — defines it
        #   ingest/gate.py     — sole production call site
        #   this test file     — calls it in INV-01 test fixtures above
        #   test_versor_closure.py — may use it for test construction
        allowed_files = {
            os.path.join("algebra", "versor.py"),
            os.path.join("ingest",  "gate.py"),
            os.path.join("tests",   "test_architectural_invariants.py"),
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
            "normalize_to_versor() called outside the allowed set.\n"
            "Construction sites must use unitize_versor() instead.\n"
            "Violations:\n" + "\n".join(violations)
        )


# ===========================================================================
# INV-02b  unitize_versor not called inside propagation/generation/vault
# ===========================================================================

class TestINV02bUnitizeNotInPropagation:
    """
    Claim: unitize_versor() is a construction primitive. It must never
    appear inside propagation, generation, or vault recall paths — those
    paths operate on versors that are already unit by construction, and
    any normalization call there would mask a broken algebraic operator.

    Forbidden module roots: field/, generate/, vault/ (recall paths).
    Allowed inside those packages: zero calls to unitize_versor.
    """

    def test_unitize_not_in_propagation_or_generation_or_vault(self):
        import ast
        import os

        # These subtrees must never call unitize_versor:
        forbidden_roots = {"field", "generate", "vault"}

        violations: list[str] = []
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for dirpath, _, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            # Check if this directory is under a forbidden root
            top = rel_dir.split(os.sep)[0]
            if top not in forbidden_roots:
                continue
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fname)
                rel  = os.path.relpath(full, root)
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
                        if name == "unitize_versor":
                            violations.append(f"{rel}:{node.lineno}")

        assert violations == [], (
            "unitize_versor() called inside a propagation, generation, or "
            "vault recall path.\n"
            "If normalization is needed here, the algebraic operator is broken\n"
            "— fix the operator, not the result.\n"
            "Violations:\n" + "\n".join(violations)
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
            if any("semantic_convergence" in w for w in (r.warnings or []))
        ]
        assert len(warned) == 2, (
            f"Expected 2 convergence warnings, got {len(warned)}"
        )
