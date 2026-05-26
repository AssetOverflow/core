"""ADR-0057 §Replay-equivalence gate.

Given a proposed chain, run the cognition lane against the active
corpus *and* against a transient copy of the active corpus with the
proposed chain appended.  Compare metrics: any regression rejects
the proposal mechanically; equivalence makes the proposal eligible
for operator review.

Trust boundary
- The active corpus file bytes are NEVER touched by this gate,
  regardless of outcome.  The transient candidate corpus is written
  to an isolated path; the runtime's ``_corpus_index`` cache is
  swapped to load from that path for the candidate measurement,
  then restored.
- No background tasks, no async, no clock-time reads.  Synchronous
  swap-measure-restore.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from chat import teaching_grounding as _tg
from teaching.metric_set import MetricSet
from teaching.proposals import ReplayEvidence


# Metrics watched for regression.  Any metric whose candidate value
# is strictly less than the baseline value counts as a regression.
_WATCHED_METRICS = MetricSet(
    version=1,
    metrics=(
        "intent_accuracy",
        "surface_groundedness",
        "term_capture_rate",
        "versor_closure_rate",
    ),
)


@contextmanager
def _swap_corpus_path(temp_path: Path) -> Iterator[None]:
    """Temporarily point ``_corpus_index`` at *temp_path*.

    Clears the lru_cache before and after the swap so the runtime
    re-reads the corpus fresh in both directions.  The active
    corpus on disk is not touched.
    """
    real_path = _tg._CORPUS_PATH
    # ADR-0064 — the cognition corpus is one of several registered
    # teaching corpora.  When we swap it for replay, we must also
    # rewrite the registry entry's path AND invalidate the aggregated
    # index so surface composers re-read the swapped corpus.
    original_specs = _tg.TEACHING_CORPORA
    swapped_specs = tuple(
        _tg.TeachingCorpusSpec(
            corpus_id=s.corpus_id,
            path=temp_path if s.corpus_id == _tg.TEACHING_CORPUS_ID else s.path,
            pack_id=s.pack_id,
        )
        for s in original_specs
    )
    try:
        _tg._CORPUS_PATH = temp_path  # type: ignore[assignment]
        _tg.TEACHING_CORPORA = swapped_specs  # type: ignore[misc]
        _tg.clear_teaching_caches()
        yield
    finally:
        _tg._CORPUS_PATH = real_path  # type: ignore[assignment]
        _tg.TEACHING_CORPORA = original_specs  # type: ignore[misc]
        _tg.clear_teaching_caches()


def _run_cognition_public() -> dict[str, float]:
    """Run the public cognition split and return a metrics dict.

    Kept inside a function so import time stays cheap for callers
    that never trigger replay.
    """
    from evals.framework import get_lane, run_lane

    lane = get_lane("cognition")
    result = run_lane(lane, version="v1", split="public")
    out: dict[str, float] = {}
    for k in _WATCHED_METRICS.metrics:
        v = result.metrics.get(k)
        if isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def _build_candidate_corpus(
    active_corpus_path: Path, candidate_chain: dict[str, Any], dest: Path
) -> None:
    """Copy active corpus to *dest* and append one candidate line."""
    if active_corpus_path.exists():
        shutil.copyfile(active_corpus_path, dest)
    else:
        dest.write_text("", encoding="utf-8")
    subject = str(candidate_chain["subject"]).strip().lower()
    intent = str(candidate_chain["intent"]).strip().lower()
    connective = str(candidate_chain["connective"]).strip()
    obj = str(candidate_chain["object"]).strip().lower()
    chain_id = f"{intent}_{subject}_{connective}_{obj}_replay"
    entry = {
        "chain_id": chain_id,
        "subject": subject,
        "intent": intent,
        "connective": connective,
        "object": obj,
        "domains_subject_k": 2,
        "domains_object_k": 1,
        "provenance": "adr-0057:discovery_promoted:replay",
    }
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run_replay_equivalence(chain: dict[str, Any]) -> ReplayEvidence:
    """Run the gate.  Active corpus bytes byte-identical pre/post.

    Returns:
      ``ReplayEvidence(baseline=..., candidate=..., regressed_metrics=...,
        replay_equivalent=...)``
    """
    active_path = _tg._CORPUS_PATH
    active_bytes_before = active_path.read_bytes() if active_path.exists() else b""

    # Baseline: just run against the active corpus.  Caches are
    # cleared to make sure we read the current state of disk for
    # every registered teaching corpus (ADR-0064).
    _tg.clear_teaching_caches()
    baseline = _run_cognition_public()

    # Candidate: build a transient corpus with the chain appended
    # and point ``_corpus_index`` at it.
    with tempfile.TemporaryDirectory() as tmpdir:
        cand_path = Path(tmpdir) / "candidate_corpus.jsonl"
        _build_candidate_corpus(active_path, chain, cand_path)
        with _swap_corpus_path(cand_path):
            candidate = _run_cognition_public()

    regressed: list[str] = []
    for metric in _WATCHED_METRICS.metrics:
        b = baseline.get(metric)
        c = candidate.get(metric)
        if b is None or c is None:
            continue
        if c < b:
            regressed.append(metric)

    # Trust-boundary assertion: active file bytes unchanged.
    active_bytes_after = active_path.read_bytes() if active_path.exists() else b""
    if active_bytes_after != active_bytes_before:  # pragma: no cover — defensive
        raise RuntimeError(
            "replay gate mutated the active corpus — trust boundary violated"
        )

    return ReplayEvidence(
        baseline=baseline,
        candidate=candidate,
        regressed_metrics=tuple(sorted(regressed)),
        replay_equivalent=not regressed,
    )


# ---------------------------------------------------------------------------
# ADR-0163 Phase C — admissibility replay gate
# ---------------------------------------------------------------------------
#
# Extends the cognition-lane replay-equivalence gate with two additional
# evidence lanes that the ``wrong = 0`` doctrine names explicitly
# (ADR-0163 §Constraint #1):
#
#   - every named capability axis (G1..G5, S1) at its public v1 split
#   - the GSM8K train_sample at evals/gsm8k_math/train_sample/v1/
#
# If accepting a proposal would lift the wrong count on the train sample
# by one or more, the gate rejects with
# ``regressed_metrics=["gsm8k_train_sample_wrong_count"]``.  The
# downstream ``propose_from_candidate`` then auto-rejects the proposal
# before it ever reaches the operator queue.
#
# Phase C produces proposals only; the candidate run is identical to
# baseline because the recognizer is not yet wired into the
# candidate-graph (Phase D / E work).  Tests inject a fake candidate
# run to exercise the wrong-count invariant before the wiring exists.

import importlib
from dataclasses import dataclass


# Public v1 capability-axis lanes named by ADR-0163 §Phase A as the
# wrong=0 floor.  Stored as (lane_id, module_path) so the dispatch is
# inspectable and tests can stub one lane at a time.
_CAPABILITY_AXIS_LANES: tuple[tuple[str, str], ...] = (
    ("G1_verb_classes", "evals.math_capability_axes.G1_verb_classes.v1.runner"),
    ("G2_comparatives", "evals.math_capability_axes.G2_comparatives.v1.runner"),
    ("G3_numerics", "evals.math_capability_axes.G3_numerics.v1.runner"),
    ("G4_multi_clause", "evals.math_capability_axes.G4_multi_clause.v1.runner"),
    ("G5_aggregate", "evals.math_capability_axes.G5_aggregate.v1.runner"),
    ("S1_rate_events", "evals.math_capability_axes.S1_rate_events.v1.runner"),
)

_GSM8K_TRAIN_SAMPLE_MODULE = "evals.gsm8k_math.train_sample.v1.runner"


@dataclass(frozen=True, slots=True)
class AdmissibilityReplayEvidence:
    """Evidence record for the Phase C admissibility gate.

    Mirrors :class:`ReplayEvidence` for the cognition lane and bolts on
    per-axis + GSM8K train-sample wrong-count evidence.  ``as_dict``
    keeps the cognition-lane fields at the top level so the existing
    ``ProposalLog.record_replay`` consumer (which round-trips via
    ``replay_evidence``) can read them unchanged.
    """

    baseline: dict[str, float]
    candidate: dict[str, float]
    regressed_metrics: tuple[str, ...]
    replay_equivalent: bool
    capability_axes: dict[str, dict[str, int]]
    gsm8k_train_sample: dict[str, int]
    wrong_count_delta: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": dict(self.baseline),
            "candidate": dict(self.candidate),
            "regressed_metrics": list(self.regressed_metrics),
            "replay_equivalent": bool(self.replay_equivalent),
            "capability_axes": {
                k: dict(v) for k, v in self.capability_axes.items()
            },
            "gsm8k_train_sample": dict(self.gsm8k_train_sample),
            "wrong_count_delta": int(self.wrong_count_delta),
        }


# In-process baseline cache (ADR-0163 §Phase C performance note).
#
# Key: sha256 of the active teaching-corpus bytes (b"" when absent).
# Value: a frozen baseline tuple of (capability_axes, gsm8k_counts).
# The cognition baseline reuses :func:`_run_cognition_public` directly;
# it is comparatively cheap, so we don't cache it here.
#
# Invalidation: write the new digest -> evicts old key by lookup.  The
# cache lives in-process only; no filesystem persistence — Phase C
# does not introduce a new persistence path (ADR-0161 §1).
_BASELINE_CACHE: dict[str, dict[str, Any]] = {}


def _active_corpus_digest(active_corpus_path: Path | None) -> str:
    """sha256 of the active teaching-corpus bytes; '' when path absent."""
    path = active_corpus_path if active_corpus_path is not None else _tg._CORPUS_PATH
    if not path.exists():
        return ""
    import hashlib as _hashlib
    return _hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_report_counts(axis_id: str, report: dict[str, Any]) -> dict[str, int]:
    """Coerce a per-axis report to a uniform {correct,wrong,refused} dict.

    Each axis runner emits its own dialect of metrics:

    - G1 reports a top-level ``counts`` dict directly.
    - G2 / G4 / G5 / S1 report ``metrics={passed, wrong, cases_total, ...}``;
      ``correct`` maps to ``passed`` and ``refused`` is the remainder.
    - G3 reports ``metrics={solved_correct, solved_wrong, refused_as_expected, ...}``.

    The wrong count is the load-bearing field — the gate's invariant
    reads ``wrong`` only — but ``correct`` and ``refused`` round out
    the record so the evidence is auditable.
    """
    if "counts" in report:
        c = report["counts"]
        return {
            "correct": int(c.get("correct", 0)),
            "wrong": int(c.get("wrong", 0)),
            "refused": int(c.get("refused", 0)),
        }
    m = report.get("metrics", {})
    if "solved_wrong" in m or "solved_correct" in m:
        return {
            "correct": int(m.get("solved_correct", 0)),
            "wrong": int(m.get("solved_wrong", 0)),
            "refused": int(m.get("refused_as_expected", 0)),
        }
    cases_total = int(m.get("cases_total", 0))
    passed = int(m.get("passed", 0))
    wrong = int(m.get("wrong", 0))
    refused = max(0, cases_total - passed - wrong)
    return {"correct": passed, "wrong": wrong, "refused": refused}


def _run_capability_axes() -> dict[str, dict[str, int]]:
    """Run every capability-axis lane; return {axis_id: counts}.

    Each runner module exposes ``_load_cases`` and ``build_report``; we
    call them directly to avoid the report-on-disk side effect of the
    runner ``main()`` entrypoint.  The capability lanes are deterministic
    against the current commit SHA.
    """
    out: dict[str, dict[str, int]] = {}
    for axis_id, module_path in _CAPABILITY_AXIS_LANES:
        mod = importlib.import_module(module_path)
        lc_args = mod._load_cases.__code__.co_argcount
        br_args = mod.build_report.__code__.co_argcount
        cases = mod._load_cases(mod._CASES_PATH) if lc_args == 1 else mod._load_cases()
        report = mod.build_report(cases) if br_args >= 1 else mod.build_report()
        out[axis_id] = _normalize_report_counts(axis_id, report)
    return out


def _run_gsm8k_train_sample() -> dict[str, int]:
    """Run the GSM8K train-sample lane; return counts."""
    mod = importlib.import_module(_GSM8K_TRAIN_SAMPLE_MODULE)
    cases = mod._load_cases(mod._CASES_PATH)
    report = mod.build_report(cases)
    return _normalize_report_counts("gsm8k_train_sample", report)


def _wrong_count_delta(
    baseline: dict[str, int], candidate: dict[str, int]
) -> int:
    """Positive iff the candidate increased the wrong count."""
    return int(candidate.get("wrong", 0)) - int(baseline.get("wrong", 0))


def run_admissibility_replay_gate(
    spec: Any,
    *,
    active_corpus_path: Path | None = None,
    _capability_axes_runner: Any = None,
    _gsm8k_runner: Any = None,
    _cognition_runner: Any = None,
) -> "AdmissibilityReplayEvidence":
    """Run the Phase C admissibility gate against *spec*.

    The gate runs three evidence lanes:

      1. The cognition lane (inherited from
         :func:`run_replay_equivalence`).
      2. Every capability axis (G1..G5, S1) at its public v1 split.
      3. The GSM8K train_sample at v1.

    For each lane the BASELINE run is cached in-process keyed on the
    active teaching-corpus digest.  The first proposal pays the full
    baseline cost; subsequent proposals against the same corpus reuse
    it.  The CANDIDATE run is computed live every time — no candidate
    caching.

    Phase C wiring of the recognizer into the candidate-graph has not
    landed (that is Phase D / E work).  Until it does, the candidate
    run produces the same counts as the baseline.  The wrong-count
    invariant is therefore enforceable by simulating an elevated
    candidate count, which is how the regression test in
    ``test_admissibility_replay_gate.py`` exercises this path.

    Test hooks ``_capability_axes_runner``, ``_gsm8k_runner``, and
    ``_cognition_runner`` exist for unit tests to inject baseline or
    candidate counts without re-running real eval lanes.  They are
    private and not part of the public contract.

    ``replay_equivalent`` is True iff:
      - the cognition lane's ``regressed_metrics`` is empty,
      - every capability axis reports ``wrong == 0``,
      - the GSM8K train_sample's ``wrong`` count did not increase.
    """
    capability_axes_runner = _capability_axes_runner or _run_capability_axes
    gsm8k_runner = _gsm8k_runner or _run_gsm8k_train_sample
    cognition_runner = _cognition_runner or _run_cognition_public

    digest = _active_corpus_digest(active_corpus_path)
    cached = _BASELINE_CACHE.get(digest)
    if cached is None:
        baseline_capability = capability_axes_runner()
        baseline_gsm8k = gsm8k_runner()
        _BASELINE_CACHE[digest] = {
            "capability_axes": baseline_capability,
            "gsm8k_train_sample": baseline_gsm8k,
        }
    else:
        baseline_capability = cached["capability_axes"]
        baseline_gsm8k = cached["gsm8k_train_sample"]

    # Cognition lane runs live (its baseline is cheap and its caches
    # are managed by chat.teaching_grounding).
    _tg.clear_teaching_caches()
    cognition_baseline = cognition_runner()

    # Candidate runs.  Phase C ships no candidate-graph wiring, so
    # the live candidate run produces baseline-equivalent counts.
    candidate_capability = capability_axes_runner()
    candidate_gsm8k = gsm8k_runner()
    cognition_candidate = cognition_runner()

    # Cognition regression detection — same logic as run_replay_equivalence.
    regressed: list[str] = []
    for metric in _WATCHED_METRICS.metrics:
        b = cognition_baseline.get(metric)
        c = cognition_candidate.get(metric)
        if b is None or c is None:
            continue
        if c < b:
            regressed.append(metric)

    # Wrong-count invariant on GSM8K train_sample.
    wrong_delta = _wrong_count_delta(baseline_gsm8k, candidate_gsm8k)
    if wrong_delta > 0:
        regressed.append("gsm8k_train_sample_wrong_count")

    # Capability-axis wrong floor.  Any axis whose candidate wrong>0
    # is a regression.  G3 numerics already carries 6 expected-refusal
    # cases that count as "correct" in the runner's verdict map, so
    # this guard reads the wrong count directly.
    capability_wrong_axes: list[str] = []
    for axis_id, counts in candidate_capability.items():
        if counts["wrong"] > 0:
            capability_wrong_axes.append(axis_id)
    if capability_wrong_axes:
        for axis_id in capability_wrong_axes:
            regressed.append(f"capability_axis_wrong:{axis_id}")

    return AdmissibilityReplayEvidence(
        baseline=cognition_baseline,
        candidate=cognition_candidate,
        regressed_metrics=tuple(sorted(set(regressed))),
        replay_equivalent=not regressed,
        capability_axes=candidate_capability,
        gsm8k_train_sample=candidate_gsm8k,
        wrong_count_delta=wrong_delta,
    )


__all__ = [
    "AdmissibilityReplayEvidence",
    "run_admissibility_replay_gate",
    "run_replay_equivalence",
]
