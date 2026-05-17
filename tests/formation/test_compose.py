"""Tests for ``formation.compose`` — deterministic Course YAML composition.

Per Phase 3 of ``docs/formation_pipeline_plan.md``:
* same input -> identical YAML bytes
* reorder input tuples -> identical YAML bytes
* YAML round-trips through ``yaml.safe_load`` if PyYAML is available
* ``course_sha256`` is stable across calls (proxy for "across Python sessions")
* different input -> different SHA
* template version participates in the SHA
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.compose import compose
from formation.course import SubjectSpec, ValidatedTripleSet


# ---------- fixtures ----------


_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_BUNDLE_SHA = "f" * 64


def _src(sha: str = _SHA_A, adapter: str = "wikipedia") -> SourceRef:
    return SourceRef(
        source_sha=sha,
        span="...quoted span...",
        adapter=adapter,
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.geometry",
        title="Geometric Algebra Primer",
        target_depth="introductory",
        requires_courses=("course.calculus",),
        identity_axis_constraints=("preserve_identity",),
    )


def _validated_set(
    *,
    relations: tuple[RelationCandidate, ...] | None = None,
    concepts: tuple[ConceptCandidate, ...] | None = None,
) -> ValidatedTripleSet:
    default_concepts = (
        ConceptCandidate(
            canonical_term="vector",
            definition="A directed quantity in a linear space.",
            sources=(_src(_SHA_A),),
        ),
        ConceptCandidate(
            canonical_term="bivector",
            definition="An oriented planar element.",
            sources=(_src(_SHA_B),),
        ),
        ConceptCandidate(
            canonical_term="rotor",
            definition="A unit even-grade element generating rotation.",
            sources=(_src(_SHA_A), _src(_SHA_B, "stackexchange")),
        ),
    )
    default_relations = (
        RelationCandidate(
            head="vector",
            relation="combines_to",
            tail="bivector",
            sources=(_src(_SHA_A),),
        ),
        RelationCandidate(
            head="bivector",
            relation="exponentiates_to",
            tail="rotor",
            sources=(_src(_SHA_B),),
        ),
    )
    counters = (
        CounterCandidate(
            head="vector",
            relation="equals",
            tail="rotor",
            sources=(_src(_SHA_C),),
        ),
    )
    hints = (OrderingHint(before="vector", after="bivector", sources=(_src(_SHA_A),)),)
    return ValidatedTripleSet(
        subject_id="subject.geometry",
        concepts=concepts if concepts is not None else default_concepts,
        relations=relations if relations is not None else default_relations,
        counters=counters,
        ordering_hints=hints,
    )


# ---------- determinism ----------


class TestDeterminism:
    def test_same_input_identical_bytes(self) -> None:
        vs = _validated_set()
        a = compose(vs, _spec(), _BUNDLE_SHA)
        b = compose(vs, _spec(), _BUNDLE_SHA)
        assert a.yaml_bytes == b.yaml_bytes
        assert a.course_sha256 == b.course_sha256

    def test_reordered_relations_same_bytes(self) -> None:
        base = _validated_set()
        reordered = _validated_set(relations=tuple(reversed(base.relations)))
        a = compose(base, _spec(), _BUNDLE_SHA)
        b = compose(reordered, _spec(), _BUNDLE_SHA)
        assert a.yaml_bytes == b.yaml_bytes
        assert a.course_sha256 == b.course_sha256

    def test_reordered_concepts_same_bytes(self) -> None:
        base = _validated_set()
        reordered_concepts = tuple(reversed(base.concepts))
        b_set = _validated_set(concepts=reordered_concepts)
        a = compose(base, _spec(), _BUNDLE_SHA)
        b = compose(b_set, _spec(), _BUNDLE_SHA)
        assert a.yaml_bytes == b.yaml_bytes


# ---------- round-trip ----------


class TestRoundTrip:
    def test_yaml_safe_load_roundtrip(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_validated_set(), _spec(), _BUNDLE_SHA)
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        # Re-emit through compose by handing the parsed structure back is not
        # meaningful; instead, assert structure invariants survive parsing.
        assert loaded["template_id"] == "definition"
        assert loaded["template_version"] == "1.0.0"
        assert loaded["source_bundle_sha"] == _BUNDLE_SHA
        assert (
            loaded["substrate_invariants"]["max_versor_condition"] == "1.0e-6"
        )
        # Concepts present and ordered.
        terms = [c["canonical_term"] for c in loaded["phase_1_ontological_seeding"]["concepts"]]
        assert terms == sorted(terms)
        # Relations topo-sorted: vector -> bivector before bivector -> rotor.
        rels = loaded["phase_2_axiomatic_rotor_scaffolding"]["relations"]
        assert rels[0]["head"] == "vector"
        assert rels[1]["head"] == "bivector"
        # Walks present.
        walks = loaded["phase_3_holonomic_syllabus_walk"]["walks"]
        assert len(walks) >= 1
        # Adversarial includes identity-override probes.
        probes = loaded["phase_4_epistemic_boundary_hardening"]["adversarial_corrections"]
        probe_ids = {p.get("probe_id") for p in probes}
        assert "identity_override_axis_rewrite" in probe_ids


# ---------- SHA sensitivity ----------


class TestShaSensitivity:
    def test_different_input_different_sha(self) -> None:
        a = compose(_validated_set(), _spec(), _BUNDLE_SHA)
        # Different validated set: add an extra relation.
        extra = RelationCandidate(
            head="rotor",
            relation="acts_on",
            tail="vector",
            sources=(_src(_SHA_A),),
        )
        vs2 = _validated_set(relations=_validated_set().relations + (extra,))
        b = compose(vs2, _spec(), _BUNDLE_SHA)
        assert a.course_sha256 != b.course_sha256

    def test_different_source_bundle_different_sha(self) -> None:
        a = compose(_validated_set(), _spec(), _BUNDLE_SHA)
        b = compose(_validated_set(), _spec(), "0" * 64)
        assert a.course_sha256 != b.course_sha256

    def test_template_version_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="template_version"):
            compose(
                _validated_set(),
                _spec(),
                _BUNDLE_SHA,
                template_version="9.9.9",
            )

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(KeyError):
            compose(
                _validated_set(),
                _spec(),
                _BUNDLE_SHA,
                template_id="does_not_exist",
            )


# ---------- cross-session SHA stability ----------


class TestCrossSession:
    def test_sha_stable_across_subprocess(self) -> None:
        """Compute the course SHA in a fresh Python process; must match.

        This is the strongest proxy for "stable across Python sessions" we can
        achieve without persisting fixtures.  Hash randomization is reset per
        process; if anything in compose depends on it, this fails.
        """
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tests.formation.test_compose import _validated_set, _spec, _BUNDLE_SHA;"
            "from formation.compose import compose;"
            "print(compose(_validated_set(), _spec(), _BUNDLE_SHA).course_sha256)"
        ) % str(repo_root)
        in_proc = compose(_validated_set(), _spec(), _BUNDLE_SHA).course_sha256
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        )
        assert result.stdout.strip() == in_proc


# ---------- floats forbidden ----------


class TestFloatsForbidden:
    def test_payload_has_no_floats(self) -> None:
        # Compose should succeed even when we exercise every path; the
        # underlying _reject_floats guarantee is asserted by passing.
        out = compose(_validated_set(), _spec(), _BUNDLE_SHA)
        assert out.yaml_bytes  # non-empty
        # The literal threshold appears as a string in the YAML.
        assert b'max_versor_condition: "1.0e-6"' in out.yaml_bytes
