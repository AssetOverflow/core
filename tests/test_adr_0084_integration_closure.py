"""ADR-0084 integration test — substrate gate against ratified content.

After PR #64 (substrate) and PR #65 (content) both landed on main, this
test was promised as the follow-up that exercises the substrate-callable
``verify_definitional_closure`` against the *real* ratified content,
not fixture packs.  Its job:

1. Pin the substrate-vs-content handshake.  Today the standalone
   ``scripts/verify_definitional_closure.py`` is the agent's dev-loop
   tool; this test is the *gate-callable* equivalent that the
   ratification pipeline can invoke.  Both must stay in agreement on
   what passes — divergence is a contract bug.

2. Catch content drift.  If a future content edit adds an unresolved
   token, an empty atom list that should not be empty, or a gloss
   that depends on a non-mounted pack, this test fails before the
   edit lands on main — independently of whether the agent's
   standalone script also catches it.

3. Document the resolution-pool contract.  ``mounted_pack_lemmas`` is
   the union of lexicon-resident lemmas across *production* packs.
   ``en_minimal_v1`` is staging per the ADR-0084 pack-content brief
   and must NOT be load-bearing for the closure rule (deliberately
   excluded here even though the standalone verifier currently
   pools it).
"""

from __future__ import annotations

import pytest

from language_packs.compiler import load_pack_entries
from language_packs.definitions import (
    load_pack_glosses,
    verify_definitional_closure,
)
from packs.primitives import load_primitives_pack


# Packs that flipped ``definitional_layer: true`` via PR #65.
# Production-only — does NOT include ``en_minimal_v1`` (staging) or
# the Greek/Hebrew packs (per-lens glosses deferred per ADR-0084
# scope limits).
OPTED_IN_PACKS: tuple[str, ...] = (
    "en_core_cognition_v1",
    "en_core_action_v1",
    "en_core_attitude_v1",
    "en_core_causation_v1",
    "en_core_meta_v1",
    "en_core_polarity_v1",
    "en_core_quantitative_v1",
    "en_core_spatial_v1",
    "en_core_temporal_v1",
    "en_core_relations_v1",
    "en_core_relations_v2",
    "en_core_relations_v3",
    "en_collapse_anchors_v1",
)


@pytest.fixture(scope="module")
def primitives_lemmas() -> frozenset[str]:
    return load_primitives_pack().lemmas


@pytest.fixture(scope="module")
def mounted_lex_lemmas() -> frozenset[str]:
    """Union of lexicon-resident lemmas across production opted-in packs.

    Built from each pack's ``lexicon.jsonl`` — the same source the
    standalone verifier uses — because that's the operational meaning
    of "a lemma in another mounted pack" (gloss entries are an additive
    overlay on the immutable lexicon, not its replacement).
    """
    lemmas: set[str] = set()
    for pack_id in OPTED_IN_PACKS:
        for entry in load_pack_entries(pack_id):
            lemmas.add(entry.lemma.lower())
            lemmas.add(entry.surface.lower())
    return frozenset(lemmas)


# --------------------------------------------------------------------------- #
# Strict-parse every opted-in pack
# --------------------------------------------------------------------------- #


class TestStrictParseOptedInPacks:
    """Every opted-in pack must strict-parse under the substrate.

    A strict-parse failure means the content carries a schema violation
    the substrate would refuse to accept — caught here before it ships.
    """

    @pytest.mark.parametrize("pack_id", OPTED_IN_PACKS)
    def test_strict_parse(self, pack_id: str) -> None:
        entries = load_pack_glosses(pack_id, strict=True)
        assert entries, f"{pack_id} has no parseable gloss entries"

    def test_total_entry_count_matches_standalone_verifier(self) -> None:
        # Standalone ``scripts/verify_definitional_closure.py`` reports
        # 342 entries.  Substrate strict-parse must see the same set
        # so the two verifiers agree on scope.
        total = sum(len(load_pack_glosses(p, strict=True)) for p in OPTED_IN_PACKS)
        assert total == 342, (
            f"Substrate parsed {total} entries; standalone verifier reports 342. "
            f"Divergence means one of the two verifiers is silently skipping rows."
        )


