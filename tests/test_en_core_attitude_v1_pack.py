"""``en_core_attitude_v1`` — adjective pack tests.

The attitude pack is the first ADJ-bearing pack in the runtime.  It
carries 40 adjectives across three semantic clusters:

  - attitude.truth_value.*   — true, false, valid, accurate, ...  (8)
  - attitude.evaluative.*    — good, bad, right, better, ...      (6)
  - attitude.epistemic.*     — certain, possible, likely, ...     (10)
  - attitude.modal.*         — necessary, sufficient, ...         (4)
  - attitude.importance.*    — important, essential, useful, ...  (6)
  - attitude.scope.*         — general, specific, broad, ...      (6)

Contracts pinned:

  - Checksum-verified load.
  - 40 entries, all POS=ADJ.
  - Every entry's primary semantic_domain begins with ``attitude.``.
  - No collision with cognition_v1 / meta_v1 / relations_v1 / relations_v2.
  - Mounted by default in ``RuntimeConfig.input_packs``.
  - Registered in ``DEFAULT_RESOLVABLE_PACK_IDS`` *after* cognition and
    meta (preserves cognition-lane and meta-lane resolution invariants).
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_attitude_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 40

EXPECTED_LEMMAS: tuple[str, ...] = (
    "true", "false", "valid", "invalid", "accurate", "inaccurate", "factual",
    "sound", "good", "bad", "right", "better", "worse", "best",
    "certain", "uncertain", "possible", "impossible", "likely", "unlikely",
    "probable", "clear", "obscure", "evident",
    "necessary", "sufficient", "required", "optional",
    "important", "essential", "relevant", "central", "primary", "useful",
    "general", "specific", "broad", "narrow", "universal", "particular",
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


def test_all_entries_are_adjectives() -> None:
    entries = _read_lexicon()
    assert len(entries) == EXPECTED_TOTAL
    for entry in entries:
        assert entry["pos"] == "ADJ", entry["entry_id"]
        assert entry["morphology_tags"] == ["adjective"], entry["entry_id"]


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    surfaces = {manifold.get_word_at(i) for i in range(len(manifold))}
    assert surfaces == set(EXPECTED_LEMMAS)


def test_every_entry_has_attitude_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        domains = entry["semantic_domains"]
        assert isinstance(domains, list) and domains, entry
        assert domains[0].startswith("attitude."), (
            f"entry {entry['entry_id']} primary domain {domains[0]!r} "
            f"is not in the attitude.* namespace"
        )


def test_no_collision_with_prior_packs() -> None:
    """Anti-leakage: must not duplicate any lemma in any earlier-mounted
    English pack.  Re-asserts the authoring-time exclusion."""
    prior_lemmas: set[str] = set()
    pack_root = _PACK_ROOT.parent
    for pack in (
        "en_core_cognition_v1",
        "en_core_meta_v1",
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


def test_provenance_is_seed_core_attitude_v1() -> None:
    for entry in _read_lexicon():
        assert entry["provenance_ids"] == ["seed:core_attitude_v1"], entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-attitude-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    cfg = RuntimeConfig()
    assert PACK_ID in cfg.input_packs


def test_pack_registered_after_cognition_and_meta() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    cog_idx = DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_cognition_v1")
    meta_idx = DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_meta_v1")
    attitude_idx = DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)
    assert cog_idx < attitude_idx
    assert meta_idx < attitude_idx


def test_resolver_routes_attitude_lemmas_to_this_pack() -> None:
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None, f"lemma {lemma!r} did not resolve"
        pack_id, domains = resolved
        assert pack_id == PACK_ID, (
            f"lemma {lemma!r} resolved to {pack_id} instead of {PACK_ID}"
        )
        assert domains[0].startswith("attitude.")


def test_prior_pack_lemma_resolution_unchanged() -> None:
    """Cognition + meta lemma resolution unaffected by attitude pack."""
    for lemma in ("truth", "knowledge", "memory"):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == "en_core_cognition_v1"
    for lemma in ("doubt", "fact", "self"):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == "en_core_meta_v1"
