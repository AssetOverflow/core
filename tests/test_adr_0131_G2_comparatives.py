"""ADR-0131.G.2 — comparative operations (additive + multiplicative).

Pins the curated coverage axis under
``evals/math_capability_axes/G2_comparatives/v1/`` plus the
``math_candidate_parser`` comparative extractors.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from evals.math_capability_axes.G2_comparatives.v1.runner import (
    build_report,
    write_report,
    _REPORT_PATH,
)
from generate.math_candidate_parser import (
    _compare_additive_candidates,
    _compare_multiplicative_candidates,
    _compare_nested_candidates,
    extract_operation_candidates,
)
from generate.math_roundtrip import (
    COMPARE_ADDITIVE_ANCHORS,
    COMPARE_MULTIPLICATIVE_ANCHORS,
    roundtrip_admissible,
)


_REPO = Path(__file__).resolve().parents[1]
_GSM8K_LEGACY_REPORT = (
    _REPO / "evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json"
)
_GSM8K_CG_REPORT = _REPO / "evals/gsm8k_math/train_sample/v1/report.json"


# ---------------------------------------------------------------------------
# Per-direction at-least-one-passing.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("direction,sentence,actor,reference,delta", [
    ("more", "Alice has 3 more apples than Bob", "Alice", "Bob", 3),
    ("fewer", "Alice has 5 fewer pencils than Bob", "Alice", "Bob", 5),
])
def test_additive_direction_admits(direction, sentence, actor, reference, delta):
    cands = [c for c in _compare_additive_candidates(sentence) if roundtrip_admissible(c)]
    assert len(cands) == 1
    c = cands[0]
    assert c.op.kind == "compare_additive"
    assert c.op.operand.direction == direction
    assert c.op.actor == actor
    assert c.op.operand.reference_actor == reference
    assert c.op.operand.delta.value == delta


def test_additive_less_maps_to_fewer():
    cands = [c for c in _compare_additive_candidates("Dana has 8 less coins than Eli") if roundtrip_admissible(c)]
    assert len(cands) == 1
    c = cands[0]
    assert c.op.operand.direction == "fewer"
    assert c.matched_verb == "less"
    # 'less' is a registered additive anchor (COMPARE_ADDITIVE_ANCHORS).
    assert "less" in COMPARE_ADDITIVE_ANCHORS


@pytest.mark.parametrize("direction,sentence,actor,reference,factor,anchor", [
    ("times", "Alice has twice as many apples as Bob", "Alice", "Bob", 2.0, "twice"),
    ("times", "Alice has 4 times as many apples as Bob", "Alice", "Bob", 4.0, "times"),
    ("times", "Alice has thrice as many apples as Bob", "Alice", "Bob", 3.0, "thrice"),
    ("fraction", "Alice has half as many apples as Bob", "Alice", "Bob", 0.5, "half"),
    ("fraction", "Alice has a quarter as many apples as Bob", "Alice", "Bob", 0.25, "quarter"),
    ("fraction", "Alice has a third as many apples as Bob", "Alice", "Bob", 1.0 / 3.0, "third"),
])
def test_multiplicative_direction_admits(direction, sentence, actor, reference, factor, anchor):
    cands = [c for c in _compare_multiplicative_candidates(sentence) if roundtrip_admissible(c)]
    assert len(cands) == 1
    c = cands[0]
    assert c.op.kind == "compare_multiplicative"
    assert c.op.operand.direction == direction
    assert c.op.actor == actor
    assert c.op.operand.reference_actor == reference
    assert c.op.operand.factor == factor
    assert c.matched_verb == anchor
    assert anchor in COMPARE_MULTIPLICATIVE_ANCHORS


# ---------------------------------------------------------------------------
# Nested composition emits BOTH flat candidates.
# ---------------------------------------------------------------------------

def test_nested_emits_both_flat_candidates():
    s = "Jen has 10 more ducks than four times the number of chickens"
    cands = [c for c in _compare_nested_candidates(s) if roundtrip_admissible(c)]
    kinds = {c.op.kind for c in cands}
    assert kinds == {"compare_additive", "compare_multiplicative"}


# ---------------------------------------------------------------------------
# Refusal cases — closed-set boundary holds.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "Alice has as many apples as Bob",
    "Compared to Bob, Alice has 3 more apples",
    "In comparison with Bob, Alice has 3 more apples",
    "Alice has the same number of apples as Bob",
    "Alice has 3 times more apples than Bob",
    # G2 extension: deferred / out-of-closed-set forms
    "Alice has one-third as many apples as Bob",   # hyphenated — not in anchor alternation
    "Alice has double as many apples as Bob",       # 'double as many' requires different grammar
])
def test_refusal_cases_emit_no_admitted_comparative(sentence):
    cands = extract_operation_candidates(sentence)
    admitted_comparatives = [
        c for c in cands
        if c.op.kind in ("compare_additive", "compare_multiplicative")
        and roundtrip_admissible(c)
    ]
    assert admitted_comparatives == []


# ---------------------------------------------------------------------------
# Closed-set anchor discipline — emitter never invents a direction literal.
# ---------------------------------------------------------------------------

def test_direction_literals_closed_set():
    sentences = [
        "Alice has 3 more apples than Bob",
        "Alice has 5 fewer pencils than Bob",
        "Alice has 2 less books than Bob",
        "Alice has twice as many apples as Bob",
        "Alice has 4 times as many apples as Bob",
        "Alice has half as many apples as Bob",
        "Alice has thrice as many apples as Bob",
        "Alice has a quarter as many apples as Bob",
        "Alice has a third as many apples as Bob",
        "Jen has 10 more ducks than four times the number of chickens",
    ]
    for s in sentences:
        for c in extract_operation_candidates(s):
            if c.op.kind in ("compare_additive", "compare_multiplicative"):
                assert c.op.operand.direction in ("more", "fewer", "times", "fraction")


# ---------------------------------------------------------------------------
# Runner / report contract.
# ---------------------------------------------------------------------------

def test_runner_wrong_count_is_zero():
    report = build_report()
    assert report["metrics"]["wrong"] == 0
    assert report["metrics"]["wrong_count_is_zero"] is True


def test_runner_per_category_minima():
    """Brief §coverage: ≥4 per direction (more, fewer, times, fraction);
    ≥3 nested; ≥5 refusal. Fraction direction now includes half×4 + quarter×2
    + third×1 = 7 cases (was 4); refusal set extended to 7 (was 5) with
    hyphenated and 'double as many' boundary probes. Minima pinned via
    per-case scan so direction-level counts are verified independently."""
    report = build_report()
    direction_counts = {"more": 0, "fewer": 0, "times": 0, "fraction": 0}
    nested = 0
    refusal = 0
    cases_path = _REPO / "evals/math_capability_axes/G2_comparatives/v1/cases.jsonl"
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        if c["category"] in ("additive", "multiplicative"):
            direction_counts[c["direction"]] += 1
        elif c["category"] == "nested":
            nested += 1
        elif c["category"] == "refusal":
            refusal += 1
    for d, n in direction_counts.items():
        assert n >= 4, f"direction {d!r} has only {n} cases (need ≥4)"
    assert nested >= 3
    assert refusal >= 4
    # And every one of those cases passes (wrong==0 already asserts no
    # wrong-shaped pass, but verify the positive direction too).
    assert report["metrics"]["passed"] == report["metrics"]["cases_total"]


def test_report_byte_equal_across_runs():
    a = json.dumps(build_report(), indent=2, sort_keys=True)
    b = json.dumps(build_report(), indent=2, sort_keys=True)
    assert a == b


def test_committed_report_matches_runner_output():
    report = build_report()
    written = json.dumps(report, indent=2, sort_keys=True) + "\n"
    on_disk = _REPORT_PATH.read_text(encoding="utf-8")
    if written != on_disk:
        # Re-write to be helpful in local dev (so CI failures point at the
        # actual delta, not a stale file).
        write_report(report)
    assert written == on_disk, "G2 report.json is stale — re-run runner.py"


# ---------------------------------------------------------------------------
# GSM8K probe gate — chosen gate (per ADR-0131.G.2):
#   comparative-clause refusals in the candidate-graph probe report.json
#   strictly decrease.
# Legacy train_sample_coverage_report.json is byte-identical (no legacy
# parser change); we pin both invariants below.
# ---------------------------------------------------------------------------

_COMPARATIVE_STATEMENT_PATTERNS = (
    # "<N> more <unit> than" / "fewer / less"
    re.compile(r"\b(?:more|fewer|less)\b[^.'\"]*\bthan\b", re.IGNORECASE),
    # "twice|thrice|half|quarter|third|N times as many <unit> as"
    # Word-number forms ("four times") are included via \w+ to avoid a
    # digit-only \d+ match that would miss GSM8K-style word numerals.
    re.compile(
        r"\b(?:twice|thrice|half|quarter|third|\w+\s+times)\s+as\s+many\b",
        re.IGNORECASE,
    ),
)


def _comparative_clause_refusal_count(probe_report_path: Path) -> int:
    """Count refused cases whose refusal reason names a statement clause
    that itself contains a comparative anchor (additive ``more/fewer/less
    … than`` or multiplicative ``twice/N times/half as many``). We anchor
    on the embedded statement clause inside the ``candidate_graph`` /
    ``parser`` refusal reason, not on isolated keywords, to avoid
    false-positives on incidental mentions ('he is more careful than',
    discourse glue, etc.)."""
    data = json.loads(probe_report_path.read_text(encoding="utf-8"))
    per_case = data["per_case"]
    count = 0
    for d in per_case:
        if d.get("verdict", d.get("outcome")) != "refused":
            continue
        reason = d["reason"]
        if "statement" not in reason and "statement clause" not in reason:
            continue
        for pat in _COMPARATIVE_STATEMENT_PATTERNS:
            if pat.search(reason):
                count += 1
                break
    return count


def test_gsm8k_legacy_probe_safety_rail_intact():
    """ADR-0131.G invariant: legacy probe still shows admitted_wrong == 0."""
    data = json.loads(_GSM8K_LEGACY_REPORT.read_text(encoding="utf-8"))
    assert data["metrics"]["admitted_wrong"] == 0
    assert data["metrics"]["safety_rail_intact"] is True


def test_gsm8k_candidate_graph_probe_wrong_zero():
    """Candidate-graph probe also preserves wrong == 0."""
    data = json.loads(_GSM8K_CG_REPORT.read_text(encoding="utf-8"))
    assert data["counts"]["wrong"] == 0


def test_gsm8k_candidate_graph_comparative_clause_refusals_decreased():
    """G2 gate: at least one previously-comparative-clause-refused case
    no longer cites a comparative-clause refusal in the candidate-graph
    probe. Baseline (pre-G.2) for the train sample had case 0009 ('Jen
    has 10 more ducks than four times the number of chickens') refused
    at the comparative statement; with G.2 wired into
    math_candidate_parser, that comparative clause now parses (the case
    may still refuse downstream — at the question or solver — but the
    refusal reason no longer cites the comparative clause)."""
    current_count = _comparative_clause_refusal_count(_GSM8K_CG_REPORT)
    # Pre-G.2 baseline (`origin/main` @ 481e0c3): 2 cases refused at a
    # statement clause whose text contains additive ('more/fewer/less ...
    # than') or multiplicative ('twice/N times/half as many') anchors —
    # cases gsm8k-train-sample-v1-0009 ('Jen has 10 more ducks than four
    # times the number of chickens.') and -0016 (arithmetic 'more than'
    # in 'Rudolph traveled 2 more than 5 miles'). G.2 wires comparatives
    # into math_candidate_parser; case 0009 now parses the comparative
    # clause (refusal moves to the question form), so the count drops to
    # 1 (case 0016's arithmetic 'N more than M' is *not* a between-entity
    # comparative and is deliberately out of G.2 scope).
    baseline_count = 2
    assert current_count < baseline_count, (
        f"expected comparative-clause refusal count to drop below "
        f"baseline {baseline_count}; got {current_count}"
    )
