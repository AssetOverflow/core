"""ADR-0119.5 — score the adversarial suite against the gsm8k_math runner.

CLI: ``python3 -m evals.gsm8k_math.adversarial.score``

Reports the runner's correct/wrong/refused triple over the adversarial
case set. The load-bearing gate is **wrong == 0** — CORE must refuse
adversarial inputs, never silently confabulate.

Exits 0 iff wrong == 0; else 1.
"""

from __future__ import annotations

from collections import Counter

from evals.gsm8k_math.adversarial.generator import generate_adversarial_cases
from evals.gsm8k_math.runner import run_lane


def main() -> int:
    cases = generate_adversarial_cases()
    report = run_lane([c.as_runner_dict() for c in cases])

    metrics = report.metrics
    print(f"adversarial suite: {metrics['cases_total']} cases")
    print(f"  correct: {metrics['correct']}")
    print(f"  wrong:   {metrics['wrong']}  (gate: must be 0)")
    print(f"  refused: {metrics['refused']}")
    print()

    # Family breakdown
    print("per-family outcome distribution:")
    family_of: dict[str, str] = {c.case_id: c.family for c in cases}
    by_family: Counter[tuple[str, str]] = Counter()
    for detail in report.case_details:
        family = family_of[detail["case_id"]]
        by_family[(family, detail["outcome"])] += 1
    families = sorted({f for (f, _) in by_family})
    for family in families:
        row = {oc: by_family[(family, oc)] for oc in ("correct", "wrong", "refused")}
        marker = " " if row["wrong"] == 0 else "✗"
        print(f"  {marker} {family:32s}  correct={row['correct']:3d}  wrong={row['wrong']:3d}  refused={row['refused']:3d}")

    print()
    print(f"misparse rate: {metrics['wrong'] / max(metrics['cases_total'], 1):.4f}")
    if metrics["wrong"] == 0:
        print("GATE PASS — zero misparse")
        return 0
    print("GATE FAIL — misparses recorded; CORE silently confabulated on adversarial inputs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
