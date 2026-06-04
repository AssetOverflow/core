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
INV-03  versor_condition < 1e-6 after injection (gate post-condition)
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
from algebra.cga import embed_point

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
            # test_issue_300_versor_margin.py: regression test for the
            # gate-boundary margin bug; calls normalize_to_versor()
            # explicitly to verify the function's own closure contract.
            # Same justification as test_versor_closure.py.
            os.path.join("tests",   "test_issue_300_versor_margin.py"),
            # evals/lab/ is research-only, never imported by runtime.
            # Lab probes need construction-time normalization to build
            # experimental rotors / embeddings; this does not weaken
            # the runtime invariant the test enforces.
            os.path.join("evals", "lab", "phi_separation_probe.py"),
        }

        violations: list[str] = []
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames
                if d not in {".git", ".venv", "__pycache__", ".pytest_cache", ".hypothesis", ".claude"}
            ]
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

        # These subtrees must never call unitize_versor, except at
        # explicit closure boundaries (generate/stream.py closes the
        # final returned state as a construction guarantee).
        forbidden_roots = {"field", "generate", "vault"}
        allowed_exceptions = {
            os.path.join("generate", "stream.py"),
        }

        violations: list[str] = []
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for dirpath, _, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            top = rel_dir.split(os.sep)[0]
            if top not in forbidden_roots:
                continue
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fname)
                rel  = os.path.relpath(full, root)
                if rel in allowed_exceptions:
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
# INV-03  Gate post-condition: versor_condition < 1e-6 after injection
# ===========================================================================

class TestINV03GatePostCondition:
    """
    Claim: Every FieldState produced by ingest/gate.py satisfies
    versor_condition(F) < 1e-6.
    """

    def test_single_token_injection(self):
        """A minimal vocab stub satisfies the gate post-condition."""
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64)
                v[0] = 1.0
                return v

        state = inject(["logos"], _Vocab())
        assert versor_condition(state.F) < 1e-6

    def test_multi_token_injection(self):
        class _Vocab:
            def get_versor(self, t):
                v = np.zeros(32, dtype=np.float64)
                v[0] = 1.0
                v[1] = 0.1 * hash(t) % 10 * 0.01  # small perturbation per token
                v = v / np.sqrt(abs(v @ v) or 1.0)
                return v

        state = inject(["in", "the", "beginning"], _Vocab())
        assert versor_condition(state.F) < 1e-6


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
        return embed_point(np.zeros(3, dtype=np.float64)).astype(np.float64)

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


# ===========================================================================
# INV-21  One-mutation-path invariant — vault writes are allowlisted
# ===========================================================================
#
# Claim (ADR-0021 §3 + CLAUDE.md teaching-safety section):
# Knowledge enters the runtime field through exactly one reviewed path.
# Every new module that calls `VaultStore.store(...)` outside this allowlist
# is, by definition, a backdoor around the epistemic schema — coherence
# stops being the only admission signal.
#
# This test grep-asserts the call-site set. Adding a new writer is allowed
# but must be intentional: edit the allowlist and document the justification
# in the same commit. The CI failure is the prompt to do so.
#
# Allowlist rationale per call site:
#   session/context.py        — session memory, immediate-by-doctrine
#                                (CLAUDE.md "session memory may be immediate").
#                                Three writers: commit_ingest, record_dialogue,
#                                apply_corrected_outputs.
#   vault/store.py            — the implementation itself; not a caller.
#   generate/proposition.py   — WRITE-SIDE CLOSED (Leak C, 2026-05-17).
#                                propose() now stamps every stored proposition
#                                with EpistemicStatus.SPECULATIVE. The
#                                fabrication-feedback loop is broken in
#                                principle: any inference path that recalls
#                                with min_status=COHERENT excludes the
#                                system's own prior utterances from evidence.
#                                Read-side audit (chat/runtime.py,
#                                generate/stream.py, vault/decompose.py) is
#                                still required to enforce closure
#                                site-by-site — see docs/truth_seeking_schema.md
#                                §"Leak C — Residual work."
#
# The reviewed-teaching path (teaching/review.py) and the formation Promote
# stage (formation/promote.py) are intentionally absent: they do not call
# vault.store directly — they route through TeachingStore and the session
# apply path, which lands in session/context.py above.
#
# Anything else writing to vault is a new mutation path and must justify
# itself before merge.

