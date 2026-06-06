"""Step E — the converse-guess estimator + its calibration gold lane.

The estimator is BLIND (never reads symmetry metadata); the reliability gate decides
licensing from MEASURED commitment precision. The load-bearing properties: the gate
DISCRIMINATES (a symmetric predicate's converse-guess earns SERVE; a directed one does
not), the SERVE license is earned by VOLUME (the Wilson floor binds at 657), and the
serving-side estimator fires only on a told converse.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.config import DEFAULT_CONFIG
from core.reliability_gate import N_MIN
from evals.determination_estimation import (
    LICENSED_PREDICATE,
    REFUSED_PREDICATE,
    build_ledger,
    load_symmetric_predicates,
    reliability_at,
    run,
)
from generate.determine.estimate import ConverseEstimate, converse_class_name, estimate_converse
from generate.meaning_graph.relational import comprehend_relational, load_relational_pack_lemmas
from generate.realize import realize_comprehension
from session.context import SessionContext

_HIGH = 10**9


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


@pytest.fixture(scope="module")
def rel_lemmas():
    return load_relational_pack_lemmas()


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH)


def _tell_relational(text: str, ctx: SessionContext, lemmas) -> None:
    realize_comprehension(comprehend_relational(text, lemmas), ctx)


# --------------------------------------------------------------------------- #
# The gate discriminates (the whole point of E)
# --------------------------------------------------------------------------- #


def test_gate_discriminates_symmetric_from_directed() -> None:
    report = run()
    assert report["gate_discriminates"] is True
    licensed = report["classes"][converse_class_name(LICENSED_PREDICATE)]
    refused = report["classes"][converse_class_name(REFUSED_PREDICATE)]
    assert licensed["serve_licensed"] is True
    assert refused["serve_licensed"] is False
    # The symmetric class is right every time; the directed class is wrong every time.
    assert licensed["tally"]["wrong"] == 0 and licensed["tally"]["correct"] > 0
    assert refused["tally"]["correct"] == 0 and refused["tally"]["wrong"] > 0


def test_serve_license_is_earned_by_volume() -> None:
    # Below the Wilson volume floor a PERFECT symmetric record is still NOT SERVE-licensed.
    assert reliability_at(LICENSED_PREDICATE, 656) < 0.99
    assert reliability_at(LICENSED_PREDICATE, 657) >= 0.99
    # And below N_MIN no reliability is claimed at all.
    assert reliability_at(LICENSED_PREDICATE, N_MIN - 1) == 0.0


def test_run_is_deterministic() -> None:
    a, b = run(), run()
    assert a == b


def test_gold_symmetry_matches_pack() -> None:
    sym = load_symmetric_predicates()
    assert LICENSED_PREDICATE in sym  # sibling_of — graph.edge.symmetric
    assert REFUSED_PREDICATE not in sym  # parent_of — graph.edge.directed


# --------------------------------------------------------------------------- #
# The serving-side estimator
# --------------------------------------------------------------------------- #


def test_estimate_fires_only_on_a_told_converse(vocab_persona, rel_lemmas) -> None:
    ctx = _ctx(vocab_persona)
    _tell_relational("Alice is the sibling of Bob.", ctx, rel_lemmas)
    # Told sibling_of(alice, bob); the converse query sibling_of(bob, alice) gets a guess.
    est = estimate_converse(ctx, "sibling_of", "bob", "alice")
    assert isinstance(est, ConverseEstimate)
    assert est.answer is True
    assert est.basis == "estimate_converse"
    assert est.subject == "bob" and est.object == "alice"
    assert est.told_structure_key  # ties the guess to the realized fact

    # No told converse → no guess (the estimator never invents evidence).
    assert estimate_converse(ctx, "sibling_of", "carol", "dave") is None


def test_estimate_is_blind_to_symmetry(vocab_persona, rel_lemmas) -> None:
    # The estimator commits the converse for a DIRECTED predicate too — being wrong
    # there is exactly what the gate measures and refuses to license.
    ctx = _ctx(vocab_persona)
    _tell_relational("Alice is the parent of Bob.", ctx, rel_lemmas)
    est = estimate_converse(ctx, "parent_of", "bob", "alice")
    assert isinstance(est, ConverseEstimate) and est.answer is True


# --------------------------------------------------------------------------- #
# E-2 — the ratified ledger artifact + serving-side license
# --------------------------------------------------------------------------- #


def test_ratified_ledger_matches_sealed_practice() -> None:
    # Provenance (the GSM8K-style --check): the committed artifact IS the deterministic
    # sealed-practice output, not a hand-edited ledger.
    from generate.determine.estimation_license import load_ratified_ledger

    committed = load_ratified_ledger()
    fresh = build_ledger()
    assert {k: (t.correct, t.wrong, t.refused) for k, t in committed.items()} == {
        k: (t.correct, t.wrong, t.refused) for k, t in fresh.items()
    }


def test_serve_license_from_ratified_ledger() -> None:
    from generate.determine.estimation_license import serve_license

    assert serve_license(LICENSED_PREDICATE).licensed is True  # sibling_of — earned SERVE
    assert serve_license(REFUSED_PREDICATE).licensed is False  # parent_of — never
    assert serve_license("nonexistent_predicate") is None  # no committed evidence → refuse


def test_tampered_ledger_is_rejected(tmp_path, monkeypatch) -> None:
    # A hand-edited ledger (counts changed without the matching hash) must be REJECTED,
    # never silently trusted — only the sealed-practice output is admissible.
    import json as _json

    import generate.determine.estimation_license as mod
    from generate.determine.estimation_license import RatifiedLedgerError, load_ratified_ledger

    good = _json.loads(mod._LEDGER_PATH.read_text(encoding="utf-8"))
    good["classes"][converse_class_name(REFUSED_PREDICATE)]["correct"] = 999  # forge a SERVE
    forged_path = tmp_path / "estimation_ledger.json"
    forged_path.write_text(_json.dumps(good), encoding="utf-8")

    load_ratified_ledger.cache_clear()
    monkeypatch.setattr(mod, "_LEDGER_PATH", forged_path)
    try:
        with pytest.raises(RatifiedLedgerError, match="content_sha256 mismatch"):
            load_ratified_ledger()
    finally:
        load_ratified_ledger.cache_clear()  # don't poison other tests' cached load


# --------------------------------------------------------------------------- #
# E-3 — the runtime wire (chat turn → disclosed estimate, license-gated)
# --------------------------------------------------------------------------- #


def _estimation_runtime(tmp_path: Path, *, enabled: bool = True) -> ChatRuntime:
    cfg = _dc_replace(
        DEFAULT_CONFIG,
        estimation_enabled=enabled,
        accrue_realized_knowledge=True,
        persist_session_state=True,
    )
    return ChatRuntime(config=cfg, engine_state_path=tmp_path)


def test_licensed_converse_is_served_disclosed_approximate(tmp_path) -> None:
    rt = _estimation_runtime(tmp_path)
    rt.chat("Alice is the sibling of Bob.")  # told sibling_of(alice, bob)
    resp = rt.chat("Is Bob the sibling of Alice?")  # converse — DETERMINE refuses
    assert resp.reach_level == "approximate"
    assert resp.surface.startswith("[approximate]")  # DISCLOSED, never asserted as fact
    assert "bob" in resp.surface and "alice" in resp.surface


def test_unlicensed_converse_stays_strict_refusal(tmp_path) -> None:
    rt = _estimation_runtime(tmp_path)
    rt.chat("Alice is the parent of Bob.")  # told parent_of(alice, bob) — DIRECTED
    resp = rt.chat("Is Bob the parent of Alice?")
    # parent_of's converse-guess is not SERVE-licensed → no widening, honest refusal.
    assert resp.reach_level == "strict"
    assert not resp.surface.startswith("[approximate]")


def test_estimation_flag_off_is_strict(tmp_path) -> None:
    rt = _estimation_runtime(tmp_path, enabled=False)
    rt.chat("Alice is the sibling of Bob.")
    resp = rt.chat("Is Bob the sibling of Alice?")
    assert resp.reach_level == "strict"
    assert not resp.surface.startswith("[approximate]")
