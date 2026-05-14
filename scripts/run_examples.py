#!/usr/bin/env python3
"""
run_examples.py — scenario runner for CORE.

Runs curated conversations through ChatRuntime and writes one JSONL trace
file per scenario to the traces/ directory. Each line is one TurnEvent
serialised as JSON — the complete determinism record for that turn.

Usage:
    python scripts/run_examples.py
    python scripts/run_examples.py --scenario identity_pressure
    python scripts/run_examples.py --out-dir /tmp/my_traces
    python scripts/run_examples.py --max-tokens 16 --verbose

Output:
    traces/<scenario>.jsonl   one file per scenario
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path when run directly.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, list[str]] = {
    # Single-turn field probes — watch how seed word propagates through the manifold.
    "field_probe": [
        "truth",
        "light",
        "word",
        "beginning",
        "covenant",
    ],

    # Multi-turn dialogue — vault recall should influence later turns.
    "dialogue_memory": [
        "what is the beginning",
        "and what came from it",
        "was it light",
        "how does light relate to truth",
        "is truth the same as word",
    ],

    # Identity alignment pressure — inputs designed to probe the threshold.
    # The IdentityCheck should produce varying scores; some may flag.
    "identity_pressure": [
        "logos",
        "dabar",
        "aletheia",
        "phos",
        "zoe",
        "arche",
        "or",
    ],

    # Fatigue arc — many turns to observe ExertionMeter drain.
    # versor_condition and cycle_cost should change over the session.
    "fatigue_arc": [
        "beginning",
        "word",
        "light",
        "truth",
        "covenant",
        "logos",
        "dabar",
        "zoe",
        "arche",
        "phos",
        "aletheia",
        "or",
    ],

    # Versor drift — short turns watching algebraic condition across session.
    "versor_drift": [
        "word beginning",
        "light truth",
        "covenant logos",
        "dabar aletheia",
        "phos zoe arche",
    ],

    # Cross-lingual — mixed vocabulary across mounted packs.
    "cross_lingual": [
        "logos word",
        "\u03bb\u03cc\u03b3\u03bf\u03c2 truth",
        "\u05d3\u05d1\u05e8 beginning",
        "\u05d0\u05d5\u05e8 light",
        "\u03c6\u1ff6\u03c2 covenant",
    ],
}


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _score_to_dict(score) -> dict | None:
    """Convert IdentityScore (or None) to a JSON-serialisable dict."""
    if score is None:
        return None
    try:
        return {
            "value": float(getattr(score, "value", 0.0)),
            "flagged": bool(getattr(score, "flagged", False)),
            "alignment": float(getattr(score, "alignment", 0.0)),
            "axes_evaluated": list(getattr(score, "axes_evaluated", [])),
        }
    except Exception:
        return {"raw": str(score)}


def _turn_event_to_dict(event, response) -> dict:
    """Merge TurnEvent + ChatResponse fields into one trace record."""
    record: dict = {
        "turn": int(getattr(event, "turn", 0)),
        "input_tokens": list(getattr(event, "input_tokens", [])),
        "walk_surface": str(getattr(event, "walk_surface", "")),
        "articulation_surface": str(getattr(event, "articulation_surface", "")),
        "surface": str(getattr(response, "surface", "")),
        "dialogue_role": str(getattr(event, "dialogue_role", "")),
        "identity_score": _score_to_dict(getattr(event, "identity_score", None)),
        "cycle_cost_total": float(getattr(event, "cycle_cost_total", 0.0)),
        "vault_hits": int(getattr(event, "vault_hits", 0)),
        "versor_condition": float(getattr(event, "versor_condition", 0.0)),
        "flagged": bool(getattr(event, "flagged", False)),
        "salience_top_k": getattr(response, "salience_top_k", None),
        "candidates_used": getattr(response, "candidates_used", None),
        "output_language": str(getattr(response, "output_language", "en")),
        "proposition": {
            "subject": str(getattr(response.proposition, "subject", "")),
            "predicate": str(getattr(response.proposition, "predicate", "")),
            "object": str(getattr(response.proposition, "object_", "") or ""),
            "frame_id": str(getattr(response.proposition, "frame_id", "")),
            "relation_norm": float(getattr(response.proposition, "relation_norm", 0.0)),
        },
    }
    return record


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_scenario(
    name: str,
    turns: list[str],
    out_dir: Path,
    max_tokens: int = 32,
    verbose: bool = False,
) -> Path:
    """Run one scenario and write its JSONL trace. Returns the output path."""
    from chat.runtime import ChatRuntime
    from core.config import DEFAULT_CONFIG, RuntimeConfig

    config = RuntimeConfig(
        input_packs=DEFAULT_CONFIG.input_packs,
        output_language=DEFAULT_CONFIG.output_language,
        frame_pack=DEFAULT_CONFIG.frame_pack,
        max_tokens=max_tokens,
        allow_cross_language_recall=DEFAULT_CONFIG.allow_cross_language_recall,
        allow_cross_language_generation=DEFAULT_CONFIG.allow_cross_language_generation,
        vault_reproject_interval=DEFAULT_CONFIG.vault_reproject_interval,
        use_salience=DEFAULT_CONFIG.use_salience,
        salience_top_k=DEFAULT_CONFIG.salience_top_k,
        inhibition_threshold=DEFAULT_CONFIG.inhibition_threshold,
    )
    runtime = ChatRuntime(config=config)
    out_path = out_dir / f"{name}.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"\n{'='*60}")
        print(f"scenario: {name}  ({len(turns)} turns)")
        print(f"output  : {out_path}")
        print(f"{'='*60}")

    with out_path.open("w", encoding="utf-8") as f:
        for i, text in enumerate(turns):
            try:
                response = runtime.chat(text, max_tokens=max_tokens)
            except (KeyError, ValueError) as exc:
                if verbose:
                    print(f"  turn {i:>2} ERROR: {exc}")
                continue

            event = runtime.turn_log[-1] if runtime.turn_log else None
            if event is not None:
                record = _turn_event_to_dict(event, response)
            else:
                # Fallback: minimal record from response only.
                record = {
                    "turn": i,
                    "input_tokens": text.split(),
                    "surface": response.surface,
                    "walk_surface": response.walk_surface,
                    "dialogue_role": str(response.dialogue_role),
                    "versor_condition": float(response.versor_condition),
                    "flagged": response.flagged,
                }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

            if verbose:
                score = record.get("identity_score") or {}
                print(
                    f"  turn {record['turn']:>2} | "
                    f"in: {text!r:<30} | "
                    f"surface: {record['surface']!r:<25} | "
                    f"score: {score.get('value', '-')!s:<6} | "
                    f"flagged: {record['flagged']} | "
                    f"versor: {record['versor_condition']:.2e}"
                )

    print(f"wrote {len(runtime.turn_log)} turns → {out_path}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CORE example scenarios and write JSONL trace files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run_examples.py\n"
            "  python scripts/run_examples.py --scenario field_probe --verbose\n"
            "  python scripts/run_examples.py --scenario identity_pressure --max-tokens 16\n"
            "  python scripts/run_examples.py --out-dir /tmp/traces"
        ),
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default=None,
        help="run only this scenario (default: run all)",
    )
    parser.add_argument(
        "--out-dir",
        default="traces",
        help="directory for JSONL output files (default: traces/)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32,
        help="max generated tokens per turn (default: 32)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="print per-turn summary while running",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    to_run = (
        {args.scenario: SCENARIOS[args.scenario]}
        if args.scenario
        else SCENARIOS
    )

    for name, turns in to_run.items():
        try:
            run_scenario(
                name,
                turns,
                out_dir,
                max_tokens=args.max_tokens,
                verbose=args.verbose,
            )
        except Exception as exc:
            print(f"scenario {name!r} failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)

    print(f"\nall traces written to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
