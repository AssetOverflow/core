"""ADR-0131.G.4 — multi-clause composition (conjoined subjects, conjoined
objects, embedded quantifiers, conjoined embedded quantifiers).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from evals.math_capability_axes.G4_multi_clause.v1.runner import (
    _REPORT_PATH,
    build_report,
    write_report,
)
from generate.math_candidate_parser import (
    CandidateInitial,
    _conj_embedded_admitted,
    _conj_object_admitted,
    _conj_subject_each_admitted,
    _embedded_quantifier_admitted,
    extract_initial_candidates,
)


_REPO = Path(__file__).resolve().parents[1]
_GSM8K_LEGACY_REPORT = (
    _REPO / "evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json"
)
_GSM8K_CG_REPORT = _REPO / "evals/gsm8k_math/train_sample/v1/report.json"


# ---------------------------------------------------------------------------
# Per-shape at-least-one-passing.
# ---------------------------------------------------------------------------

def test_conj_subject_each_emits_two_initials():
    cands = _conj_subject_each_admitted("Aaron and Carson each saved up 40 dollars")
    assert {(c.initial.entity, c.initial.quantity.value, c.initial.quantity.unit)
            for c in cands} == {
        ("Aaron", 40, "dollars"),
        ("Carson", 40, "dollars"),
    }


def test_conj_subject_each_with_kin_appositive():
    cands = _conj_subject_each_admitted(
        "Aaron and his brother Carson each saved up 40 dollars to go to dinner"
    )
    entities = sorted(c.initial.entity for c in cands)
    assert entities == ["Aaron", "Carson"]


def test_conj_object_emits_two_initials():
    cands = _conj_object_admitted("Francine has 5 boxes and 7 crayons")
    assert {(c.initial.entity, c.initial.quantity.value, c.initial.quantity.unit)
            for c in cands} == {
        ("Francine", 5, "boxes"),
        ("Francine", 7, "crayons"),
    }


def test_embedded_quantifier_emits_product():
    cands = _embedded_quantifier_admitted("Ella has 4 bags with 20 apples in each bag")
    assert len(cands) == 1
    c = cands[0]
    assert c.initial.entity == "Ella"
    assert c.initial.quantity.value == 80
    assert c.initial.quantity.unit == "apples"


def test_embedded_quantifier_optional_container2():
    """`in each` without re-naming the container is admitted."""
    cands = _embedded_quantifier_admitted("Maya has 3 jars with 12 cookies in each")
    assert len(cands) == 1
    assert cands[0].initial.quantity.value == 36


def test_conj_embedded_emits_sum():
    cands = _conj_embedded_admitted(
        "Ella has 4 bags with 20 apples in each bag and 6 bags with 25 apples in each bag"
    )
    assert len(cands) == 1
    c = cands[0]
    assert c.initial.entity == "Ella"
    assert c.initial.quantity.value == 230  # 4*20 + 6*25
    assert c.initial.quantity.unit == "apples"


# ---------------------------------------------------------------------------
# Refusal probes — closed-set / wrong==0 boundary holds.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sentence,why", [
    ("Aaron and Carson saved 40 dollars together",
     "collective reading via 'together' — distributive 'each' required"),
    ("Aaron and Carson each saved 40 dollars altogether",
     "'altogether' contradicts distributive 'each'"),
    ("Aaron and Bob and Carson each have 5 apples",
     "three-way conjunction is out of closed-set shape"),
    ("Aaron has 5 apples and Bob has 3 marbles",
     "cross-entity conjunction (both halves carry verb+subject)"),
    ("Ella has 4 bags with 20 apples in each box",
     "ambiguous 'each' scope: container2 disagrees with leading container"),
    ("Ella has 4 bags with 20 apples in each bag and 6 crates with 25 pears in each crate",
     "mixed-unit conjoined embedded sum is undefined"),
    ("Aaron has 5 apples. He gives 2 to Bob",
     "cross-sentence coreference — pronoun across sentence boundary"),
    ("Sam has 5 dimes and 3 dimes",
     "same-unit conjoined object — overwrite-on-collision would drop first conjunct"),
])
def test_refusal_cases_emit_no_admitted_multi_clause(sentence, why):
    """Closed-set boundary: every documented refusal probe must emit
    zero admitted multi-clause candidates."""
    # We check each extractor independently rather than a union; if ANY
    # multi-clause extractor admits, the case is breached.
    each = _conj_subject_each_admitted(sentence)
    obj = _conj_object_admitted(sentence)
    emb = _embedded_quantifier_admitted(sentence)
    conj_emb = _conj_embedded_admitted(sentence)
    admitted = each + obj + emb + conj_emb
    assert admitted == [], (
        f"refusal probe breached ({why!r}): admitted "
        f"{[(c.initial.entity, c.initial.quantity.value, c.initial.quantity.unit) for c in admitted]}"
    )


# ---------------------------------------------------------------------------
# Distributive-`each` policy — explicit adversarial probe (brief constraint).
# ---------------------------------------------------------------------------

def test_refuses_each_with_together():
    """Distributive-only: 'each ... together' is a contradiction."""
    assert _conj_subject_each_admitted(
        "Aaron and Carson each saved 40 dollars together"
    ) == []


def test_collective_without_each_refuses():
    """No 'each' → no distributive emission."""
    assert _conj_subject_each_admitted(
        "Aaron and Carson saved 40 dollars together"
    ) == []


# ---------------------------------------------------------------------------
# Cross-sentence coreference stays refused.
# ---------------------------------------------------------------------------

def test_cross_sentence_pronoun_refuses_multi_clause():
    """The brief explicitly defers cross-sentence coreference. None of
    the multi-clause extractors should fire on a two-sentence input."""
    s = "Aaron has 5 apples. He gives 2 to Bob"
    assert _conj_subject_each_admitted(s) == []
    assert _conj_object_admitted(s) == []
    assert _embedded_quantifier_admitted(s) == []
    assert _conj_embedded_admitted(s) == []


# ---------------------------------------------------------------------------
# Runner / report contract.
# ---------------------------------------------------------------------------

def test_runner_wrong_count_is_zero():
    report = build_report()
    assert report["metrics"]["wrong"] == 0
    assert report["metrics"]["wrong_count_is_zero"] is True


def test_runner_per_shape_minima():
    """Brief §coverage: ≥6 per shape + ≥6 refusal probes."""
    cases_path = (
        _REPO / "evals/math_capability_axes/G4_multi_clause/v1/cases.jsonl"
    )
    by_cat: dict[str, int] = {}
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
    for cat in (
        "conj_subject_each", "conj_object",
        "embedded_quantifier", "conj_embedded",
    ):
        assert by_cat.get(cat, 0) >= 6, f"{cat} has only {by_cat.get(cat,0)} (need ≥6)"
    assert by_cat.get("refusal", 0) >= 6


def test_report_byte_equal_across_runs():
    a = json.dumps(build_report(), indent=2, sort_keys=True)
    b = json.dumps(build_report(), indent=2, sort_keys=True)
    assert a == b


def test_committed_report_matches_runner_output():
    report = build_report()
    written = json.dumps(report, indent=2, sort_keys=True) + "\n"
    on_disk = _REPORT_PATH.read_text(encoding="utf-8")
    if written != on_disk:
        write_report(report)
    assert written == on_disk, "G4 report.json is stale — re-run runner.py"


# ---------------------------------------------------------------------------
# extract_initial_candidates wiring — multi-clause shapes are reachable
# via the public entry point (the binding-graph consumes through this).
# ---------------------------------------------------------------------------

def test_extract_initial_candidates_includes_conj_each():
    cands = extract_initial_candidates("Alice and Bob each have 5 apples")
    entities = sorted(c.initial.entity for c in cands)
    assert "Alice" in entities and "Bob" in entities


def test_extract_initial_candidates_includes_embedded():
    cands = extract_initial_candidates("Ella has 4 bags with 20 apples in each bag")
    values = {c.initial.quantity.value for c in cands}
    assert 80 in values, f"expected derived product 80 to appear; got {values}"


# ---------------------------------------------------------------------------
# GSM8K-probe gate — chosen gate (per ADR-0131.G.4):
#   multi-clause statement-clause refusals in the candidate-graph probe
#   strictly decrease (legacy probe stays byte-identical — legacy parser
#   untouched).
# ---------------------------------------------------------------------------

_MULTI_CLAUSE_STATEMENT_PATTERNS = (
    # conjoined subject + each / distributive
    re.compile(r"\beach\s+(?:saved|have|has|had|earned|got|received|bought|made|paid)\b", re.IGNORECASE),
    # embedded quantifier / conjoined embedded
    re.compile(r"\bwith\s+\d+\s+\w+\s+in\s+each\b", re.IGNORECASE),
    # conjoined object NPs (a count, a unit, 'and', another count + unit)
    re.compile(r"\bhas\s+\d+\s+\w+\s+and\s+\d+\s+\w+\b", re.IGNORECASE),
)


def _multi_clause_statement_refusal_count(probe_report_path: Path) -> int:
    """Count refused cases citing a statement-clause refusal whose
    embedded sentence text matches a multi-clause anchor pattern."""
    data = json.loads(probe_report_path.read_text(encoding="utf-8"))
    count = 0
    for d in data["per_case"]:
        if d.get("verdict", d.get("outcome")) != "refused":
            continue
        reason = d["reason"]
        if "statement" not in reason:
            continue
        for pat in _MULTI_CLAUSE_STATEMENT_PATTERNS:
            if pat.search(reason):
                count += 1
                break
    return count


def test_gsm8k_legacy_probe_safety_rail_intact():
    data = json.loads(_GSM8K_LEGACY_REPORT.read_text(encoding="utf-8"))
    assert data["metrics"]["admitted_wrong"] == 0
    assert data["metrics"]["safety_rail_intact"] is True


def test_gsm8k_candidate_graph_probe_wrong_zero():
    data = json.loads(_GSM8K_CG_REPORT.read_text(encoding="utf-8"))
    assert data["counts"]["wrong"] == 0


def test_gsm8k_candidate_graph_multi_clause_refusals_decreased():
    """G.4 gate: multi-clause statement-clause refusal count strictly
    decreases in the candidate-graph probe. Pre-G.4 baseline
    (origin/main @ 481e0c3) included case `gsm8k-train-sample-v1-0042`
    ('Ella has 4 bags with 20 apples in each bag and six bags with 25
    apples in each bag.') refusing at the statement clause; with G.4
    the conjoined-embedded shape parses and the refusal class moves
    downstream (to the question layer).
    """
    current = _multi_clause_statement_refusal_count(_GSM8K_CG_REPORT)
    # Baseline measured on origin/main 481e0c3 with the same matcher:
    # 2 cases — gsm8k-train-sample-v1-0026 ('Aaron and his brother Carson
    # each saved up $40 ...') and -0042 ('Ella has 4 bags with 20 apples
    # in each bag and six bags with 25 apples in each bag.'). After G.4:
    # case 0042 parses (the conjoined-embedded shape is now admissible)
    # and refuses downstream at the question layer; case 0026 stays
    # refused because the '$' currency prefix blocks the value slot
    # (deferred to the G.3 numeric-literals axis). Expected current=1.
    baseline = 2
    assert current < baseline, (
        f"expected multi-clause statement-refusal count to drop below "
        f"baseline {baseline}; got {current}"
    )
