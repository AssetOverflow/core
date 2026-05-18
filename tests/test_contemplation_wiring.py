"""ADR-0056 Phase C1 — runtime wiring of the contemplation pass.

Pinned contracts:

  - ``attach_contemplation`` is opt-in; default off ⇒ Phase B JSONL
    output is byte-identical to pre-C1 wiring.
  - When enabled, each emitted candidate is replaced by its
    contemplated form (Phase C1 fields populated).
  - Wiring does NOT mutate the active teaching corpus on disk.
  - Toggling off restores Phase B raw output.
"""

from __future__ import annotations

import json

import pytest

from chat.runtime import ChatRuntime
from chat.teaching_grounding import _CORPUS_PATH
from generate.intent import IntentTag
from teaching.discovery_sink import DiscoveryBufferSink


CORPUS_BYTES_BEFORE = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""


def _find_pack_lemma_without_active_chain() -> tuple[str, IntentTag]:
    """Mirror of helper in tests/test_discovery_candidates.py."""
    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    pack = _pack_index()
    corpus = _corpus_index()
    for lemma in sorted(pack.keys()):
        if (lemma, "cause") not in corpus:
            return lemma, IntentTag.CAUSE
        if (lemma, "verification") not in corpus:
            return lemma, IntentTag.VERIFICATION
    pytest.skip("No pack lemma without an active corpus chain")


def _send_prompt_expecting_emission(rt: ChatRuntime, sink: DiscoveryBufferSink) -> dict:
    lemma, intent_tag = _find_pack_lemma_without_active_chain()
    if intent_tag is IntentTag.CAUSE:
        prompt = f"Why does {lemma} matter?"
    else:
        prompt = f"Does {lemma} require evidence?"
    rt.chat(prompt)
    assert len(sink.lines) == 1, sink.lines
    return json.loads(sink.lines[0])


# ---------------------------------------------------------------------------
# Default behaviour: contemplation OFF
# ---------------------------------------------------------------------------


def test_default_does_not_contemplate():
    """No call to attach_contemplation ⇒ no C1 fields in the JSONL."""
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    payload = _send_prompt_expecting_emission(rt, sink)

    # Phase B keys only.  No C1 fields.
    assert "polarity" not in payload
    assert "claim_domain" not in payload
    assert "evidence" not in payload
    assert "sub_questions" not in payload


# ---------------------------------------------------------------------------
# Opt-in: contemplation ON
# ---------------------------------------------------------------------------


def test_attach_contemplation_enriches_emitted_candidates():
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    payload = _send_prompt_expecting_emission(rt, sink)

    # C1 fields present.
    assert "polarity" in payload
    assert "claim_domain" in payload
    assert "evidence" in payload
    assert "sub_questions" in payload
    assert payload["polarity"] in ("affirms", "falsifies", "undetermined")
    assert payload["claim_domain"] in ("factual", "relational", "evaluative")


def test_attach_contemplation_then_disable_restores_raw():
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    rt.attach_contemplation(enabled=False)
    payload = _send_prompt_expecting_emission(rt, sink)
    assert "polarity" not in payload


# ---------------------------------------------------------------------------
# Trust boundary: contemplation never mutates the corpus
# ---------------------------------------------------------------------------


def test_inline_contemplation_does_not_mutate_corpus():
    rt = ChatRuntime()
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    _ = _send_prompt_expecting_emission(rt, sink)
    after = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""
    assert after == CORPUS_BYTES_BEFORE


# ---------------------------------------------------------------------------
# Determinism: same prompt twice ⇒ identical contemplated payload
# (modulo Phase B fields which are already deterministic)
# ---------------------------------------------------------------------------


def test_contemplated_emission_deterministic_across_calls():
    rt1 = ChatRuntime()
    sink1 = DiscoveryBufferSink()
    rt1.attach_discovery_sink(sink1)
    rt1.attach_contemplation(enabled=True)
    p1 = _send_prompt_expecting_emission(rt1, sink1)

    rt2 = ChatRuntime()
    sink2 = DiscoveryBufferSink()
    rt2.attach_discovery_sink(sink2)
    rt2.attach_contemplation(enabled=True)
    p2 = _send_prompt_expecting_emission(rt2, sink2)

    # Phase B fields + C1 fields must match.  Source trace hash is
    # content-derived so it is stable across fresh runtimes given
    # identical prompts.
    assert p1 == p2


# ---------------------------------------------------------------------------
# No sink ⇒ no contemplation (would be hidden work)
# ---------------------------------------------------------------------------


def test_no_sink_no_contemplation_work():
    """attach_contemplation alone does nothing without a sink — the
    work would be unobservable."""
    rt = ChatRuntime()
    rt.attach_contemplation(enabled=True)
    # No sink attached; sending a fall-through prompt must not raise
    # and must produce no candidate emission.
    lemma, intent_tag = _find_pack_lemma_without_active_chain()
    if intent_tag is IntentTag.CAUSE:
        prompt = f"Why does {lemma} matter?"
    else:
        prompt = f"Does {lemma} require evidence?"
    rt.chat(prompt)  # no exception
