"""ADR-0184 S4b — deterministic candidate-trace canonicalization and checks.

One canonical trace per corpus problem captures everything the equivalence proof
needs:

* the semantic worlds the boundary enumerates (provenance);
* the candidates it emits — values, order, AND duplicate multiplicity;
* the pooled candidate set and each candidate's commit-eligibility class
  (``complete`` / ``exempt`` / ``None``);
* the resolutions (``compose_accumulation``, ``resolve_pooled``), including
  refusals (``None`` — fail-closed is part of the contract being pinned).

Traces are pure data (sorted keys, fixed separators), so the corpus-level SHA-256
is a deterministic fingerprint of derivation-lane behavior.  The committed
artifact under ``v1/`` is the stable reference: it pins the behavior proven
byte-equal to the pre-ledger legacy path by the #684/#685 cross-tree
differentials.  Comparing live traces against it is therefore NOT a
self-comparison — the reference is frozen evidence, the live run is the code
under test.

This module also re-derives the pool's commit law from trace content
(:func:`authority_violations`) so a bypass of verifier/pool authority is
*detectable from the trace itself*, and ties every emitted candidate back to its
world via the S4b faithfulness checker
(:func:`generate.derivation.state.provenance.faithfulness_violations`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from generate.derivation.accumulate import accumulation_candidates, compose_accumulation
from generate.derivation.model import GroundedDerivation
from generate.derivation.pool import pooled_candidates, resolve_pooled
from generate.derivation.state.model import SemanticLedger
from generate.derivation.state.provenance import faithfulness_violations
from generate.derivation.state.replay import replay_accumulation_ledger
from generate.derivation.state.source import (
    accumulation_ledger_worlds,
    semantic_state_candidates,
)
from generate.derivation.verify import Resolution, classify_derivation

_EQUIVALENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _EQUIVALENCE_DIR.parent.parent.parent
EXPECTED_TRACES_PATH = _EQUIVALENCE_DIR / "v1" / "expected_traces.jsonl"
MANIFEST_PATH = _EQUIVALENCE_DIR / "v1" / "manifest.json"

# The corpus is every problem under evals/gsm8k_math/**/cases.jsonl, de-duplicated
# by exact text — the same definition the #684/#685 differentials used.
_CASES_GLOB = "evals/gsm8k_math/**/cases.jsonl"


def corpus_problems() -> tuple[str, ...]:
    """Every unique problem text in the corpus, sorted (deterministic order)."""
    problems: set[str] = set()
    for path in sorted(REPO_ROOT.glob(_CASES_GLOB)):
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                case = json.loads(line)
                text = case.get("problem") or case.get("question") or case.get("text")
                if text:
                    problems.add(text)
    return tuple(sorted(problems))


def canonical_derivation(derivation: GroundedDerivation) -> dict[str, Any]:
    return {
        "start": [derivation.start.value, derivation.start.unit, derivation.start.source_token],
        "steps": [
            [
                step.op,
                step.operand.value,
                step.operand.unit,
                step.operand.source_token,
                step.cue,
                step.comparative,
            ]
            for step in derivation.steps
        ],
        "answer": derivation.answer,
        "answer_unit": derivation.answer_unit,
    }


def canonical_resolution(resolution: Resolution | None) -> dict[str, Any] | None:
    if resolution is None:
        return None
    return {
        "answer": resolution.answer,
        "answer_unit": resolution.answer_unit,
        "derivation": canonical_derivation(resolution.derivation),
    }


def canonical_world(world: SemanticLedger) -> list[list[Any]]:
    return [
        [
            transition.op,
            transition.key.entity,
            transition.key.unit,
            transition.quantity.value,
            transition.quantity.unit,
            transition.quantity.source_token,
            transition.cue,
            transition.clause_index,
        ]
        for transition in world.transitions
    ]


def problem_sha(problem_text: str) -> str:
    return hashlib.sha256(problem_text.encode("utf-8")).hexdigest()


def problem_trace(problem_text: str) -> dict[str, Any]:
    """The canonical behavior trace for one problem (pure data, sorted keys)."""
    worlds = accumulation_ledger_worlds(problem_text)
    semantic = semantic_state_candidates(problem_text)
    pooled = pooled_candidates(problem_text)
    return {
        "problem_sha": problem_sha(problem_text),
        "preview": problem_text[:64],
        "worlds": [canonical_world(world) for world in worlds],
        "semantic": [canonical_derivation(d) for d in semantic],
        "wrapper_equal": accumulation_candidates(problem_text) == semantic,
        "compose": canonical_resolution(compose_accumulation(problem_text)),
        "pooled": [canonical_derivation(d) for d in pooled],
        "classifications": [classify_derivation(d, problem_text) for d in pooled],
        "resolution": canonical_resolution(resolve_pooled(problem_text)),
    }


def corpus_traces() -> list[dict[str, Any]]:
    """Canonical traces for the whole corpus, sorted by problem SHA."""
    traces = [problem_trace(text) for text in corpus_problems()]
    traces.sort(key=lambda trace: str(trace["problem_sha"]))
    return traces


def trace_line(trace: dict[str, Any]) -> str:
    """The canonical single-line JSON encoding (artifact + hashing format)."""
    return json.dumps(trace, sort_keys=True, separators=(",", ":"))


def traces_sha(traces: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for trace in traces:
        digest.update(trace_line(trace).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_expected_traces() -> list[dict[str, Any]]:
    with EXPECTED_TRACES_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def compare_traces(
    expected: list[dict[str, Any]], live: list[dict[str, Any]]
) -> tuple[str, ...]:
    """Every per-problem, per-dimension difference between two trace lists.

    Empty iff equivalent.  Dimension-labelled so a failure names what drifted
    (candidate values, order/multiplicity, classifications, refusals, ...).
    """
    differences: list[str] = []
    expected_by_sha = {str(t["problem_sha"]): t for t in expected}
    live_by_sha = {str(t["problem_sha"]): t for t in live}
    for sha in sorted(set(expected_by_sha) - set(live_by_sha)):
        differences.append(f"{sha[:16]}: problem missing from live corpus")
    for sha in sorted(set(live_by_sha) - set(expected_by_sha)):
        differences.append(f"{sha[:16]}: problem missing from expected artifact")
    for sha in sorted(set(expected_by_sha) & set(live_by_sha)):
        exp, liv = expected_by_sha[sha], live_by_sha[sha]
        for dimension in sorted(set(exp) | set(liv)):
            if exp.get(dimension) != liv.get(dimension):
                differences.append(
                    f"{sha[:16]} ({str(exp.get('preview', ''))[:40]!r}): "
                    f"{dimension} differs"
                )
    return tuple(differences)


def authority_violations(trace: dict[str, Any]) -> tuple[str, ...]:
    """Ways ``trace`` violates the verifier/pool commit law — empty iff lawful.

    Re-derives the *commit-licensing* direction of ``resolve_pooled`` from trace
    content alone, so a bypassed authority is detectable from the trace:

    * a resolution requires at least one ``complete``-classified pooled candidate
      (an exempt-only or unclassified pool must refuse);
    * a resolution requires agreement — every classified candidate's answer must
      match the committed answer (disagreement must refuse);
    * an empty pool must refuse (fail-closed).

    These are necessary conditions for any commit, not a re-implementation of the
    refusal side: a refusal (``resolution: null``) is always lawful here.  That
    asymmetry is deliberate — wrong=0 hazards live only on the commit side.
    """
    violations: list[str] = []
    resolution = trace.get("resolution")
    pooled = trace.get("pooled") or []
    classifications = trace.get("classifications") or []
    if resolution is None:
        return ()
    if not isinstance(resolution, dict):
        return (f"resolution has non-canonical type {type(resolution).__name__}",)
    if not pooled:
        violations.append("resolution committed from an empty pool (fail-closed broken)")
    if "complete" not in classifications:
        violations.append(
            "resolution committed without any 'complete'-classified candidate "
            "(exempt-only/unclassified commit — verifier/pool authority bypassed)"
        )
    committed_answer = resolution.get("answer")
    for candidate, kind in zip(pooled, classifications):
        if kind is None or not isinstance(candidate, dict):
            continue
        answer = candidate.get("answer")
        if (
            isinstance(answer, (int, float))
            and isinstance(committed_answer, (int, float))
            and round(float(answer), 9) != round(float(committed_answer), 9)
        ):
            violations.append(
                "resolution committed despite a disagreeing classified candidate "
                f"({answer!r} != {committed_answer!r})"
            )
            break
    return tuple(violations)


def replay_faithfulness_report(problem_text: str) -> tuple[str, ...]:
    """Faithfulness violations for every (world, replayed candidate) pair of a
    problem, plus structural consistency of the boundary enumeration itself."""
    violations: list[str] = []
    replayed: list[GroundedDerivation] = []
    for index, world in enumerate(accumulation_ledger_worlds(problem_text)):
        derivation = replay_accumulation_ledger(world)
        if derivation is None:
            # builder-produced worlds always replay today; a refusal here is a
            # structural change worth flagging loudly, not skipping silently.
            violations.append(f"world {index} refused replay")
            continue
        replayed.append(derivation)
        violations.extend(
            f"world {index}: {violation}"
            for violation in faithfulness_violations(world, derivation)
        )
    if tuple(replayed) != semantic_state_candidates(problem_text):
        violations.append("boundary candidates are not the in-order replay of the worlds")
    return tuple(violations)
