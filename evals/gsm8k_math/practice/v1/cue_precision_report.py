"""ADR-0177 CP-2a — the cue-precision measurement.

Trains the CP-1 ledger over the gold-labelled sealed cases (train_sample + the
ADR-0163-F additive practice set) using the *real* search candidate enumerators,
then reports each ``(cue, op, unit_shape)`` pattern's commitment precision via the
pinned conservative floor.

This is the diagnostic the cue-precision thesis rests on: it shows which cues are
*reliable* (high floor over enough committed trials) versus which are noise. CP-2b
consults this table to decide which patterns a self-verifying chain may be trusted
on; until then it is a read-only measurement that changes no search/gate behaviour
(serving stays ``3/47/0``).

Deterministic and replay-stable: fixed case order, fixed enumerator order, the
ledger's canonical sorted storage.
"""

from __future__ import annotations

from generate.cue_precision.ledger import CuePrecisionLedger
from generate.cue_precision.trainer import TrainingCase, train_from_cases
from generate.derivation.multistep import candidate_chains
from generate.derivation.search import _sentence_candidates
from evals.gsm8k_math.practice.v1.runner import _load_practice_cases
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases

# The real readings the search weighs: the multiplicative per-sentence products
# (the lane the practice scorer attempts) and the multistep principled chains
# (which carry the additive candidates the ADR-0163-F set exercises). Fixed order.
_ENUMERATORS = (_sentence_candidates, candidate_chains)


def _training_cases() -> list[TrainingCase]:
    """All gold-labelled sealed cases, train_sample first then practice. Stable."""
    cases: list[TrainingCase] = []
    for record in _load_cases(_CASES_PATH):
        cases.append((record["question"], float(record["answer_numeric"])))
    for record in _load_practice_cases():
        cases.append((record["question"], float(record["answer_numeric"])))
    return cases


def build_cue_precision_ledger() -> CuePrecisionLedger:
    """Train the ledger over every sealed case with the real enumerators."""
    return train_from_cases(_training_cases(), _ENUMERATORS)


def format_reliability_table(ledger: CuePrecisionLedger) -> str:
    """A deterministic Markdown table of every learned pattern, sorted canonically."""
    lines = [
        "| cue | op | unit_shape | correct | wrong | committed | reliability |",
        "|-----|----|-----------|--------:|------:|----------:|------------:|",
    ]
    for tally in ledger.tallies:  # already canonically sorted
        p = tally.pattern
        lines.append(
            f"| {p.cue} | {p.op} | {p.unit_shape} | {tally.correct} | "
            f"{tally.wrong} | {tally.committed} | {tally.reliability:.4f} |"
        )
    return "\n".join(lines)


def main() -> int:
    ledger = build_cue_precision_ledger()
    cases = _training_cases()
    print(f"cue-precision ledger trained over {len(cases)} sealed cases")
    print(f"distinct (cue, op, unit_shape) patterns: {len(ledger.tallies)}")
    print(format_reliability_table(ledger))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
