"""Step B — inline realization in the live turn loop.

A conversation ACCRUES knowledge: a declarative turn realizes a fact into the held
self; a question turn is determined over realized knowledge — answered as-told, or
refused (open-world). Gated by ``accrue_realized_knowledge``; off by default leaves the
surface contract and behavior unchanged. With persistence on, the accrued fact survives
reboot — the "one continuous life" made real across an interruption.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


def _rt(*, accrue: bool, persist: bool = False, engine_state_path=None) -> ChatRuntime:
    config = replace(
        RuntimeConfig(),
        accrue_realized_knowledge=accrue,
        persist_session_state=persist,
    )
    return ChatRuntime(config=config, engine_state_path=engine_state_path)


# --------------------------------------------------------------------------- #
# Accrual: the conversation accumulates knowledge it can reason over
# --------------------------------------------------------------------------- #


def test_declarative_turn_accrues_a_realized_fact() -> None:
    rt = _rt(accrue=True)
    rt.chat("Truth is a concept.")
    accrual = rt.last_turn_accrual()
    assert accrual is not None and accrual.kind == "realized"
    assert accrual.realized.created is True


def test_question_turn_is_determined_from_accrued_knowledge() -> None:
    rt = _rt(accrue=True)
    rt.chat("Truth is a concept.")
    rt.chat("Is truth a concept?")
    accrual = rt.last_turn_accrual()
    assert accrual is not None and accrual.kind == "determined"
    det = accrual.determination
    assert det.answer is True
    assert det.basis == "as_told"  # SPECULATIVE session memory, never "verified"


def test_untold_question_refuses_open_world() -> None:
    rt = _rt(accrue=True)
    rt.chat("Truth is a concept.")
    rt.chat("Is truth a virtue?")  # never told
    det = rt.last_turn_accrual().determination
    # Undetermined, never a fabricated answer or an asserted False (open-world).
    assert type(det).__name__ == "Undetermined"
    assert det.reason in {"not_entailed", "ungrounded"}


def test_idempotent_retell_is_not_recreated() -> None:
    rt = _rt(accrue=True)
    rt.chat("Truth is a concept.")
    assert rt.last_turn_accrual().realized.created is True
    rt.chat("Truth is a concept.")  # same fact again
    assert rt.last_turn_accrual().realized.created is False  # structural dedup


# --------------------------------------------------------------------------- #
# Off by default: no behavior change, surface contract intact
# --------------------------------------------------------------------------- #


def test_flag_off_does_not_accrue_and_keeps_surface() -> None:
    rt = _rt(accrue=False)
    response = rt.chat("Truth is a concept.")
    assert rt.last_turn_accrual() is None
    # the turn still returns a real surface (no behavior change when the flag is off)
    assert isinstance(response.surface, str) and response.surface


def test_accrual_does_not_alter_the_surface() -> None:
    # The same input yields the same surface with accrual on vs off (B-1 records,
    # does not surface — the surface contract is untouched).
    off = _rt(accrue=False).chat("Truth is a concept.")
    on = _rt(accrue=True).chat("Truth is a concept.")
    assert on.surface == off.surface
    assert on.articulation_surface == off.articulation_surface


# --------------------------------------------------------------------------- #
# One continuous life: accrued knowledge survives reboot
# --------------------------------------------------------------------------- #


def test_accrued_knowledge_survives_reboot(tmp_path) -> None:
    esp = tmp_path / "engine_state"
    # life 1: tell a fact, then the process ends
    rt1 = _rt(accrue=True, persist=True, engine_state_path=esp)
    rt1.chat("Truth is a concept.")
    assert rt1.last_turn_accrual().kind == "realized"

    # reboot: a NEW runtime over the SAME checkpoint resumes the SAME life
    rt2 = _rt(accrue=True, persist=True, engine_state_path=esp)
    rt2.chat("Is truth a concept?")
    det = rt2.last_turn_accrual().determination
    assert det.answer is True and det.basis == "as_told"  # remembered across the reboot


def test_no_accrual_persistence_without_persist_flag(tmp_path) -> None:
    esp = tmp_path / "engine_state"
    rt1 = _rt(accrue=True, persist=False, engine_state_path=esp)
    rt1.chat("Truth is a concept.")
    # without persistence the fact accrues only in-session; a reboot does not recall it
    rt2 = _rt(accrue=True, persist=False, engine_state_path=esp)
    rt2.chat("Is truth a concept?")
    det = rt2.last_turn_accrual().determination
    assert type(det).__name__ == "Undetermined"


# --------------------------------------------------------------------------- #
# Robustness: accrual is additive, never crashes a turn
# --------------------------------------------------------------------------- #


def test_uncomprehended_turn_is_a_clean_noop() -> None:
    rt = _rt(accrue=True)
    response = rt.chat("Hello there friend.")  # no fact/question to accrue
    assert response.surface  # the turn still returns normally
    accrual = rt.last_turn_accrual()
    # either nothing comprehensible (kind="none") or a refusal that realized nothing
    assert accrual is None or accrual.kind in {"none", "realized", "determined"}
