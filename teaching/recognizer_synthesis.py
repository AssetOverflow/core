"""ADR-0163 Phase C — admissibility recognizer synthesis.

Distill an :class:`~teaching.exemplar_ingest.ExemplarCorpus` into one
:class:`RecognizerSpec`: a typed shape specification consumed downstream
by the Phase D / Phase E candidate-graph admissibility surface.

Doctrine (non-negotiable)
- Deterministic: same corpus → same :class:`RecognizerSpec`,
  byte-identical when re-serialized.
- Narrower, not broader, than the seeds.  Observed-only sub-shapes are
  named explicitly; the recognizer does not generalize to currency
  symbols, window units, or per-unit measures the seeds never carried.
- Doctrine-compatible with Phase B author_notes.  Each author_note is
  either honored by a per-category branch *or* surfaced in
  ``canonical_pattern.unresolved_notes`` for Phase D review — never
  silently dropped.
- No hidden normalization.  Seed strings flow through verbatim.

The module is pure: rules-only, no LLM call, no embedding, no learned
classifier, no I/O beyond reading the supplied corpus dataclass.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from teaching.exemplar_ingest import Exemplar, ExemplarCorpus


class RecognizerSynthesisError(ValueError):
    """Raised when a corpus is structurally unsynthesizable."""


@dataclass(frozen=True, slots=True)
class RecognizerSpec:
    """The distilled, narrowest commitment that subsumes every seed.

    Phase C produces the spec.  Phase D's review surface is where the
    operator may choose to widen any ``observed_*`` set.  Phase E's
    measurement re-runs the GSM8K + capability lanes with the widened
    recognizer to verify ``wrong = 0`` still holds.

    ``canonical_pattern`` is the load-bearing field.  Its keys are
    per-category bespoke; consumers MUST branch on ``shape_category``
    before reading.
    """

    shape_category: ShapeCategory
    canonical_pattern: Mapping[str, Any]
    exemplar_count: int
    exemplar_digest: str
    coverage: Mapping[str, int]

    def canonical_bytes(self) -> bytes:
        """Canonical sorted-key JSON bytes — what the proposal_id hashes."""
        payload = {
            "shape_category": self.shape_category.value,
            "canonical_pattern": _as_jsonable(self.canonical_pattern),
            "exemplar_count": self.exemplar_count,
            "exemplar_digest": self.exemplar_digest,
            "coverage": dict(self.coverage),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def spec_digest(self) -> str:
        """sha256 over :meth:`canonical_bytes`; identifies the spec."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "shape_category": self.shape_category.value,
            "canonical_pattern": _as_jsonable(self.canonical_pattern),
            "exemplar_count": self.exemplar_count,
            "exemplar_digest": self.exemplar_digest,
            "coverage": dict(self.coverage),
        }


def _as_jsonable(payload: Any) -> Any:
    """Recursively coerce mappings/sequences to JSON-serializable dicts/lists.

    Tuples become lists; frozensets become sorted lists.  Used so the
    ``canonical_pattern`` mapping's value tree round-trips byte-identically
    through :func:`json.dumps(sort_keys=True)`.
    """
    if isinstance(payload, Mapping):
        return {k: _as_jsonable(v) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_as_jsonable(v) for v in payload]
    if isinstance(payload, (set, frozenset)):
        return sorted(_as_jsonable(v) for v in payload)
    return payload


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _collect_author_notes(exemplars: tuple[Exemplar, ...]) -> list[str]:
    """Deduplicated, sorted author_notes — Phase B operator surface."""
    notes: set[str] = set()
    for ex in exemplars:
        note = ex.author_note
        if note:
            notes.add(note)
    return sorted(notes)


