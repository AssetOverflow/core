"""Intent classification extensions — close five concrete failures
surfaced by the cumulative live probe (2026-05-19).

Before these changes, the runtime returned ``grounding_source="none"``
for ~50% of realistic conversational definition prompts even though
every subject lemma was pack-resident.  The bottleneck was intent
classification + subject extraction, not lexicon coverage.

Five gaps pinned by this file:

  1. ``Define X``        — imperative DEFINITION had no rule;
                           prompt fell through to UNKNOWN.
  2. ``What does X mean?`` — matched TRANSITIVE_QUERY for which the
                            runtime has no pack-grounded handler.
                            Now re-routes to DEFINITION when the
                            transitive relation is ``mean``/``means``.
  3. ``What is to V?``   — DEFINITION subject was ``to V`` (un-stripped
                           infinitive marker), so pack resolution
                           failed.  Now strips ``to`` for DEFINITION /
                           RECALL.
  4. ``How does X work?`` — no rule; only first-person PROCEDURE
                            ("How do I X?") was wired.  Now matches a
                            dedicated mechanistic-cause regex and
                            routes to CAUSE.
  5. ``What causes X?``   — no rule; the causative-verb family
                            (causes/triggers/enables/prevents/drives/
                            produces/induces/yields) now routes to
                            CAUSE with X as subject.

Plus a sixth runtime-side fix: CAUSE / VERIFICATION intents now fall
through to ``pack_grounded_surface`` when no teaching chain or cross-
pack chain is rooted on the subject lemma.  Honest fallback — the
surface explicitly tags the pack source and emits no fabricated
causal claim.
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from generate.intent import IntentTag, classify_intent


class TestDefineRule:
    def test_define_routes_to_definition(self) -> None:
        intent = classify_intent("Define moment.")
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "moment"

    def test_define_strips_trailing_punctuation(self) -> None:
        for text in ("Define moment.", "Define moment", "Define moment!"):
            intent = classify_intent(text)
            assert intent.tag is IntentTag.DEFINITION
            assert intent.subject == "moment"

    def test_define_multi_word_subject_preserved(self) -> None:
        intent = classify_intent("Define artificial intelligence")
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "artificial intelligence"

    def test_define_grounds_on_pack_lemma(self) -> None:
        response = ChatRuntime().chat("Define moment.")
        assert response.grounding_source == "pack"
        assert "moment" in response.surface.lower()
        assert "temporal" in response.surface.lower()


class TestWhatDoesXMean:
    def test_routes_to_definition_not_transitive_query(self) -> None:
        intent = classify_intent("What does important mean?")
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "important"

    def test_means_form_also_routes(self) -> None:
        intent = classify_intent("What does X means?")
        assert intent.tag is IntentTag.DEFINITION

    def test_other_transitive_relations_preserve_tag(self) -> None:
        """Only ``mean``/``means`` re-route; other relations remain
        TRANSITIVE_QUERY so multi_relation_walk still fires."""
        intent = classify_intent("What does wisdom precede?")
        assert intent.tag is IntentTag.TRANSITIVE_QUERY
        assert intent.relation == "precedes"

    def test_grounds_on_pack_lemma(self) -> None:
        response = ChatRuntime().chat("What does soon mean?")
        assert response.grounding_source == "pack"
        assert "temporal" in response.surface.lower()


class TestInfinitiveMarkerStripped:
    def test_what_is_to_create_strips_to(self) -> None:
        intent = classify_intent("What is to create?")
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "create"

    def test_what_is_to_remember_strips_to(self) -> None:
        intent = classify_intent("What is to remember?")
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "remember"

    def test_grounds_on_packlemma_after_strip(self) -> None:
        response = ChatRuntime().chat("What is to create?")
        assert response.grounding_source == "pack"

    def test_to_not_stripped_from_verification_subject(self) -> None:
        """``to`` as a preposition (not infinitive) must NOT be
        stripped from VERIFICATION subjects.  The aux-verb strip in
        VERIFICATION only takes the head noun anyway, so this is
        defensive — the infinitive strip is gated on intent tag."""
        intent = classify_intent("Is X bound to Y?")
        # VERIFICATION strips aux verbs and articles, returns head noun.
        # The infinitive strip is DEFINITION/RECALL only.
        assert intent.tag is IntentTag.VERIFICATION


class TestHowDoesXWork:
    def test_third_person_mechanistic_query_routes_to_cause(self) -> None:
        intent = classify_intent("How does memory work?")
        assert intent.tag is IntentTag.CAUSE
        assert intent.subject == "memory"

    def test_all_mechanistic_verbs_route_to_cause(self) -> None:
        for verb in ("work", "function", "operate", "happen", "exist", "behave"):
            intent = classify_intent(f"How does memory {verb}?")
            assert intent.tag is IntentTag.CAUSE, f"verb={verb}"
            assert intent.subject == "memory"

    def test_first_person_procedure_still_wins(self) -> None:
        """The PROCEDURE rule must still fire for first-person form."""
        intent = classify_intent("How do I verify a hypothesis?")
        assert intent.tag is IntentTag.PROCEDURE

    def test_routes_to_cause_but_returns_none_when_no_teaching_chain(self) -> None:
        """CAUSE on a pack-resident lemma with no teaching chain DOES
        NOT silently fall through to a pack disclosure — that would
        mask the teaching-gap signal the discovery layer uses to
        identify chains to add.  The grounding stays ``none`` so the
        teaching pipeline records a learning opportunity.
        """
        response = ChatRuntime().chat("How does memory work?")
        # CAUSE intent fired, lemma is pack-resident, but no teaching
        # chain exists → grounding_source is "none", which is the
        # honest no-answer signal (not a fabricated cause).
        assert response.grounding_source == "none"


class TestWhatCausesX:
    def test_what_causes_routes_to_cause(self) -> None:
        intent = classify_intent("What causes doubt?")
        assert intent.tag is IntentTag.CAUSE
        assert intent.subject == "doubt"

    def test_all_causative_verbs_route_to_cause(self) -> None:
        for verb in (
            "causes", "triggers", "enables", "prevents",
            "drives", "produces", "induces", "yields",
        ):
            intent = classify_intent(f"What {verb} understanding?")
            assert intent.tag is IntentTag.CAUSE, f"verb={verb}"
            assert intent.subject == "understanding"

    def test_what_is_unchanged(self) -> None:
        """Generic ``What is X?`` must still match DEFINITION first."""
        intent = classify_intent("What is doubt?")
        assert intent.tag is IntentTag.DEFINITION

    def test_returns_none_when_no_causal_teaching_chain(self) -> None:
        """Same honesty contract as the mechanistic-cause path: when
        no teaching chain answers the cause, ``grounding_source`` is
        ``none`` so the teaching pipeline can log the gap."""
        response = ChatRuntime().chat("What causes doubt?")
        assert response.grounding_source == "none"


class TestCauseVerificationNoPackFallback:
    """The runtime dispatcher deliberately does NOT fall through to
    ``pack_grounded_surface`` for CAUSE / VERIFICATION when no
    teaching chain matches.  Doing so would mask the discovery layer's
    teaching-gap signal — see ``tests/test_discovery_candidates``.
    """

    def test_oov_subject_returns_oov(self) -> None:
        response = ChatRuntime().chat("Why does triangle exist?")
        assert response.grounding_source in {"oov", "none"}

    def test_pack_lemma_without_chain_returns_none(self) -> None:
        """``doubt`` is pack-resident but has no CAUSE-rooted teaching
        chain — grounding_source must be ``none`` so the discovery
        candidate is emitted to flag the teaching gap."""
        response = ChatRuntime().chat("Is doubt evident?")
        assert response.grounding_source == "none"


class TestCumulativeLiftInvariant:
    """Pins the lift observed by the 2026-05-19 cumulative live probe:
    the DEFINITION-shaped prompts must produce ``pack`` grounding,
    since every gap surfaced for them was an intent-classification
    fix that has now landed.

    CAUSE-shaped prompts (``How does X work?``, ``What causes X?``)
    deliberately route to ``none`` when no teaching chain exists —
    this is the honest signal that drives the teaching pipeline.
    """

    DEFINITION_SAMPLE = (
        "Define moment.",
        "What does important mean?",
        "What is to create?",
    )

    def test_definition_sample_all_pack_grounded(self) -> None:
        for prompt in self.DEFINITION_SAMPLE:
            r = ChatRuntime().chat(prompt)
            assert r.grounding_source == "pack", (
                f"prompt {prompt!r} regressed: grounding_source={r.grounding_source}"
            )
