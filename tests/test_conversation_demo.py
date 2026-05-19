"""Conversation demo — pins the layperson-facing chat transcript.

These tests use ``stream=False`` so the demo runs instantly.  They
verify the structured JSON report (which is what downstream
consumers integrate against), not the streamed visual layout.
"""

from __future__ import annotations

import pytest

from evals.conversation.run_demo import run_demo


@pytest.fixture(scope="module")
def demo_report() -> dict:
    return run_demo(emit_json=True, stream=False)


def test_demo_has_five_turns(demo_report: dict) -> None:
    assert len(demo_report["turns"]) == 5


def test_demo_closes_the_learning_loop(demo_report: dict) -> None:
    assert demo_report["learning_loop_closed"] is True
    assert demo_report["active_corpus_byte_identical"] is True


def test_scene1_pack_lookup_grounds_in_pack(demo_report: dict) -> None:
    s1 = demo_report["turns"][0]
    assert s1["scene"] == "S1_pack_lookup"
    assert s1["prompt"] == "What is truth?"
    assert s1["grounding_source"] == "pack"
    assert "truth" in s1["surface"].lower()
    assert "lexicon" in s1["note"].lower()


def test_scene2_teaching_chain_grounds_in_teaching(demo_report: dict) -> None:
    s2 = demo_report["turns"][1]
    assert s2["scene"] == "S2_teaching_chain"
    assert s2["prompt"] == "Walk me through recall."
    assert s2["grounding_source"] == "teaching"
    assert "reveals memory" in s2["surface"].lower()
    assert "chain" in s2["note"].lower()


def test_scene3_compound_handles_both_clauses(demo_report: dict) -> None:
    s3 = demo_report["turns"][2]
    assert s3["scene"] == "S3_compound"
    assert s3["grounding_source"] in {"pack", "teaching"}
    sentence_count = sum(1 for ch in s3["surface"] if ch in ".!?")
    assert sentence_count >= 4
    assert "truth" in s3["surface"].lower()


def test_scene4_cold_turn_does_not_make_up_an_answer(demo_report: dict) -> None:
    s4a = demo_report["turns"][3]
    assert s4a["scene"] == "S4a_cold_turn"
    assert s4a["grounding_source"] in {"none", "oov"}
    surface_low = s4a["surface"].lower()
    assert "don't know" in surface_low or "haven't learned" in surface_low or "insufficient" in surface_low


def test_scene4_after_teaching_is_grounded_with_new_chain(demo_report: dict) -> None:
    s4b = demo_report["turns"][4]
    assert s4b["scene"] == "S4b_after_teaching"
    assert s4b["grounding_source"] == "teaching"
    surface_low = s4b["surface"].lower()
    assert "narrative" in surface_low
    assert "meaning" in surface_low


def test_demo_json_shape_is_stable(demo_report: dict) -> None:
    assert set(demo_report.keys()) == {
        "turns", "learning_loop_closed", "active_corpus_byte_identical",
    }
    for turn in demo_report["turns"]:
        assert set(turn.keys()) == {
            "scene", "prompt", "surface", "grounding_source", "note",
        }


def test_humanize_surface_rewrites_teaching_grounded() -> None:
    """The display-only humaniser must put the propositional sentence
    first and keep every load-bearing token from the production
    teaching-grounded format."""
    from evals.conversation.run_demo import _humanize_surface

    raw = (
        "narrative — teaching-grounded (cognition_chains_v1): "
        "rhetoric.narrative; language.discourse. narrative reveals meaning "
        "(cognition.meaning). No session evidence yet."
    )
    out = _humanize_surface(raw, grounding_source="teaching")
    # Propositional sentence first, sentence-cased.
    assert out.startswith("Narrative reveals meaning.")
    # Every load-bearing token preserved (trust boundary).
    assert "teaching-grounded" in out
    assert "cognition_chains_v1" in out
    assert "rhetoric.narrative" in out
    assert "language.discourse" in out
    assert "cognition.meaning" in out
    assert "No session evidence yet." in out


def test_humanize_surface_is_passthrough_for_non_teaching() -> None:
    from evals.conversation.run_demo import _humanize_surface

    pack_surface = "Truth is a claim. pack-grounded (en_core_cognition_v1)."
    assert _humanize_surface(pack_surface, grounding_source="pack") == pack_surface

    discourse_surface = "Recall is to retrieve a stored state from memory. Recall reveals memory."
    # Discourse-planner output doesn't match the raw teaching-grounded
    # format — passes through unchanged.
    assert _humanize_surface(discourse_surface, grounding_source="teaching") == discourse_surface


def test_demo_does_not_mutate_active_teaching_corpus() -> None:
    """The demo must be read-only against the live corpus."""
    from chat import teaching_grounding as _tg

    before = _tg._CORPUS_PATH.read_bytes() if _tg._CORPUS_PATH.exists() else b""
    run_demo(emit_json=True, stream=False)
    after = _tg._CORPUS_PATH.read_bytes() if _tg._CORPUS_PATH.exists() else b""
    assert before == after
