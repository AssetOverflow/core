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


__all__ = ["run_replay_equivalence"]
