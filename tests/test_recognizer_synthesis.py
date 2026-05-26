"""ADR-0163 Phase C — recognizer_synthesis tests.

Pins:
- synthesize_recognizer is deterministic (same corpus -> same spec bytes)
- synthesize_recognizer is pure (no I/O, no global state)
- per-category canonical_pattern subsumes every seed
- the pattern is NARROWER than a generic any-shape (an out-of-corpus
  seed must not match)
- author_notes are honored or surfaced — never silently dropped
- the module performs no LLM / embedding / ML import
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from teaching.exemplar_ingest import (
    Exemplar,
    ExemplarCorpus,
    load_exemplar_corpus,
)
from teaching.recognizer_synthesis import (
    RecognizerSpec,
    synthesize_recognizer,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLARS_ROOT = _REPO_ROOT / "teaching" / "admissibility_exemplars"
_ROUND_1: tuple[tuple[str, ShapeCategory], ...] = (
    ("descriptive_setup_no_quantity_v1.jsonl", ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY),
    ("temporal_aggregation_v1.jsonl", ShapeCategory.TEMPORAL_AGGREGATION),
    ("rate_with_currency_v1.jsonl", ShapeCategory.RATE_WITH_CURRENCY),
)


@pytest.fixture(scope="module")
def corpora() -> dict[ShapeCategory, ExemplarCorpus]:
    out: dict[ShapeCategory, ExemplarCorpus] = {}
    for filename, cat in _ROUND_1:
        out[cat] = load_exemplar_corpus(_EXEMPLARS_ROOT / filename)
    return out


# ---------------------------------------------------------------------------
# Determinism + purity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("_filename", "category"), _ROUND_1)
def test_synthesis_is_deterministic(
    _filename: str,
    category: ShapeCategory,
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    corpus = corpora[category]
    a = synthesize_recognizer(corpus)
    b = synthesize_recognizer(corpus)
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.spec_digest() == b.spec_digest()


@pytest.mark.parametrize(("_filename", "category"), _ROUND_1)
def test_synthesis_is_pure_no_io(
    monkeypatch: pytest.MonkeyPatch,
    _filename: str,
    category: ShapeCategory,
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    corpus = corpora[category]
    real_open = builtins.open

    def _no_open(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            f"synthesize_recognizer opened a file: args={args}"
        )

    monkeypatch.setattr(builtins, "open", _no_open)
    try:
        spec = synthesize_recognizer(corpus)
    finally:
        monkeypatch.setattr(builtins, "open", real_open)
    assert isinstance(spec, RecognizerSpec)


# ---------------------------------------------------------------------------
# Subsumption + narrowness
# ---------------------------------------------------------------------------


def _matches(spec: RecognizerSpec, ex: Exemplar) -> bool:
    """Mechanical predicate: does *spec* subsume *ex*?

    The recognizer's canonical_pattern is bespoke per category, so the
    matcher is bespoke too.  Each branch checks every axis the spec
    constrains.  Used only in tests to assert (a) every seed matches
    and (b) an out-of-corpus seed does not.
    """
    p = spec.canonical_pattern
    graph = ex.expected_graph
    if spec.shape_category is ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY:
        return (
            graph["graph_intent"] == p["graph_intent"]
            and graph["outcome"] == p["outcome"]
            and len(graph["quantity_anchors"]) == p["quantity_anchor_count"]
        )
    if spec.shape_category is ShapeCategory.TEMPORAL_AGGREGATION:
        if graph["graph_intent"] != p["graph_intent"]:
            return False
        if graph["outcome"] != p["outcome"]:
            return False
        anchors = graph["quantity_anchors"]
        if not (p["anchor_count_min"] <= len(anchors) <= p["anchor_count_max"]):
            return False
        observed_units = set(p["observed_window_units"])
        observed_quants = set(p["observed_window_quantifiers"])
        for a in anchors:
            if a["kind"] != p["anchor_kind"]:
                return False
            if a["window_unit"] not in observed_units:
                return False
            if a["window_quantifier"] not in observed_quants:
                return False
        return True
    if spec.shape_category is ShapeCategory.RATE_WITH_CURRENCY:
        if graph["graph_intent"] != p["graph_intent"]:
            return False
        if graph["outcome"] != p["outcome"]:
            return False
        anchors = graph["quantity_anchors"]
        if not (p["anchor_count_min"] <= len(anchors) <= p["anchor_count_max"]):
            return False
        observed_curr = set(p["observed_currency_symbols"])
        observed_pu = set(p["observed_per_units"])
        observed_ak = set(p["observed_amount_kinds"])
        for a in anchors:
            if a["kind"] != p["anchor_kind"]:
                return False
            if a["currency_symbol"] not in observed_curr:
                return False
            if a["per_unit"] not in observed_pu:
                return False
            if a["amount_kind"] not in observed_ak:
                return False
        return True
    raise AssertionError(f"no matcher for {spec.shape_category!r}")


@pytest.mark.parametrize(("_filename", "category"), _ROUND_1)
def test_canonical_pattern_subsumes_every_seed(
    _filename: str,
    category: ShapeCategory,
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    corpus = corpora[category]
    spec = synthesize_recognizer(corpus)
    for ex in corpus.exemplars:
        assert _matches(spec, ex), (
            f"{ex.exemplar_id}: synthesized spec does NOT subsume its own seed"
        )


def _ex(category: ShapeCategory, graph: dict[str, Any]) -> Exemplar:
    return Exemplar(
        exemplar_id="out-of-corpus-0001",
        shape_category=category,
        statement="test",
        expected_graph=graph,
        provenance={"source": "phase_b_seed", "author": "test", "round": 1, "category_rank": 0},
    )


def test_descriptive_pattern_rejects_seed_with_anchor(
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    """A descriptive-setup recognizer must not match a statement carrying
    an anchor — that would mean admitting quantitative shapes as setup."""
    spec = synthesize_recognizer(corpora[ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY])
    fake = _ex(
        ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY,
        {
            "subject": "x",
            "quantity_anchors": [
                {
                    "kind": "currency_per_unit_rate",
                    "currency_symbol": "$",
                    "amount": "1",
                    "amount_kind": "integer",
                    "per_unit": "hour",
                    "subject_role": "x",
                },
            ],
            "graph_intent": "setup",
            "outcome": "inadmissible_by_design",
        },
    )
    assert not _matches(spec, fake)


def test_temporal_pattern_rejects_unseen_window_unit(
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    """If the seeds never carry a millisecond window, the recognizer
    must not generalize to it.  Phase D's review can widen; synthesis
    does not."""
    spec = synthesize_recognizer(corpora[ShapeCategory.TEMPORAL_AGGREGATION])
    observed_units = set(spec.canonical_pattern["observed_window_units"])
    # Find any window unit NOT in the observed set.  The Phase B
    # vocabulary covers second..year, but seeds may use a subset.
    all_units = {"day", "week", "month", "year", "hour", "minute", "second"}
    unseen = all_units - observed_units
    assert unseen, "no unseen window unit available — corpus covers vocabulary"
    fake_unit = sorted(unseen)[0]
    fake = _ex(
        ShapeCategory.TEMPORAL_AGGREGATION,
        {
            "subject": "x",
            "quantity_anchors": [
                {
                    "kind": "event_count_per_window",
                    "count_token": "1",
                    "window_unit": fake_unit,
                    "window_quantifier": "each",
                    "subject_role": "x",
                },
            ],
            "graph_intent": "aggregate",
            "outcome": "admissible",
        },
    )
    assert not _matches(spec, fake), (
        f"recognizer wrongly generalized to unseen window_unit={fake_unit!r}"
    )


def test_rate_pattern_rejects_unseen_currency(
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    """Same narrowness rule for currencies: the seeds cite a subset of
    {$, £, €, ¥}.  Currencies outside that subset must not match."""
    spec = synthesize_recognizer(corpora[ShapeCategory.RATE_WITH_CURRENCY])
    observed = set(spec.canonical_pattern["observed_currency_symbols"])
    all_sym = {"$", "£", "€", "¥"}
    unseen = all_sym - observed
    if not unseen:
        # Every currency in the vocabulary appeared.  Fall back to a
        # synthetic currency not in the vocabulary at all.
        fake_sym = "₿"  # bitcoin sign — not in _VALID_CURRENCY_SYMBOLS
    else:
        fake_sym = sorted(unseen)[0]
    fake = _ex(
        ShapeCategory.RATE_WITH_CURRENCY,
        {
            "subject": "x",
            "quantity_anchors": [
                {
                    "kind": "currency_per_unit_rate",
                    "currency_symbol": fake_sym,
                    "amount": "10",
                    "amount_kind": "integer",
                    "per_unit": list(spec.canonical_pattern["observed_per_units"])[0],
                    "subject_role": "x",
                },
            ],
            "graph_intent": "rate",
            "outcome": "admissible",
        },
    )
    assert not _matches(spec, fake), (
        f"recognizer wrongly generalized to unseen currency={fake_sym!r}"
    )


# ---------------------------------------------------------------------------
# Author_notes are honored or surfaced — never silently dropped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("_filename", "category"), _ROUND_1)
def test_author_notes_surface_in_unresolved_notes(
    _filename: str,
    category: ShapeCategory,
    corpora: dict[ShapeCategory, ExemplarCorpus],
) -> None:
    corpus = corpora[category]
    spec = synthesize_recognizer(corpus)
    unresolved = set(spec.canonical_pattern["unresolved_notes"])
    for ex in corpus.exemplars:
        note = ex.author_note
        if not note:
            continue
        assert note in unresolved, (
            f"{ex.exemplar_id}: author_note silently dropped: {note!r}"
        )


def test_module_imports_no_llm_or_ml() -> None:
    """Phase C synthesis is rules-only.  No transformer / embedding."""
    import teaching.recognizer_synthesis as m
    module_file = m.__file__
    assert module_file is not None
    src = Path(module_file).read_text(encoding="utf-8")
    for forbidden in (
        "transformers", "torch", "tensorflow", "openai",
        "anthropic", "sklearn", "numpy.random",
    ):
        assert forbidden not in src, (
            f"forbidden import {forbidden!r} in recognizer_synthesis.py"
        )
