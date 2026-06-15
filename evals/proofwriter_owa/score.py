"""Score the ProofWriter-OWA refusal floor: `determine()` vs the independent oracle.

For each fixture item: compute the OWA gold with the disjoint `oracle.label(...)`, then run
the production path (`comprehend`/`comprehend_relational` -> `realize` -> `determine`) and
compare. The invariant is **wrong=0**: `determine()` may assert True only on a gold-`True`
item; asserting True on a gold `Unknown` or `False` is a soundness breach (it would mean
the engine claimed entailment where the open world does not entail it).

Measure-only — imports no `generate.derivation` / `core.reliability_gate`; NOT a
capability-index domain. A refusal on a gold-`True` item is a coverage miss (recorded),
never a wrong — UNLESS the item is marked `serving_support` (within the engine's claimed
support), in which case it must determine True.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from chat.runtime import ChatRuntime
from evals.proofwriter_owa.oracle import label as owa_label
from generate.determine import Determined, determine
from generate.meaning_graph.reader import Refusal, comprehend
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import realize_comprehension
from session.context import SessionContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures.jsonl"
_HIGH = 10**9


def _load(path: Path = _FIXTURES) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _comprehend_any(text: str, pack):
    """Relational reader first (specific), else the general comprehension reader."""
    c = comprehend_relational(text, pack)
    if isinstance(c, Refusal):
        return comprehend(text)
    return c


def run(path: Path = _FIXTURES) -> dict[str, Any]:
    items = _load(path)
    pack = load_relational_pack_lemmas()
    rt = ChatRuntime(no_load_state=True)
    vocab, persona = rt._context.vocab, rt._context.persona

    correct = refused = wrong = 0
    wrongs: list[dict[str, Any]] = []
    coverage_gaps: list[dict[str, Any]] = []  # serving_support gold-True that refused

    for it in items:
        gold = owa_label(it["facts"], it["query"])
        ctx = SessionContext(
            vocab=vocab, persona=persona, vault_reproject_interval=_HIGH
        )
        for fact in it["facts"]:
            realize_comprehension(_comprehend_any(fact, pack), ctx)
        res = determine(_comprehend_any(it["query"], pack), ctx)
        asserted_true = isinstance(res, Determined) and res.answer is True

        if asserted_true and gold == "True":
            correct += 1
        elif asserted_true:  # gold Unknown/False but engine asserted True -> BREACH
            wrong += 1
            wrongs.append({"id": it["id"], "gold": gold, "query": it["query"]})
        else:
            refused += 1
            if it.get("serving_support") and gold == "True":
                coverage_gaps.append({"id": it["id"], "query": it["query"]})

    return {
        "domain": "proofwriter_owa",
        "total": len(items),
        "correct": correct,
        "refused": refused,
        "wrong": wrong,
        "wrongs": wrongs,
        "coverage_gaps": coverage_gaps,
        "counts": {"correct": correct, "wrong": wrong, "refused": refused},
    }


def main() -> int:
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "wrongs"}, indent=2, sort_keys=True))
    if r["wrong"]:
        print(
            "WRONG > 0 — determine asserted True on a non-True OWA gold (soundness breach):",
            file=sys.stderr,
        )
        print(json.dumps(r["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
