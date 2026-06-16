"""The option-A verdict: does the field's incidence reading add independent signal
over a FAIR same-grammar rational control, or is it reducible (decoration / servant)?

For each over-determined incidence case it runs three deciders:
- the independent GOLD (rational cross-product),
- the FAIR CONTROL (rational line-equation — a same-grammar symbolic reader),
- the FIELD reader (conformal incidence via graded_wedge + is_incident).

The only question that decides the verdict:
- ``field_caught`` — cases where the field refuses/flags an inconsistency the fair
  control admits as consistent (a real independent catch). >0 ⇒ STRONG_PASS.
- ``field_worse``  — cases where the field is WRONG vs gold while the control is right
  (a liability — e.g. f64 incidence drift the exact arithmetic does not have).
If field_caught == 0 and field never disagrees with the control, the field is a
correct-but-REDUCIBLE coherence check: a useful servant at best, not independent
reasoning. That is the honest, expected outcome to confirm or refute.

Run:  PYTHONPATH=. .venv/bin/python -m evals.field_incidence.ablation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.field_incidence.gold import control_consistency, gold_consistency
from generate.field_incidence_reader import read_incidence

_CASES = Path(__file__).resolve().parent / "cases.jsonl"


def run() -> dict[str, Any]:
    cases = [json.loads(l) for l in _CASES.read_text().splitlines() if l.strip()]
    gold_integrity: list[str] = []
    field_correct = control_correct = 0
    field_caught: list[str] = []        # field flags an inconsistency the control admits
    field_worse: list[dict] = []        # field wrong vs gold where control is right
    field_vs_control_disagree: list[str] = []
    rows = []

    for c in cases:
        cid, pts, inc = c["id"], c["points"], c["incidences"]
        gold = gold_consistency(pts, inc)
        if gold != c["class"]:
            gold_integrity.append(f"{cid}: gold={gold} != class={c['class']}")
            continue
        control = control_consistency(pts, inc)
        fr = read_incidence(pts, inc)
        field = "refused" if fr.refused else fr.verdict

        if control == gold:
            control_correct += 1
        if field == gold:
            field_correct += 1
        if field != control:
            field_vs_control_disagree.append(cid)
        # field catches what control misses: control says consistent, truth is inconsistent,
        # field does NOT say consistent.
        if control == "consistent" and gold == "inconsistent" and field != "consistent":
            field_caught.append(cid)
        # field is a liability: field wrong vs gold, control right.
        if field != gold and control == gold:
            field_worse.append({"id": cid, "field": field, "gold": gold})
        rows.append({"id": cid, "gold": gold, "control": control, "field": field})

    n = len(rows)
    reducible = (not field_vs_control_disagree) and (not field_caught)
    if field_caught and not field_worse:
        verdict = "STRONG_PASS_field_adds_independent_signal"
    elif field_worse:
        verdict = "LIABILITY_field_worse_than_arithmetic"
    elif reducible:
        verdict = "REDUCIBLE_servant_no_independent_signal"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "total": n,
        "verdict": verdict,
        "field_correct": field_correct,
        "control_correct": control_correct,
        "field_caught_what_control_missed": field_caught,
        "field_worse_than_arithmetic": field_worse,
        "field_vs_control_disagreements": field_vs_control_disagree,
        "gold_integrity_failures": gold_integrity,
        "rows": rows,
    }


def main() -> int:
    rep = run()
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=2))
    return 1 if rep["gold_integrity_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