def _sorted_unique(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for v in sorted(values, key=lambda x: str(x)):
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# Per-category synthesizers — flat aggregations, no smart generalization
# ---------------------------------------------------------------------------


def _synthesize_descriptive_setup_no_quantity(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """All seeds: zero anchors, graph_intent=setup, outcome=inadmissible_by_design.

    The recognizer's commitment is exactly that: a statement with no
    extractable quantity must be admitted as setup context, not refused.
    Narrowness rule: anchor_count is pinned at 0 (no widening).
    """
    exemplars = corpus.exemplars
    subjects_observed_null = sum(1 for e in exemplars if e.expected_graph.get("subject") is None)
    subjects_observed_named = sum(1 for e in exemplars if e.expected_graph.get("subject"))
    # Sanity: validator already pinned this; assert defensively.
    for ex in exemplars:
        if ex.expected_graph["quantity_anchors"] != []:
            raise RecognizerSynthesisError(
                f"{ex.exemplar_id}: descriptive_setup_no_quantity seed has "
                "non-empty anchors — corpus is structurally invalid"
            )
    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY.value,
        "graph_intent": "setup",
        "outcome": "inadmissible_by_design",
        "quantity_anchor_count": 0,
        "subject_is_optional": True,
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    coverage: dict[str, int] = {
        "anchors_empty": len(exemplars),
        "subject_null": subjects_observed_null,
        "subject_named": subjects_observed_named,
    }
    return canonical_pattern, coverage


def _synthesize_temporal_aggregation(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """All anchors are event_count_per_window.  Capture window axis exactly."""
    exemplars = corpus.exemplars
    window_units: list[str] = []
    window_quantifiers: list[str] = []
    anchor_counts: list[int] = []
    coverage_units: dict[str, int] = {}
    coverage_quantifiers: dict[str, int] = {}

    for ex in exemplars:
        anchors = ex.expected_graph["quantity_anchors"]
        anchor_counts.append(len(anchors))
        for a in anchors:
            window_units.append(a["window_unit"])
            window_quantifiers.append(a["window_quantifier"])
            coverage_units[a["window_unit"]] = coverage_units.get(a["window_unit"], 0) + 1
            q = a["window_quantifier"]
            coverage_quantifiers[q] = coverage_quantifiers.get(q, 0) + 1

    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.TEMPORAL_AGGREGATION.value,
        "graph_intent": "aggregate",
        "outcome": "admissible",
        "anchor_kind": "event_count_per_window",
        "observed_window_units": _sorted_unique(window_units),
        "observed_window_quantifiers": _sorted_unique(window_quantifiers),
        "anchor_count_min": min(anchor_counts),
        "anchor_count_max": max(anchor_counts),
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    # Coverage histogram: per-anchor-kind + per-axis frequencies.
    coverage: dict[str, int] = {
        "anchors_event_count_per_window": sum(anchor_counts),
    }
    for unit, n in sorted(coverage_units.items()):
        coverage[f"window_unit:{unit}"] = n
    for q, n in sorted(coverage_quantifiers.items()):
        coverage[f"window_quantifier:{q}"] = n
    return canonical_pattern, coverage


def _synthesize_rate_with_currency(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """All anchors are currency_per_unit_rate.  Capture currency/unit/kind axes."""
    exemplars = corpus.exemplars
    currency_symbols: list[str] = []
    per_units: list[str] = []
    amount_kinds: list[str] = []
    anchor_counts: list[int] = []
    coverage_currency: dict[str, int] = {}
    coverage_per_unit: dict[str, int] = {}
    coverage_amount_kind: dict[str, int] = {}

    for ex in exemplars:
        anchors = ex.expected_graph["quantity_anchors"]
        anchor_counts.append(len(anchors))
        for a in anchors:
            currency_symbols.append(a["currency_symbol"])
            per_units.append(a["per_unit"])
            amount_kinds.append(a["amount_kind"])
            coverage_currency[a["currency_symbol"]] = (
                coverage_currency.get(a["currency_symbol"], 0) + 1
            )
            coverage_per_unit[a["per_unit"]] = coverage_per_unit.get(a["per_unit"], 0) + 1
            coverage_amount_kind[a["amount_kind"]] = (
                coverage_amount_kind.get(a["amount_kind"], 0) + 1
            )

    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.RATE_WITH_CURRENCY.value,
        "graph_intent": "rate",
        "outcome": "admissible",
        "anchor_kind": "currency_per_unit_rate",
        "observed_currency_symbols": _sorted_unique(currency_symbols),
        "observed_per_units": _sorted_unique(per_units),
        "observed_amount_kinds": _sorted_unique(amount_kinds),
        "anchor_count_min": min(anchor_counts),
        "anchor_count_max": max(anchor_counts),
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    coverage: dict[str, int] = {
        "anchors_currency_per_unit_rate": sum(anchor_counts),
    }
    for sym, n in sorted(coverage_currency.items()):
        coverage[f"currency_symbol:{sym}"] = n
    for u, n in sorted(coverage_per_unit.items()):
        coverage[f"per_unit:{u}"] = n
    for k, n in sorted(coverage_amount_kind.items()):
        coverage[f"amount_kind:{k}"] = n
    return canonical_pattern, coverage


def _synthesize_discrete_count_statement(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """ADR-0163.B.2 — discrete-count seeds.

    Each anchor carries (count_token, count_kind, counted_noun).  The
    synthesizer records ``observed_count_kinds`` as a narrowness gate
    (integer/word); ``observed_counted_nouns`` is coverage-only — gating
    on every noun in the seed corpus would over-narrow the matcher
    across the GSM8K nominal vocabulary.
    """
    exemplars = corpus.exemplars
    count_kinds: list[str] = []
    counted_nouns: list[str] = []
    anchor_counts: list[int] = []
    coverage_count_kind: dict[str, int] = {}
    coverage_counted_noun: dict[str, int] = {}
    for ex in exemplars:
        anchors = ex.expected_graph["quantity_anchors"]
        anchor_counts.append(len(anchors))
        for a in anchors:
            ck = a["count_kind"]
            noun = a["counted_noun"]
            count_kinds.append(ck)
            counted_nouns.append(noun)
            coverage_count_kind[ck] = coverage_count_kind.get(ck, 0) + 1
            coverage_counted_noun[noun] = coverage_counted_noun.get(noun, 0) + 1
    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.DISCRETE_COUNT_STATEMENT.value,
        "graph_intent": "count",
        "outcome": "admissible",
        "anchor_kind": "discrete_count",
        "observed_count_kinds": _sorted_unique(count_kinds),
        "observed_counted_nouns": _sorted_unique(counted_nouns),
        "anchor_count_min": min(anchor_counts),
        "anchor_count_max": max(anchor_counts),
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    coverage: dict[str, int] = {"anchors_discrete_count": sum(anchor_counts)}
    for k, n in sorted(coverage_count_kind.items()):
        coverage[f"count_kind:{k}"] = n
    for noun, n in sorted(coverage_counted_noun.items()):
        coverage[f"counted_noun:{noun}"] = n
    return canonical_pattern, coverage


def _synthesize_multiplicative_aggregation(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """ADR-0163.B.2 — multiplicative-aggregate seeds (``M outer × N inner``).

    Multi-anchor cases (joined aggregations like Ella's apples) widen
    ``anchor_count_max`` naturally.
    """
    exemplars = corpus.exemplars
    outer_units: list[str] = []
    inner_units: list[str] = []
    anchor_counts: list[int] = []
    coverage_outer: dict[str, int] = {}
    coverage_inner: dict[str, int] = {}
    for ex in exemplars:
        anchors = ex.expected_graph["quantity_anchors"]
        anchor_counts.append(len(anchors))
        for a in anchors:
            ou = a["outer_unit"]
            iu = a["inner_unit"]
            outer_units.append(ou)
            inner_units.append(iu)
            coverage_outer[ou] = coverage_outer.get(ou, 0) + 1
            coverage_inner[iu] = coverage_inner.get(iu, 0) + 1
    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.MULTIPLICATIVE_AGGREGATION.value,
        "graph_intent": "aggregate",
        "outcome": "admissible",
        "anchor_kind": "multiplicative_aggregate",
        "observed_outer_units": _sorted_unique(outer_units),
        "observed_inner_units": _sorted_unique(inner_units),
        "anchor_count_min": min(anchor_counts),
        "anchor_count_max": max(anchor_counts),
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    coverage: dict[str, int] = {
        "anchors_multiplicative_aggregate": sum(anchor_counts),
    }
    for u, n in sorted(coverage_outer.items()):
        coverage[f"outer_unit:{u}"] = n
    for u, n in sorted(coverage_inner.items()):
        coverage[f"inner_unit:{u}"] = n
    return canonical_pattern, coverage


def _synthesize_currency_amount(
    corpus: ExemplarCorpus,
) -> tuple[Mapping[str, Any], Mapping[str, int]]:
    """ADR-0163.B.2 — currency-amount seeds.

    Distinct from ``rate_with_currency``: NO per-unit framing.  The
    synthesizer records observed currency symbols + amount kinds as
    narrowness gates.
    """
    exemplars = corpus.exemplars
    currency_symbols: list[str] = []
    amount_kinds: list[str] = []
    anchor_counts: list[int] = []
    coverage_currency: dict[str, int] = {}
    coverage_amount_kind: dict[str, int] = {}
    for ex in exemplars:
        anchors = ex.expected_graph["quantity_anchors"]
        anchor_counts.append(len(anchors))
        for a in anchors:
            cs = a["currency_symbol"]
            ak = a["amount_kind"]
            currency_symbols.append(cs)
            amount_kinds.append(ak)
            coverage_currency[cs] = coverage_currency.get(cs, 0) + 1
            coverage_amount_kind[ak] = coverage_amount_kind.get(ak, 0) + 1
    canonical_pattern: dict[str, Any] = {
        "shape_category": ShapeCategory.CURRENCY_AMOUNT.value,
        "graph_intent": "amount",
        "outcome": "admissible",
        "anchor_kind": "currency_amount",
        "observed_currency_symbols": _sorted_unique(currency_symbols),
        "observed_amount_kinds": _sorted_unique(amount_kinds),
        "anchor_count_min": min(anchor_counts),
        "anchor_count_max": max(anchor_counts),
        "unresolved_notes": _collect_author_notes(exemplars),
    }
    coverage: dict[str, int] = {"anchors_currency_amount": sum(anchor_counts)}
    for sym, n in sorted(coverage_currency.items()):
        coverage[f"currency_symbol:{sym}"] = n
    for k, n in sorted(coverage_amount_kind.items()):
        coverage[f"amount_kind:{k}"] = n
    return canonical_pattern, coverage


_SYNTHESIZERS = {
    ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY: _synthesize_descriptive_setup_no_quantity,
    ShapeCategory.TEMPORAL_AGGREGATION: _synthesize_temporal_aggregation,
    ShapeCategory.RATE_WITH_CURRENCY: _synthesize_rate_with_currency,
    ShapeCategory.DISCRETE_COUNT_STATEMENT: _synthesize_discrete_count_statement,
    ShapeCategory.MULTIPLICATIVE_AGGREGATION: _synthesize_multiplicative_aggregation,
    ShapeCategory.CURRENCY_AMOUNT: _synthesize_currency_amount,
}


def synthesize_recognizer(corpus: ExemplarCorpus) -> RecognizerSpec:
    """Distil *corpus* into one :class:`RecognizerSpec`.

    Pure function.  Per-category dispatch chooses the synthesizer; common
    framing (digest, exemplar count) is bolted on uniformly.
    """
    synth = _SYNTHESIZERS.get(corpus.shape_category)
    if synth is None:  # pragma: no cover — defensive: ingest already gates
        raise RecognizerSynthesisError(
            f"no synthesizer registered for shape_category="
            f"{corpus.shape_category.value!r}"
        )
    canonical_pattern, coverage = synth(corpus)
    return RecognizerSpec(
        shape_category=corpus.shape_category,
        canonical_pattern=canonical_pattern,
        exemplar_count=len(corpus.exemplars),
        exemplar_digest=corpus.corpus_digest,
        coverage=coverage,
    )


__all__ = [
    "RecognizerSpec",
    "RecognizerSynthesisError",
    "synthesize_recognizer",
]