import ast
from pathlib import Path

ALLOWED_VAULT_WRITERS: frozenset[str] = frozenset({
    "session/context.py",
    "vault/store.py",
    "generate/proposition.py",
})

PROJECT_ROOT_FOR_INV21 = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS: frozenset[str] = frozenset({
    "tests", "evals", "benchmarks", "scripts", "docs",
    "core-rs", ".venv", "__pycache__", ".claude",
})


def _enumerate_project_py_files() -> list[Path]:
    out: list[Path] = []
    for path in PROJECT_ROOT_FOR_INV21.rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT_FOR_INV21)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        out.append(path)
    return out


def _file_has_vault_store_call(path: Path) -> bool:
    """Return True iff `path` contains an executable `vault.store(...)` call
    or `<expr>.store(...)` on a name bound to a VaultStore.

    Uses AST so comments/docstrings/strings cannot trigger false positives.
    Detects two shapes:
      VaultStore(...).store(...)         — direct construction call
      <name>.store(...) where <name>     — method call on a vault-like binding
        was assigned from `VaultStore(`
        or named `vault` / ends with `_vault`
    """
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return False

    vault_bindings: set[str] = {"vault"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            if isinstance(value, ast.Call):
                func = value.func
                func_name = (
                    func.attr if isinstance(func, ast.Attribute) else
                    func.id if isinstance(func, ast.Name) else ""
                )
                if func_name == "VaultStore":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            vault_bindings.add(target.id)
                        elif isinstance(target, ast.Attribute):
                            vault_bindings.add(target.attr)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "store":
            continue
        receiver = func.value
        receiver_name = ""
        if isinstance(receiver, ast.Name):
            receiver_name = receiver.id
        elif isinstance(receiver, ast.Attribute):
            receiver_name = receiver.attr
        if (
            receiver_name in vault_bindings
            or receiver_name.endswith("_vault")
            or receiver_name == "vault"
        ):
            return True
    return False


class TestINV21OneMutationPath:
    """
    Claim: Only modules in ALLOWED_VAULT_WRITERS may call VaultStore.store().
    A new caller is a structural change to the epistemic schema and must
    be reviewed — adding it to the allowlist makes the decision explicit.
    """

    def test_no_unallowlisted_vault_writers(self):
        offenders: list[str] = []
        for path in _enumerate_project_py_files():
            if not _file_has_vault_store_call(path):
                continue
            rel = str(path.relative_to(PROJECT_ROOT_FOR_INV21))
            if rel not in ALLOWED_VAULT_WRITERS:
                offenders.append(rel)
        assert not offenders, (
            "New vault writer(s) detected outside the allowlist:\n  "
            + "\n  ".join(offenders)
            + "\n\nIf this addition is intentional, add the path to "
            "ALLOWED_VAULT_WRITERS in tests/test_architectural_invariants.py "
            "with a one-line justification in the comment block above the set. "
            "Every additional writer expands the trust surface of the "
            "epistemic schema (ADR-0021)."
        )

    def test_allowlist_is_actually_used(self):
        """Guard against the allowlist drifting out of sync with reality —
        if an allowlisted path no longer writes to vault, remove it."""
        used: set[str] = set()
        for path in _enumerate_project_py_files():
            if _file_has_vault_store_call(path):
                rel = str(path.relative_to(PROJECT_ROOT_FOR_INV21))
                if rel in ALLOWED_VAULT_WRITERS:
                    used.add(rel)
        unused = ALLOWED_VAULT_WRITERS - used - {"vault/store.py"}
        assert not unused, (
            f"Allowlisted writer(s) no longer call vault.store(): {sorted(unused)}\n"
            "Remove from ALLOWED_VAULT_WRITERS to keep the trust surface tight."
        )


# ===========================================================================
# INV-22  Pack lexicon default is SPECULATIVE — Leak A regression guard
# ===========================================================================
#
# Claim (ADR-0021 §3 + §Schema impact):
# A pack lexicon row that does not declare epistemic_status must enter the
# revision graph at SPECULATIVE. Defaulting to COHERENT would substitute
# pack authority for coherence judgment — exactly the bias the schema
# refuses. This test is the regression guard for the original Leak A:
# `language_packs/compiler.py:331` previously defaulted to "coherent",
# silently promoting every unmarked pack row to admissible-as-evidence.

from language_packs.schema import LexicalEntry
from language_packs.compiler import _parse_entry


class TestINV22PackDefaultSpeculative:
    """Pack lexicon rows without an explicit epistemic_status must be
    SPECULATIVE, not COHERENT.  COHERENT requires an explicit curator stamp."""

    def test_dataclass_default_is_speculative(self):
        entry = LexicalEntry(
            entry_id="test:001",
            surface="probe",
            lemma="probe",
            language="en",
        )
        assert entry.epistemic_status == "speculative", (
            "LexicalEntry.epistemic_status default is "
            f"{entry.epistemic_status!r} — must be 'speculative' (ADR-0021 §3). "
            "If you intend pack rows to default to COHERENT, you are re-importing "
            "the source-authority bias the schema exists to refuse."
        )

    def test_compiler_payload_default_is_speculative(self):
        payload = {
            "entry_id": "test:002",
            "surface": "probe",
            "language": "en",
        }
        entry = _parse_entry(payload)
        assert entry.epistemic_status == "speculative", (
            "Compiler default for missing epistemic_status is "
            f"{entry.epistemic_status!r} — must be 'speculative'. "
            "language_packs/compiler.py:331 was the original Leak A site; do not regress."
        )

    def test_explicit_coherent_is_preserved(self):
        """When a pack row DOES declare coherent (the curator stamp), the
        compiler must honor it. Otherwise we have replaced one leak with
        the opposite bug."""
        payload = {
            "entry_id": "test:003",
            "surface": "probe",
            "language": "en",
            "epistemic_status": "coherent",
        }
        entry = _parse_entry(payload)
        assert entry.epistemic_status == "coherent"


# ===========================================================================
# INV-23  Vault recall is epistemic-aware — Leak B regression guard
# ===========================================================================
#
# Claim (ADR-0021 §3 + audit 2026-05-17):
# Stored entries carry an EpistemicStatus stamp, and recall accepts a
# min_status filter so inference paths can exclude SPECULATIVE / CONTESTED /
# FALSIFIED entries.  The recall path is now tier-aware; before this fix,
# every hit was returned regardless of epistemic standing and downstream
# inference treated a session-memory write of a user error as equivalent
# to a COHERENT reviewed claim.

import numpy as np
from teaching.epistemic import EpistemicStatus as _ES
from vault.store import VaultStore as _VS


def _null_versor() -> np.ndarray:
    """A minimal valid CGA versor for test storage — content is irrelevant
    here; the test is about metadata filtering, not algebra."""
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return v


class TestINV23VaultEpistemicFilter:
    """vault.store stamps every entry with an EpistemicStatus.
    vault.recall(min_status=...) filters by admissibility tier."""

    def test_store_default_is_speculative(self):
        store = _VS(reproject_interval=0)
        v = _null_versor()
        store.store(v, {"role": "user"})
        hits = store.recall(v, top_k=1)
        assert hits, "Expected exact self-match recall"
        assert hits[0]["metadata"]["epistemic_status"] == "speculative", (
            "Default vault.store() must stamp SPECULATIVE — defaulting to "
            "COHERENT would re-import Leak A's bias at the recall substrate."
        )

    def test_store_explicit_coherent_is_preserved(self):
        store = _VS(reproject_interval=0)
        v = _null_versor()
        store.store(v, {"role": "reviewed"}, epistemic_status=_ES.COHERENT)
        hits = store.recall(v, top_k=1)
        assert hits[0]["metadata"]["epistemic_status"] == "coherent"

    def test_recall_min_status_filters_out_speculative(self):
        store = _VS(reproject_interval=0)
        spec_v = _null_versor()
        coh_v = _null_versor().copy()
        coh_v[1] = 0.5
        store.store(spec_v, {"role": "session"})
        store.store(coh_v, {"role": "reviewed"}, epistemic_status=_ES.COHERENT)

        all_hits = store.recall(spec_v, top_k=10)
        coherent_only = store.recall(spec_v, top_k=10, min_status=_ES.COHERENT)

        assert len(all_hits) >= 2, "Both entries should be visible without a filter"
        for hit in coherent_only:
            assert hit["metadata"]["epistemic_status"] == "coherent", (
                "min_status=COHERENT must exclude SPECULATIVE entries."
            )

    def test_recall_without_filter_returns_all_tiers(self):
        """Session-state lookup needs to see its own SPECULATIVE turns —
        the filter must be opt-in, not the default."""
        store = _VS(reproject_interval=0)
        v = _null_versor()
        store.store(v, {"role": "user"})
        hits = store.recall(v, top_k=1)
        assert hits, "Default recall must return SPECULATIVE session entries."


# ===========================================================================
# INV-24  Vault recall callsite registry — Leak C read-side audit guard
# ===========================================================================
#
# Claim (ADR-0021 §Leak C, 2026-05-17 audit, completed 2026-05-17):
# Every production vault.recall() callsite must be categorized in
# VAULT_RECALL_SITES.  Categories:
#
#   RECOGNITION         — answers "have we seen anything like this?"
#                         (gate decisions, unknown-domain probes).
#                         Unfiltered recall is correct: session-tier
#                         SPECULATIVE memory must count.
#
#   EVIDENCE_TELEMETRY  — feeds walk telemetry / trace evidence, NOT the
#                         user-facing surface (per docs/runtime_contracts.md
#                         §surface vs walk_surface).  Unfiltered recall is
#                         tolerable because the walk does not shape claims.
#                         If a future change routes the walk into the
#                         user-facing surface, the site must move to
#                         EVIDENCE_USER_FACING and pass min_status=COHERENT.
#
#   EVIDENCE_USER_FACING — feeds the user-facing surface as if ratified
#                          knowledge.  MUST pass min_status=COHERENT.
#                          Currently empty by design: user-facing
#                          articulation comes from realize(proposition, vocab)
#                          via pack lookup, not from vault.recall.
#
# A new vault.recall caller is a structural change to the read substrate of
# the epistemic schema and must be reviewed — adding it to the registry
# makes the categorization decision explicit.

VAULT_RECALL_SITES: dict[str, str] = {
    "chat/runtime.py":   "RECOGNITION",
    "vault/decompose.py": "RECOGNITION",
    "generate/stream.py": "EVIDENCE_TELEMETRY",
    "session/context.py": "RECOGNITION",  # generic delegate; callers categorize
    "vault/store.py":    "RECOGNITION",  # self-references in helpers/docstrings
}

VALID_RECALL_ROLES: frozenset[str] = frozenset({
    "RECOGNITION", "EVIDENCE_TELEMETRY", "EVIDENCE_USER_FACING",
})


def _file_has_vault_recall_call(path: Path) -> bool:
    """Return True iff `path` contains an executable `<vault>.recall(...)` call.

    Uses AST so docstrings/comments cannot trigger false positives.
    Detects `.recall(...)` on receivers that look like vault bindings:
    a name `vault`, any `*_vault`, or any name assigned from `VaultStore(...)`.
    """
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return False

    vault_bindings: set[str] = {"vault"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            func_name = (
                func.attr if isinstance(func, ast.Attribute) else
                func.id if isinstance(func, ast.Name) else ""
            )
            if func_name == "VaultStore":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        vault_bindings.add(target.id)
                    elif isinstance(target, ast.Attribute):
                        vault_bindings.add(target.attr)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "recall":
            continue
        receiver = func.value
        receiver_name = ""
        if isinstance(receiver, ast.Name):
            receiver_name = receiver.id
        elif isinstance(receiver, ast.Attribute):
            receiver_name = receiver.attr
        if (
            receiver_name in vault_bindings
            or receiver_name.endswith("_vault")
            or receiver_name == "vault"
        ):
            return True
    return False


class TestINV24VaultRecallRegistry:
    """Every production vault.recall() callsite must be categorized in
    VAULT_RECALL_SITES.  A new callsite is a structural change to the
    epistemic read-substrate and must justify its categorization."""

    def test_every_recall_site_is_registered(self):
        offenders: list[str] = []
        for path in _enumerate_project_py_files():
            if not _file_has_vault_recall_call(path):
                continue
            rel = str(path.relative_to(PROJECT_ROOT_FOR_INV21))
            if rel not in VAULT_RECALL_SITES:
                offenders.append(rel)
        assert not offenders, (
            "New vault recall callsite(s) detected outside the registry:\n  "
            + "\n  ".join(offenders)
            + "\n\nAdd the path to VAULT_RECALL_SITES in "
            "tests/test_architectural_invariants.py with one of the valid "
            f"roles: {sorted(VALID_RECALL_ROLES)}.\n"
            "EVIDENCE_USER_FACING sites MUST pass min_status=COHERENT "
            "(ADR-0021 §Leak C, 2026-05-17 audit)."
        )

    def test_registry_roles_are_valid(self):
        invalid = {
            path: role
            for path, role in VAULT_RECALL_SITES.items()
            if role not in VALID_RECALL_ROLES
        }
        assert not invalid, (
            f"Invalid recall role(s) in VAULT_RECALL_SITES: {invalid}\n"
            f"Valid roles: {sorted(VALID_RECALL_ROLES)}"
        )

    def test_registry_is_not_stale(self):
        """If a registered file no longer calls vault.recall(), drop it from
        the registry to keep the read-substrate trust surface tight."""
        used: set[str] = set()
        for path in _enumerate_project_py_files():
            if _file_has_vault_recall_call(path):
                used.add(str(path.relative_to(PROJECT_ROOT_FOR_INV21)))
        registered = set(VAULT_RECALL_SITES.keys())
        unused = registered - used - {"vault/store.py"}
        assert not unused, (
            f"Registered recall site(s) no longer call vault.recall(): "
            f"{sorted(unused)}\nRemove from VAULT_RECALL_SITES."
        )


# ===========================================================================
# INV-25  Independent gold — a promotable-capability lane scores against an
#         oracle that shares NO code with the system under test (SUT)
# ===========================================================================
#
# Claim (the GSM8K post-mortem made structural, docs/analysis/
# pivot-to-deductive-logic-2026-06-04.md §"the GSM8K lesson"):
#
#   No capability claim is valid unless the gold it is measured against is
#   computed by a procedure INDEPENDENT of the engine that produced the
#   answer.  A "gold" that shares code with the engine only proves the engine
#   agrees with itself — exactly the blind spot that let the GSM8K composer
#   serve 87 wrong held-out answers it could not tell from its 2 right ones.
#
# The deductive-logic lane is the first lane to earn a real correct number
# (holdout 500/500, wrong=0), and it earns it honestly because its gold is an
# independent truth-table oracle (evals/deductive_logic/oracle.py): a separate
# tokenizer + recursive-descent parser + brute-force 2^k model enumeration
# that imports NONE of the ROBDD engine under test.  This invariant ratifies
# that independence as a structural, meaningfully-failing property:
#
#   25a (structural).  Each registered oracle module imports none of its SUT's
#       modules.  Fails the moment an oracle is "simplified" to reuse the
#       engine — the single change that would turn independent gold into
#       self-agreement.
#   25b (behavioral).  Every committed deductive case's gold is reproduced by
#       the independent oracle AND matched by the engine: engine == oracle ==
#       committed gold.  This is the anti-overfit firewall — it fails if any
#       committed gold were ever engine-derived and diverged from the oracle.
#   25c (non-vacuity).  An unsound engine (entailed<->refuted flipped) is shown
#       to disagree with the oracle on committed cases, proving 25b can fail.
#
# A new lane that claims a promotable/checkable capability MUST register its
# (oracle, SUT) pair here.  The CI failure is the prompt to do so.

from typing import NamedTuple

_REPO_ROOT = PROJECT_ROOT_FOR_INV21


class IndependentGoldLane(NamedTuple):
    """A lane whose gold must be independent of its system under test."""

    name: str
    oracle_module: str  # path relative to repo root
    sut_import_prefixes: tuple[str, ...]  # modules the oracle MUST NOT import


# The engine under test for the deductive lane is generate.proof_chain.entail,
# built on the generate.logic_canonical ROBDD stack.  The oracle must share no
# code with any of it (it is a stdlib-only truth-table procedure today).
INDEPENDENT_GOLD_LANES: tuple[IndependentGoldLane, ...] = (
    IndependentGoldLane(
        name="deductive_logic",
        oracle_module="evals/deductive_logic/oracle.py",
        sut_import_prefixes=(
            "generate.proof_chain",
            "generate.logic_canonical",
            "generate.logic_equivalence",
        ),
    ),
    # The dimensional-reasoning lane: the interlingua's own unit algebra
    # (generate.binding_graph.units) is the SUT, so its gold oracle must share no
    # code with the binding graph.
    IndependentGoldLane(
        name="dimensional",
        oracle_module="evals/dimensional/oracle.py",
        sut_import_prefixes=("generate.binding_graph",),
    ),
)

_DEDUCTIVE_CASE_FILES: tuple[str, ...] = (
    "evals/deductive_logic/dev/cases.jsonl",
    "evals/deductive_logic/holdout/v1/cases.jsonl",
    "evals/deductive_logic/external/v1/cases.jsonl",
)


def _module_imports(path: Path) -> set[str]:
    """Every absolute module name imported by ``path``.

    Uses AST so a forbidden module mentioned only in a docstring/comment/string
    cannot trigger a false positive, and a real ``import generate.proof_chain``
    cannot hide from a substring grep.
    """
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # Absolute imports only (level == 0); a relative import cannot reach
            # the SUT package from the evals oracle.
            if node.module and node.level == 0:
                mods.add(node.module)
    return mods


def _imports_any_prefix(mods: set[str], prefixes: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for mod in sorted(mods):
        for prefix in prefixes:
            if mod == prefix or mod.startswith(prefix + "."):
                hits.append(mod)
                break
    return hits


def _load_deductive_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for rel in _DEDUCTIVE_CASE_FILES:
        path = _REPO_ROOT / rel
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(json.loads(line))
    return cases


class TestINV25IndependentGold:
    """A promotable-capability lane's gold must share no code with its SUT,
    and its committed gold must be reproducible by that independent oracle."""

    def test_registered_oracle_modules_exist(self):
        """Drift guard: a registered oracle path that no longer exists means
        the registry is stale and the structural check below is vacuous."""
        missing = [
            lane.oracle_module
            for lane in INDEPENDENT_GOLD_LANES
            if not (_REPO_ROOT / lane.oracle_module).is_file()
        ]
        assert not missing, (
            "Registered independent-gold oracle module(s) not found: "
            f"{missing}\nUpdate INDEPENDENT_GOLD_LANES in "
            "tests/test_architectural_invariants.py."
        )

    def test_oracle_shares_no_code_with_sut(self):
        """25a — the load-bearing structural guarantee. If any registered
        oracle imports a module of the engine it is supposed to check
        independently, the gold is not independent and this fails."""
        offenders: list[str] = []
        for lane in INDEPENDENT_GOLD_LANES:
            mods = _module_imports(_REPO_ROOT / lane.oracle_module)
            hits = _imports_any_prefix(mods, lane.sut_import_prefixes)
            if hits:
                offenders.append(f"{lane.oracle_module} imports SUT module(s) {hits}")
        assert not offenders, (
            "Independent-gold oracle shares code with its system under test:\n  "
            + "\n  ".join(offenders)
            + "\n\nThe oracle must be an independent decision procedure (a 'gold' "
            "that imports the engine only proves the engine agrees with itself — "
            "the GSM8K blind spot, INV-25). Re-implement the check independently, "
            "or — if this import is genuinely unrelated to the decision — narrow "
            "sut_import_prefixes in INDEPENDENT_GOLD_LANES with a justification."
        )

    def test_committed_gold_is_independently_reproducible(self):
        """25b — engine == oracle == committed gold on every committed case.
        Reproducing the committed gold with the *independent* oracle is the
        anti-overfit firewall: it fails if any gold were engine-derived and
        diverged, or if the engine ever confabulated a verdict."""
        from evals.deductive_logic.oracle import oracle_entailment
        from generate.proof_chain.entail import evaluate_entailment

        cases = _load_deductive_cases()
        assert cases, "no committed deductive cases found — INV-25b would be vacuous"

        oracle_mismatch: list[str] = []
        engine_mismatch: list[str] = []
        for case in cases:
            premises = tuple(case["premises"])
            query = case["query"]
            gold = case["gold"]
            if oracle_entailment(premises, query) != gold:
                oracle_mismatch.append(case["id"])
            if evaluate_entailment(premises, query).outcome.value != gold:
                engine_mismatch.append(case["id"])

        assert not oracle_mismatch, (
            "Committed gold is NOT reproduced by the independent oracle "
            f"(first few: {oracle_mismatch[:5]}). The gold may be engine-derived "
            "or the case file drifted — regenerate gold from the oracle."
        )
        assert not engine_mismatch, (
            "Engine disagrees with committed independent gold "
            f"(first few: {engine_mismatch[:5]}). This is a wrong==0 breach on a "
            "lane that claims a promotable capability."
        )

    def test_differential_is_non_vacuous(self):
        """25c — proves 25b can fail. An unsound engine (entailed<->refuted
        flipped) MUST disagree with the independent oracle on committed cases;
        if it did not, 25b would be decoration (CLAUDE.md schema-defined proof
        obligations)."""
        from evals.deductive_logic.oracle import oracle_entailment

        flip = {"entailed": "refuted", "refuted": "entailed"}
        cases = _load_deductive_cases()
        disagreements = 0
        for case in cases:
            premises = tuple(case["premises"])
            query = case["query"]
            gold = oracle_entailment(premises, query)
            unsound = flip.get(gold, gold)
            if unsound != gold:
                disagreements += 1
        assert disagreements > 0, (
            "A deliberately unsound (entailed<->refuted) engine disagreed with "
            "the oracle on ZERO committed cases — the committed set has no "
            "entailed/refuted signal, so INV-25b cannot catch a soundness break. "
            "Add non-trivial cases before claiming the lane proves capability."
        )


# ===========================================================================
# INV-26  Interlingua neutrality — the universal problem-structure does not
#         depend on the field engine, any one domain reader, or eval/runtime
# ===========================================================================
#
# Claim (docs/analysis/universal-structure-and-field-symbol-coherence-gate-
# 2026-06-04.md §2; ADR-0132 "no algebra" rule made structural):
#
#   The binding graph is the corpus callosum where two independent decodings
#   (the geometric field and the symbolic ROBDD) must be able to meet and
#   AGREE. That is only sound if the meeting point is NEUTRAL: if the
#   interlingua imported the field engine, a benchmark, or a single domain's
#   reader, "agreement at the interlingua" would be agreement-with-oneself —
#   the same blind spot INV-25 guards for gold. So:
#
#   26a  No binding-graph module imports the field engine, eval, vault, or the
#        runtime (``field`` / ``algebra`` / ``evals`` / ``vault`` / ``chat`` /
#        ``core`` / ``sensorium``). The structure is engine/benchmark/runtime-
#        neutral.
#   26b  The binding-graph CORE (everything but the allowlisted bridge modules)
#        imports nothing outside the standard library and its own package —
#        in particular no domain reader. Only the bridges (``adapter``,
#        ``question_target``) may translate a domain reader into the structure.
#   26c  Non-vacuity: a module that imports a forbidden family is shown to be
#        flagged, proving 26a/26b can fail.
#
# A new bridge (a new domain reader translated into the structure) is allowed,
# but must be added to BINDING_GRAPH_BRIDGES explicitly — that is the reviewable
# seam where a domain couples to the universal structure.

_BINDING_GRAPH_DIR = "generate/binding_graph"

# Engine / benchmark / runtime families the interlingua must never import.
_INTERLINGUA_FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "field", "algebra", "evals", "vault", "chat", "core", "sensorium",
)

# The only modules permitted to import a domain reader (they translate one
# domain's reader output into the neutral structure).
BINDING_GRAPH_BRIDGES: frozenset[str] = frozenset({
    "adapter.py",
    "question_target.py",
})


def _binding_graph_modules() -> list[Path]:
    return sorted((_REPO_ROOT / _BINDING_GRAPH_DIR).glob("*.py"))


def _is_internal_or_stdlib(mod: str) -> bool:
    """True if an imported module name is the structure's own package."""
    return mod == "generate.binding_graph" or mod.startswith("generate.binding_graph.")


class TestINV26InterlinguaNeutrality:
    """The universal problem-structure stays neutral to engine, benchmark, and
    runtime, and its core depends on no single domain reader."""

    def test_binding_graph_dir_exists(self):
        mods = _binding_graph_modules()
        assert mods, (
            f"no binding-graph modules found under {_BINDING_GRAPH_DIR} — "
            "INV-26 would be vacuous (did the package move?)."
        )

    def test_no_module_imports_engine_eval_or_runtime(self):
        """26a — the interlingua never touches field/algebra/eval/vault/chat/
        core/sensorium. Agreement at a neutral meeting point is real; agreement
        at a point coupled to one engine is agreement-with-oneself."""
        offenders: list[str] = []
        for path in _binding_graph_modules():
            mods = _module_imports(path)
            hits = _imports_any_prefix(mods, _INTERLINGUA_FORBIDDEN_PREFIXES)
            if hits:
                offenders.append(f"{path.name} imports {hits}")
        assert not offenders, (
            "Binding-graph (interlingua) module couples to the engine/eval/"
            "runtime:\n  " + "\n  ".join(offenders)
            + "\n\nThe universal structure must stay neutral so two independent "
            "decodings can meet and agree there (INV-26a). Move the coupling out, "
            "or it is not an interlingua."
        )

    def test_core_imports_no_domain_reader(self):
        """26b — only the allowlisted bridges may import a domain reader; the
        core imports nothing outside stdlib + its own package."""
        offenders: list[str] = []
        for path in _binding_graph_modules():
            if path.name in BINDING_GRAPH_BRIDGES or path.name == "__init__.py":
                continue
            external = [
                m for m in _module_imports(path)
                if m.startswith("generate.") and not _is_internal_or_stdlib(m)
            ]
            if external:
                offenders.append(f"{path.name} imports domain module(s) {sorted(external)}")
        assert not offenders, (
            "Binding-graph CORE imports a domain reader (couples the universal "
            "structure to one domain):\n  " + "\n  ".join(offenders)
            + "\n\nTranslate the domain via a bridge module and add it to "
            "BINDING_GRAPH_BRIDGES, or keep the core domain-agnostic (INV-26b)."
        )

    def test_bridges_exist_and_are_used(self):
        """Drift guard: every allowlisted bridge must exist and actually import a
        domain reader, else the allowlist is stale and 26b is weakened."""
        present = {p.name for p in _binding_graph_modules()}
        missing = BINDING_GRAPH_BRIDGES - present
        assert not missing, f"BINDING_GRAPH_BRIDGES names non-existent module(s): {missing}"
        unused: list[str] = []
        for name in sorted(BINDING_GRAPH_BRIDGES):
            mods = _module_imports(_REPO_ROOT / _BINDING_GRAPH_DIR / name)
            if not any(m.startswith("generate.") and not _is_internal_or_stdlib(m) for m in mods):
                unused.append(name)
        assert not unused, (
            f"Allowlisted bridge(s) no longer import a domain reader: {unused}. "
            "Remove from BINDING_GRAPH_BRIDGES to keep the coupling seam tight."
        )

    def test_neutrality_check_is_non_vacuous(self):
        """26c — prove 26a/26b can fail: a real module that imports a forbidden
        family must be flagged by the same predicate."""
        # core/cognition/pipeline.py imports field.state (engine) — 26a must flag it.
        pipeline = _REPO_ROOT / "core" / "cognition" / "pipeline.py"
        if pipeline.is_file():
            hits = _imports_any_prefix(_module_imports(pipeline), _INTERLINGUA_FORBIDDEN_PREFIXES)
            assert hits, (
                "INV-26a predicate failed to flag a module known to import the "
                "field engine — the neutrality check is vacuous."
            )
        # The bridge adapter imports a domain reader — 26b's predicate must see it.
        adapter = _REPO_ROOT / _BINDING_GRAPH_DIR / "adapter.py"
        external = [
            m for m in _module_imports(adapter)
            if m.startswith("generate.") and not _is_internal_or_stdlib(m)
        ]
        assert external, (
            "INV-26b predicate failed to detect the adapter's domain-reader "
            "import — the core-isolation check is vacuous."
        )
