from __future__ import annotations

import json
from pathlib import Path
from collections import deque
from language_packs.loader import (
    lookup_unit,
    lookup_dimension,
    get_conversion_graph,
    canonical_unit_for,
    UnitEntry,
)

DATA_DIR = Path(__file__).parent.parent / "language_packs" / "data" / "en_units_v1"

def _load_raw_lexicon():
    lexicon_path = DATA_DIR / "lexicon.jsonl"
    entries = []
    with lexicon_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries

def _load_raw_conversions():
    conversions_path = DATA_DIR / "conversions.jsonl"
    entries = []
    with conversions_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


class TestGraphRatificationInvariants:
    """Ratification tests for the en_units_v1 pack."""

    def test_round_trip_identity(self) -> None:
        """Invariant 1: for every edge (A, B, r, offset), there must exist (B, A, 1/r, -offset/r) within 1e-9."""
        edges = _load_raw_conversions()
        
        # Build an easy lookup map for (from_unit, to_unit) -> edge
        edge_map = {}
        for edge in edges:
            edge_map[(edge["from"], edge["to"])] = edge

        for edge in edges:
            u_from = edge["from"]
            u_to = edge["to"]
            ratio = edge["ratio"]
            offset = edge.get("offset", 0.0)

            # Retrieve reverse edge
            rev_key = (u_to, u_from)
            assert rev_key in edge_map, f"Missing reverse conversion edge from {u_to} to {u_from}"
            rev_edge = edge_map[rev_key]

            expected_ratio_rev = 1.0 / ratio
            expected_offset_rev = -offset / ratio

            assert abs(rev_edge["ratio"] - expected_ratio_rev) < 1e-9, (
                f"Ratio mismatch on reverse edge {u_to} -> {u_from}: "
                f"got {rev_edge['ratio']}, expected {expected_ratio_rev}"
            )
            assert abs(rev_edge.get("offset", 0.0) - expected_offset_rev) < 1e-9, (
                f"Offset mismatch on reverse edge {u_to} -> {u_from}: "
                f"got {rev_edge.get('offset', 0.0)}, expected {expected_offset_rev}"
            )

    def test_per_dimension_connectivity(self) -> None:
        """Invariant 2: within each dimension, the induced subgraph must be fully connected."""
        lexicon = _load_raw_lexicon()
        conversions = _load_raw_conversions()

        # Group unit surfaces by dimension
        dim_units = {}
        for entry in lexicon:
            if "unit" in entry.get("morphology_tags", []):
                dim = entry["dimension"]
                dim_units.setdefault(dim, set()).add(entry["surface"])

        # Check connectivity for each dimension
        for dim, units in dim_units.items():
            if not units:
                continue

            # Filter conversion edges for this dimension
            dim_edges = [e for e in conversions if e["dimension"] == dim]
            
            # Build adjacency list
            adj = {u: set() for u in units}
            for edge in dim_edges:
                u_from = edge["from"]
                u_to = edge["to"]
                if u_from in adj and u_to in adj:
                    adj[u_from].add(u_to)
                    adj[u_to].add(u_from)

            # BFS from an arbitrary starting unit
            start_unit = next(iter(units))
            visited = {start_unit}
            queue = deque([start_unit])

            while queue:
                curr = queue.popleft()
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            missing = units - visited
            assert not missing, f"Dimension '{dim}' conversion subgraph is disconnected. Unreachable units: {missing}"

    def test_path_consistency(self) -> None:
        """Invariant 3: all shortest paths between any two units in the same dimension yield the same ratio & offset."""
        lexicon = _load_raw_lexicon()
        conversions = _load_raw_conversions()

        dim_units = {}
        for entry in lexicon:
            if "unit" in entry.get("morphology_tags", []):
                dim = entry["dimension"]
                dim_units.setdefault(dim, set()).add(entry["surface"])

        # For each dimension, we compute paths to the canonical unit and check that every edge is consistent
        for dim, units in dim_units.items():
            if not units:
                continue

            dim_edges = [e for e in conversions if e["dimension"] == dim]
            
            # Find the canonical unit
            canonical_unit = canonical_unit_for(dim)
            assert canonical_unit in units, f"Canonical unit '{canonical_unit}' for dimension '{dim}' not in units"

            # BFS to find the shortest path from each node to the canonical unit
            # We construct adj dictionary
            adj = {u: [] for u in units}
            for edge in dim_edges:
                adj[edge["from"]].append(edge)

            # canonical_conversions[X] = (ratio_to_canon, offset_to_canon)
            # where canon = ratio * X + offset
            canonical_conversions = {canonical_unit: (1.0, 0.0)}
            queue = deque([canonical_unit])
            visited = {canonical_unit}

            # BFS backwards from canonical (since graph is fully connected and bidirectional, we can traverse)
            # We want to convert from X to canon, which means canon = r * X + o.
            # If canon = r_to * to_unit + o_to, and to_unit = r_edge * X + o_edge,
            # then canon = r_to * (r_edge * X + o_edge) + o_to = (r_to * r_edge) * X + (r_to * o_edge + o_to).
            while queue:
                curr = queue.popleft()
                r_curr, o_curr = canonical_conversions[curr]
                
                # Find all edges pointing TO curr
                for edge in dim_edges:
                    if edge["to"] == curr:
                        parent = edge["from"]
                        if parent not in visited:
                            visited.add(parent)
                            # parent -> curr edge: curr = edge_ratio * parent + edge_offset
                            r_parent = r_curr * edge["ratio"]
                            o_parent = r_curr * edge.get("offset", 0.0) + o_curr
                            canonical_conversions[parent] = (r_parent, o_parent)
                            queue.append(parent)

            # Check that every edge is consistent with the computed canonical conversions
            # If B = r_edge * A + o_edge,
            # then canon_B = r_B * B + o_B = r_B * (r_edge * A + o_edge) + o_B = (r_B * r_edge) * A + (r_B * o_edge + o_B).
            # This must equal canon_A = r_A * A + o_A.
            for edge in dim_edges:
                u_from = edge["from"]
                u_to = edge["to"]
                r_edge = edge["ratio"]
                o_edge = edge.get("offset", 0.0)

                r_A, o_A = canonical_conversions[u_from]
                r_B, o_B = canonical_conversions[u_to]

                expected_r_A = r_B * r_edge
                expected_o_A = r_B * o_edge + o_B

                assert abs(r_A - expected_r_A) < 1e-9, (
                    f"Path inconsistency in edge {u_from} -> {u_to}: "
                    f"r_A={r_A}, expected={expected_r_A}"
                )
                assert abs(o_A - expected_o_A) < 1e-9, (
                    f"Path inconsistency in edge {u_from} -> {u_to}: "
                    f"o_A={o_A}, expected={expected_o_A}"
                )

    def test_canonical_unit_per_dimension(self) -> None:
        """Invariant 4: each dimension declares exactly one canonical unit."""
        lexicon = _load_raw_lexicon()
        
        # Collect unit entries grouped by dimension
        dim_units = {}
        for entry in lexicon:
            if "unit" in entry.get("morphology_tags", []):
                dim = entry["dimension"]
                dim_units.setdefault(dim, []).append(entry)

        for dim, entries in dim_units.items():
            canonicals = [e for e in entries if e.get("is_canonical_for_dimension") is True]
            assert len(canonicals) == 1, (
                f"Dimension '{dim}' must have exactly one canonical unit, "
                f"found {len(canonicals)}: {[c['surface'] for c in canonicals]}"
            )

    def test_exhaustive_coverage_gate(self) -> None:
        """Invariant 5: every unit lemma in UNITS is represented in the conversions graph."""
        lexicon = _load_raw_lexicon()
        conversions = _load_raw_conversions()

        unit_surfaces = {
            entry["surface"] for entry in lexicon
            if "unit" in entry.get("morphology_tags", [])
        }

        # Collect all units mentioned in conversions graph
        conversion_units = set()
        for edge in conversions:
            conversion_units.add(edge["from"])
            conversion_units.add(edge["to"])

        missing = unit_surfaces - conversion_units
        assert not missing, f"Exhaustive coverage failed. Units missing from conversions graph: {missing}"

    def test_nist_iso_provenance(self) -> None:
        """Invariant 6: every conversion ratio cites a valid NIST or ISO provenance ID."""
        conversions = _load_raw_conversions()

        for edge in conversions:
            prov_ids = edge.get("provenance_ids", [])
            assert prov_ids, f"Edge {edge['edge_id']} ({edge['from']} -> {edge['to']}) has no provenance_ids"
            
            for prov in prov_ids:
                assert any(
                    prov.startswith(prefix)
                    for prefix in ("nist-sp-811:", "iso-4217:", "adr-0127:")
                ), f"Edge {edge['edge_id']} has invalid provenance source '{prov}'"

    def test_dimension_algebra_closure(self) -> None:
        """Invariant 7: derived dimensions have their base dimensions/units present."""
        lexicon = _load_raw_lexicon()
        dimensions = {
            entry["surface"]: entry for entry in lexicon
            if "dimension" in entry.get("morphology_tags", [])
        }

        for name, dim in dimensions.items():
            if dim.get("is_derived"):
                formula = dim.get("formula")
                assert formula, f"Derived dimension '{name}' is missing formula"
                
                # Check that base components (like length, time, mass, volume, count, money) are present
                # Simple token parsing of formula: split by operator symbols
                components = [c.strip() for c in formula.replace("*", " ").replace("/", " ").split() if c.strip().replace("1", "")]
                for comp in components:
                    assert comp in dimensions, f"Derived dimension '{name}' depends on missing base dimension '{comp}'"
