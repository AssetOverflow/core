"""Generate cases for the Phase 5.1 English fluency OOD lane.

Each case is one (construction, domain, item) tuple realised into
a PropositionGraph JSON.  Vocabulary is drawn from four domains
none of which appear in en_core_cognition_v1:

  - nature:    river/wind/cloud/valley/dune
  - tech:      server/packet/signal/database/cable
  - domestic:  train/coffee/chair/door/lamp
  - chemistry: molecule/atom/reaction/bond/enzyme  (holdouts)

Predicates default to regular verbs ("flows", "carries", "warms")
so that morphology gaps (irregular past tense, plural agreement)
do not confound the structural fluency claim.  The few cases that
intentionally probe morphology are isolated and documented in
gaps.md.

Run:
    .venv/bin/python scripts/generate_english_fluency_ood.py
"""

from __future__ import annotations

import json
from pathlib import Path

# Use the realizer's own pluralizer so constraints stay aligned with
# what the realizer will emit under quantifiers.  G2 fix.
from generate.templates import pluralize

# (subject, predicate, object) triples per domain.
# Each triple uses a regular verb for tense/aspect compatibility.
DOMAINS = {
    "nature": [
        ("river", "flows", "valley"),
        ("wind", "shapes", "dune"),
        ("cloud", "covers", "ridge"),
    ],
    "tech": [
        ("server", "returns", "packet"),
        ("cable", "carries", "signal"),
        ("database", "stores", "record"),
    ],
    "domestic": [
        ("train", "passes", "station"),
        ("coffee", "warms", "cup"),
        ("lamp", "lights", "room"),
    ],
}
HOLDOUT_DOMAIN = {
    "chemistry": [
        ("molecule", "binds", "enzyme"),
        ("atom", "forms", "bond"),
        ("reaction", "produces", "compound"),
    ],
}

# 13 grammatical constructions, mirroring grammatical_coverage.
# For each, a builder takes one (subj, pred, obj) and returns a case dict
# (without the id, which is filled per (construction, domain, i)).
CONSTRUCTIONS: list[tuple[str, str]] = [
    ("C01", "simple_declarative"),
    ("C02", "negation"),
    ("C03", "conjunction"),
    ("C04", "disjunction"),
    ("C05", "complement"),
    ("C06", "relative"),
    ("C07", "universal"),
    ("C08", "existential"),
    ("C09", "past_tense"),
    ("C10", "present_tense"),
    ("C11", "future_tense"),
    ("C12", "perfective"),
    ("C13", "imperfective"),
]


def _node(node_id: str, subj: str, pred: str, obj: str, **extra) -> dict:
    n = {"node_id": node_id, "subject": subj, "predicate": pred, "obj": obj}
    n.update(extra)
    return n


