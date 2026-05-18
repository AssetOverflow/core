"""ADR-0055 Phase B — DiscoveryCandidate emission + sink contracts.

Pinned contracts:

  - ``extract_discovery_candidates`` is pure and deterministic; same
    inputs ⇒ identical ``candidate_id``.
  - The ``would_have_grounded`` trigger fires only when ALL of:
    fall-through (grounding_source == "none"), intent ∈ {CAUSE,
    VERIFICATION}, subject lemma is a pack lemma, (subject, intent)
    is NOT in the active corpus.
  - Candidate emission **never** mutates the active teaching corpus
    or runtime state.
  - Sink is opt-in.  No sink attached ⇒ behaviour identical to pre-B.
  - ``DiscoveryMonthlyFileSink`` rolls over by month; previous file
    is closed cleanly.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import pytest

from chat.runtime import ChatRuntime
from generate.intent import IntentTag
from teaching.discovery import (
    DiscoveryCandidate,
    extract_discovery_candidates,
    format_candidate_jsonl,
)
from teaching.discovery_sink import (
    DiscoveryBufferSink,
    DiscoveryMonthlyFileSink,
)


# ---------------------------------------------------------------------------
# Synthetic TurnEvent shim (avoids needing a full runtime turn just to test
# the pure rule firing)
# ---------------------------------------------------------------------------


class _TE:
    def __init__(
        self,
        *,
        grounding_source: str = "none",
        trace_hash: str = "abcd",
        refusal_emitted: bool = False,
        hedge_injected: bool = False,
    ) -> None:
        self.grounding_source = grounding_source
        self.trace_hash = trace_hash
        self.refusal_emitted = refusal_emitted
        self.hedge_injected = hedge_injected
        self.verdicts = None


# ---------------------------------------------------------------------------
# extract_discovery_candidates — pure predicate
# ---------------------------------------------------------------------------


def test_fires_on_would_have_grounded_for_cause_on_unknown_pack_lemma() -> None:
    """``principle`` is a pack lemma; (principle, cause) is NOT in the
    active cognition corpus.  ``judgment`` was the historical fixture
    here, but the epistemology v1 curriculum unit (commit ``2acf71f``)
    added ``cause_judgment_requires_wisdom`` — so ``principle`` is the
    new still-cold cognition exemplar.  If a future curriculum unit
    ratifies a ``(principle, *)`` chain, this test pytest-skips and the
    fixture should rotate to the next cold lemma."""
    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    assert "principle" in _pack_index()
    if ("principle", "cause") in _corpus_index():
        pytest.skip("principle/cause is in the active corpus; pick another fixture")

    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.CAUSE,
        "principle",
    )
    assert len(cands) == 1
    c = cands[0]
    assert c.trigger == "would_have_grounded"
    assert c.proposed_chain["subject"] == "principle"
    assert c.proposed_chain["intent"] == "cause"
    assert c.proposed_chain["connective"] is None
    assert c.proposed_chain["object"] is None
    assert c.pack_consistent is True
    assert c.boundary_clean is True
    assert c.review_state == "unreviewed"


def test_does_not_fire_when_grounding_source_is_pack() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="pack"),
        IntentTag.CAUSE,
        "principle",
    )
    assert cands == ()


def test_does_not_fire_when_grounding_source_is_teaching() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="teaching"),
        IntentTag.CAUSE,
        "principle",
    )
    assert cands == ()


def test_does_not_fire_for_definition_intent() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.DEFINITION,
        "principle",
    )
    assert cands == ()


def test_does_not_fire_for_unknown_intent() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.UNKNOWN,
        "principle",
    )
    assert cands == ()


def test_does_not_fire_for_non_pack_lemma() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.CAUSE,
        "zzznotalemma",
    )
    assert cands == ()


def test_does_not_fire_when_chain_already_in_corpus() -> None:
    """``(light, cause)`` IS in the corpus today (``cause_light_reveals_truth``)
    — the would_have_grounded predicate must not fire."""
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.CAUSE,
        "light",
    )
    assert cands == ()


def test_does_not_fire_on_empty_lemma() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.CAUSE,
        "",
    )
    assert cands == ()


def test_does_not_fire_on_none_lemma() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none"),
        IntentTag.CAUSE,
        None,
    )
    assert cands == ()


def test_candidate_id_is_deterministic() -> None:
    """Identical inputs MUST produce the identical candidate_id —
    this is the load-bearing replay property."""
    a = extract_discovery_candidates(
        _TE(grounding_source="none", trace_hash="seed-1"),
        IntentTag.CAUSE,
        "principle",
    )
    b = extract_discovery_candidates(
        _TE(grounding_source="none", trace_hash="seed-1"),
        IntentTag.CAUSE,
        "principle",
    )
    assert a[0].candidate_id == b[0].candidate_id


def test_candidate_id_changes_with_trace_hash() -> None:
    a = extract_discovery_candidates(
        _TE(grounding_source="none", trace_hash="seed-1"),
        IntentTag.CAUSE,
        "principle",
    )
    b = extract_discovery_candidates(
        _TE(grounding_source="none", trace_hash="seed-2"),
        IntentTag.CAUSE,
        "principle",
    )
    assert a[0].candidate_id != b[0].candidate_id


def test_boundary_clean_false_when_refusal_emitted() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none", refusal_emitted=True),
        IntentTag.CAUSE,
        "principle",
    )
    # The trigger still fires (refusal does not block evidence), but
    # boundary_clean flips to False so reviewers can filter these out
    # downstream.
    assert len(cands) == 1
    assert cands[0].boundary_clean is False


def test_boundary_clean_false_when_hedge_injected() -> None:
    cands = extract_discovery_candidates(
        _TE(grounding_source="none", hedge_injected=True),
        IntentTag.CAUSE,
        "principle",
    )
    assert len(cands) == 1
    assert cands[0].boundary_clean is False


# ---------------------------------------------------------------------------
# format_candidate_jsonl — stable on-disk shape
# ---------------------------------------------------------------------------


def test_format_jsonl_is_sorted_keys_compact() -> None:
    cand = DiscoveryCandidate(
        candidate_id="x",
        proposed_chain={"subject": "principle", "intent": "cause", "connective": None, "object": None},
        trigger="would_have_grounded",
        source_turn_trace="t",
        pack_consistent=True,
        boundary_clean=True,
    )
    line = format_candidate_jsonl(cand)
    parsed = json.loads(line)
    assert parsed["candidate_id"] == "x"
    # Compact separators — no whitespace between key/value or fields.
    assert ", " not in line
    assert ": " not in line


# ---------------------------------------------------------------------------
# Runtime integration — sink opt-in + behaviour parity
# ---------------------------------------------------------------------------


def _find_pack_lemma_without_active_chain() -> tuple[str, IntentTag]:
    """Pick a (lemma, intent) that lives in the pack but not in the
    corpus.  Used so the integration tests are not coupled to a
    specific lemma whose status might change as the corpus grows."""
    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    pack = _pack_index()
    corpus = _corpus_index()
    for lemma in pack:
        if (lemma, "cause") not in corpus:
            return lemma, IntentTag.CAUSE
        if (lemma, "verification") not in corpus:
            return lemma, IntentTag.VERIFICATION
    pytest.skip("Every pack lemma already has a corpus chain — no would-have-grounded candidate possible")


def test_runtime_no_sink_no_emission() -> None:
    """No sink attached ⇒ no error, no side effect."""
    rt = ChatRuntime()
    rt.chat("Why does judgment matter?")
    # Just must not crash and turn_log must have grown.
    assert len(rt.turn_log) >= 1


def test_runtime_emits_to_buffer_sink_on_would_have_grounded() -> None:
    """Wire a buffer sink, send a CAUSE prompt on a lemma without a
    corpus chain, expect one JSONL line."""
    lemma, intent_tag = _find_pack_lemma_without_active_chain()
    if intent_tag is IntentTag.CAUSE:
        prompt = f"Why does {lemma} matter?"
    else:
        prompt = f"Does {lemma} require evidence?"

    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.chat(prompt)

    assert len(sink.lines) == 1
    payload = json.loads(sink.lines[0])
    assert payload["trigger"] == "would_have_grounded"
    assert payload["proposed_chain"]["subject"] == lemma
    assert payload["review_state"] == "unreviewed"


def test_runtime_does_not_emit_when_turn_is_grounded() -> None:
    """``light`` + CAUSE grounds via the teaching corpus today; no
    candidate should be emitted on a grounded turn."""
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.chat("Why does light matter?")
    assert sink.lines == []


def test_runtime_detach_sink_stops_emission() -> None:
    lemma, _ = _find_pack_lemma_without_active_chain()
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_discovery_sink(None)
    rt.chat(f"Why does {lemma} matter?")
    assert sink.lines == []


def test_runtime_emission_does_not_mutate_corpus_on_disk() -> None:
    """Phase B's core trust-boundary claim: emission writes nothing
    to the corpus."""
    from chat.teaching_grounding import _CORPUS_PATH

    lemma, _ = _find_pack_lemma_without_active_chain()
    before = _CORPUS_PATH.read_bytes()
    rt = ChatRuntime()
    rt.attach_discovery_sink(DiscoveryBufferSink())
    rt.chat(f"Why does {lemma} matter?")
    after = _CORPUS_PATH.read_bytes()
    assert before == after


# ---------------------------------------------------------------------------
# DiscoveryMonthlyFileSink — rollover semantics
# ---------------------------------------------------------------------------


def test_monthly_sink_writes_jsonl_in_expected_month_path(tmp_path: Path) -> None:
    fixed = datetime(2026, 5, 18, tzinfo=timezone.utc)
    sink = DiscoveryMonthlyFileSink(tmp_path, clock=lambda: fixed)
    sink.emit('{"a":1}')
    sink.close()
    written = tmp_path / "2026" / "2026-05.jsonl"
    assert written.exists()
    assert written.read_text(encoding="utf-8").splitlines() == ['{"a":1}']


def test_monthly_sink_rolls_over_on_month_change(tmp_path: Path) -> None:
    fake = {"now": datetime(2026, 5, 31, tzinfo=timezone.utc)}
    sink = DiscoveryMonthlyFileSink(tmp_path, clock=lambda: fake["now"])
    sink.emit('{"a":1}')
    fake["now"] = datetime(2026, 6, 1, tzinfo=timezone.utc)
    sink.emit('{"b":2}')
    sink.close()
    may = (tmp_path / "2026" / "2026-05.jsonl").read_text(encoding="utf-8")
    jun = (tmp_path / "2026" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert may.splitlines() == ['{"a":1}']
    assert jun.splitlines() == ['{"b":2}']


def test_monthly_sink_append_only_existing_lines_preserved(tmp_path: Path) -> None:
    target = tmp_path / "2026" / "2026-05.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text('{"x":0}\n', encoding="utf-8")
    fixed = datetime(2026, 5, 18, tzinfo=timezone.utc)
    sink = DiscoveryMonthlyFileSink(tmp_path, clock=lambda: fixed)
    sink.emit('{"y":1}')
    sink.close()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines == ['{"x":0}', '{"y":1}']


def test_monthly_sink_context_manager_closes(tmp_path: Path) -> None:
    fixed = datetime(2026, 5, 18, tzinfo=timezone.utc)
    with DiscoveryMonthlyFileSink(tmp_path, clock=lambda: fixed) as sink:
        sink.emit('{"a":1}')
    # After exit, internal file handle is closed.
    assert sink._fh is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Doctrine — no corpus mutation, no runtime state mutation
# ---------------------------------------------------------------------------


def test_pure_extract_does_not_load_or_mutate_runtime_state() -> None:
    """Calling the extractor repeatedly must not change pack or
    corpus internal state — a smoke test that the extractor is
    a pure read."""
    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    pack_before = dict(_pack_index())
    corpus_before = dict(_corpus_index())
    for _ in range(5):
        extract_discovery_candidates(_TE(), IntentTag.CAUSE, "principle")
    pack_after = dict(_pack_index())
    corpus_after = dict(_corpus_index())
    assert pack_before.keys() == pack_after.keys()
    assert corpus_before.keys() == corpus_after.keys()
