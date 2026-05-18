"""Tests for ``formation.templates.falsification``."""

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
_BUNDLE_SHA = "f" * 64


def _src(sha: str = _SHA_A) -> SourceRef:
    return SourceRef(sha, "span", "wikipedia", "2026-05-17T00:00:00Z")


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.fals",
        title="A Falsification Pack",
        target_depth="introductory",
    )


def _vs(
    *,
    relations: tuple[RelationCandidate, ...] | None = None,
    counters: tuple[CounterCandidate, ...] | None = None,
) -> ValidatedTripleSet:
    concepts = (
        ConceptCandidate("light", "electromagnetic radiation", (_src(),)),
        ConceptCandidate("sound", "pressure wave in matter", (_src(),)),
    )
    default_relations = (
        RelationCandidate("light", "travels_in", "vacuum", (_src(),)),
        RelationCandidate("sound", "travels_in", "matter", (_src(),)),
    )
    default_counters = (
        CounterCandidate("sound", "travels_in", "vacuum", (_src(_SHA_B),)),
        CounterCandidate("orphan", "is", "wrong", (_src(),)),
    )
    return ValidatedTripleSet(
        subject_id="subject.fals",
        concepts=concepts,
        relations=relations if relations is not None else default_relations,
        counters=counters if counters is not None else default_counters,
        ordering_hints=(),
    )


class TestDeterminism:
    def test_same_input_identical_bytes(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        assert a.yaml_bytes == b.yaml_bytes

    def test_reordered_counters_same_bytes(self) -> None:
        base = _vs()
        rev = _vs(counters=tuple(reversed(base.counters)))
        a = compose(base, _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        b = compose(rev, _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        assert a.yaml_bytes == b.yaml_bytes


class TestParadigm:
    def test_polarity_pair_matches_counter_to_alternative(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        pairs = loaded["phase_2_falsification_corpus"]["polarity_pairs"]
        # "sound" counter pairs with "sound travels_in matter" relation.
        sound_pair = next(p for p in pairs if p["rejected_claim"]["head"] == "sound")
        assert sound_pair["coherent_alternative"]["head"] == "sound"
        assert sound_pair["coherent_alternative"]["tail"] == "matter"

    def test_unmatched_counter_recorded(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        unmatched = loaded["phase_2_falsification_corpus"]["unmatched_counters"]
        heads = {c["head"] for c in unmatched}
        assert "orphan" in heads

    def test_walks_are_polarity_flips(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        walks = loaded["phase_3_polarity_walks"]["walks"]
        assert all(w["kind"] == "polarity_flip" for w in walks)
        assert all(len(w["steps"]) == 2 for w in walks)
        assert walks[0]["steps"][0]["polarity"] == "reject"
        assert walks[0]["steps"][1]["polarity"] == "accept"

    def test_paradigm_gates_present(self) -> None:
        yaml = pytest.importorskip("yaml")
        out = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        loaded = yaml.safe_load(out.yaml_bytes.decode("utf-8"))
        gates = loaded["phase_5_ratified_consolidation"]["ratification_gates"]
        assert "counter_rejection_rate_eq_1" in gates
        assert "alternative_acceptance_rate_eq_1" in gates


class TestErrors:
    def test_rejects_empty_counters(self) -> None:
        with pytest.raises(ValueError, match="at least one counter"):
            compose(_vs(counters=()), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")


class TestCrossSession:
    def test_sha_stable_across_subprocess(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tests.formation.test_template_falsification import _vs, _spec, _BUNDLE_SHA;"
            "from formation.compose import compose;"
            "print(compose(_vs(), _spec(), _BUNDLE_SHA, template_id='falsification', template_version='1.0.0').course_sha256)"
        ) % str(repo_root)
        in_proc = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0").course_sha256
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True, capture_output=True, text=True,
            cwd=str(repo_root),
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        )
        assert result.stdout.strip() == in_proc