def build_case(cid: str, code: str, name: str, triple: tuple[str, str, str], aux: tuple[str, str, str] | None = None) -> dict:
    subj, pred, obj = triple
    g_nodes: list[dict]
    g_edges: list[dict] = []
    constraints: dict = {"max_words": 12}
    accept: list[str] | None = None

    if code == "C01":
        g_nodes = [_node("n1", subj, pred, obj)]
        accept = [f"{subj} {pred} {obj}"]
        constraints["must_contain"] = [subj, pred, obj]
        constraints["word_order"] = [subj, pred, obj]
    elif code == "C02":
        g_nodes = [_node("n1", subj, pred, obj, negated=True)]
        constraints["must_contain"] = [subj, "not", obj]
        constraints["word_order"] = [subj, "not", obj]
    elif code == "C03":
        assert aux is not None
        g_nodes = [_node("n1", subj, pred, obj), _node("n2", *aux)]
        g_edges = [{"source": "n1", "target": "n2", "relation": "conjunction"}]
        constraints["must_contain"] = [subj, "and", aux[0]]
        constraints["word_order"] = [subj, "and", aux[0]]
        constraints["max_words"] = 14
    elif code == "C04":
        assert aux is not None
        g_nodes = [_node("n1", subj, pred, obj), _node("n2", *aux)]
        g_edges = [{"source": "n1", "target": "n2", "relation": "disjunction"}]
        constraints["must_contain"] = [subj, "or", aux[0]]
        constraints["word_order"] = [subj, "or", aux[0]]
        constraints["max_words"] = 14
    elif code == "C05":
        assert aux is not None
        g_nodes = [_node("n1", aux[0], aux[1], aux[2]), _node("n2", subj, pred, obj)]
        g_edges = [{"source": "n1", "target": "n2", "relation": "complement"}]
        constraints["must_contain"] = [aux[0], "that", subj]
        constraints["word_order"] = [aux[0], "that", subj]
        constraints["max_words"] = 14
    elif code == "C06":
        assert aux is not None
        g_nodes = [_node("n1", subj, pred, obj), _node("n2", subj, aux[1], aux[2])]
        g_edges = [{"source": "n1", "target": "n2", "relation": "relative"}]
        # Realizer emits comma-bounded relative clause; accept the
        # punctuated form (the structural rubric is too word-strict to
        # parse commas, so we pin the surface exactly).
        accept = [
            f"{subj}, which {aux[1]} {aux[2]}, {pred} {obj}",
            f"{subj} which {aux[1]} {aux[2]} {pred} {obj}",
        ]
        constraints["must_contain"] = [subj, "which", aux[2], obj]
        constraints["max_words"] = 14
    elif code == "C07":
        # Universal quantifier triggers plural subject (G2 fix).
        plural_subj = pluralize(subj)
        g_nodes = [_node("n1", subj, pred, obj, quantifier="all")]
        constraints["must_contain"] = ["all", plural_subj, obj]
        constraints["word_order"] = ["all", plural_subj, obj]
    elif code == "C08":
        plural_subj = pluralize(subj)
        g_nodes = [_node("n1", subj, pred, obj, quantifier="some")]
        constraints["must_contain"] = ["some", plural_subj, obj]
        constraints["word_order"] = ["some", plural_subj, obj]
    elif code == "C09":
        g_nodes = [_node("n1", subj, pred, obj, tense="past")]
        constraints["must_contain"] = [subj, obj]
        constraints["word_order"] = [subj, obj]
    elif code == "C10":
        g_nodes = [_node("n1", subj, pred, obj, tense="present")]
        accept = [f"{subj} {pred} {obj}"]
        constraints["must_contain"] = [subj, pred, obj]
        constraints["word_order"] = [subj, pred, obj]
    elif code == "C11":
        g_nodes = [_node("n1", subj, pred, obj, tense="future")]
        constraints["must_contain"] = [subj, "will", obj]
        constraints["word_order"] = [subj, "will", obj]
    elif code == "C12":
        g_nodes = [_node("n1", subj, pred, obj, aspect="perfective")]
        constraints["must_contain"] = [subj, "has", obj]
        constraints["word_order"] = [subj, "has", obj]
    elif code == "C13":
        g_nodes = [_node("n1", subj, pred, obj, aspect="imperfective")]
        constraints["must_contain"] = [subj, "is", obj]
        constraints["word_order"] = [subj, "is", obj]
    else:
        raise AssertionError(f"unknown construction {code}")

    case = {
        "id": cid,
        "construction": code,
        "construction_name": name,
        "proposition_graph": {"nodes": g_nodes, "edges": g_edges},
        "constraints": constraints,
    }
    if accept:
        case["accept_surfaces"] = accept
    return case


def emit_split(domains: dict[str, list[tuple[str, str, str]]], prefix: str, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for domain, triples in domains.items():
        for code, name in CONSTRUCTIONS:
            for i, triple in enumerate(triples):
                aux = triples[(i + 1) % len(triples)]
                cid = f"{prefix}_{domain}_{code}_{i+1:02d}"
                case = build_case(cid, code, name, triple, aux=aux)
                lines.append(json.dumps(case))
    out_path.write_text("\n".join(lines) + "\n")
    return len(lines)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    n_public = emit_split(DOMAINS, "EFO-PUB", root / "evals" / "english_fluency_ood" / "public" / "v1" / "cases.jsonl")
    n_hold = emit_split(HOLDOUT_DOMAIN, "EFO-HOLD", root / "evals" / "english_fluency_ood" / "holdouts" / "v1" / "cases.jsonl")
    # Tiny dev set: one of each construction from the first domain
    dev_path = root / "evals" / "english_fluency_ood" / "dev" / "cases.jsonl"
    dev_lines: list[str] = []
    triples = DOMAINS["nature"]
    for code, name in CONSTRUCTIONS:
        case = build_case(f"EFO-DEV_{code}", code, name, triples[0], aux=triples[1])
        dev_lines.append(json.dumps(case))
    dev_path.write_text("\n".join(dev_lines) + "\n")
    print(f"public: {n_public} cases, holdouts: {n_hold} cases, dev: {len(dev_lines)} cases")