# --------------------------------------------------------------------------- #
# Closure rule against the production resolution pool
# --------------------------------------------------------------------------- #


class TestClosureAgainstProductionPool:
    """Every opted-in pack must close against (same-pack + production-
    mounted lexicon + primitives) — staging packs deliberately excluded.
    """

    @pytest.mark.parametrize("pack_id", OPTED_IN_PACKS)
    def test_pack_closes(
        self,
        pack_id: str,
        mounted_lex_lemmas: frozenset[str],
        primitives_lemmas: frozenset[str],
    ) -> None:
        violations = verify_definitional_closure(
            pack_id,
            mounted_pack_lemmas=mounted_lex_lemmas,
            primitive_lemmas=primitives_lemmas,
            strict=True,
        )
        assert violations == (), (
            f"{pack_id} has {len(violations)} unresolved tokens against the "
            f"production pool: "
            + ", ".join(f"{v.lemma}→{v.unresolved_token!r}" for v in violations)
        )

    def test_no_violations_total(
        self,
        mounted_lex_lemmas: frozenset[str],
        primitives_lemmas: frozenset[str],
    ) -> None:
        # Aggregate gate — the integration contract for ADR-0084 as a
        # whole: every opted-in pack closes against the production
        # pool with zero unresolved tokens.
        total_violations = 0
        for pack_id in OPTED_IN_PACKS:
            total_violations += len(
                verify_definitional_closure(
                    pack_id,
                    mounted_pack_lemmas=mounted_lex_lemmas,
                    primitive_lemmas=primitives_lemmas,
                    strict=True,
                )
            )
        assert total_violations == 0


# --------------------------------------------------------------------------- #
# Staging exclusion contract
# --------------------------------------------------------------------------- #


class TestStagingExclusion:
    """``en_minimal_v1`` is staging and must not be load-bearing for the
    closure rule.  If a future content edit makes any opted-in pack
    depend on en_minimal_v1 to resolve, this test catches it — that
    dependency would be a production-vs-staging leak.
    """

    def test_no_production_pack_depends_on_en_minimal_v1(
        self,
        primitives_lemmas: frozenset[str],
    ) -> None:
        # Build a pool WITHOUT en_minimal_v1 — the production pool.
        production_pool: set[str] = set()
        for pack_id in OPTED_IN_PACKS:
            for entry in load_pack_entries(pack_id):
                production_pool.add(entry.lemma.lower())
                production_pool.add(entry.surface.lower())

        # Then check: every opted-in pack closes against that pool.
        # If a pack secretly leans on en_minimal_v1, this fails with a
        # concrete unresolved-token list.
        for pack_id in OPTED_IN_PACKS:
            violations = verify_definitional_closure(
                pack_id,
                mounted_pack_lemmas=production_pool,
                primitive_lemmas=primitives_lemmas,
                strict=True,
            )
            assert not violations, (
                f"{pack_id} leaks into en_minimal_v1 — unresolved without "
                f"staging pool: "
                + ", ".join(f"{v.lemma}→{v.unresolved_token!r}" for v in violations)
            )


# --------------------------------------------------------------------------- #
# Primitives floor coverage
# --------------------------------------------------------------------------- #


class TestPrimitivesFloor:
    """Floor-level sanity: the primitives pack must carry the foundation
    words the brief named — and the ones the content ended up leaning
    on.  Catches accidental removals from the primitives pack."""

    REQUIRED_FLOOR = (
        # From the original ADR-0084 brief's category list
        "exist", "be", "not_be", "not",
        "same", "different",
        "cause", "because", "change",
        "say", "mean",
        "if", "then", "and", "or",
        # The ones added during integration because the content leaned
        # on them via en_minimal_v1 (which is staging and not load-
        # bearing) — promoted to primitives so production closure is
        # robust.
        "can", "action",
    )

    def test_required_primitives_present(self, primitives_lemmas: frozenset[str]) -> None:
        missing = sorted(set(self.REQUIRED_FLOOR) - primitives_lemmas)
        assert not missing, f"primitives pack missing required floor lemmas: {missing}"
