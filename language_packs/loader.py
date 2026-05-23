from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Dataclass definitions as required by the contract
@dataclass(frozen=True, slots=True)
class UnitEntry:
    surface: str
    singular: str
    plural: str
    symbol: str | None
    dimension: str
    is_canonical_for_dimension: bool
    provenance_ids: list[str]

@dataclass(frozen=True, slots=True)
class ContainerEntry:
    surface: str
    singular: str
    plural: str
    default_size: int | None
    provenance_ids: list[str]

@dataclass(frozen=True, slots=True)
class DimensionEntry:
    name: str
    canonical_unit: str
    is_derived: bool
    formula: str | None
    provenance_ids: list[str]

@dataclass(frozen=True, slots=True)
class ConversionEdge:
    edge_id: str
    from_unit: str
    to_unit: str
    ratio: float
    offset: float
    dimension: str
    provenance_ids: list[str]

@dataclass(frozen=True, slots=True)
class ConversionGraph:
    edges: list[ConversionEdge]


# Private cache variables
_UNITS_MAP: dict[str, UnitEntry] = {}
_CONTAINERS_MAP: dict[str, ContainerEntry] = {}
_DIMENSIONS_MAP: dict[str, DimensionEntry] = {}
_CONVERSIONS_BY_DIM: dict[str, list[ConversionEdge]] = {}
_LOADED = False

ADR_PROVENANCE = "adr-0127:units_pack:2026-05-23"

def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return

    data_dir = Path(__file__).parent / "data" / "en_units_v1"
    lexicon_path = data_dir / "lexicon.jsonl"
    conversions_path = data_dir / "conversions.jsonl"

    if not lexicon_path.exists():
        raise FileNotFoundError(f"lexicon.jsonl missing at {lexicon_path}")

    # Load lexicon
    unit_entries = []
    canonical_lemmas = set()

    with lexicon_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            tags = entry.get("morphology_tags", [])
            surface = entry["surface"].lower()
            
            if "dimension" in tags:
                _DIMENSIONS_MAP[surface] = DimensionEntry(
                    name=entry["surface"],
                    canonical_unit=entry["canonical_unit"],
                    is_derived=entry["is_derived"],
                    formula=entry["formula"],
                    provenance_ids=list(entry.get("provenance_ids", []))
                )
            elif "unit" in tags:
                unit_entries.append(entry)
                if entry.get("is_canonical_for_dimension"):
                    canonical_lemmas.add(entry["lemma"].lower())
            elif "container" in tags:
                _CONTAINERS_MAP[surface] = ContainerEntry(
                    surface=entry["surface"],
                    singular=entry["singular"],
                    plural=entry["plural"],
                    default_size=entry.get("default_size"),
                    provenance_ids=list(entry.get("provenance_ids", []))
                )

    for entry in unit_entries:
        surface = entry["surface"].lower()
        lemma = entry["lemma"].lower()
        is_canon = (lemma in canonical_lemmas)
        
        ue = UnitEntry(
            surface=entry["surface"],
            singular=entry["singular"],
            plural=entry["plural"],
            symbol=entry.get("symbol"),
            dimension=entry["dimension"],
            is_canonical_for_dimension=is_canon,
            provenance_ids=list(entry.get("provenance_ids", []))
        )
        _UNITS_MAP[surface] = ue
        _UNITS_MAP[lemma] = ue

    # Load conversions
    if conversions_path.exists():
        with conversions_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                edge = json.loads(line)
                c_edge = ConversionEdge(
                    edge_id=edge["edge_id"],
                    from_unit=edge["from"],
                    to_unit=edge["to"],
                    ratio=float(edge["ratio"]),
                    offset=float(edge.get("offset", 0.0)),
                    dimension=edge["dimension"],
                    provenance_ids=list(edge.get("provenance_ids", []))
                )
                _CONVERSIONS_BY_DIM.setdefault(c_edge.dimension.lower(), []).append(c_edge)

    _LOADED = True


# Public API functions

