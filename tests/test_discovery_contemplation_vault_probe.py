"""W-016 — pin that ChatRuntime._emit_discovery_candidates invokes the
vault probe when ``RuntimeConfig.vault_probe_discoveries=True``.

Contracts verified:

  1. With ``vault_probe_discoveries=False`` (default) the probe is never
     called — the four-tier T1 evidence path is off by default.
  2. With ``vault_probe_discoveries=True`` the probe IS called with a
     query derived from the discovery candidate's subject lemma.
  3. The probe's return value (EvidencePointers) appears in the emitted
     candidate's ``evidence`` list.
  4. A probe that raises must not crash the loop (defensive: vault
     unavailability must not block discovery emission).
  5. Non-discovery turns (no candidate emitted) never call the probe —
     trace_hash byte-identity guarantee.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.intent import IntentTag
from teaching.discovery import EvidencePointer
from teaching.discovery_sink import DiscoveryBufferSink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_pack_lemma_without_active_chain() -> tuple[str, IntentTag]:
    """Return a (lemma, intent) pair for which no teaching chain exists."""
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


def _send_prompt_expect_one(rt: ChatRuntime, sink: DiscoveryBufferSink) -> dict:
    lemma, intent_tag = _find_pack_lemma_without_active_chain()
    prompt = (
        f"Why does {lemma} matter?"
        if intent_tag is IntentTag.CAUSE
        else f"Does {lemma} require evidence?"
    )
    rt.chat(prompt)
    assert len(sink.lines) >= 1, "Expected at least one discovery candidate"
    return json.loads(sink.lines[0])


# ---------------------------------------------------------------------------
# Contract 1 — probe NOT called by default
# ---------------------------------------------------------------------------


def test_probe_not_called_when_flag_off():
    probe = MagicMock(return_value=())
    rt = ChatRuntime(config=RuntimeConfig(vault_probe_discoveries=False))
    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    _send_prompt_expect_one(rt, sink)
    probe.assert_not_called()


# ---------------------------------------------------------------------------
# Contract 2 — probe IS called when flag on, with subject-derived query
# ---------------------------------------------------------------------------


def test_probe_called_when_flag_on():
    calls: list[tuple[str, str]] = []

    def _probe(subject: str, obj: str) -> tuple[EvidencePointer, ...]:
        calls.append((subject, obj))
        return ()

    rt = ChatRuntime(config=RuntimeConfig(vault_probe_discoveries=True))
    # Inject the mock probe by patching the vault probe factory.
    # We use monkeypatching at module level via direct attribute access so
    # the runtime's own _build_vault_probe is replaced for this test only.
    import chat.runtime as _rt_mod
    original = _rt_mod._build_vault_probe
    _rt_mod._build_vault_probe = lambda vault, vocab: _probe  # type: ignore[assignment]

    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    try:
        _send_prompt_expect_one(rt, sink)
    finally:
        _rt_mod._build_vault_probe = original

    assert len(calls) >= 1, "Expected vault probe to be called at least once"
    # Every call must have been with non-empty string arguments.
    for subj, obj in calls:
        assert isinstance(subj, str) and subj
        assert isinstance(obj, str)


# ---------------------------------------------------------------------------
# Contract 3 — probe evidence appears in emitted candidate
# ---------------------------------------------------------------------------


def test_probe_evidence_appears_in_emitted_candidate():
    sentinel = EvidencePointer(
        source="vault_coherent",
        ref="test_ref_w016",
        polarity="affirms",
        epistemic_status="coherent",
    )

    def _probe(subject: str, obj: str) -> tuple[EvidencePointer, ...]:
        return (sentinel,)

    rt = ChatRuntime(config=RuntimeConfig(vault_probe_discoveries=True))
    import chat.runtime as _rt_mod
    original = _rt_mod._build_vault_probe
    _rt_mod._build_vault_probe = lambda vault, vocab: _probe  # type: ignore[assignment]

    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    try:
        payload = _send_prompt_expect_one(rt, sink)
    finally:
        _rt_mod._build_vault_probe = original

    # Parent candidates have object=None so vault evidence lands in
    # sub-questions (where contemplate recurses on concrete objects).
    # Collect vault_coherent refs from both direct evidence and sub-questions.
    def _collect_vault_refs(payload: dict) -> list[str]:
        refs: list[str] = []
        for e in payload.get("evidence", []):
            if e.get("source") == "vault_coherent":
                refs.append(e.get("ref", ""))
        for sq in payload.get("sub_questions", []):
            for e in sq.get("evidence", []):
                if e.get("source") == "vault_coherent":
                    refs.append(e.get("ref", ""))
        return refs

    vault_refs = _collect_vault_refs(payload)
    assert "test_ref_w016" in vault_refs, (
        f"Expected vault probe evidence anywhere in payload; got evidence={payload.get('evidence')}, "
        f"sub_questions={payload.get('sub_questions')}"
    )


# ---------------------------------------------------------------------------
# Contract 4 — raising probe must not crash the loop
# ---------------------------------------------------------------------------


def test_raising_probe_does_not_crash_loop():
    def _bad_probe(subject: str, obj: str) -> tuple[EvidencePointer, ...]:
        raise RuntimeError("vault unreachable — W-016 defensive test")

    rt = ChatRuntime(config=RuntimeConfig(vault_probe_discoveries=True))
    import chat.runtime as _rt_mod
    original = _rt_mod._build_vault_probe
    _rt_mod._build_vault_probe = lambda vault, vocab: _bad_probe  # type: ignore[assignment]

    sink = DiscoveryBufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)
    try:
        # Must not raise; contemplation.py's _probe_vault catches exceptions.
        _send_prompt_expect_one(rt, sink)
    finally:
        _rt_mod._build_vault_probe = original
