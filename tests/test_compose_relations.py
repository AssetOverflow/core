"""Unit tests for compose_relations operator and FRAME_TRANSFER intent.

Covers the compositionality lane's `novel_pair_under_seen_relation`
pattern: given R(A, a_val) and R(B, b_val), the probe "What does A R
in B?" should yield both tails.
"""

from __future__ import annotations

from generate.intent import IntentTag, classify_intent
from generate.operators import FrameComposeResult, compose_relations


class TestComposeRelations:
    def test_returns_both_tails_when_both_edges_present(self):
        triples = (
            ("truth", "grounds", "judgment"),
            ("knowledge", "grounds", "inference"),
        )
        result = compose_relations(
            triples, head="truth", frame="knowledge", relation="grounds"
        )
        assert result.subject_tail == "judgment"
        assert result.frame_tail == "inference"

    def test_returns_none_for_missing_edge(self):
        triples = (("truth", "grounds", "judgment"),)
        result = compose_relations(
            triples, head="truth", frame="knowledge", relation="grounds"
        )
        assert result.subject_tail == "judgment"
        assert result.frame_tail is None

    def test_case_insensitive_inputs(self):
        triples = (("Truth", "Grounds", "Judgment"),)
        result = compose_relations(
            triples, head="TRUTH", frame="knowledge", relation="GROUNDS"
        )
        assert result.head == "truth"
        assert result.subject_tail == "judgment"

    def test_first_write_wins_for_duplicate_heads(self):
        triples = (
            ("truth", "grounds", "judgment"),
            ("truth", "grounds", "second"),
        )
        result = compose_relations(
            triples, head="truth", frame="truth", relation="grounds"
        )
        assert result.subject_tail == "judgment"

    def test_pure_function_replay_deterministic(self):
        triples = (
            ("truth", "grounds", "judgment"),
            ("knowledge", "grounds", "inference"),
        )
        a = compose_relations(triples, "truth", "knowledge", "grounds")
        b = compose_relations(triples, "truth", "knowledge", "grounds")
        assert a == b

    def test_as_dict_is_json_safe(self):
        result = FrameComposeResult(
            head="truth",
            frame="knowledge",
            relation="grounds",
            subject_tail="judgment",
            frame_tail="inference",
        )
        d = result.as_dict()
        assert d["head"] == "truth"
        assert d["frame_tail"] == "inference"


class TestFrameTransferIntent:
    def test_classifies_frame_transfer_form(self):
        intent = classify_intent("What does truth ground in knowledge?")
        assert intent.tag is IntentTag.FRAME_TRANSFER
        assert intent.subject == "truth"
        assert intent.relation == "grounds"
        assert intent.frame == "knowledge"

    def test_belong_to_in_form_normalises_to_belongs_to(self):
        intent = classify_intent("What does recognition belong to in naming?")
        assert intent.tag is IntentTag.FRAME_TRANSFER
        assert intent.subject == "recognition"
        assert intent.relation == "belongs_to"
        assert intent.frame == "naming"

    def test_does_not_match_single_entity_probe(self):
        intent = classify_intent("What does wisdom precede?")
        assert intent.tag is IntentTag.TRANSITIVE_QUERY
        assert intent.frame is None
