"""Tests for ``formation.templates.procedural``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from formation.candidate import (
    ConceptCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.compose import compose
from formation.course import SubjectSpec, ValidatedTripleSet

_SHA_A = "a" * 64
_BUNDLE_SHA = "f" * 64


def _src() -> SourceRef:
    return SourceRef(_SHA_A, "span", "wikipedia", "2026-05-17T00:00:00Z")


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.procedure",
        title="A Procedure",
        target_depth="introductory",
    )


def _vs(
    *,
    relations: tuple[RelationCandidate, ...] | None = None,
    hints: tuple[OrderingHint, ...] = (),
) -> ValidatedTripleSet:
    concepts = (
        ConceptCandidate("ready", "ready state", (_src(),)),
        ConceptCandidate("running", "running state", (_src(),)),
        ConceptCandidate("done", "done state", (_src(),)),
    )
    default_relations = (
        RelationCandidate("ready", "start", "running", (_src(),)),
        RelationCandidate("running", "finish", "done", (_src(),)),
    )
    return ValidatedTripleSet(
        subject_id="subject.procedure",
        concepts=concepts,
        relations=relations if relations is not None else default_relations,
        counters=(),
        ordering_hints=hints,
    )


class TestDeterminism:
    def test_same_input_identical_bytes(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        assert a.yaml_bytes == b.yaml_bytes

    def test_reordered_relations_same_bytes(self) -> None:
        base = _vs()
        rev = _vs(relations=tuple(reversed(base.relations)))
        a = compose(base, _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        b = compose(rev, _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        assert a.yaml_bytes == b.yaml_bytes


class TestParadigm:
    def test_linear_walk(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        walks = loaded["phase_3_linear_procedural_walk"]["walks"]
        assert len(walks) == 1
        steps = walks[0]["steps"]
        assert [s["head"] for s in steps] == ["ready", "running"]
        assert walks[0]["kind"] == "linear_total"

    def test_transitions_have_pre_post(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        transitions = loaded["phase_2_transition_scaffolding"]["transitions"]
        assert transitions[0]["precondition_state"] == "ready"
        assert transitions[0]["postcondition_state"] == "running"

    def test_paradigm_gates_present(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        gates = loaded["phase_5_ratified_consolidation"]["ratification_gates"]
        assert "linear_order_strict" in gates
        assert "every_transition_walked_exactly_once" in gates

    def test_canned_violation_probes(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        probes = loaded["phase_4_epistemic_boundary_hardening"]["adversarial_corrections"]
        ids = {p["probe_id"] for p in probes}
        assert "procedural_precondition_violation" in ids
        assert "procedural_step_skip" in ids
        assert "procedural_back_edge" in ids


class TestErrors:
    def test_rejects_branch(self) -> None:
        rels = (
            RelationCandidate("ready", "start", "running", (_src(),)),
            RelationCandidate("ready", "abort", "done", (_src(),)),
        )
        with pytest.raises(ValueError, match="out-edges"):
            compose(_vs(relations=rels), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")

    def test_rejects_cycle(self) -> None:
        rels = (
            RelationCandidate("a", "step", "b", (_src(),)),
            RelationCandidate("b", "step", "a", (_src(),)),
        )
        with pytest.raises(ValueError):
            compose(_vs(relations=rels), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")

    def test_rejects_disconnected(self) -> None:
        rels = (
            RelationCandidate("a", "step", "b", (_src(),)),
            RelationCandidate("c", "step", "d", (_src(),)),
        )
        with pytest.raises(ValueError):
            compose(_vs(relations=rels), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")

    def test_rejects_hint_contradiction(self) -> None:
        hints = (OrderingHint(before="done", after="ready", sources=(_src(),)),)
        with pytest.raises(ValueError, match="contradicts"):
            compose(_vs(hints=hints), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")

    def test_rejects_empty_relations(self) -> None:
        with pytest.raises(ValueError):
            compose(_vs(relations=()), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0")


class TestCrossSession:
    def test_sha_stable_across_subprocess(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tests.formation.test_template_procedural import _vs, _spec, _BUNDLE_SHA;"
            "from formation.compose import compose;"
            "print(compose(_vs(), _spec(), _BUNDLE_SHA, template_id='procedural', template_version='1.0.0').course_sha256)"
        ) % str(repo_root)
        in_proc = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="procedural", template_version="1.0.0").course_sha256
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True, capture_output=True, text=True,
            cwd=str(repo_root),
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        )
        assert result.stdout.strip() == in_proc
