#!/usr/bin/env python3
"""
review_trace.py — JSONL trace reader for CORE.

Reads trace files produced by run_examples.py or `core session` and
prints formatted reports for post-hoc determinism inspection.

Usage:
    python scripts/review_trace.py traces/field_probe.jsonl
    python scripts/review_trace.py traces/identity_pressure.jsonl --summary
    python scripts/review_trace.py traces/fatigue_arc.jsonl --fatigue
    python scripts/review_trace.py traces/versor_drift.jsonl --drift
    python scripts/review_trace.py traces/dialogue_memory.jsonl --turn 2
    python scripts/review_trace.py traces/identity_pressure.jsonl --flagged
    python scripts/review_trace.py traces/identity_pressure.jsonl --identity
    python scripts/review_trace.py traces/*.jsonl --summary  (glob supported)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# JSONL loading
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    events = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"warning: {path}:{lineno}: {exc}", file=sys.stderr)
    return events


def _load_all(paths: list[Path]) -> dict[str, list[dict]]:
    result = {}
    for p in paths:
        result[p.stem] = _load_jsonl(p)
    return result


# ---------------------------------------------------------------------------
# Report views
# ---------------------------------------------------------------------------

_COL = {
    "turn": 4, "input": 30, "surface": 28, "role": 16,
    "score": 6, "cost": 6, "flagged": 7, "versor": 9,
}


def _header() -> str:
    return (
        f"{'TURN':>{_COL['turn']}}  "
        f"{'INPUT':<{_COL['input']}}  "
        f"{'SURFACE':<{_COL['surface']}}  "
        f"{'ROLE':<{_COL['role']}}  "
        f"{'SCORE':>{_COL['score']}}  "
        f"{'COST':>{_COL['cost']}}  "
        f"{'FLAGGED':<{_COL['flagged']}}  "
        f"{'VERSOR':>{_COL['versor']}}"
    )


def _row(e: dict) -> str:
    score = (e.get("identity_score") or {})
    score_val = score.get("value", "-")
    score_str = f"{score_val:.3f}" if isinstance(score_val, float) else str(score_val)
    inp = " ".join(e.get("input_tokens", []))
    return (
        f"{e.get('turn', '?'):>{_COL['turn']}}  "
        f"{inp[:_COL['input']]:<{_COL['input']}}  "
        f"{str(e.get('surface', ''))[:_COL['surface']]:<{_COL['surface']}}  "
        f"{str(e.get('dialogue_role', ''))[:_COL['role']]:<{_COL['role']}}  "
        f"{score_str:>{_COL['score']}}  "
        f"{e.get('cycle_cost_total', 0.0):>{_COL['cost']}.1f}  "
        f"{'YES' if e.get('flagged') else 'no':<{_COL['flagged']}}  "
        f"{e.get('versor_condition', 0.0):>{_COL['versor']}.2e}"
    )


def view_summary(name: str, events: list[dict]) -> None:
    print(f"\n─── {name} ({len(events)} turns) ───")
    print(_header())
    print("─" * (sum(_COL.values()) + len(_COL) * 2 + 2))
    for e in events:
        print(_row(e))


def view_turn(name: str, events: list[dict], turn: int) -> None:
    matches = [e for e in events if e.get("turn") == turn]
    if not matches:
        print(f"{name}: no turn {turn}")
        return
    e = matches[0]
    print(f"\n─── {name} / turn {turn} ───")
    print(f"  input_tokens      : {e.get('input_tokens')}")
    print(f"  surface           : {e.get('surface')!r}")
    print(f"  walk_surface      : {e.get('walk_surface')!r}")
    print(f"  articulation_surf : {e.get('articulation_surface')!r}")
    print(f"  dialogue_role     : {e.get('dialogue_role')}")
    print(f"  versor_condition  : {e.get('versor_condition', 0.0):.4e}")
    print(f"  cycle_cost_total  : {e.get('cycle_cost_total', 0.0):.2f}")
    print(f"  vault_hits        : {e.get('vault_hits')}")
    print(f"  flagged           : {e.get('flagged')}")
    score = e.get("identity_score") or {}
    if score:
        print(f"  identity_score:")
        print(f"    value           : {score.get('value')}")
        print(f"    flagged         : {score.get('flagged')}")
        print(f"    alignment       : {score.get('alignment')}")
        print(f"    axes_evaluated  : {score.get('axes_evaluated')}")
    prop = e.get("proposition") or {}
    if prop:
        print(f"  proposition:")
        print(f"    subject         : {prop.get('subject')!r}")
        print(f"    predicate       : {prop.get('predicate')!r}")
        print(f"    object          : {prop.get('object')!r}")
        print(f"    frame_id        : {prop.get('frame_id')}")
        print(f"    relation_norm   : {prop.get('relation_norm', 0.0):.4f}")


def view_flagged(name: str, events: list[dict]) -> None:
    flagged = [e for e in events if e.get("flagged")]
    print(f"\n─── {name} ─ flagged turns ({len(flagged)}/{len(events)}) ───")
    if not flagged:
        print("  none")
        return
    print(_header())
    for e in flagged:
        print(_row(e))


def view_drift(name: str, events: list[dict]) -> None:
    print(f"\n─── {name} ─ versor_condition drift ───")
    print(f"  {'TURN':>4}  {'VERSOR_CONDITION':>18}  {'DELTA':>14}")
    prev = None
    for e in events:
        val = float(e.get("versor_condition", 0.0))
        delta = (val - prev) if prev is not None else 0.0
        sign = "+" if delta >= 0 else ""
        print(f"  {e.get('turn', '?'):>4}  {val:>18.6e}  {sign}{delta:>13.6e}")
        prev = val


def view_identity(name: str, events: list[dict]) -> None:
    print(f"\n─── {name} ─ identity scores ───")
    print(f"  {'TURN':>4}  {'VALUE':>8}  {'ALIGNMENT':>10}  {'FLAGGED':<8}  AXES")
    for e in events:
        score = e.get("identity_score") or {}
        val = score.get("value", "-")
        val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
        aln = score.get("alignment", "-")
        aln_str = f"{aln:.4f}" if isinstance(aln, float) else str(aln)
        axes = ", ".join(str(a) for a in (score.get("axes_evaluated") or []))
        print(
            f"  {e.get('turn', '?'):>4}  {val_str:>8}  {aln_str:>10}  "
            f"{'YES' if score.get('flagged') else 'no':<8}  {axes}"
        )


def view_fatigue(name: str, events: list[dict]) -> None:
    print(f"\n─── {name} ─ fatigue arc (cycle_cost_total) ───")
    print(f"  {'TURN':>4}  {'COST':>8}  {'CUMULATIVE':>12}  {'VAULT_HITS':>10}")
    cumulative = 0.0
    for e in events:
        cost = float(e.get("cycle_cost_total", 0.0))
        cumulative += cost
        print(
            f"  {e.get('turn', '?'):>4}  {cost:>8.2f}  {cumulative:>12.2f}  "
            f"{e.get('vault_hits', 0):>10}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review CORE JSONL trace files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/review_trace.py traces/field_probe.jsonl\n"
            "  python scripts/review_trace.py traces/identity_pressure.jsonl --flagged\n"
            "  python scripts/review_trace.py traces/fatigue_arc.jsonl --fatigue\n"
            "  python scripts/review_trace.py traces/dialogue_memory.jsonl --turn 3\n"
            "  python scripts/review_trace.py traces/versor_drift.jsonl --drift\n"
        ),
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSONL trace file(s) to review",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=True,
        help="print one-line-per-turn summary table (default)",
    )
    parser.add_argument(
        "--turn",
        type=int,
        default=None,
        metavar="N",
        help="print full detail for turn N",
    )
    parser.add_argument(
        "--flagged",
        action="store_true",
        help="show only flagged turns",
    )
    parser.add_argument(
        "--drift",
        action="store_true",
        help="print versor_condition per turn",
    )
    parser.add_argument(
        "--identity",
        action="store_true",
        help="print identity_score breakdown per turn",
    )
    parser.add_argument(
        "--fatigue",
        action="store_true",
        help="print cycle_cost_total per turn (exertion arc)",
    )
    args = parser.parse_args()

    paths = [Path(f) for f in args.files]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"error: file not found: {p}", file=sys.stderr)
        return 1

    traces = _load_all(paths)
    any_view_requested = any([
        args.turn is not None,
        args.flagged,
        args.drift,
        args.identity,
        args.fatigue,
    ])

    for name, events in traces.items():
        if args.turn is not None:
            view_turn(name, events, args.turn)
        if args.flagged:
            view_flagged(name, events)
        if args.drift:
            view_drift(name, events)
        if args.identity:
            view_identity(name, events)
        if args.fatigue:
            view_fatigue(name, events)
        if not any_view_requested or args.summary:
            view_summary(name, events)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
