"""Tests for ``formation.templates.composed_relation``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    RelationCandidate,
    SourceRef,
)
from formation.compose import compose
from formation.course import SubjectSpec, ValidatedTripleSet

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_BUNDLE_SHA = "f" * 64


def _src(sha: str = _SHA_A, adapter: str = "wikipedia") -> SourceRef:
    return SourceRef(
        source_sha=sha,
        span="...span...",
        adapter=adapter,
        retrieved_at="2026-05-17T00:00:00Z",
    )


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.composed",
        title="Composed Relations Primer",
        target_depth="introductory",
    )


def _vs(
    *,
    relations: tuple[RelationCandidate, ...] | None = None,
    counters: tuple[CounterCandidate, ...] | None = None,
) -> ValidatedTripleSet:
    default_concepts = (
        ConceptCandidate("alpha", "first node", (_src(_SHA_A),)),
        ConceptCandidate("beta", "second node", (_src(_SHA_A),)),
        ConceptCandidate("gamma", "third node", (_src(_SHA_B),)),
    )
    default_relations = (
        RelationCandidate("alpha", "causes", "beta", (_src(_SHA_A),)),
        RelationCandidate("beta", "causes", "gamma", (_src(_SHA_A),)),
    )
    default_counters = (
        CounterCandidate("alpha", "blocks", "gamma", (_src(_SHA_C),)),
    )
    return ValidatedTripleSet(
        subject_id="subject.composed",
        concepts=default_concepts,
        relations=relations if relations is not None else default_relations,
        counters=counters if counters is not None else default_counters,
        ordering_hints=(),
    )


def _compose() -> bytes:
    return compose(
        _vs(),
        _spec(),
        _BUNDLE_SHA,
        template_id="composed_relation",
        template_version="1.0.0",
    ).yaml_bytes


class TestDeterminism:
    def test_same_input_identical_bytes(self) -> None:
        assert _compose() == _compose()

    def test_reordered_relations_same_bytes(self) -> None:
        base = _vs()
        rev = _vs(relations=tuple(reversed(base.relations)))
        a = compose(
            base, _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        b = compose(
            rev, _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        assert a.yaml_bytes == b.yaml_bytes


class TestParadigm:
    def test_composed_relations_emitted(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(
            _vs(), _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        composed = loaded["phase_3_holonomic_syllabus_walk"]["composed_relations"]
        assert len(composed) == 1
        entry = composed[0]
        assert entry["head"] == "alpha"
        assert entry["tail"] == "gamma"
        assert entry["composition_kind"] == "transitive"
        assert entry["inferred_relation"] == "causes"

    def test_lifting_kind_when_predicates_differ(self) -> None:
        yaml = pytest.importorskip("yaml")
        rels = (
            RelationCandidate("alpha", "causes", "beta", (_src(_SHA_A),)),
            RelationCandidate("beta", "entails", "gamma", (_src(_SHA_A),)),
        )
        out = compose(
            _vs(relations=rels), _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        composed = loaded["phase_3_holonomic_syllabus_walk"]["composed_relations"]
        assert composed[0]["composition_kind"] == "lifting"
        assert composed[0]["inferred_relation"] == "composes_to"

    def test_paradigm_specific_gate_present(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(
            _vs(), _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        gates = loaded["phase_5_ratified_consolidation"]["ratification_gates"]
        assert "every_composed_relation_replayed" in gates

    def test_chain_break_probe_uses_matching_counter(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(
            _vs(), _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        probes = loaded["phase_4_epistemic_boundary_hardening"]["chain_break_probes"]
        assert len(probes) == 1
        assert probes[0]["counter_relation"] == "blocks"

    def test_chain_break_probe_canned_when_no_match(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(
            _vs(counters=()),
            _spec(),
            _BUNDLE_SHA,
            template_id="composed_relation",
            template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        probes = loaded["phase_4_epistemic_boundary_hardening"]["chain_break_probes"]
        assert probes[0]["counter_relation"] == "spurious_inference"


class TestErrors:
    def test_rejects_single_relation(self) -> None:
        vs = _vs(relations=(_vs().relations[0],))
        with pytest.raises(ValueError, match="at least two relations"):
            compose(
                vs, _spec(), _BUNDLE_SHA,
                template_id="composed_relation", template_version="1.0.0",
            )


class TestCrossSession:
    def test_sha_stable_across_subprocess(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tests.formation.test_template_composed_relation import _vs, _spec, _BUNDLE_SHA;"
            "from formation.compose import compose;"
            "print(compose(_vs(), _spec(), _BUNDLE_SHA, template_id='composed_relation', template_version='1.0.0').course_sha256)"
        ) % str(repo_root)
        in_proc = compose(
            _vs(), _spec(), _BUNDLE_SHA,
            template_id="composed_relation", template_version="1.0.0",
        ).course_sha256
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True, capture_output=True, text=True,
            cwd=str(repo_root),
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        )
        assert result.stdout.strip() == in_proc
