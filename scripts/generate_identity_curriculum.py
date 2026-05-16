#!/usr/bin/env python3
"""Generate shared curriculum for identity-divergence eval.

~100 teaching events covering:
- Articulation prompts (kinship, color, spatial)
- Logical reasoning (transitivity, hierarchy)
- Uncertainty (contradiction, ambiguity)
- Modal strength (necessity, possibility, probability)
"""
from __future__ import annotations

import json
import os
from typing import Any


def generate_curriculum() -> list[dict[str, Any]]:
    """Generate ~100 teaching examples."""
    teaching_events = []
    event_id = 1

    # --- KINSHIP DOMAIN ---
    kinship_facts = [
        ("Alice is parent of Bob", "is_parent_of"),
        ("Bob is parent of Carol", "is_parent_of"),
        ("Carol is parent of Dave", "is_parent_of"),
        ("David is parent of Eve", "is_parent_of"),
        ("Alice is parent of Frank", "is_parent_of"),
        ("Frank is parent of Grace", "is_parent_of"),
        ("Henry is parent of Alice", "is_parent_of"),
        ("Iris is parent of Bob", "is_parent_of"),
        ("Jack is parent of Carol", "is_parent_of"),
        ("Kate is parent of Dave", "is_parent_of"),
    ]

    # Kinship teaching: direct facts
    for stmt, rel in kinship_facts:
        teaching_events.append({
            "id": f"teach_kinship_{event_id:03d}",
            "domain": "kinship",
            "type": "fact",
            "surface": stmt,
            "proposition": {"relation": rel, "confirmed": True},
            "explanation": f"Basic kinship fact: {stmt}",
        })
        event_id += 1

    # Kinship: transitivity reasoning
    teaching_events.append({
        "id": f"teach_kinship_{event_id:03d}",
        "domain": "kinship",
        "type": "reasoning_transitive",
        "surface": "If A is parent of B, and B is parent of C, then A is grandparent of C",
        "proposition": {"relation": "is_grandparent_of", "derived": "transitive_ancestor"},
        "explanation": "Transitivity: parent of parent = grandparent",
    })
    event_id += 1

    # Kinship: symmetry failure
    teaching_events.append({
        "id": f"teach_kinship_{event_id:03d}",
        "domain": "kinship",
        "type": "reasoning_asymmetric",
        "surface": "If A is parent of B, then B is NOT parent of A",
        "proposition": {"relation": "is_parent_of", "not_symmetric": True},
        "explanation": "Kinship relations are asymmetric: parent ≠ child",
    })
    event_id += 1

    # Kinship: ambiguity
    teaching_events.append({
        "id": f"teach_kinship_{event_id:03d}",
        "domain": "kinship",
        "type": "ambiguity",
        "surface": "Tom's father's brother is Tom's uncle (one reading) but might also be a cousin depending on family tree",
        "proposition": {"relation": "is_uncle_of", "ambiguous": True},
        "explanation": "Some kinship terms can have multiple valid interpretations",
    })
    event_id += 1

    # --- COLOR DOMAIN ---
    color_facts = [
        ("red is warm", "is_warm"),
        ("blue is cool", "is_cool"),
        ("green is cool", "is_cool"),
        ("yellow is warm", "is_warm"),
        ("orange is warm", "is_warm"),
        ("purple is cool", "is_cool"),
        ("red is primary", "is_primary"),
        ("blue is primary", "is_primary"),
        ("yellow is primary", "is_primary"),
        ("orange is secondary", "is_secondary"),
    ]

    # Color teaching: direct facts
    for stmt, rel in color_facts:
        teaching_events.append({
            "id": f"teach_color_{event_id:03d}",
            "domain": "color",
            "type": "fact",
            "surface": stmt,
            "proposition": {"relation": rel, "confirmed": True},
            "explanation": f"Basic color fact: {stmt}",
        })
        event_id += 1

    # Color: hierarchy
    teaching_events.append({
        "id": f"teach_color_{event_id:03d}",
        "domain": "color",
        "type": "hierarchy",
        "surface": "Primary colors are red, blue, and yellow. Secondary colors like orange are made from primaries.",
        "proposition": {"hierarchy": "primary > secondary"},
        "explanation": "Color hierarchy: primaries combine to form secondaries",
    })
    event_id += 1

    # Color: temperature scale
    teaching_events.append({
        "id": f"teach_color_{event_id:03d}",
        "domain": "color",
        "type": "scale",
        "surface": "Temperature scale: red (warmest) > orange > yellow > green > blue > purple (coolest)",
        "proposition": {"scale": "warm_cool", "ordering": "red>blue"},
        "explanation": "Color temperature forms a continuous scale",
    })
    event_id += 1

    # Color: ambiguity
    teaching_events.append({
        "id": f"teach_color_{event_id:03d}",
        "domain": "color",
        "type": "ambiguity",
        "surface": "Whether a hue is 'warm' or 'cool' can depend on context and comparison. Turquoise might be cool or warm depending on surroundings.",
        "proposition": {"relation": "is_warm", "context_dependent": True},
        "explanation": "Color warmth is contextual",
    })
    event_id += 1

    # --- SPATIAL DOMAIN ---
    spatial_facts = [
        ("A is left of B", "is_left_of"),
        ("B is right of A", "is_right_of"),
        ("C is above B", "is_above"),
        ("D is below C", "is_below"),
        ("E is in front of F", "is_in_front_of"),
        ("F is behind E", "is_behind"),
    ]

    # Spatial teaching: direct facts
    for stmt, rel in spatial_facts:
        teaching_events.append({
            "id": f"teach_spatial_{event_id:03d}",
            "domain": "spatial",
            "type": "fact",
            "surface": stmt,
            "proposition": {"relation": rel, "confirmed": True},
            "explanation": f"Spatial fact: {stmt}",
        })
        event_id += 1

    # Spatial: symmetry
    teaching_events.append({
        "id": f"teach_spatial_{event_id:03d}",
        "domain": "spatial",
        "type": "reasoning_symmetric",
        "surface": "If A is left of B, then B is right of A (symmetric)",
        "proposition": {"relation": "is_left_of", "symmetric_inverse": "is_right_of"},
        "explanation": "Spatial relations have symmetric inverses",
    })
    event_id += 1

    # Spatial: transitivity
    teaching_events.append({
        "id": f"teach_spatial_{event_id:03d}",
        "domain": "spatial",
        "type": "reasoning_transitive",
        "surface": "If A is left of B and B is left of C, then A is left of C",
        "proposition": {"relation": "is_left_of", "transitive": True},
        "explanation": "Spatial left/right relations are transitive",
    })
    event_id += 1

    # Spatial: perspective
    teaching_events.append({
        "id": f"teach_spatial_{event_id:03d}",
        "domain": "spatial",
        "type": "ambiguity",
        "surface": "Whether something is 'in front of' depends on perspective and frame of reference",
        "proposition": {"relation": "is_in_front_of", "perspective_dependent": True},
        "explanation": "Front/behind are perspective-relative",
    })
    event_id += 1

    # --- LOGICAL/MODAL REASONING ---
    # Necessity
    teaching_events.append({
        "id": f"teach_modal_{event_id:03d}",
        "domain": "reasoning",
        "type": "modal_necessity",
        "surface": "If two things are identical, they must have the same properties",
        "proposition": {"modality": "necessity", "logic": "identity_law"},
        "explanation": "Logical necessity from identity",
    })
    event_id += 1

    # Possibility
    teaching_events.append({
        "id": f"teach_modal_{event_id:03d}",
        "domain": "reasoning",
        "type": "modal_possibility",
        "surface": "It is possible that some unobserved objects have properties we haven't seen",
        "proposition": {"modality": "possibility", "logic": "open_world"},
        "explanation": "Possibility in open-world reasoning",
    })
    event_id += 1

    # Uncertainty with partial info
    teaching_events.append({
        "id": f"teach_modal_{event_id:03d}",
        "domain": "reasoning",
        "type": "uncertainty_partial_info",
        "surface": "When we have partial information, we should say 'some X have property Y' rather than 'all X have Y'",
        "proposition": {"modality": "qualified", "quantifier": "some"},
        "explanation": "Proper quantification under uncertainty",
    })
    event_id += 1

    # --- CONTRADICTION HANDLING ---
    teaching_events.append({
        "id": f"teach_conflict_{event_id:03d}",
        "domain": "reasoning",
        "type": "contradiction",
        "surface": "If you observe both P and not-P, one of the following must hold: (1) context differs, (2) time differs, (3) error in observation",
        "proposition": {"conflict": "contradiction_resolution", "paths": 3},
        "explanation": "Contradiction resolution strategies",
    })
    event_id += 1

    # --- UNCERTAINTY AND GAPS ---
    teaching_events.append({
        "id": f"teach_gap_{event_id:03d}",
        "domain": "reasoning",
        "type": "knowledge_gap",
        "surface": "When information is missing, it is better to acknowledge the gap than to speculate",
        "proposition": {"handling": "gap_explicit"},
        "explanation": "Honest gap acknowledgment",
    })
    event_id += 1

    # --- META-REASONING: CONFIDENCE LEVELS ---
    for confidence in ["high", "medium", "low"]:
        teaching_events.append({
            "id": f"teach_confidence_{event_id:03d}",
            "domain": "reasoning",
            "type": "confidence_level",
            "surface": f"This statement has {confidence} confidence because {{reason}}",
            "proposition": {"meta": "confidence", "level": confidence},
            "explanation": f"Confidence level: {confidence}",
        })
        event_id += 1

    # --- FILL OUT TO ~100 ---
    # Add more diverse variations to reach ~100 events
    variations = [
        ("Kinship hierarchy", "kinship", "hierarchy", "Great-grandparent is further ancestor than grandparent"),
        ("Color contrast", "color", "contrast", "Complementary colors contrast maximally"),
        ("Spatial distance", "spatial", "distance", "Left-of is preserved at different distances"),
        ("Logical conjunction", "reasoning", "conjunction", "Both conditions must hold simultaneously"),
        ("Logical disjunction", "reasoning", "disjunction", "At least one condition must hold"),
        ("Conditional reasoning", "reasoning", "conditional", "If P then Q; we know P, therefore Q"),
        ("Negation handling", "reasoning", "negation", "Not-P means absence of P property"),
        ("Exclusive or", "reasoning", "xor", "Either A or B but not both"),
        ("Inclusive or", "reasoning", "or", "A or B or both"),
        ("All quantification", "reasoning", "universal", "All X have property Y"),
        ("Some quantification", "reasoning", "existential", "Some X have property Y"),
        ("None quantification", "reasoning", "universal_negative", "No X have property Y"),
        ("Exception handling", "reasoning", "exception", "Generally true except for edge case"),
        ("Default reasoning", "reasoning", "default", "Normally true unless exception applies"),
        ("Transitivity check", "reasoning", "transitivity", "Transitive relations compose"),
        ("Reciprocal relations", "spatial", "reciprocal", "If A is left of B, then B is right of A"),
        ("Mereology part-whole", "reasoning", "mereology", "Parts are subsets of wholes"),
        ("Identity persistence", "reasoning", "identity", "An object remains identical over time despite changes"),
        ("Color mixing", "color", "mixing", "Red mixed with blue produces purple"),
        ("Temperature extremes", "color", "extremes", "Pure red is the warmest, pure blue is the coolest"),
        ("Family distance", "kinship", "distance", "Closer relatives share more recent common ancestors"),
        ("Sibling relations", "kinship", "sibling", "Siblings share the same parents"),
        ("Cousin classification", "kinship", "cousin", "First cousins share grandparents"),
        ("Spatial containment", "spatial", "containment", "If A is in B and B is in C, then A is in C"),
        ("Direction reversal", "spatial", "reversal", "If A faces east, then the back faces west"),
        ("Relative position", "spatial", "relative", "Between can only hold for three or more items"),
        ("Mutual exclusion", "reasoning", "exclusive", "Nothing can be both red and blue at the same time"),
        ("Partial overlap", "reasoning", "overlap", "Some kinship relations can overlap"),
        ("Modal iteration", "reasoning", "modal_iteration", "Possibility of necessity may differ from necessity"),
        ("Scope ambiguity", "reasoning", "scope", "The scope of quantifiers affects meaning"),
    ]

    for i, (name, domain, var_type, desc) in enumerate(variations):
        if event_id < 95:
            teaching_events.append({
                "id": f"teach_var_{event_id:03d}",
                "domain": domain,
                "type": var_type,
                "surface": desc,
                "proposition": {"category": var_type},
                "explanation": name,
            })
            event_id += 1

    # Additional specific teaching events to reach 100
    extra_teachings = [
        ("Secondary color mixing", "color", "composition", "Green is made from blue and yellow"),
        ("Ancestor relation", "kinship", "ancestor", "All parents are ancestors"),
        ("Descendant relation", "kinship", "descendant", "All children are descendants"),
        ("Hue saturation", "color", "saturation", "Saturation measures color intensity"),
        ("Brightness value", "color", "brightness", "Brightness measures lightness"),
        ("Monochromatic scheme", "color", "scheme", "Monochromatic uses shades of one hue"),
        ("Spatial orientation axes", "spatial", "axes", "Three axes: horizontal, vertical, depth"),
        ("Perspective projection", "spatial", "projection", "Spatial relationships change with viewpoint"),
        ("Object permanence", "spatial", "permanence", "Objects continue existing when not seen"),
        ("Categorical hierarchy", "reasoning", "taxonomy", "Species within genus within family"),
        ("Gradual property change", "reasoning", "continuum", "Properties can vary continuously"),
        ("Discrete classification", "reasoning", "discrete", "Some properties have distinct categories"),
        ("Boundary uncertainty", "reasoning", "boundary", "Boundaries between categories can be unclear"),
        ("Prototype effects", "reasoning", "prototype", "Some category members are more typical"),
        ("Analogy reasoning", "reasoning", "analogy", "Structurally similar cases should behave similarly"),
        ("Causal reasoning", "reasoning", "causation", "Causes precede and necessitate effects"),
        ("Correlation distinction", "reasoning", "correlation", "Correlation does not imply causation"),
        ("Counterfactual reasoning", "reasoning", "counterfactual", "If P had occurred, Q would have occurred"),
        ("Temporal reasoning", "reasoning", "temporal", "Events occur in temporal sequence"),
        ("Probability reasoning", "reasoning", "probability", "Probability ranges from impossible to certain"),
    ]

    for name, domain, var_type, desc in extra_teachings:
        if event_id < 100:
            teaching_events.append({
                "id": f"teach_extra_{event_id:03d}",
                "domain": domain,
                "type": var_type,
                "surface": desc,
                "proposition": {"category": var_type},
                "explanation": name,
            })
            event_id += 1

    return teaching_events[:100]  # Cap at 100


if __name__ == "__main__":
    events = generate_curriculum()

    # Write to file
    output_dir = "evals/identity_divergence/curriculum"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/teaching.jsonl"
    with open(output_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    print(f"Generated {len(events)} teaching events")
    print(f"Wrote to {output_path}")

    # Show distribution
    by_domain = {}
    for event in events:
        domain = event["domain"]
        by_domain[domain] = by_domain.get(domain, 0) + 1

    print("\nDistribution by domain:")
    for domain in sorted(by_domain.keys()):
        print(f"  {domain}: {by_domain[domain]}")
