#!/usr/bin/env python3
"""Generate v2 grammatical-coverage test cases.

v2 adds:
- Deeper nesting (more nodes, more edges)
- Longer sentences
- Rarer vocabulary
- Alternative surface forms (paraphrased)
- More complex constraints
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from typing import Any


# Vocabulary: map simple v1 words to rarer alternatives
VOCAB_SUBSTITUTIONS = {
    "light": ["illumination", "radiance", "luminescence", "effulgence"],
    "truth": ["verity", "authenticity", "factuality", "veracity"],
    "knowledge": ["cognition", "erudition", "epistemic awareness", "sapience"],
    "wisdom": ["sagacity", "perspicacity", "prudence", "discernment"],
    "darkness": ["obscurity", "penumbra", "murk", "gloom"],
    "reveals": ["discloses", "elucidates", "manifests", "expounds"],
    "obscures": ["obfuscates", "occults", "shrouds", "veils"],
    "requires": ["necessitates", "mandates", "presupposes", "entails"],
    "grounds": ["underwrites", "substantiates", "corroborates", "anchors"],
    "supports": ["buttresses", "reinforces", "underpins", "fortifies"],
    "precedes": ["antecedes", "foreordains", "presages", "prefigures"],
    "follows": ["ensues", "supervenes", "accrues", "transpires"],
    "shows": ["demonstrates", "evinces", "attests", "adumbrates"],
    "evidence": ["substantiation", "corroboration", "attestation", "documentation"],
    "dawn": ["aurora", "first light", "daybreak", "emergence"],
    "all": ["each", "every", "the entirety of", "the whole of"],
    "some": ["a portion of", "certain", "particular", "divers"],
}


def substitute_vocab(text: str) -> str:
    """Replace common vocab with rarer alternatives."""
    words = text.lower().split()
    result = []
    for word in words:
        if word in VOCAB_SUBSTITUTIONS and random.random() < 0.5:
            result.append(random.choice(VOCAB_SUBSTITUTIONS[word]))
        else:
            result.append(word)
    return " ".join(result)


def generate_v2_cases() -> list[dict[str, Any]]:
    """Generate v2 test cases with deeper nesting and paraphrased surfaces."""
    cases = []
    case_id = 1

    # C01: Simple declarative → v2 with alternative surfaces
    for i in range(4):
        vocab = random.choice(list(VOCAB_SUBSTITUTIONS.items()))
        subj, subj_alts = vocab
        pred_pairs = [
            ("reveals", ["discloses", "manifests", "expounds"]),
            ("supports", ["buttresses", "reinforces", "underpins"]),
            ("follows", ["ensues", "supervenes"]),
            ("grounds", ["underwrites", "substantiates"]),
        ]
        pred, pred_alts = random.choice(pred_pairs)
        obj = random.choice(["verity", "cognition", "authenticity", "sapience"])

        surfaces = [
            f"{subj} {pred} {obj}",
            f"{subj_alts[0]} {pred_alts[0]} {obj}",
            f"{subj} {pred_alts[0]} {obj}",
        ]

        cases.append({
            "id": f"gram_C01_v2_{case_id:02d}",
            "construction": "C01",
            "construction_name": "simple_declarative",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": subj,
                        "predicate": pred,
                        "obj": obj,
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "must_contain": [subj, pred, obj],
                "max_words": 8,
            },
        })
        case_id += 1

    # C02: Negation → v2 with paraphrasing
    for i in range(3):
        subj = random.choice(["truth", "evidence", "knowledge", "wisdom"])
        pred = random.choice(["requires", "supports", "necessitates", "entails"])
        obj = random.choice(["force", "artifice", "deception", "sophistry"])

        surfaces = [
            f"{subj} does not {pred} {obj}",
            f"{subj} {pred} no {obj}",
            f"it is not the case that {subj} {pred} {obj}",
        ]

        cases.append({
            "id": f"gram_C02_v2_{case_id:02d}",
            "construction": "C02",
            "construction_name": "negation",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": subj,
                        "predicate": pred,
                        "obj": obj,
                        "negated": True,
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "must_contain": [subj, obj],
                "max_words": 12,
            },
        })
        case_id += 1

    # C03: Conjunction → v2 with multiple items
    for i in range(3):
        items = random.sample(
            ["light", "truth", "knowledge", "wisdom", "evidence"],
            k=3,
        )

        surfaces = [
            f"{items[0]}, {items[1]}, and {items[2]} ground understanding",
            f"{items[0]}, as well as {items[1]} and {items[2]}, support inquiry",
        ]

        nodes = []
        for idx, item in enumerate(items):
            nodes.append({
                "node_id": f"n{idx+1}",
                "subject": item,
                "predicate": "ground" if idx == 0 else "support",
                "obj": "understanding",
            })

        cases.append({
            "id": f"gram_C03_v2_{case_id:02d}",
            "construction": "C03",
            "construction_name": "conjunction",
            "proposition_graph": {
                "nodes": nodes,
                "edges": [
                    {"source": f"n{i}", "target": f"n{i+1}", "relation": "conjunction"}
                    for i in range(len(items) - 1)
                ],
            },
            "accept_surfaces": surfaces,
            "constraints": {
                "must_contain": items + ["ground", "understanding"],
                "max_words": 14,
            },
        })
        case_id += 1

    # C04: Disjunction → v2
    for i in range(2):
        opt1 = random.choice(["light", "darkness"])
        opt2 = random.choice(["truth", "illusion"])
        result = random.choice(["precedes dawn", "precedes enlightenment"])

        surfaces = [
            f"either {opt1} or {opt2} {result}",
            f"{opt1} or {opt2} {result}",
        ]

        cases.append({
            "id": f"gram_C04_v2_{case_id:02d}",
            "construction": "C04",
            "construction_name": "disjunction",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": opt1, "predicate": result.split()[1], "obj": "dawn"},
                    {"node_id": "n2", "subject": opt2, "predicate": result.split()[1], "obj": "dawn"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "relation": "disjunction"}
                ],
            },
            "accept_surfaces": surfaces,
            "constraints": {
                "must_contain": [opt1, opt2, "or"],
                "max_words": 10,
            },
        })
        case_id += 1

    # C05: Embedded clause (deeper nesting) → v2 with complex embedding
    for i in range(3):
        surfaces = [
            "wisdom demonstrates that evidence substantiates the claim that truth underlies all inquiry",
            "sage revelation discloses that corroboration supports the thesis that authenticity grounds knowledge",
            "discernment shows that documentation proves that verity underlies cognition",
        ]

        cases.append({
            "id": f"gram_C05_v2_{case_id:02d}",
            "construction": "C05",
            "construction_name": "embedded_clause",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "wisdom", "predicate": "demonstrates", "obj": "n2"},
                    {"node_id": "n2", "subject": "evidence", "predicate": "substantiates", "obj": "n3"},
                    {"node_id": "n3", "subject": "truth", "predicate": "underlies", "obj": "inquiry"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "relation": "complement"},
                    {"source": "n2", "target": "n3", "relation": "complement"},
                ],
            },
            "accept_surfaces": [surfaces[i]],
            "constraints": {
                "must_contain": ["that"],
                "max_words": 16,
            },
        })
        case_id += 1

    # C06: Relative clause → v2 with longer nesting
    for i in range(2):
        surfaces = [
            "verity, which undergirds all cognition, reveals the path toward illumination",
            "authenticity, which substantiates epistemic inquiry, discloses wisdom",
        ]

        cases.append({
            "id": f"gram_C06_v2_{case_id:02d}",
            "construction": "C06",
            "construction_name": "relative_clause",
            "proposition_graph": {
                "nodes": [
                    {"node_id": "n1", "subject": "truth", "predicate": "undergirds", "obj": "cognition"},
                    {"node_id": "n2", "subject": "truth", "predicate": "reveals", "obj": "path"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "relation": "relative"}
                ],
            },
            "accept_surfaces": [surfaces[i]],
            "constraints": {
                "must_contain": ["which", "truth"],
                "max_words": 14,
            },
        })
        case_id += 1

    # C07: Universal quantification → v2 with paraphrasing
    # Note: realizer produces "all/every X verb Y", not complex paraphrases
    for i in range(2):
        subj = random.choice(["light", "knowledge"])
        pred = random.choice(["reveals", "grounds"])
        obj = random.choice(["truth", "understanding"])
        
        surfaces = [
            f"all {subj} {pred} {obj}",
            f"every {subj} {pred} {obj}",
        ]

        cases.append({
            "id": f"gram_C07_v2_{case_id:02d}",
            "construction": "C07",
            "construction_name": "universal_quantification",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": subj,
                        "predicate": pred,
                        "obj": obj,
                        "quantifier": "all",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces,
            "constraints": {
                "must_contain": [subj, pred, obj],
                "max_words": 8,
            },
        })
        case_id += 1

    # C08: Existential quantification → v2
    for i in range(2):
        surfaces = [
            "certain instances of substantiation corroborate the foundations of knowledge",
            "particular forms of evidence ground epistemic certainty",
        ]

        cases.append({
            "id": f"gram_C08_v2_{case_id:02d}",
            "construction": "C08",
            "construction_name": "existential_quantification",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": "evidence",
                        "predicate": "grounds",
                        "obj": "knowledge",
                        "quantifier": "some",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": [surfaces[i]],
            "constraints": {
                "must_contain": ["some"],
                "max_words": 10,
            },
        })
        case_id += 1

    # C09: Past tense → v2 with paraphrasing
    for i in range(3):
        subj = random.choice(["wisdom", "knowledge", "evidence"])
        obj = random.choice(["truth", "inquiry", "enlightenment"])

        surfaces = [
            f"the {subj} previously disclosed the nature of {obj}",
            f"{subj} had substantiated principles of {obj}",
            f"historical {subj} undergirded {obj}",
        ]

        cases.append({
            "id": f"gram_C09_v2_{case_id:02d}",
            "construction": "C09",
            "construction_name": "past_tense",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": subj,
                        "predicate": "disclosed",
                        "obj": obj,
                        "tense": "past",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "max_words": 10,
            },
        })
        case_id += 1

    # C10: Present tense → v2 with alternative constructions
    for i in range(3):
        obj = random.choice(["verity", "cognition", "authenticity"])

        surfaces = [
            f"illumination perpetually sustains {obj}",
            f"radiance continuously buttresses {obj}",
            f"light presently undergirds {obj}",
        ]

        cases.append({
            "id": f"gram_C10_v2_{case_id:02d}",
            "construction": "C10",
            "construction_name": "present_tense",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": "light",
                        "predicate": "sustains",
                        "obj": obj,
                        "tense": "present",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "max_words": 8,
            },
        })
        case_id += 1

    # C11: Future tense → v2
    for i in range(3):
        obj = random.choice(["wisdom", "understanding", "enlightenment"])

        surfaces = [
            f"truth shall eventually illuminate the path to {obj}",
            f"verity will perpetually guide seekers toward {obj}",
            f"authenticity is destined to undergird {obj}",
        ]

        cases.append({
            "id": f"gram_C11_v2_{case_id:02d}",
            "construction": "C11",
            "construction_name": "future_tense",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": "truth",
                        "predicate": "illuminate",
                        "obj": obj,
                        "tense": "future",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "max_words": 12,
            },
        })
        case_id += 1

    # C12: Perfective aspect → v2
    for i in range(3):
        obj = random.choice(["our understanding", "the inquiry", "the discourse"])

        surfaces = [
            f"wisdom has conclusively established the foundations of {obj}",
            f"evidence has thoroughly substantiated principles guiding {obj}",
            f"truth has permanently undergirded {obj}",
        ]

        cases.append({
            "id": f"gram_C12_v2_{case_id:02d}",
            "construction": "C12",
            "construction_name": "perfective_aspect",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": "wisdom",
                        "predicate": "established",
                        "obj": obj,
                        "aspect": "perfective",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "must_contain": ["has"],
                "max_words": 12,
            },
        })
        case_id += 1

    # C13: Imperfective aspect → v2
    for i in range(3):
        activity = random.choice(["revealing truth", "substantiating claims", "undergirding knowledge"])

        surfaces = [
            f"light is continuously {activity}",
            f"wisdom remains perpetually {activity}",
            f"evidence is perpetually {activity}",
        ]

        cases.append({
            "id": f"gram_C13_v2_{case_id:02d}",
            "construction": "C13",
            "construction_name": "imperfective_aspect",
            "proposition_graph": {
                "nodes": [
                    {
                        "node_id": "n1",
                        "subject": "light",
                        "predicate": "revealing",
                        "obj": "truth",
                        "aspect": "imperfective",
                    }
                ],
                "edges": [],
            },
            "accept_surfaces": surfaces[:2],
            "constraints": {
                "must_contain": ["is"],
                "max_words": 10,
            },
        })
        case_id += 1

    return cases


if __name__ == "__main__":
    cases = generate_v2_cases()

    # Write v2 public test set
    output_path = "evals/grammatical_coverage/public/v2/cases.jsonl"
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")

    print(f"Generated {len(cases)} v2 cases")
    print(f"Wrote to {output_path}")

    # Show distribution
    by_construction = defaultdict(int)
    for case in cases:
        by_construction[case["construction"]] += 1

    print("\nDistribution:")
    for c in sorted(by_construction.keys()):
        print(f"  {c}: {by_construction[c]}")
