"""
evals/industry_demos/run_all.py — ADR-0046 suite runner.

Runs all three falsifiable industry demos in sequence.  Each demo makes
exactly one claim that a transformer-LLM wrapper cannot reproduce.  This
runner collects structured JSON evidence from all three, prints a human-
readable report, and exits 0 iff every demo passes.

Usage::

    python -m evals.industry_demos.run_all

Output (stdout):
    - Per-demo banner + JSON evidence block.
    - Final structured JSON: {"all_passed": bool, "results": [...]}

Exit code:
    0  — all three demos passed.
    1  — one or more demos failed or raised an exception.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any


# ---------- demo registry ----------

_DEMOS = [
    ("demo_01_forward_constraint",      "evals.industry_demos.demo_01_forward_constraint"),
    ("demo_02_geometry_drives_identity", "evals.industry_demos.demo_02_geometry_drives_identity"),
    ("demo_03_deterministic_audit",      "evals.industry_demos.demo_03_deterministic_audit"),
]

_SEP = "=" * 72


# ---------- runner ----------


def _run_demo(name: str, module_path: str) -> dict[str, Any]:
    """Import and run a single demo module.  Returns its result dict.

    Wraps the run() call in a broad try/except so that a crash in one
    demo does not prevent the others from executing.  A crashed demo
    is recorded as failed with the traceback embedded in the evidence.
    """
    import importlib
    try:
        mod = importlib.import_module(module_path)
        result: dict[str, Any] = mod.run()
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        result = {
            "demo": name,
            "claim": "(exception — see evidence.traceback)",
            "evidence": {"traceback": tb},
            "passed": False,
        }
    return result


def run_all() -> dict[str, Any]:
    """Execute all registered demos and return a summary dict."""
    results: list[dict[str, Any]] = []

    for name, module_path in _DEMOS:
        print(_SEP)
        print(f"DEMO: {name}")
        print(_SEP)

        result = _run_demo(name, module_path)
        results.append(result)

        status = "PASS" if result.get("passed") else "FAIL"
        print(f"Status : {status}")
        print(f"Claim  : {result.get('claim', '')}")
        print("Evidence:")
        print(json.dumps(result.get("evidence", {}), indent=2))
        print()

    all_passed = all(r.get("passed") for r in results)

    print(_SEP)
    print(f"SUITE RESULT: {'ALL PASSED' if all_passed else 'ONE OR MORE FAILED'}")
    print(_SEP)

    summary = {
        "all_passed": all_passed,
        "results": results,
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    summary = run_all()
    sys.exit(0 if summary["all_passed"] else 1)
