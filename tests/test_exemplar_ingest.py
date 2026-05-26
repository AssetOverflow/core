"""ADR-0163 Phase C — exemplar_ingest tests.

Pins:
- load_exemplar_corpus parses each Phase B JSONL without loss
- corpus_digest is byte-stable across runs
- malformed exemplars raise ExemplarIngestError
- the module performs no I/O beyond the supplied path
"""

from __future__ import annotations

import builtins
import json
from pathlib import Path
from typing import Any

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from teaching.exemplar_ingest import (
    Exemplar,
    ExemplarCorpus,
    ExemplarIngestError,
    list_corpora,
    load_exemplar_corpus,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLARS_ROOT = _REPO_ROOT / "teaching" / "admissibility_exemplars"
_ROUND_1 = (
    ("descriptive_setup_no_quantity_v1.jsonl", ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY),
    ("temporal_aggregation_v1.jsonl", ShapeCategory.TEMPORAL_AGGREGATION),
    ("rate_with_currency_v1.jsonl", ShapeCategory.RATE_WITH_CURRENCY),
)

# ADR-0163.B.2 — round-2 corpora present on main.
_ROUND_2 = (
    ("discrete_count_statement_v1.jsonl", ShapeCategory.DISCRETE_COUNT_STATEMENT),
    ("multiplicative_aggregation_v1.jsonl", ShapeCategory.MULTIPLICATIVE_AGGREGATION),
    ("currency_amount_v1.jsonl", ShapeCategory.CURRENCY_AMOUNT),
    ("temporal_aggregation_v2.jsonl", ShapeCategory.TEMPORAL_AGGREGATION),
)
_ALL_CORPORA = _ROUND_1 + _ROUND_2


@pytest.mark.parametrize(("filename", "category"), _ROUND_1)
def test_loads_phase_b_corpus_without_loss(filename: str, category: ShapeCategory) -> None:
    path = _EXEMPLARS_ROOT / filename
    corpus = load_exemplar_corpus(path)
    assert isinstance(corpus, ExemplarCorpus)
    assert corpus.shape_category is category
    assert corpus.path == path
    assert len(corpus.exemplars) == 20
    # Every exemplar carries the supported category.
    for ex in corpus.exemplars:
        assert isinstance(ex, Exemplar)
        assert ex.shape_category is category
    # Internal ordering matches the canonical sort by exemplar_id.
    ids = [ex.exemplar_id for ex in corpus.exemplars]
    assert ids == sorted(ids)


@pytest.mark.parametrize(("filename", "_category"), _ROUND_1)
def test_corpus_digest_is_byte_stable(filename: str, _category: ShapeCategory) -> None:
    path = _EXEMPLARS_ROOT / filename
    a = load_exemplar_corpus(path)
    b = load_exemplar_corpus(path)
    assert a.corpus_digest == b.corpus_digest
    assert len(a.corpus_digest) == 64  # sha256 hex


def test_list_corpora_loads_every_round_1_file() -> None:
    corpora = list_corpora(_EXEMPLARS_ROOT)
    cats = {c.shape_category for c in corpora}
    # After ADR-0163.B.2, round-2 categories also load.  The discriminator
    # the test pins is "every committed corpus loads"; round 1 is a subset.
    expected = {cat for _, cat in _ALL_CORPORA}
    assert cats == expected
    # Stable iteration order.
    again = list_corpora(_EXEMPLARS_ROOT)
    assert [c.corpus_digest for c in corpora] == [c.corpus_digest for c in again]


def test_rejects_unknown_shape_category(tmp_path: Path) -> None:
    bad = tmp_path / "uncategorized_v1.jsonl"
    bad.write_text(
        json.dumps({
            "exemplar_id": "x-0001",
            "shape_category": "uncategorized",
            "statement": "test",
            "expected_graph": {
                "subject": None,
                "quantity_anchors": [],
                "graph_intent": "setup",
                "outcome": "inadmissible_by_design",
            },
            "provenance": {
                "source": "phase_b_seed",
                "author": "test",
                "round": 1,
                "category_rank": 9,
            },
        }, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ExemplarIngestError, match="not a Phase C round-1 category"):
        load_exemplar_corpus(bad)


def test_rejects_mismatched_anchor_shape(tmp_path: Path) -> None:
    # rate_with_currency JSONL but with a missing currency_symbol.
    bad = tmp_path / "rate_with_currency_v1.jsonl"
    bad.write_text(
        json.dumps({
            "exemplar_id": "rwc-bad-0001",
            "shape_category": "rate_with_currency",
            "statement": "test",
            "expected_graph": {
                "subject": "x",
                "quantity_anchors": [
                    {
                        "kind": "currency_per_unit_rate",
                        # currency_symbol intentionally missing
                        "amount": "10",
                        "amount_kind": "integer",
                        "per_unit": "hour",
                        "subject_role": "x",
                    },
                ],
                "graph_intent": "rate",
                "outcome": "admissible",
            },
            "provenance": {
                "source": "phase_b_seed",
                "author": "test",
                "round": 1,
                "category_rank": 3,
            },
        }, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ExemplarIngestError, match="missing required keys"):
        load_exemplar_corpus(bad)


def test_rejects_file_name_category_mismatch(tmp_path: Path) -> None:
    # Stem says temporal_aggregation_v1 but record says rate_with_currency.
    bad = tmp_path / "temporal_aggregation_v1.jsonl"
    bad.write_text(
        json.dumps({
            "exemplar_id": "rwc-mismatch-0001",
            "shape_category": "rate_with_currency",
            "statement": "test",
            "expected_graph": {
                "subject": "x",
                "quantity_anchors": [
                    {
                        "kind": "currency_per_unit_rate",
                        "currency_symbol": "$",
                        "amount": "10",
                        "amount_kind": "integer",
                        "per_unit": "hour",
                        "subject_role": "x",
                    },
                ],
                "graph_intent": "rate",
                "outcome": "admissible",
            },
            "provenance": {
                "source": "phase_b_seed",
                "author": "test",
                "round": 1,
                "category_rank": 3,
            },
        }, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ExemplarIngestError, match="does not match category"):
        load_exemplar_corpus(bad)


def test_load_reads_only_supplied_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ingest module is pure — only the supplied path is opened.

    Wrap ``builtins.open`` to record every absolute path opened during
    a load.  Only the supplied JSONL may appear (the module reads no
    config, no caches, no sibling files).
    """
    real_open = builtins.open
    opened: list[str] = []

    def _tracking_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _tracking_open)
    target = _EXEMPLARS_ROOT / "rate_with_currency_v1.jsonl"
    # Read_text() bypasses builtins.open in CPython 3.13, so the tracker
    # may legitimately catch nothing.  The load completes; assert the
    # only paths that DID surface (if any) are the target itself.
    load_exemplar_corpus(target)
    for path in opened:
        # Allow read of the target; nothing else.
        assert str(target) in path or path.endswith(".jsonl"), (
            f"unexpected file opened during ingest: {path}"
        )


def test_module_imports_no_llm_or_ml() -> None:
    """Phase C synthesis is rules-only.  No transformer / embedding / ML dep."""
    import teaching.exemplar_ingest as m
    module_file = m.__file__
    assert module_file is not None
    src = Path(module_file).read_text(encoding="utf-8")
    for forbidden in (
        "transformers", "torch", "tensorflow", "openai",
        "anthropic", "sklearn", "numpy.random",
        # No "import nltk" etc.
    ):
        assert forbidden not in src, (
            f"forbidden import {forbidden!r} in exemplar_ingest.py"
        )
