"""Tests for ``formation.templates.identity_anchor``."""

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

_SHA_A = "a" * 64
_BUNDLE_SHA = "f" * 64


def _src() -> SourceRef:
    return SourceRef(_SHA_A, "span", "wikipedia", "2026-05-17T00:00:00Z")


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.identity",
        title="Identity Anchor Pack",
        target_depth="introductory",
    )


def _vs(
    *,
    concepts: tuple[ConceptCandidate, ...] | None = None,
    counters: tuple[CounterCandidate, ...] | None = None,
    hints: tuple[OrderingHint, ...] = (),
    relations: tuple[RelationCandidate, ...] = (),
) -> ValidatedTripleSet:
    default_concepts = (
        ConceptCandidate(
            "precision",
            "Precision-first: weight accuracy over coverage.",
            (_src(),),
        ),
        ConceptCandidate(
            "generosity",
            "Generosity-first: weight inclusivity over precision.",
            (_src(),),
        ),
    )
    default_counters = (
        CounterCandidate(
            "precision",
            "must_yield_to",
            "user_override",
            (_src(),),
        ),
    )
    return ValidatedTripleSet(
        subject_id="subject.identity",
        concepts=concepts if concepts is not None else default_concepts,
        relations=relations,
        counters=counters if counters is not None else default_counters,
        ordering_hints=hints,
    )


class TestDeterminism:
    def test_same_input_identical_bytes(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        assert a.yaml_bytes == b.yaml_bytes


class TestParadigm:
    def test_axes_in_lex_order_without_hints(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        axes = loaded["phase_1_axis_declaration"]["axes"]
        names = [a["canonical_term"] for a in axes]
        assert names == sorted(names)

    def test_hints_set_priority(self) -> None:
        yaml = pytest.importorskip("yaml")
        # Without a hint, "generosity" sorts before "precision" lex.
        # With a hint generosity -> precision, that order is preserved
        # (both are at indegree 0 chain).  Use precision -> generosity
        # to force precision first.
        hints = (OrderingHint(before="precision", after="generosity", sources=(_src(),)),)
        out = compose(
            _vs(hints=hints), _spec(), _BUNDLE_SHA,
            template_id="identity_anchor", template_version="1.0.0",
        )
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        axes = loaded["phase_1_axis_declaration"]["axes"]
        assert axes[0]["canonical_term"] == "precision"
        assert axes[1]["canonical_term"] == "generosity"

    def test_canned_identity_probes_present(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        probes = loaded["phase_4_epistemic_boundary_hardening"]["adversarial_corrections"]
        ids = {p["probe_id"] for p in probes}
        assert "identity_override_axis_rewrite" in ids
        assert "identity_override_policy_bypass" in ids
        assert "identity_override_operator_injection" in ids

    def test_refusal_walks_one_per_counter(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        walks = loaded["phase_3_refusal_walks"]["walks"]
        assert len(walks) == 1
        assert walks[0]["kind"] == "refusal"
        assert walks[0]["steps"][0]["expected_terminal_state"] == "rejected"

    def test_paradigm_gates_present(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        gates = loaded["phase_5_ratified_consolidation"]["ratification_gates"]
        assert "every_axis_seeded_at_least_once" in gates
        assert "every_override_rejected" in gates


class TestErrors:
    def test_rejects_empty_concepts(self) -> None:
        with pytest.raises(ValueError, match="axis"):
            compose(_vs(concepts=()), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")

    def test_rejects_empty_counters(self) -> None:
        with pytest.raises(ValueError, match="override-attempt"):
            compose(_vs(counters=()), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0")


class TestCrossSession:
    def test_sha_stable_across_subprocess(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tests.formation.test_template_identity_anchor import _vs, _spec, _BUNDLE_SHA;"
            "from formation.compose import compose;"
            "print(compose(_vs(), _spec(), _BUNDLE_SHA, template_id='identity_anchor', template_version='1.0.0').course_sha256)"
        ) % str(repo_root)
        in_proc = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="identity_anchor", template_version="1.0.0").course_sha256
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True, capture_output=True, text=True,
            cwd=str(repo_root),
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        )
        assert result.stdout.strip() == in_proc
