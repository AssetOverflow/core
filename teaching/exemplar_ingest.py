"""ADR-0163 Phase C — admissibility exemplar ingest.

Pure-function loader for the operator-authored exemplar corpora under
``teaching/admissibility_exemplars/``.  Returns frozen :class:`ExemplarCorpus`
records whose canonical bytes (sorted JSONL, single trailing newline) the
:attr:`ExemplarCorpus.corpus_digest` field hashes deterministically.

Trust boundary
- Pure functions.  The only file read is the path supplied by the caller
  (or, in ``list_corpora``, the contents of
  ``teaching/admissibility_exemplars/``).  No global state, no caches
  outlive a call, no writes.
- Validation is rules-only.  No LLM, no embedding, no learned classifier.
- The schema enforced here mirrors
  ``teaching/admissibility_exemplars/contract.md`` and the per-category
  dispatcher pattern in ``tests/test_admissibility_exemplars.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory


_EXEMPLARS_ROOT_DEFAULT: Path = (
    Path(__file__).resolve().parent / "admissibility_exemplars"
)

_REQUIRED_TOP_KEYS: frozenset[str] = frozenset({
    "exemplar_id", "shape_category", "statement", "expected_graph", "provenance",
})
_REQUIRED_GRAPH_KEYS: frozenset[str] = frozenset({
    "subject", "quantity_anchors", "graph_intent", "outcome",
})
_REQUIRED_PROVENANCE_KEYS: frozenset[str] = frozenset({
    "source", "author", "round", "category_rank",
})

_VALID_WINDOW_UNITS: frozenset[str] = frozenset({
    "day", "week", "month", "year", "hour", "minute", "second",
})
_VALID_WINDOW_QUANTIFIERS: frozenset[str] = frozenset({"each", "every", "per"})
_VALID_CURRENCY_SYMBOLS: frozenset[str] = frozenset({"$", "£", "€", "¥"})
_VALID_AMOUNT_KINDS: frozenset[str] = frozenset({"integer", "decimal", "word"})


# The categories Phase C ingests in round 1.  Adding a category here
# requires landing its exemplar corpus + its synthesizer first.
_SUPPORTED_CATEGORIES: frozenset[ShapeCategory] = frozenset({
    ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY,
    ShapeCategory.TEMPORAL_AGGREGATION,
    ShapeCategory.RATE_WITH_CURRENCY,
})


class ExemplarIngestError(ValueError):
    """Raised when an exemplar JSONL violates the Phase B contract."""


@dataclass(frozen=True, slots=True)
class Exemplar:
    """One parsed exemplar record.

    Mirrors the JSONL line verbatim.  ``expected_graph`` and
    ``provenance`` keep their full submaps so the synthesizer can read
    every field the contract surfaces (including the optional
    ``author_note``).
    """

    exemplar_id: str
    shape_category: ShapeCategory
    statement: str
    expected_graph: Mapping[str, Any]
    provenance: Mapping[str, Any]

    @property
    def case_id(self) -> str | None:
        """Optional GSM8K train-sample case_id this exemplar cites."""
        cid = self.provenance.get("train_case_id")
        return str(cid) if cid else None

    @property
    def author_note(self) -> str | None:
        note = self.provenance.get("author_note")
        return str(note) if note else None


@dataclass(frozen=True, slots=True)
class ExemplarCorpus:
    """One ingested exemplar corpus + the digest of its canonical bytes.

    ``corpus_digest`` is a sha256 over the file's canonical re-encoding
    (sorted by ``exemplar_id``, sorted-key JSON, single trailing newline).
    Two corpora whose seeds carry identical content produce identical
    digests regardless of incidental whitespace.
    """

    shape_category: ShapeCategory
    path: Path
    exemplars: tuple[Exemplar, ...]
    corpus_digest: str


# ---------------------------------------------------------------------------
# Per-category validation dispatch
# ---------------------------------------------------------------------------


def _require_keys(
    ctx: str, payload: Mapping[str, Any], required: frozenset[str]
) -> None:
    missing = required - set(payload.keys())
    if missing:
        raise ExemplarIngestError(
            f"{ctx} missing required keys: {sorted(missing)}"
        )


def _validate_descriptive_setup(ctx: str, graph: Mapping[str, Any]) -> None:
    anchors = graph["quantity_anchors"]
    if not isinstance(anchors, list):
        raise ExemplarIngestError(f"{ctx} quantity_anchors must be list")
    if anchors != []:
        raise ExemplarIngestError(
            f"{ctx} descriptive_setup_no_quantity requires empty anchors"
        )
    if graph["graph_intent"] != "setup":
        raise ExemplarIngestError(f"{ctx} graph_intent must be 'setup'")
    if graph["outcome"] != "inadmissible_by_design":
        raise ExemplarIngestError(
            f"{ctx} outcome must be 'inadmissible_by_design'"
        )


def _validate_temporal_aggregation(ctx: str, graph: Mapping[str, Any]) -> None:
    anchors = graph["quantity_anchors"]
    if not isinstance(anchors, list) or not anchors:
        raise ExemplarIngestError(f"{ctx} temporal_aggregation needs ≥1 anchor")
    for a in anchors:
        if not isinstance(a, Mapping):
            raise ExemplarIngestError(f"{ctx} anchor must be a mapping")
        _require_keys(ctx, a, frozenset({
            "kind", "count_token", "window_unit",
            "window_quantifier", "subject_role",
        }))
        if a["kind"] != "event_count_per_window":
            raise ExemplarIngestError(
                f"{ctx} anchor kind must be 'event_count_per_window'"
            )
        if a["window_unit"] not in _VALID_WINDOW_UNITS:
            raise ExemplarIngestError(
                f"{ctx} window_unit {a['window_unit']!r} not in "
                f"{sorted(_VALID_WINDOW_UNITS)}"
            )
        if a["window_quantifier"] not in _VALID_WINDOW_QUANTIFIERS:
            raise ExemplarIngestError(
                f"{ctx} window_quantifier {a['window_quantifier']!r} not in "
                f"{sorted(_VALID_WINDOW_QUANTIFIERS)}"
            )
        if not isinstance(a["count_token"], str) or not a["count_token"]:
            raise ExemplarIngestError(f"{ctx} count_token must be non-empty str")
        if not isinstance(a["subject_role"], str) or not a["subject_role"]:
            raise ExemplarIngestError(f"{ctx} subject_role must be non-empty str")
    if graph["graph_intent"] != "aggregate":
        raise ExemplarIngestError(f"{ctx} graph_intent must be 'aggregate'")
    if graph["outcome"] != "admissible":
        raise ExemplarIngestError(f"{ctx} outcome must be 'admissible'")


def _validate_rate_with_currency(ctx: str, graph: Mapping[str, Any]) -> None:
    anchors = graph["quantity_anchors"]
    if not isinstance(anchors, list) or not anchors:
        raise ExemplarIngestError(f"{ctx} rate_with_currency needs ≥1 anchor")
    for a in anchors:
        if not isinstance(a, Mapping):
            raise ExemplarIngestError(f"{ctx} anchor must be a mapping")
        _require_keys(ctx, a, frozenset({
            "kind", "currency_symbol", "amount", "amount_kind",
            "per_unit", "subject_role",
        }))
        if a["kind"] != "currency_per_unit_rate":
            raise ExemplarIngestError(
                f"{ctx} anchor kind must be 'currency_per_unit_rate'"
            )
        if a["currency_symbol"] not in _VALID_CURRENCY_SYMBOLS:
            raise ExemplarIngestError(
                f"{ctx} currency_symbol {a['currency_symbol']!r} not in "
                f"{sorted(_VALID_CURRENCY_SYMBOLS)}"
            )
        if a["amount_kind"] not in _VALID_AMOUNT_KINDS:
            raise ExemplarIngestError(
                f"{ctx} amount_kind {a['amount_kind']!r} not in "
                f"{sorted(_VALID_AMOUNT_KINDS)}"
            )
        for fld in ("amount", "per_unit", "subject_role"):
            if not isinstance(a[fld], str) or not a[fld]:
                raise ExemplarIngestError(
                    f"{ctx} {fld} must be non-empty str"
                )
    if graph["graph_intent"] != "rate":
        raise ExemplarIngestError(f"{ctx} graph_intent must be 'rate'")
    if graph["outcome"] != "admissible":
        raise ExemplarIngestError(f"{ctx} outcome must be 'admissible'")


_CATEGORY_VALIDATORS = {
    ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY: _validate_descriptive_setup,
    ShapeCategory.TEMPORAL_AGGREGATION: _validate_temporal_aggregation,
    ShapeCategory.RATE_WITH_CURRENCY: _validate_rate_with_currency,
}


def _parse_record(path: Path, idx: int, raw: Mapping[str, Any]) -> Exemplar:
    ctx = f"{path}:{idx}"
    _require_keys(ctx, raw, _REQUIRED_TOP_KEYS)

    cat_str = raw["shape_category"]
    if not any(cat_str == c.value for c in ShapeCategory):
        raise ExemplarIngestError(
            f"{ctx} shape_category {cat_str!r} not in ShapeCategory"
        )
    shape_category = ShapeCategory(cat_str)
    if shape_category not in _SUPPORTED_CATEGORIES:
        raise ExemplarIngestError(
            f"{ctx} shape_category {cat_str!r} is not a Phase C round-1 "
            f"category; supported = "
            f"{sorted(c.value for c in _SUPPORTED_CATEGORIES)}"
        )

    statement = raw["statement"]
    if not isinstance(statement, str) or not statement:
        raise ExemplarIngestError(f"{ctx} statement must be non-empty str")

    graph = raw["expected_graph"]
    if not isinstance(graph, Mapping):
        raise ExemplarIngestError(f"{ctx} expected_graph must be a mapping")
    _require_keys(ctx, graph, _REQUIRED_GRAPH_KEYS)

    prov = raw["provenance"]
    if not isinstance(prov, Mapping):
        raise ExemplarIngestError(f"{ctx} provenance must be a mapping")
    _require_keys(ctx, prov, _REQUIRED_PROVENANCE_KEYS)

    _CATEGORY_VALIDATORS[shape_category](ctx, graph)

    return Exemplar(
        exemplar_id=str(raw["exemplar_id"]),
        shape_category=shape_category,
        statement=statement,
        expected_graph=dict(graph),
        provenance=dict(prov),
    )


def _canonical_bytes(records: list[Mapping[str, Any]]) -> bytes:
    """Re-encode records as sorted-by-exemplar_id canonical JSONL bytes.

    Two physically different files whose records carry identical content
    produce the same canonical bytes (and hence the same ``corpus_digest``).
    Trailing whitespace, key ordering inside records, and line-by-line
    insertion order are all normalized.
    """
    sorted_records = sorted(records, key=lambda r: r["exemplar_id"])
    chunks = []
    for r in sorted_records:
        chunks.append(json.dumps(r, sort_keys=True, separators=(",", ":")))
    return ("\n".join(chunks) + "\n").encode("utf-8")


def load_exemplar_corpus(path: Path) -> ExemplarCorpus:
    """Load and validate one exemplar corpus from *path*.

    Pure function.  Same path + same bytes → identical
    :class:`ExemplarCorpus`.  Raises :class:`ExemplarIngestError` for any
    contract violation; partial corpora are never returned.
    """
    if not path.exists():
        raise ExemplarIngestError(f"exemplar corpus not found: {path}")
    raw = path.read_text(encoding="utf-8")
    if not raw:
        raise ExemplarIngestError(f"exemplar corpus is empty: {path}")
    records_raw: list[Mapping[str, Any]] = []
    parsed: list[Exemplar] = []
    for idx, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExemplarIngestError(
                f"{path}:{idx} invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(record, Mapping):
            raise ExemplarIngestError(
                f"{path}:{idx} record must be a JSON object"
            )
        records_raw.append(record)
        parsed.append(_parse_record(path, idx, record))

    # File-name to category binding.  The contract guarantees one
    # category per file; enforce it on read so a misnamed file fails
    # loudly rather than silently producing a mixed corpus.
    category = parsed[0].shape_category
    for ex in parsed[1:]:
        if ex.shape_category != category:
            raise ExemplarIngestError(
                f"{path} mixes categories: {category.value!r} and "
                f"{ex.shape_category.value!r} both present"
            )
    expected_stem = f"{category.value}_v1"
    if path.stem != expected_stem:
        raise ExemplarIngestError(
            f"{path} stem {path.stem!r} does not match category "
            f"{category.value!r}; expected stem {expected_stem!r}"
        )

    # Deterministic order on the in-memory list mirrors the canonical
    # bytes the digest is computed over.
    parsed.sort(key=lambda e: e.exemplar_id)

    digest = hashlib.sha256(_canonical_bytes(records_raw)).hexdigest()

    return ExemplarCorpus(
        shape_category=category,
        path=path,
        exemplars=tuple(parsed),
        corpus_digest=digest,
    )


def list_corpora(root: Path | None = None) -> tuple[ExemplarCorpus, ...]:
    """Load every ``*_v1.jsonl`` under *root* (default exemplars dir).

    Returns corpora sorted by ``shape_category.value`` so callers get a
    stable iteration order regardless of filesystem listing semantics.
    """
    base = root if root is not None else _EXEMPLARS_ROOT_DEFAULT
    if not base.is_dir():
        raise ExemplarIngestError(f"exemplars root is not a directory: {base}")
    corpora: list[ExemplarCorpus] = []
    for path in sorted(base.glob("*_v1.jsonl")):
        corpora.append(load_exemplar_corpus(path))
    corpora.sort(key=lambda c: c.shape_category.value)
    return tuple(corpora)


__all__ = [
    "Exemplar",
    "ExemplarCorpus",
    "ExemplarIngestError",
    "list_corpora",
    "load_exemplar_corpus",
]
