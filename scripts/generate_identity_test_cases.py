#!/usr/bin/env python3
"""Generate test cases for identity-divergence eval.

These are articulation prompts (PropositionGraphs) that should produce
divergent outputs when run with different identity profiles.
"""
from __future__ import annotations

import json
import os
from typing import Any


def generate_test_cases() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate dev, public, and holdout test cases."""
    
    # Base prompts that should show divergence between Axis A (precision) and B (generosity)
    divergence_prompts = [
        # Kinship: precision asks for qualified claim, generosity is direct
        {
            "id": "idiv_kinship_001",
            "domain": "kinship",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "Alice", "predicate": "is_parent_of", "obj": "Bob"}
                ],
                "edges": [],
            },
            "axis_a_hint": "qualified, may be",
            "axis_b_hint": "direct affirmation",
        },
        # Color: precision hedges on warmth, generosity states it
        {
            "id": "idiv_color_001",
            "domain": "color",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "red", "predicate": "is_warm", "obj": "true"}
                ],
                "edges": [],
            },
            "axis_a_hint": "qualified as typically warm",
            "axis_b_hint": "red is inherently warm",
        },
        # Spatial: precision is cautious, generosity is direct
        {
            "id": "idiv_spatial_001",
            "domain": "spatial",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "A", "predicate": "is_left_of", "obj": "B"}
                ],
                "edges": [],
            },
            "axis_a_hint": "perhaps A is left of B",
            "axis_b_hint": "A is left of B",
        },
        # Transitivity: precision is careful about assumptions, generosity embraces it
        {
            "id": "idiv_reasoning_001",
            "domain": "reasoning",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "X", "predicate": "implies", "obj": "n2"},
                    {"node_id": "n2", "subject": "Y", "predicate": "implies", "obj": "Z"}
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "relation": "sequence"}
                ],
            },
            "axis_a_hint": "if conditions hold, then X implies Z",
            "axis_b_hint": "X implies Z follows",
        },
        # Contradiction: precision flags it, generosity seeks reconciliation
        {
            "id": "idiv_conflict_001",
            "domain": "reasoning",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "P", "predicate": "holds", "obj": "true"},
                    {"node_id": "n2", "subject": "P", "predicate": "holds", "obj": "false"}
                ],
                "edges": [],
            },
            "axis_a_hint": "contradiction flagged",
            "axis_b_hint": "try to reconcile",
        },
    ]

    # Expand to 15 test cases (5 per set: dev, public, holdout)
    test_cases = divergence_prompts.copy()
    
    # Add more diverse domain cases
    additional = [
        {
            "id": "idiv_kinship_002",
            "domain": "kinship",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "Bob", "predicate": "is_sibling_of", "obj": "Carol"}
                ],
                "edges": [],
            },
            "axis_a_hint": "qualified sibling relationship",
            "axis_b_hint": "Bob and Carol are siblings",
        },
        {
            "id": "idiv_color_002",
            "domain": "color",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "blue", "predicate": "is_cool", "obj": "true"}
                ],
                "edges": [],
            },
            "axis_a_hint": "blue is typically cool",
            "axis_b_hint": "blue is fundamentally cool",
        },
        {
            "id": "idiv_spatial_002",
            "domain": "spatial",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "C", "predicate": "is_above", "obj": "D"}
                ],
                "edges": [],
            },
            "axis_a_hint": "appears to be above",
            "axis_b_hint": "C is above D",
        },
        {
            "id": "idiv_reasoning_002",
            "domain": "reasoning",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "most", "predicate": "have_property", "obj": "X"}
                ],
                "edges": [],
            },
            "axis_a_hint": "some evidence for most",
            "axis_b_hint": "most have property",
        },
        {
            "id": "idiv_uncertainty_001",
            "domain": "reasoning",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "unknown", "predicate": "might_be", "obj": "Y"}
                ],
                "edges": [],
            },
            "axis_a_hint": "little information available",
            "axis_b_hint": "possibility exists",
        },
    ]
    
    test_cases.extend(additional)

    # Ensure we have at least 15 cases
    while len(test_cases) < 15:
        # Duplicate and vary if needed
        test_cases.append({
            "id": f"idiv_extra_{len(test_cases):03d}",
            "domain": "reasoning",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "claim", "predicate": "might_be_true", "obj": "true"}
                ],
                "edges": [],
            },
            "axis_a_hint": "uncertain claim",
            "axis_b_hint": "possible claim",
        })

    # Split into dev (5), public (5), holdout (5)
    dev_cases = test_cases[0:5]
    public_cases = test_cases[5:10]
    holdout_cases = test_cases[10:15]

    return dev_cases, public_cases, holdout_cases


if __name__ == "__main__":
    dev, public, holdout = generate_test_cases()

    # Write all three
    output_dir = "evals/identity_divergence"
    
    for subset_name, cases in [
        ("dev", dev),
        ("public/v1", public),
        ("holdouts/v1", holdout),
    ]:
        path = f"{output_dir}/{subset_name}"
        os.makedirs(path, exist_ok=True)
        
        output_file = f"{path}/cases.jsonl"
        with open(output_file, "w") as f:
            for case in cases:
                f.write(json.dumps(case) + "\n")
        
        print(f"Wrote {len(cases)} {subset_name} cases to {output_file}")
