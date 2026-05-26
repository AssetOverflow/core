"""ADR-0163 Phase B — admissibility exemplar corpora tests.

Validates the operator-authored exemplar corpora under
``teaching/admissibility_exemplars/`` against the schema specified in
``teaching/admissibility_exemplars/contract.md``.

The tests are pure, deterministic, and read-only — they import no runtime
module beyond ``evals.refusal_taxonomy.shape_categories`` (for enum binding)
and never mutate any file under ``generate/``, ``evals/``, or
``teaching/proposals/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLARS_ROOT = _REPO_ROOT / "teaching" / "admissibility_exemplars"
_GSM8K_TRAIN_REPORT = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"
)

# Round 1 categories, with their file stem and expected category-rank.
_ROUND_1: tuple[tuple[str, ShapeCategory, int], ...] = (
    (
        "descriptive_setup_no_quantity_v1",
        ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY,
        1,
    ),
    ("temporal_aggregation_v1", ShapeCategory.TEMPORAL_AGGREGATION, 2),
    ("rate_with_currency_v1", ShapeCategory.RATE_WITH_CURRENCY, 3),
)

_REQUIRED_TOP_KEYS: frozenset[str] = frozenset(
    {"exemplar_id", "shape_category", "statement", "expected_graph", "provenance"}
)
_REQUIRED_GRAPH_KEYS: frozenset[str] = frozenset(
    {"subject", "quantity_anchors", "graph_intent", "outcome"}
)
_REQUIRED_PROVENANCE_KEYS: frozenset[str] = frozenset(
    {"source", "author", "round", "category_rank"}
)

_VALID_WINDOW_UNITS: frozenset[str] = frozenset(
    {"day", "week", "month", "year", "hour", "minute", "second"}
)
_VALID_WINDOW_QUANTIFIERS: frozenset[str] = frozenset({"each", "every", "per"})
_VALID_CURRENCY_SYMBOLS: frozenset[str] = frozenset({"$", "£", "€", "¥"})
_VALID_AMOUNT_KINDS: frozenset[str] = frozenset({"integer", "decimal", "word"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    if not raw.endswith("\n"):
        raise AssertionError(f"{path} must end with a single trailing newline")
    if raw.endswith("\n\n"):
        raise AssertionError(f"{path} must not have multiple trailing newlines")
    lines = raw.splitlines()
    records: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        if line != line.rstrip():
            raise AssertionError(
                f"{path}:{idx} has trailing whitespace"
            )
        records.append(json.loads(line))
    return records


def _train_sample_case_ids() -> set[str]:
    report = json.loads(_GSM8K_TRAIN_REPORT.read_text(encoding="utf-8"))
    return {entry["case_id"] for entry in report.get("per_case", [])}


# ---------------------------------------------------------------------------
# File presence
# ---------------------------------------------------------------------------


def test_exemplars_root_exists_and_marker_is_empty():
    assert _EXEMPLARS_ROOT.is_dir(), _EXEMPLARS_ROOT
    init = _EXEMPLARS_ROOT / "__init__.py"
    assert init.is_file()
    assert init.read_text(encoding="utf-8") == ""


def test_contract_exists():
    assert (_EXEMPLARS_ROOT / "contract.md").is_file()


@pytest.mark.parametrize(("stem", "_category", "_rank"), _ROUND_1)
def test_corpus_file_exists(stem: str, _category: ShapeCategory, _rank: int):
    path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
    assert path.is_file(), path


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("stem", "category", "rank"), _ROUND_1)
def test_records_schema(stem: str, category: ShapeCategory, rank: int):
    path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
    records = _load_jsonl(path)
    assert 1 <= len(records) <= 20, f"{path} has {len(records)} records"

    seen_ids: set[str] = set()
    for idx, record in enumerate(records, start=1):
        missing = _REQUIRED_TOP_KEYS - set(record)
        assert not missing, f"{path}:{idx} missing top-level keys: {missing}"

        eid = record["exemplar_id"]
        assert isinstance(eid, str) and eid, f"{path}:{idx} bad exemplar_id"
        assert eid not in seen_ids, f"{path}:{idx} duplicate exemplar_id {eid}"
        seen_ids.add(eid)

        # exemplar_id format: "<prefix>-v1-<NNNN>".  The prefix is per-file.
        parts = eid.rsplit("-", 2)
        assert len(parts) == 3 and parts[1] == "v1", (
            f"{path}:{idx} exemplar_id {eid!r} must match <prefix>-v1-<NNNN>"
        )
        assert parts[2].isdigit() and len(parts[2]) == 4, (
            f"{path}:{idx} exemplar_id suffix {parts[2]!r} must be 4 digits"
        )

        # shape_category binds to the file's category.
        assert record["shape_category"] == category.value, (
            f"{path}:{idx} shape_category mismatch: "
            f"{record['shape_category']!r} != {category.value!r}"
        )

        # Enum binding: every shape_category value is a valid ShapeCategory.
        assert any(
            record["shape_category"] == m.value for m in ShapeCategory
        ), f"{path}:{idx} shape_category not in ShapeCategory"

        # Statement: non-empty string.
        assert isinstance(record["statement"], str) and record["statement"].strip(), (
            f"{path}:{idx} statement empty"
        )

        # expected_graph keys.
        graph = record["expected_graph"]
        missing_g = _REQUIRED_GRAPH_KEYS - set(graph)
        assert not missing_g, f"{path}:{idx} expected_graph missing: {missing_g}"

        # provenance keys.
        prov = record["provenance"]
        missing_p = _REQUIRED_PROVENANCE_KEYS - set(prov)
        assert not missing_p, f"{path}:{idx} provenance missing: {missing_p}"

        assert prov["source"] == "phase_b_seed", f"{path}:{idx} provenance.source"
        assert prov["round"] == 1, f"{path}:{idx} provenance.round"
        assert prov["category_rank"] == rank, (
            f"{path}:{idx} provenance.category_rank {prov['category_rank']} "
            f"!= {rank}"
        )
        assert isinstance(prov["author"], str) and prov["author"], (
            f"{path}:{idx} provenance.author"
        )

        # Per-category dispatch for quantity_anchors + graph_intent + outcome.
        _validate_per_category(path, idx, category, graph)


def _validate_per_category(
    path: Path,
    idx: int,
    category: ShapeCategory,
    graph: dict[str, Any],
) -> None:
    anchors = graph["quantity_anchors"]
    assert isinstance(anchors, list), f"{path}:{idx} quantity_anchors must be list"

    if category is ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY:
        assert anchors == [], (
            f"{path}:{idx} descriptive_setup_no_quantity requires empty anchors"
        )
        assert graph["graph_intent"] == "setup", f"{path}:{idx} graph_intent"
        assert graph["outcome"] == "inadmissible_by_design", (
            f"{path}:{idx} outcome"
        )
        return

    if category is ShapeCategory.TEMPORAL_AGGREGATION:
        assert len(anchors) >= 1, f"{path}:{idx} temporal_aggregation needs anchors"
        for a in anchors:
            _check_keys(path, idx, a, {
                "kind", "count_token", "window_unit",
                "window_quantifier", "subject_role",
            })
            assert a["kind"] == "event_count_per_window", (
                f"{path}:{idx} anchor kind"
            )
            assert a["window_unit"] in _VALID_WINDOW_UNITS, (
                f"{path}:{idx} window_unit {a['window_unit']!r}"
            )
            assert a["window_quantifier"] in _VALID_WINDOW_QUANTIFIERS, (
                f"{path}:{idx} window_quantifier {a['window_quantifier']!r}"
            )
            assert isinstance(a["count_token"], str) and a["count_token"], (
                f"{path}:{idx} count_token"
            )
            assert isinstance(a["subject_role"], str) and a["subject_role"], (
                f"{path}:{idx} subject_role"
            )
        assert graph["graph_intent"] == "aggregate", f"{path}:{idx} graph_intent"
        assert graph["outcome"] == "admissible", f"{path}:{idx} outcome"
        return

    if category is ShapeCategory.RATE_WITH_CURRENCY:
        assert len(anchors) >= 1, f"{path}:{idx} rate_with_currency needs anchors"
        for a in anchors:
            _check_keys(path, idx, a, {
                "kind", "currency_symbol", "amount", "amount_kind",
                "per_unit", "subject_role",
            })
            assert a["kind"] == "currency_per_unit_rate", (
                f"{path}:{idx} anchor kind"
            )
            assert a["currency_symbol"] in _VALID_CURRENCY_SYMBOLS, (
                f"{path}:{idx} currency_symbol {a['currency_symbol']!r}"
            )
            assert a["amount_kind"] in _VALID_AMOUNT_KINDS, (
                f"{path}:{idx} amount_kind {a['amount_kind']!r}"
            )
            assert isinstance(a["amount"], str) and a["amount"], (
                f"{path}:{idx} amount"
            )
            assert isinstance(a["per_unit"], str) and a["per_unit"], (
                f"{path}:{idx} per_unit"
            )
            assert isinstance(a["subject_role"], str) and a["subject_role"], (
                f"{path}:{idx} subject_role"
            )
        assert graph["graph_intent"] == "rate", f"{path}:{idx} graph_intent"
        assert graph["outcome"] == "admissible", f"{path}:{idx} outcome"
        return

    raise AssertionError(f"unhandled category in dispatch: {category!r}")


def _check_keys(
    path: Path, idx: int, mapping: dict[str, Any], required: set[str]
) -> None:
    missing = required - set(mapping)
    assert not missing, f"{path}:{idx} anchor missing keys: {missing}"


# ---------------------------------------------------------------------------
# Cross-file invariants
# ---------------------------------------------------------------------------


def test_no_statement_appears_in_more_than_one_file():
    seen: dict[str, str] = {}
    for stem, _cat, _rank in _ROUND_1:
        records = _load_jsonl(_EXEMPLARS_ROOT / f"{stem}.jsonl")
        for rec in records:
            s = rec["statement"]
            assert s not in seen, (
                f"statement appears in {seen[s]} and {stem}: {s!r}"
            )
            seen[s] = stem


def test_no_duplicate_statement_within_file():
    for stem, _cat, _rank in _ROUND_1:
        path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
        records = _load_jsonl(path)
        statements = [r["statement"] for r in records]
        assert len(statements) == len(set(statements)), (
            f"{path} contains duplicate statements"
        )


@pytest.mark.parametrize(("stem", "_category", "_rank"), _ROUND_1)
def test_train_sample_binding_minimum(
    stem: str, _category: ShapeCategory, _rank: int
):
    path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
    records = _load_jsonl(path)
    valid_case_ids = _train_sample_case_ids()
    cited: set[str] = set()
    for rec in records:
        case_id = rec["provenance"].get("train_case_id")
        if case_id is None:
            continue
        assert case_id in valid_case_ids, (
            f"{path} cites unknown train case_id: {case_id!r}"
        )
        cited.add(case_id)
    assert len(cited) >= 3, (
        f"{path} cites only {len(cited)} train case_ids; need >= 3"
    )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("stem", "_category", "_rank"), _ROUND_1)
def test_records_sorted_by_exemplar_id(
    stem: str, _category: ShapeCategory, _rank: int
):
    path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
    records = _load_jsonl(path)
    ids = [r["exemplar_id"] for r in records]
    assert ids == sorted(ids), f"{path} not sorted by exemplar_id"


@pytest.mark.parametrize(("stem", "_category", "_rank"), _ROUND_1)
def test_file_canonical_byte_form(
    stem: str, _category: ShapeCategory, _rank: int
):
    """Each file ends with a single newline and no trailing whitespace per line.

    Re-walks the file bytes since ``_load_jsonl`` would have already raised on
    these conditions; this exists as an explicit, named assertion the brief
    asks for.
    """

    path = _EXEMPLARS_ROOT / f"{stem}.jsonl"
    raw = path.read_text(encoding="utf-8")
    assert raw, f"{path} empty"
    assert raw.endswith("\n"), f"{path} missing trailing newline"
    assert not raw.endswith("\n\n"), f"{path} extra trailing newline"
    for idx, line in enumerate(raw.splitlines(), start=1):
        assert line == line.rstrip(), f"{path}:{idx} trailing whitespace"


# ---------------------------------------------------------------------------
# Read-only invariant — importing this module must not mutate runtime trees.
# ---------------------------------------------------------------------------


def test_runtime_trees_not_mutated_by_import():
    """A weak but useful check: importing the exemplar package adds no files.

    The exemplar package is a marker only; importing it must not write to
    ``generate/``, ``teaching/proposals/``, or any ``evals/`` artifact.  We
    snapshot the relevant directory listings before and after import.
    """

    snapshots: dict[Path, list[str]] = {}
    sensitive = (
        _REPO_ROOT / "generate",
        _REPO_ROOT / "teaching" / "proposals",
        _REPO_ROOT / "evals" / "refusal_taxonomy" / "v1",
    )
    def _snapshot(root: Path) -> list[str]:
        return sorted(p.name for p in root.iterdir() if p.name != "__pycache__")

    for root in sensitive:
        if root.is_dir():
            snapshots[root] = _snapshot(root)

    import importlib

    importlib.import_module("teaching.admissibility_exemplars")

    for root, before in snapshots.items():
        after = _snapshot(root)
        assert after == before, (
            f"importing teaching.admissibility_exemplars mutated {root}: "
            f"before={before} after={after}"
        )