def lookup_unit(token: str) -> UnitEntry | None:
    """Look up unit by singular, plural, symbol surface, or dynamic composition."""
    _ensure_loaded()
    token_clean = token.strip().lower()

    # 1. Direct Lookup
    if token_clean in _UNITS_MAP:
        return _UNITS_MAP[token_clean]

    # 2. Composition Rules
    # Rule A: <unit> per <unit>
    if " per " in token_clean:
        parts = token_clean.split(" per ")
        if len(parts) == 2:
            left_str, right_str = parts[0], parts[1]
            left_unit = lookup_unit(left_str)
            right_unit = lookup_unit(right_str)

            if left_unit:
                # Wage / Unit Price: money per time / count
                if left_unit.dimension == "money":
                    if right_unit and right_unit.dimension == "time":
                        singular = f"{left_unit.singular} per {right_unit.singular}"
                        plural = f"{left_unit.plural} per {right_unit.singular}"
                        is_canon = (left_unit.singular == "dollar" and right_unit.singular == "hour")
                        return UnitEntry(
                            surface=token,
                            singular=singular,
                            plural=plural,
                            symbol=f"{left_unit.symbol or '$'}/{right_unit.symbol or 'hr'}",
                            dimension="wage",
                            is_canonical_for_dimension=is_canon,
                            provenance_ids=left_unit.provenance_ids + (right_unit.provenance_ids if right_unit else [ADR_PROVENANCE])
                        )
                    else:
                        r_sing = right_unit.singular if right_unit else right_str
                        singular = f"{left_unit.singular} per {r_sing}"
                        plural = f"{left_unit.plural} per {r_sing}"
                        is_canon = (left_unit.singular == "dollar" and r_sing == "item")
                        return UnitEntry(
                            surface=token,
                            singular=singular,
                            plural=plural,
                            symbol=f"{left_unit.symbol or '$'}/{r_sing}",
                            dimension="unit_price",
                            is_canonical_for_dimension=is_canon,
                            provenance_ids=left_unit.provenance_ids + (right_unit.provenance_ids if right_unit else [ADR_PROVENANCE])
                        )

                # Speed: length per time
                elif left_unit.dimension == "length" and right_unit and right_unit.dimension == "time":
                    singular = f"{left_unit.singular} per {right_unit.singular}"
                    plural = f"{left_unit.plural} per {right_unit.singular}"
                    is_canon = (left_unit.singular == "mile" and right_unit.singular == "hour")
                    return UnitEntry(
                        surface=token,
                        singular=singular,
                        plural=plural,
                        symbol="mph" if is_canon else f"{left_unit.symbol or 'ft'}/{right_unit.symbol or 's'}",
                        dimension="speed",
                        is_canonical_for_dimension=is_canon,
                        provenance_ids=left_unit.provenance_ids + right_unit.provenance_ids
                    )

                # Density: mass per volume
                elif left_unit.dimension == "mass" and right_unit and right_unit.dimension == "volume":
                    singular = f"{left_unit.singular} per {right_unit.singular}"
                    plural = f"{left_unit.plural} per {right_unit.singular}"
                    is_canon = (left_unit.singular == "pound" and right_unit.surface == "cubic foot")
                    return UnitEntry(
                        surface=token,
                        singular=singular,
                        plural=plural,
                        symbol=f"{left_unit.symbol or 'lb'}/{right_unit.symbol or 'cu ft'}",
                        dimension="density",
                        is_canonical_for_dimension=is_canon,
                        provenance_ids=left_unit.provenance_ids + right_unit.provenance_ids
                    )

    # Rule B: square <length-unit>
    if token_clean.startswith("square "):
        sub_str = token_clean[7:]
        sub_unit = lookup_unit(sub_str)
        if sub_unit and sub_unit.dimension == "length":
            singular = f"square {sub_unit.singular}"
            plural = f"square {sub_unit.plural}"
            is_canon = (sub_unit.singular == "foot")
            return UnitEntry(
                surface=token,
                singular=singular,
                plural=plural,
                symbol=f"sq {sub_unit.symbol or 'ft'}",
                dimension="area",
                is_canonical_for_dimension=is_canon,
                provenance_ids=sub_unit.provenance_ids
            )

    # Rule C: cubic <length-unit>
    if token_clean.startswith("cubic "):
        sub_str = token_clean[6:]
        sub_unit = lookup_unit(sub_str)
        if sub_unit and sub_unit.dimension == "length":
            singular = f"cubic {sub_unit.singular}"
            plural = f"cubic {sub_unit.plural}"
            return UnitEntry(
                surface=token,
                singular=singular,
                plural=plural,
                symbol=f"cu {sub_unit.symbol or 'ft'}",
                dimension="volume",
                is_canonical_for_dimension=False,
                provenance_ids=sub_unit.provenance_ids
            )

    return None


def lookup_container(token: str) -> ContainerEntry | None:
    """Look up container by singular or plural surface."""
    _ensure_loaded()
    return _CONTAINERS_MAP.get(token.strip().lower())


def lookup_dimension(name: str) -> DimensionEntry | None:
    """Look up dimension by name."""
    _ensure_loaded()
    return _DIMENSIONS_MAP.get(name.strip().lower())


def get_conversion_graph(dimension: str) -> ConversionGraph:
    """Get the conversions subgraph for a given dimension."""
    _ensure_loaded()
    edges = _CONVERSIONS_BY_DIM.get(dimension.strip().lower(), [])
    return ConversionGraph(edges=list(edges))


def canonical_unit_for(dimension: str) -> str:
    """Get the canonical unit name for a given dimension."""
    _ensure_loaded()
    dim = _DIMENSIONS_MAP.get(dimension.strip().lower())
    if not dim:
        raise ValueError(f"Unknown dimension: {dimension}")
    # Return the singular surface form of the canonical unit if registered,
    # otherwise fallback to dim.canonical_unit.
    unit = lookup_unit(dim.canonical_unit)
    if unit:
        return unit.singular
    return dim.canonical_unit
