"""Contract tests for the Phase C ratified glosses.

Pins:
  - Every pack with a ``glosses.jsonl`` file has a matching
    ``glosses_checksum`` in its manifest.
  - Every gloss entry references a lemma that is ratified in the
    same pack's ``lexicon.jsonl`` (lexicon-residency invariant —
    re-asserted from the storage layer up).
  - The total ratified gloss count meets a floor (>= 300).
  - At least one gloss resolves end-to-end for the most common
    conversational lemmas (sanity check for the wiring + content).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from chat.pack_resolver import (
    DEFAULT_RESOLVABLE_PACK_IDS,
    _pack_glosses_for,
    _pack_lexicon_for,
    clear_resolver_cache,
    resolve_gloss,
)


_DATA = Path(__file__).resolve().parent.parent / "language_packs" / "data"


def _packs_with_glosses() -> list[str]:
    out = []
    for p in DEFAULT_RESOLVABLE_PACK_IDS:
        if (_DATA / p / "glosses.jsonl").exists():
            out.append(p)
    return out


class TestGlossesPresent:
    def test_at_least_eight_packs_ship_glosses(self) -> None:
        """Phase C seeds glosses in 9 English content packs."""
        packs = _packs_with_glosses()
        assert len(packs) >= 8, (
            f"expected >=8 packs with glosses, got {len(packs)}: {packs}"
        )

    def test_total_gloss_count_floor(self) -> None:
        """The Phase C dispatch targeted ~330 glosses; this is the
        regression floor."""
        clear_resolver_cache()
        total = sum(len(_pack_glosses_for(p)) for p in _packs_with_glosses())
        assert total >= 300, f"total gloss count {total} below floor 300"


class TestManifestChecksumDiscipline:
    def test_every_glossed_pack_has_matching_checksum(self) -> None:
        for pack_id in _packs_with_glosses():
            manifest = json.loads(
                (_DATA / pack_id / "manifest.json").read_text(encoding="utf-8")
            )
            assert "glosses_checksum" in manifest, pack_id
            declared = manifest["glosses_checksum"]
            assert isinstance(declared, str) and len(declared) == 64, (pack_id, declared)
            actual = hashlib.sha256(
                (_DATA / pack_id / "glosses.jsonl").read_bytes()
            ).hexdigest()
            assert actual == declared, (
                f"glosses_checksum drift on {pack_id}: "
                f"declared={declared[:16]}… actual={actual[:16]}…"
            )

    def test_lexicon_checksum_unchanged_by_gloss_landing(self) -> None:
        """Adding glosses must NOT bump the lexicon checksum.  The
        lexicon is immutable; only glosses_checksum changes when
        glosses are added or revised."""
        for pack_id in _packs_with_glosses():
            manifest = json.loads(
                (_DATA / pack_id / "manifest.json").read_text(encoding="utf-8")
            )
            actual_lex_checksum = hashlib.sha256(
                (_DATA / pack_id / "lexicon.jsonl").read_bytes()
            ).hexdigest()
            assert manifest["checksum"] == actual_lex_checksum, pack_id


class TestLexiconResidencyAcrossAllGlosses:
    """Every authored gloss must reference a lemma that exists in the
    same pack's lexicon.jsonl.  This is the storage-layer enforcement
    of the resolve_gloss runtime invariant — any drift in glosses.jsonl
    that introduces an unratified lemma fails this test."""

    def test_every_gloss_lemma_is_lexicon_resident(self) -> None:
        clear_resolver_cache()
        for pack_id in _packs_with_glosses():
            lex = _pack_lexicon_for(pack_id)
            glosses = _pack_glosses_for(pack_id)
            for lemma in glosses:
                assert lemma in lex, (
                    f"pack {pack_id} ships a gloss for {lemma!r} but the "
                    f"lemma is not in its lexicon.jsonl"
                )


class TestEndToEndSmoke:
    """Resolve known high-frequency conversational lemmas through
    resolve_gloss and assert the runtime composes a fluent surface."""

    HIGH_FREQ_LEMMAS = (
        # cognition
        "truth", "knowledge", "memory", "evidence", "thought",
        # meta
        "doubt", "fact", "idea", "self", "believe", "know",
        # attitude
        "true", "good", "important", "certain", "necessary",
        # temporal
        "now", "moment", "future", "past", "before",
        # spatial
        "here", "place", "above",
        # action
        "make", "create", "change", "use",
        # causation
        "effect", "outcome",
        # polarity
        "always", "never", "yes",
    )

    def test_high_freq_lemmas_resolve_a_gloss(self) -> None:
        clear_resolver_cache()
        misses = []
        for lemma in self.HIGH_FREQ_LEMMAS:
            entry = resolve_gloss(lemma)
            if entry is None:
                misses.append(lemma)
        assert not misses, (
            f"resolve_gloss returned None for high-frequency lemmas: {misses}"
        )

    def test_fluent_surface_contains_lemma_case_insensitive(self) -> None:
        """End-to-end: pack_grounded_surface composes a fluent sentence
        for every high-freq lemma; the lemma (lowercase) appears in the
        rendered surface."""
        from chat.pack_grounding import pack_grounded_surface
        clear_resolver_cache()
        for lemma in self.HIGH_FREQ_LEMMAS:
            surface = pack_grounded_surface(lemma)
            assert surface is not None, lemma
            assert lemma in surface.lower(), (lemma, surface)
            assert "pack-grounded" in surface, (lemma, surface)
            # No dotted-domain-inventory in gloss-backed surfaces.
            assert "; " not in surface, (lemma, surface)


class TestSurfaceFormatInvariants:
    """A handful of structural invariants the gloss-backed surfaces
    must respect.  These are what the deterministic_fluency lane
    checks at scale — repeated here per-pack for tighter attribution."""

    SAMPLE = ("truth", "doubt", "important", "now", "place", "make", "effect", "always")

    def test_surfaces_have_terminal_punctuation(self) -> None:
        from chat.pack_grounding import pack_grounded_surface
        clear_resolver_cache()
        for lemma in self.SAMPLE:
            s = pack_grounded_surface(lemma)
            assert s is not None and s.rstrip().endswith("."), (lemma, s)

    def test_surfaces_contain_no_placeholders(self) -> None:
        from chat.pack_grounding import pack_grounded_surface
        clear_resolver_cache()
        for lemma in self.SAMPLE:
            s = pack_grounded_surface(lemma)
            assert s is not None
            for marker in ("...", "<pending>", "<prior>"):
                assert marker not in s, (lemma, marker, s)
