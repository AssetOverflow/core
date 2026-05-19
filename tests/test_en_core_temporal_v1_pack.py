"""``en_core_temporal_v1`` — temporal pack tests.

The temporal pack is the first time-bearing pack in the runtime.  Prior
to it, zero temporal vocabulary existed in any mounted English pack —
queries about *when*, *before*, *after*, *now*, *future*, *past* all
fell through to OOV.  Pack contains 28 entries across three clusters:

  - temporal.deictic.*    — now, today, soon, recently, ...  (10 adverbs)
  - temporal.relative.*   — before, after, during, until, ago, prior,
                            henceforth, while, since  (9 mixed POS)
  - temporal.noun.*       — moment, period, era, future, past, present,
                            duration, instant, time  (9 nouns)

Contracts pinned:

  - Checksum-verified load.
  - 28 entries.
  - Every entry's primary semantic_domain begins with ``temporal.``.
  - Mixed POS distribution preserved (12 ADV / 9 NOUN / 5 ADP / 1 SCONJ
    / 1 ADJ) — the resolver is POS-agnostic so this is exposed in the
    underlying lexicon but does not affect resolution.
  - No collision with any prior English pack.
  - Mounted by default in ``RuntimeConfig.input_packs``.
  - Registered in ``DEFAULT_RESOLVABLE_PACK_IDS`` after attitude pack;
    cognition+meta+attitude resolution unchanged.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_temporal_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 28
EXPECTED_POS_COUNTS = {"ADV": 12, "ADP": 5, "SCONJ": 1, "ADJ": 1, "NOUN": 9}

EXPECTED_LEMMAS: tuple[str, ...] = (
    "now", "today", "tomorrow", "yesterday", "soon", "later", "recently",
    "eventually", "currently", "formerly",
    "before", "after", "during", "while", "until", "since", "ago",
    "prior", "henceforth",
    "moment", "period", "duration", "instant", "era", "future", "past",
    "present", "time",
)


def _read_lexicon() -> list[dict]:
    path = _PACK_ROOT / "lexicon.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert all(c in "0123456789abcdef" for c in manifest.checksum)
    assert len(manifold) == EXPECTED_TOTAL


def test_pos_distribution_matches_design() -> None:
    entries = _read_lexicon()
    pos_counts = Counter(e["pos"] for e in entries)
    assert dict(pos_counts) == EXPECTED_POS_COUNTS


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    surfaces = {manifold.get_word_at(i) for i in range(len(manifold))}
    assert surfaces == set(EXPECTED_LEMMAS)


def test_every_entry_has_temporal_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        domains = entry["semantic_domains"]
        assert isinstance(domains, list) and domains, entry
        assert domains[0].startswith("temporal."), (
            f"entry {entry['entry_id']} primary domain {domains[0]!r} "
            f"is not in the temporal.* namespace"
        )


def test_no_collision_with_prior_packs() -> None:
    """Anti-leakage: no overlap with any earlier-mounted English pack."""
    prior_lemmas: set[str] = set()
    pack_root = _PACK_ROOT.parent
    for pack in (
        "en_core_cognition_v1",
        "en_core_meta_v1",
        "en_core_attitude_v1",
        "en_core_relations_v1",
        "en_core_relations_v2",
    ):
        for line in (pack_root / pack / "lexicon.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                prior_lemmas.add(json.loads(line)["lemma"].lower())
    for entry in _read_lexicon():
        lemma = entry["lemma"].lower()
        assert lemma not in prior_lemmas, (
            f"lemma {lemma!r} collides with a prior-mounted pack"
        )


def test_provenance_is_seed_core_temporal_v1() -> None:
    for entry in _read_lexicon():
        assert entry["provenance_ids"] == ["seed:core_temporal_v1"], entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-temporal-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    cfg = RuntimeConfig()
    assert PACK_ID in cfg.input_packs


def test_pack_registered_after_prior_content_packs() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    for earlier in ("en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1"):
        assert DEFAULT_RESOLVABLE_PACK_IDS.index(earlier) < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)


def test_resolver_routes_temporal_lemmas_to_this_pack() -> None:
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None, f"lemma {lemma!r} did not resolve"
        pack_id, domains = resolved
        assert pack_id == PACK_ID, (
            f"lemma {lemma!r} resolved to {pack_id} instead of {PACK_ID}"
        )
        assert domains[0].startswith("temporal.")


def test_prior_pack_lemma_resolution_unchanged() -> None:
    """Cognition / meta / attitude resolution unaffected by temporal pack."""
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("knowledge", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("fact", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("certain", "en_core_attitude_v1"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected, (
            f"{lemma!r} resolved to {resolved[0] if resolved else None}, "
            f"expected {expected}"
        )
