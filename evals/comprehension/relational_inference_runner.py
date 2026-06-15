"""Score the one-hop relational-inference DETERMINE capability on independent gold.

told fact(s) -> ``determine(query)`` vs hand-authored gold ``(predicate, subject,
object)``. The gold is authored by reading the inverse/symmetric relational algebra,
INDEPENDENTLY of ``generate.determine`` / ``generate.meaning_graph.relational``
(INV-25 / INV-27) — the engine never produced it.

A refusal is a COVERAGE miss (``refused``), never a wrong; only a ``Determined`` that
disagrees with gold — wrong predicate/subject/object, or ``answer`` not True — is
``wrong``, and wrong must stay 0. The confuser cases that MUST refuse live in
``refusals.jsonl`` + the dedicated lane test. This is the positive-coverage lane that
puts the one-hop relational-inference capability ON the capability index (breadth 9->10).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from chat.runtime import ChatRuntime
from generate.determine import Determined, determine
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import realize_comprehension
from session.context import SessionContext

_CASES = (
    Path(__file__).resolve().parent.parent
    / "relational_inference"
    / "v1"
    / "cases.jsonl"
)
_HIGH = 10**9


def _load_cases(path: Path = _CASES) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run(path: Path = _CASES) -> dict[str, Any]:
    cases = _load_cases(path)
    pack = load_relational_pack_lemmas()
    rt = ChatRuntime(no_load_state=True)
    vocab, persona = rt._context.vocab, rt._context.persona

    correct = wrong = refused = 0
    wrongs: list[dict[str, Any]] = []

    for case in cases:
        ctx = SessionContext(
            vocab=vocab, persona=persona, vault_reproject_interval=_HIGH
        )
        for fact in case["facts"]:
            realize_comprehension(comprehend_relational(fact, pack), ctx)
        res = determine(comprehend_relational(case["query"], pack), ctx)
        if not isinstance(res, Determined):
            refused += 1  # coverage miss, not a wrong
            continue
        got = [res.answer, res.predicate, res.subject, res.object]
        gold = [True, case["predicate"], case["subject"], case["object"]]
        if got == gold:
            correct += 1
        else:
            wrong += 1
            wrongs.append({"id": case.get("id"), "got": got, "gold": gold})

    return {
        "domain": "comprehension_relational_inference",
        "total": len(cases),
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "wrongs": wrongs,
        "counts": {"correct": correct, "wrong": wrong, "refused": refused},
    }


def main() -> int:
    report = run()
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "wrongs"},
            indent=2,
            sort_keys=True,
        )
    )
    if report["wrong"]:
        print(
            "WRONG > 0 — relational inference produced a wrong determination:",
            file=sys.stderr,
        )
        print(json.dumps(report["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
