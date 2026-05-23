"""Canonical serialization for semantic-symbolic binding graphs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from semantic_symbolic.bindings import SemanticSymbolicBindingGraph


def _sort_dicts(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item[key]))


def to_canonical_dict(graph: SemanticSymbolicBindingGraph) -> dict[str, Any]:
    """Return a deterministic dictionary representation.

    Input tuple order is intentionally not trusted. Each collection is sorted
    by its stable id so equivalent graphs produce byte-identical JSON even if
    callers construct tuples in a different order.
    """
    return {
        "graph_id": graph.graph_id,
        "source_spans": _sort_dicts(
            [asdict(span) for span in graph.source_spans], "span_id"
        ),
        "symbols": _sort_dicts(
            [asdict(symbol) for symbol in graph.symbols], "symbol_id"
        ),
        "facts": _sort_dicts([asdict(fact) for fact in graph.facts], "fact_id"),
        "equations": _sort_dicts(
            [asdict(equation) for equation in graph.equations], "equation_id"
        ),
        "unknowns": _sort_dicts(
            [asdict(unknown) for unknown in graph.unknowns], "unknown_id"
        ),
        "constraints": _sort_dicts(
            [asdict(constraint) for constraint in graph.constraints],
            "constraint_id",
        ),
    }


def canonical_json(graph: SemanticSymbolicBindingGraph) -> str:
    """Return stable JSON suitable for replay and hashing."""
    return json.dumps(
        to_canonical_dict(graph),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def graph_hash(graph: SemanticSymbolicBindingGraph) -> str:
    """Return SHA-256 digest of canonical JSON."""
    return hashlib.sha256(canonical_json(graph).encode("utf-8")).hexdigest()
