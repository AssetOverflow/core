"""ADR-0055 Phase A — teaching corpus audit + supersession + typed provenance.

Pinned contracts:

  - ``teaching.audit.audit_corpus`` is pure, deterministic, and never
    mutates the corpus or the pack.
  - The active runtime loader (``chat.teaching_grounding._corpus_index``)
    and the audit module agree on which entries are dropped and why.
  - ``superseded_by`` retires an earlier chain from the active view but
    leaves it on disk.
  - Legacy ``"reviewed"`` provenance source token maps to
    ``"hand_authored"`` so the current corpus reports the typed enum
    without a file rewrite.
  - Pack-consistency drop is surfaced with the specific lemma name in
    the reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from teaching.audit import audit_corpus
from teaching.provenance import Provenance, parse_provenance


# ---------------------------------------------------------------------------
# parse_provenance — typed shape
# ---------------------------------------------------------------------------


def test_parse_legacy_reviewed_token_maps_to_hand_authored() -> None:
    p = parse_provenance("adr-0052:reviewed:2026-05-17")
    assert p.adr_id == "adr-0052"
    assert p.source == "hand_authored"
    assert p.review_date == "2026-05-17"
    assert p.raw == "adr-0052:reviewed:2026-05-17"


def test_parse_canonical_hand_authored() -> None:
    p = parse_provenance("adr-9999:hand_authored:2099-12-31")
    assert p.source == "hand_authored"


def test_parse_discovery_promoted() -> None:
    p = parse_provenance("adr-9999:discovery_promoted:2099-12-31")
    assert p.source == "discovery_promoted"


def test_parse_imported() -> None:
    p = parse_provenance("adr-9999:imported:2099-12-31")
    assert p.source == "imported"


def test_parse_unknown_source_token_falls_back() -> None:
    p = parse_provenance("adr-9999:gibberish:2099-12-31")
    assert p.source == "unknown"
    # adr_id and review_date are still captured.
    assert p.adr_id == "adr-9999"
    assert p.review_date == "2099-12-31"


def test_parse_non_string_input_safe() -> None:
    assert parse_provenance(None).source == "unknown"
    assert parse_provenance(42).source == "unknown"
    assert parse_provenance({"adr": "x"}).source == "unknown"


def test_parse_empty_string_safe() -> None:
    p = parse_provenance("")
    assert p == Provenance(adr_id=None, source="unknown", review_date=None, raw="")


def test_parse_short_string_no_crash() -> None:
    p = parse_provenance("adr-0052")
    assert p.source == "unknown"
    assert p.raw == "adr-0052"


def test_parse_extra_trailing_colons_folded_into_date() -> None:
    p = parse_provenance("adr-9999:hand_authored:2099-12-31:extra")
    # Folding into review_date keeps drift safe — no crash, no silent loss.
    assert p.review_date == "2099-12-31:extra"


# ---------------------------------------------------------------------------
# audit_corpus — real corpus, no mutations
# ---------------------------------------------------------------------------


def test_audit_real_corpus_runs_clean() -> None:
    report = audit_corpus()
    assert report.lines_on_disk == report.lines_loaded
    assert report.dropped == ()
    assert len(report.loaded) >= 10
    assert report.corpus_id == "cognition_chains_v1"


def test_audit_loaded_entries_have_typed_provenance() -> None:
    report = audit_corpus()
    for entry in report.loaded:
        assert entry.provenance.source in {
            "hand_authored", "discovery_promoted", "imported", "unknown",
        }


def test_audit_is_deterministic() -> None:
    a = audit_corpus()
    b = audit_corpus()
    assert a.as_dict() == b.as_dict()


def test_audit_as_dict_is_json_serialisable() -> None:
    report = audit_corpus()
    blob = json.dumps(report.as_dict(), sort_keys=True)
    assert "cognition_chains_v1" in blob


# ---------------------------------------------------------------------------
# audit_corpus — synthetic corpora exercising drop reasons
# ---------------------------------------------------------------------------


def _write_corpus(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "cognition_chains_v1.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_audit_surfaces_invalid_json(tmp_path: Path) -> None:
    path = _write_corpus(tmp_path, ["not json at all"])
    report = audit_corpus(path)
    assert report.lines_on_disk == 1
    assert report.lines_loaded == 0
    assert len(report.dropped) == 1
    assert report.dropped[0].reason == "invalid_json"


def test_audit_surfaces_unsupported_intent(tmp_path: Path) -> None:
    path = _write_corpus(tmp_path, [json.dumps({
        "chain_id": "x", "subject": "light", "intent": "definition",
        "connective": "is", "object": "truth",
        "provenance": "adr-test:hand_authored:2026-05-18",
    })])
    report = audit_corpus(path)
    assert len(report.dropped) == 1
    assert report.dropped[0].reason == "unsupported_intent:definition"


def test_audit_surfaces_pack_missing_subject(tmp_path: Path) -> None:
    path = _write_corpus(tmp_path, [json.dumps({
        "chain_id": "x", "subject": "zzznotalemma", "intent": "cause",
        "connective": "reveals", "object": "truth",
        "provenance": "adr-test:hand_authored:2026-05-18",
    })])
    report = audit_corpus(path)
    assert len(report.dropped) == 1
    assert report.dropped[0].reason == "pack_missing_subject:zzznotalemma"


def test_audit_surfaces_pack_missing_object(tmp_path: Path) -> None:
    path = _write_corpus(tmp_path, [json.dumps({
        "chain_id": "x", "subject": "light", "intent": "cause",
        "connective": "reveals", "object": "zzznotalemma",
        "provenance": "adr-test:hand_authored:2026-05-18",
    })])
    report = audit_corpus(path)
    assert len(report.dropped) == 1
    assert report.dropped[0].reason == "pack_missing_object:zzznotalemma"


def test_audit_surfaces_missing_required_field(tmp_path: Path) -> None:
    path = _write_corpus(tmp_path, [json.dumps({
        "chain_id": "x", "subject": "", "intent": "cause",
        "connective": "reveals", "object": "truth",
    })])
    report = audit_corpus(path)
    assert len(report.dropped) == 1
    assert report.dropped[0].reason == "missing_required_field:subject"


# ---------------------------------------------------------------------------
# Supersession — disk preserves history, active view drops superseded
# ---------------------------------------------------------------------------


def test_supersession_drops_earlier_chain_from_active_view(tmp_path: Path) -> None:
    older = {
        "chain_id": "cause_light_reveals_truth",
        "subject": "light", "intent": "cause", "connective": "reveals",
        "object": "truth", "domains_subject_k": 2, "domains_object_k": 1,
        "provenance": "adr-test:hand_authored:2026-05-18",
    }
    newer = {
        "chain_id": "cause_light_grounds_truth",
        "subject": "light", "intent": "cause", "connective": "grounds",
        "object": "truth", "domains_subject_k": 2, "domains_object_k": 1,
        "provenance": "adr-test:hand_authored:2026-05-19",
        "superseded_by": "cause_light_reveals_truth",
    }
    path = _write_corpus(tmp_path, [json.dumps(older), json.dumps(newer)])
    report = audit_corpus(path)
    assert report.lines_on_disk == 2
    assert report.lines_loaded == 1
    # The newer entry retires the older one.
    assert report.dropped[0].chain_id == "cause_light_reveals_truth"
    assert report.dropped[0].reason == "superseded_by:cause_light_reveals_truth"
    # Newer entry is active.
    assert report.loaded[0].chain_id == "cause_light_grounds_truth"


def test_default_superseded_by_is_null_in_loaded_entries() -> None:
    """Existing corpus uses default null — must round-trip unchanged."""
    report = audit_corpus()
    assert all(entry.superseded_by is None for entry in report.loaded)


# ---------------------------------------------------------------------------
# Runtime parity — runtime loader and audit agree
# ---------------------------------------------------------------------------


def test_runtime_loader_and_audit_agree_on_active_chain_ids() -> None:
    """Whatever audit_corpus says is loaded must also be what the
    runtime loader has indexed (modulo the keying — runtime keys by
    (subject, intent); audit lists chain_ids)."""
    from chat.teaching_grounding import _corpus_index

    _corpus_index.cache_clear()
    runtime_chains = {c.chain_id for c in _corpus_index().values()}
    audit_chains = {c.chain_id for c in audit_corpus().loaded}
    assert runtime_chains == audit_chains


def test_runtime_loader_honors_superseded_by(tmp_path: Path) -> None:
    """If a corpus on disk has supersession, the runtime loader's
    active set must match the audit report."""
    older = {
        "chain_id": "cause_light_reveals_truth",
        "subject": "light", "intent": "cause", "connective": "reveals",
        "object": "truth",
        "provenance": "adr-test:hand_authored:2026-05-18",
    }
    newer = {
        "chain_id": "cause_light_grounds_truth",
        "subject": "light", "intent": "cause", "connective": "grounds",
        "object": "truth",
        "provenance": "adr-test:hand_authored:2026-05-19",
        "superseded_by": "cause_light_reveals_truth",
    }
    path = _write_corpus(tmp_path, [json.dumps(older), json.dumps(newer)])

    from chat import teaching_grounding as tg

    with patch.object(tg, "_CORPUS_PATH", path):
        tg._corpus_index.cache_clear()
        try:
            index = tg._corpus_index()
            active = {c.chain_id for c in index.values()}
            assert active == {"cause_light_grounds_truth"}
        finally:
            tg._corpus_index.cache_clear()


# ---------------------------------------------------------------------------
# Audit is read-only (trust boundary)
# ---------------------------------------------------------------------------


def test_audit_does_not_mutate_corpus_on_disk() -> None:
    from chat.teaching_grounding import _CORPUS_PATH

    before = _CORPUS_PATH.read_bytes()
    audit_corpus()
    after = _CORPUS_PATH.read_bytes()
    assert before == after
