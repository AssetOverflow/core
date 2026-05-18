"""Cross-template registry tests."""

from __future__ import annotations

import pytest

from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    RelationCandidate,
    SourceRef,
)
from formation.compose import compose
from formation.course import SubjectSpec, ValidatedTripleSet
from formation.templates import get_template, registered_template_ids

_SHA = "a" * 64
_BUNDLE_SHA = "f" * 64


def _src() -> SourceRef:
    return SourceRef(_SHA, "span", "wikipedia", "2026-05-17T00:00:00Z")


def _spec() -> SubjectSpec:
    return SubjectSpec("subject.cross", "Cross Template Probe", "introductory")


def _vs() -> ValidatedTripleSet:
    return ValidatedTripleSet(
        subject_id="subject.cross",
        concepts=(
            ConceptCandidate("alpha", "first", (_src(),)),
            ConceptCandidate("beta", "second", (_src(),)),
            ConceptCandidate("gamma", "third", (_src(),)),
        ),
        relations=(
            RelationCandidate("alpha", "causes", "beta", (_src(),)),
            RelationCandidate("beta", "causes", "gamma", (_src(),)),
        ),
        counters=(CounterCandidate("alpha", "blocks", "gamma", (_src(),)),),
        ordering_hints=(),
    )


class TestRegistry:
    def test_known_templates(self) -> None:
        assert registered_template_ids() == (
            "composed_relation",
            "definition",
            "falsification",
            "identity_anchor",
            "procedural",
        )

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(KeyError):
            get_template("does_not_exist")

    def test_all_templates_share_version_one(self) -> None:
        for tid in registered_template_ids():
            assert get_template(tid).template_version == "1.0.0"


class TestCrossTemplateShaDistinct:
    """Same inputs through different templates must produce different SHAs."""

    def test_definition_vs_composed_relation(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="definition", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="composed_relation", template_version="1.0.0")
        assert a.course_sha256 != b.course_sha256

    def test_definition_vs_falsification(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="definition", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        assert a.course_sha256 != b.course_sha256

    def test_composed_vs_falsification(self) -> None:
        a = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="composed_relation", template_version="1.0.0")
        b = compose(_vs(), _spec(), _BUNDLE_SHA, template_id="falsification", template_version="1.0.0")
        assert a.course_sha256 != b.course_sha256
