"""``en_core_meta_v1`` — conversational substrate pack tests.

The meta pack carries 77 lemmas (73 seed + 4 added under adr-0085-style-v2
review) across four semantic clusters that the cognition pack deliberately
omits:

  - meta.speech_act.*       — say, tell, claim, deny, suggest, ...  (20+ verbs)
  - meta.mental_state.*     — know, believe, want, doubt, decide, ... (18+ verbs)
  - meta.perception.*       — see, hear, feel, notice, find, ...     (11+ verbs)
  - meta.self_reference.*   — self, mind, view, role, model, ...     (10 nouns)
  - meta.discourse.*        — fact, idea, statement, instance, ...   (14 nouns)

Contracts pinned here:

  - Checksum-verified load (bytes-on-disk match manifest digest).
  - 77 entries total, broken down 53 VERB / 24 NOUN.
  - Every lemma carries a semantic_domains list starting with ``meta.``.
  - No collision with ``en_core_cognition_v1`` lemmas (forbidden list
    enforced at authoring time — re-asserted here as a regression gate).
  - Pack is mounted by default in ``RuntimeConfig.input_packs``.
  - Pack is registered with ``DEFAULT_RESOLVABLE_PACK_IDS`` after
    ``en_core_cognition_v1`` so any future lemma collision preserves
    cognition's resolution (cognition lane byte-identity invariant).
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_meta_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 77
EXPECTED_VERB = 53
EXPECTED_NOUN = 24

# Allowed provenance shapes:
#   - ``["seed:core_meta_v1"]`` for original seed entries
#   - ``["seed:core_meta_v1", "adr-0085-style-v2:reviewed:2026-05-22"]`` /
#     ``["seed:core_meta", "adr-0085-style-v2:reviewed:2026-05-22"]`` for
#     entries added under the ADR-0085 style-v2 review.
# The ``seed:core_meta`` (no _v1) shape on two entries (feel, think) is a
# known author-time inconsistency; the test allows it rather than masking it.
_ALLOWED_PROVENANCE_SHAPES: frozenset[tuple[str, ...]] = frozenset({
    ("seed:core_meta_v1",),
    ("seed:core_meta_v1", "adr-0085-style-v2:reviewed:2026-05-22"),
    ("seed:core_meta", "adr-0085-style-v2:reviewed:2026-05-22"),
})

EXPECTED_REPRESENTATIVE_LEMMAS: tuple[str, ...] = (
    "say", "tell", "deny", "suggest", "respond",
    "know", "believe", "doubt", "decide", "hold",
    "see", "hear", "notice", "find",
    "self", "mind", "view", "model", "system",
    "fact", "idea", "statement", "instance", "example",
)

COGNITION_V1_FORBIDDEN: frozenset[str] = frozenset({
    "word", "truth", "light", "life", "beginning", "creation",
    "knowledge", "wisdom", "spirit", "person", "question", "answer",
    "reason", "cause", "memory", "correction", "meaning", "definition",
    "comparison", "identity", "concept", "context", "define", "explain",
    "compare", "infer", "remember", "correct", "verify", "ask", "mean",
    "reveal", "relate", "distinguish", "teach", "learn", "recall",
    "be", "have", "contrast", "precede", "follow", "belong", "ground",
    "support", "why", "how", "because", "evidence", "inference",
    "procedure", "verification", "distinction", "relation", "thought",
    "understanding", "judgment", "principle", "order", "therefore",
    "however", "then", "first", "metaphor", "simile", "analogy",
    "narrative", "story", "voice", "style", "register", "tone",
    "rhetoric", "figure", "symbol", "image", "discourse", "account",
})


def _read_lexicon() -> list[dict]:
    path = _PACK_ROOT / "lexicon.jsonl"
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        out.append(json.loads(raw))
    return out


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert all(c in "0123456789abcdef" for c in manifest.checksum)
    assert len(manifold) == EXPECTED_TOTAL


def test_lexicon_pos_split() -> None:
    entries = _read_lexicon()
    assert len(entries) == EXPECTED_TOTAL
    verbs = [e for e in entries if e["pos"] == "VERB"]
    nouns = [e for e in entries if e["pos"] == "NOUN"]
    assert len(verbs) == EXPECTED_VERB
    assert len(nouns) == EXPECTED_NOUN


def test_representative_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    surfaces = {manifold.get_word_at(i) for i in range(len(manifold))}
    for lemma in EXPECTED_REPRESENTATIVE_LEMMAS:
        assert lemma in surfaces, f"expected lemma {lemma!r} missing from pack"


def test_every_entry_has_meta_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        domains = entry["semantic_domains"]
        assert isinstance(domains, list) and domains, entry
        assert domains[0].startswith("meta."), (
            f"entry {entry['entry_id']} primary domain {domains[0]!r} "
            f"is not in the meta.* namespace"
        )


def test_no_collision_with_cognition_v1() -> None:
    """Anti-leakage: meta pack must not duplicate cognition_v1 lemmas.

    The author-time forbidden list is re-asserted here so a future edit
    to the lexicon cannot quietly introduce a collision that would
    silently break cognition's first-match-wins resolution.
    """
    for entry in _read_lexicon():
        lemma = entry["lemma"].lower()
        assert lemma not in COGNITION_V1_FORBIDDEN, (
            f"lemma {lemma!r} collides with en_core_cognition_v1"
        )


def test_provenance_is_seed_core_meta_v1() -> None:
    for entry in _read_lexicon():
        shape = tuple(entry["provenance_ids"])
        assert shape in _ALLOWED_PROVENANCE_SHAPES, entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-meta-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    cfg = RuntimeConfig()
    assert PACK_ID in cfg.input_packs


def test_pack_registered_in_default_resolvable_ids_after_cognition() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    cog_idx = DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_cognition_v1")
    meta_idx = DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)
    assert cog_idx < meta_idx, (
        "cognition must precede meta in resolver order to preserve "
        "the cognition-lane byte-identity invariant"
    )


def test_resolver_routes_meta_lemmas_to_this_pack() -> None:
    """Every representative lemma resolves to en_core_meta_v1."""
    for lemma in EXPECTED_REPRESENTATIVE_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None, f"lemma {lemma!r} did not resolve"
        pack_id, domains = resolved
        assert pack_id == PACK_ID, (
            f"lemma {lemma!r} resolved to {pack_id} instead of {PACK_ID}"
        )
        assert domains[0].startswith("meta."), domains


def test_cognition_lemma_resolution_unchanged() -> None:
    """First-match-wins keeps cognition lemmas resolving to cognition."""
    for lemma in ("truth", "knowledge", "memory", "evidence"):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == "en_core_cognition_v1"
