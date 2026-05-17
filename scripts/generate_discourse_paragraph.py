"""Generate cases for the discourse_paragraph benchmark lane.

Tests that the realizer can produce **multi-sentence paragraph-scale
output** from chained propositions, given a multi-step
ArticulationTarget with rhetorical moves (SEQUENCE, ELABORATE,
CONTRAST).  Each case stresses paragraph length, subject coverage,
discourse-marker presence, and deterministic replay.

Each case carries:
  - a graph of N ≥ 3 nodes (subject-predicate-object triples)
  - an ordered move list ([ASSERT, SEQUENCE, ELABORATE, ...])
  - acceptance constraints (min_sentences, must_contain_subjects,
    discourse_markers)

Topics are designed to be **structurally rich** — every case is more
than a 3-word SVO probe.

Run:
    .venv/bin/python scripts/generate_discourse_paragraph.py
"""

from __future__ import annotations

import json
from pathlib import Path


# Each topic: ordered triples + ordered rhetorical moves matching length.
# Moves: ASSERT (open), SEQUENCE (next step), ELABORATE (furthermore),
# CONTRAST (in contrast), CORRECT (correction).  See
# generate.templates._MOVE_TEMPLATES for emitted discourse markers.
PUBLIC_TOPICS: list[dict] = [
    {
        "topic": "epistemic_chain",
        "triples": [
            ("wisdom", "grounds", "knowledge"),
            ("knowledge", "requires", "evidence"),
            ("evidence", "supports", "truth"),
            ("truth", "reveals", "reality"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "scientific_method",
        "triples": [
            ("observation", "grounds", "hypothesis"),
            ("hypothesis", "implies", "prediction"),
            ("prediction", "follows", "experiment"),
            ("experiment", "supports", "theory"),
            ("theory", "entails", "explanation"),
        ],
        "moves": ["ASSERT", "ELABORATE", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "creation_arc",
        "triples": [
            ("light", "precedes", "form"),
            ("form", "grounds", "matter"),
            ("matter", "supports", "structure"),
            ("structure", "reveals", "order"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "logical_dependency",
        "triples": [
            ("premise", "supports", "conclusion"),
            ("conclusion", "requires", "validity"),
            ("validity", "entails", "soundness"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE"],
    },
    {
        "topic": "ethical_grounding",
        "triples": [
            ("virtue", "grounds", "action"),
            ("action", "requires", "intention"),
            ("intention", "supports", "consequence"),
            ("consequence", "reveals", "character"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "linguistic_layers",
        "triples": [
            ("sound", "grounds", "phoneme"),
            ("phoneme", "supports", "morpheme"),
            ("morpheme", "builds", "word"),
            ("word", "composes", "sentence"),
            ("sentence", "conveys", "meaning"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE", "ELABORATE"],
    },
    {
        "topic": "mathematical_chain",
        "triples": [
            ("axiom", "grounds", "theorem"),
            ("theorem", "entails", "corollary"),
            ("corollary", "supports", "application"),
            ("application", "yields", "insight"),
        ],
        "moves": ["ASSERT", "ELABORATE", "SEQUENCE", "SEQUENCE"],
    },
    {
        "topic": "narrative_progression",
        "triples": [
            ("conflict", "drives", "tension"),
            ("tension", "precedes", "climax"),
            ("climax", "yields", "resolution"),
            ("resolution", "reveals", "theme"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "biological_hierarchy",
        "triples": [
            ("gene", "encodes", "protein"),
            ("protein", "builds", "cell"),
            ("cell", "composes", "tissue"),
            ("tissue", "forms", "organ"),
            ("organ", "supports", "organism"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE", "ELABORATE"],
    },
    {
        "topic": "physical_causation",
        "triples": [
            ("force", "drives", "motion"),
            ("motion", "transfers", "energy"),
            ("energy", "yields", "heat"),
            ("heat", "raises", "temperature"),
        ],
        "moves": ["ASSERT", "ELABORATE", "SEQUENCE", "SEQUENCE"],
    },
    # Contrast-shaped cases — exercises the "in contrast" template.
    {
        "topic": "contrastive_definitions",
        "triples": [
            ("knowledge", "requires", "evidence"),
            ("belief", "requires", "trust"),
            ("wisdom", "grounds", "judgment"),
        ],
        "moves": ["ASSERT", "CONTRAST", "ELABORATE"],
    },
    {
        "topic": "method_contrast",
        "triples": [
            ("deduction", "yields", "certainty"),
            ("induction", "yields", "probability"),
            ("abduction", "yields", "explanation"),
        ],
        "moves": ["ASSERT", "CONTRAST", "ELABORATE"],
    },
]


HOLDOUT_TOPICS: list[dict] = [
    {
        "topic": "musical_construction",
        "triples": [
            ("note", "composes", "chord"),
            ("chord", "supports", "harmony"),
            ("harmony", "yields", "phrase"),
            ("phrase", "builds", "melody"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "social_structure",
        "triples": [
            ("custom", "grounds", "tradition"),
            ("tradition", "supports", "institution"),
            ("institution", "shapes", "society"),
            ("society", "reveals", "culture"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE"],
    },
    {
        "topic": "computational_pipeline",
        "triples": [
            ("input", "drives", "computation"),
            ("computation", "yields", "output"),
            ("output", "supports", "decision"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE"],
    },
    {
        "topic": "psychological_development",
        "triples": [
            ("sensation", "grounds", "perception"),
            ("perception", "supports", "memory"),
            ("memory", "yields", "learning"),
            ("learning", "shapes", "behavior"),
            ("behavior", "reveals", "character"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE", "SEQUENCE", "ELABORATE"],
    },
    {
        "topic": "economic_flow",
        "triples": [
            ("labor", "yields", "value"),
            ("value", "supports", "exchange"),
            ("exchange", "drives", "growth"),
        ],
        "moves": ["ASSERT", "SEQUENCE", "ELABORATE"],
    },
]


# Common discourse markers the realizer emits per RhetoricalMove
# (see generate.templates._MOVE_TEMPLATES).
_MARKERS_BY_MOVE: dict[str, str] = {
    "ASSERT": "",
    "ELABORATE": "furthermore",
    "CONTRAST": "in contrast",
    "SEQUENCE": "next",
    "CORRECT": "correction:",
}


def _build_case(prefix: str, idx: int, topic: dict) -> dict:
    triples = topic["triples"]
    moves = topic["moves"]
    assert len(triples) == len(moves), f"length mismatch in {topic['topic']}"

    nodes = [
        {
            "node_id": f"n{i+1}",
            "subject": s,
            "predicate": p,
            "obj": o,
        }
        for i, (s, p, o) in enumerate(triples)
    ]
    steps = [
        {"node_id": f"n{i+1}", "move": m}
        for i, m in enumerate(moves)
    ]
    must_contain_subjects = [t[0] for t in triples]
    discourse_markers = sorted(
        {_MARKERS_BY_MOVE[m] for m in moves if _MARKERS_BY_MOVE[m]}
    )

    return {
        "id": f"{prefix}_{idx:03d}",
        "topic": topic["topic"],
        "graph": {"nodes": nodes, "edges": []},
        "steps": steps,
        "min_sentences": len(triples),
        "must_contain_subjects": must_contain_subjects,
        "discourse_markers": discourse_markers,
        "max_sentences": len(triples) + 2,  # tolerate small over-runs from
                                            # downstream wrapping
    }


def _emit(prefix: str, topics: list[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(_build_case(prefix, i + 1, t), ensure_ascii=False)
        for i, t in enumerate(topics)
    ]
    out_path.write_text("\n".join(lines) + "\n")
    return len(lines)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    lane = root / "evals" / "discourse_paragraph"
    n_pub = _emit("DP-PUB",  PUBLIC_TOPICS,  lane / "public" / "v1" / "cases.jsonl")
    n_hold = _emit("DP-HOLD", HOLDOUT_TOPICS, lane / "holdouts" / "v1" / "cases.jsonl")
    n_dev = _emit("DP-DEV",  PUBLIC_TOPICS[:1], lane / "dev" / "cases.jsonl")
    print(f"discourse_paragraph  public={n_pub}  holdouts={n_hold}  dev={n_dev}")
