"""Measure the ratification score distribution across cognition eval cases.

Finding 3 (audit 2026-05-20).  The current default ``threshold=0.0`` in
``generate.intent_ratifier.ratify_intent`` admits anything with non-
negative projection — the field gate is structurally live but
semantically inactive.

This script runs every cognition eval prompt through a fresh
``ChatRuntime``, captures the raw ``cga_inner(prompt, anchor)`` score
emitted by ``ratify_intent``, and prints the distribution by split and
intent.  Use the output to choose a calibrated threshold (the audit
suggests the ~10th percentile of the RATIFIED distribution as a
starting point so the bottom decile of weakly-aligned transitions
demotes to UNKNOWN without breaking any case that currently passes).

Run::

    uv run python scripts/calibrate_ratification_threshold.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from generate.intent import classify_intent
from generate.intent_ratifier import ratify_intent


SPLITS = {
    "public": Path("evals/cognition/public/v1/cases.jsonl"),
    "dev": Path("evals/cognition/dev/cases.jsonl"),
    "holdout": Path("evals/cognition/holdouts/cases_plaintext.jsonl"),
}


def _load_cases(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


_capture_buffer: list[dict] = []


def _capture_score(prompt: str) -> dict:
    """Run the prompt through the pipeline and capture the ratification score.

    The pipeline's own ``_ratify_intent`` runs inside ``run()`` after the
    chat path has primed the session state.  We monkeypatch
    ``ratify_intent`` for the duration of the call so the captured score
    reflects the exact same field-versor / anchor pair the production
    path uses — no parallel state-priming logic to drift.

    The pipeline captures ``field_state_before`` ahead of any ingest
    for this prompt, so a fresh runtime returns None on turn 1 and the
    ratifier short-circuits to PASSTHROUGH.  We run a no-op prime turn
    first so the score-bearing call reflects a real session.
    """
    rt = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime=rt)
    # Prime the field so turn N+1 has a real ``field_state_before``.
    pipeline.run("prime", max_tokens=2)

    import generate.intent_ratifier as _ir
    original = _ir.ratify_intent
    captured: list[dict] = []

    def _spy(intent, prompt_versor, *, vocab, threshold=0.0):
        result = original(intent, prompt_versor, vocab=vocab, threshold=threshold)
        captured.append({
            "seed_tag": intent.tag.value,
            "outcome": result.outcome.value,
            "score": result.score,
        })
        return result

    # core/cognition/pipeline.py imports ``ratify_intent`` at module load;
    # patch both the source module and the imported reference.
    import core.cognition.pipeline as _pl
    _ir.ratify_intent = _spy
    _pl.ratify_intent = _spy
    try:
        pipeline.run(prompt, max_tokens=8)
    finally:
        _ir.ratify_intent = original
        _pl.ratify_intent = original

    if not captured:
        return {"prompt": prompt, "outcome": "no_ratification_fired"}
    rec = captured[-1]
    rec["prompt"] = prompt
    return rec


def _summarize(rows: list[dict]) -> None:
    by_outcome: dict[str, list[float]] = {}
    skipped: dict[str, int] = {}
    for r in rows:
        if "score" not in r:
            skipped[r.get("outcome", "unknown")] = skipped.get(r.get("outcome", "unknown"), 0) + 1
            continue
        by_outcome.setdefault(r["outcome"], []).append(r["score"])
    if skipped:
        for reason, n in sorted(skipped.items()):
            print(f"    skipped[{reason}] = {n}")
    for outcome, scores in sorted(by_outcome.items()):
        if not scores:
            continue
        scores_sorted = sorted(scores)
        pct = lambda p: scores_sorted[max(0, int(len(scores_sorted) * p) - 1)]  # noqa: E731
        print(
            f"    {outcome:>12}  n={len(scores):>3}  "
            f"min={min(scores):+.4f}  p10={pct(0.10):+.4f}  "
            f"p25={pct(0.25):+.4f}  median={statistics.median(scores):+.4f}  "
            f"p75={pct(0.75):+.4f}  max={max(scores):+.4f}"
        )


def main() -> None:
    all_rows: list[dict] = []
    for split, path in SPLITS.items():
        cases = _load_cases(path)
        if not cases:
            print(f"[{split}] no cases at {path}")
            continue
        print(f"\n[{split}] {len(cases)} cases")
        rows = [_capture_score(c["prompt"]) for c in cases]
        all_rows.extend(rows)
        _summarize(rows)

    print("\n[all splits combined]")
    _summarize(all_rows)


if __name__ == "__main__":
    main()
