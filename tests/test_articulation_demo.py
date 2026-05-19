"""Articulation demo — pins the load-bearing claim per scene.

The headline claim: ``RuntimeConfig.discourse_planner=True`` produces
deterministic, grounded, multi-sentence articulation across EXPLAIN,
COMPOUND, and WALKTHROUGH prompt shapes; the same prompts under the
flag-off baseline collapse to single-anchor or OOV surfaces.

If any assertion below fails, the demo's headline claim no longer
holds.

Performance: ``run_demo()`` instantiates ~13 ``ChatRuntime`` objects
(3 scenes x 2 flags + 3 prompts x 3 reruns for determinism).  Module-
scoped fixture caches one run across every test in this file.
"""

from __future__ import annotations

import pytest

from evals.articulation.run_demo import run_demo


@pytest.fixture(scope="module")
def demo_report() -> dict:
    return run_demo(emit_json=True)


def test_demo_all_claims_supported(demo_report: dict) -> None:
    assert demo_report["all_claims_supported"] is True
    assert len(demo_report["scenes"]) == 4


def test_s1_explain_lifts_to_multi_sentence_teaching(demo_report: dict) -> None:
    s1 = demo_report["scenes"][0]
    assert s1["scene"] == "S1_explain"
    assert s1["detail"]["claim_supported"] is True
    on = s1["detail"]["flag_on"]
    off = s1["detail"]["flag_off"]
    assert on["grounding_source"] == "teaching"
    assert off["grounding_source"] == "pack"
    assert on["sentence_count"] >= off["sentence_count"] + 2
    assert on["sentence_count"] >= 3
    assert "truth" in on["surface"].lower()


def test_s2_compound_lifts_oov_to_grounded(demo_report: dict) -> None:
    s2 = demo_report["scenes"][1]
    assert s2["scene"] == "S2_compound"
    assert s2["detail"]["claim_supported"] is True
    on = s2["detail"]["flag_on"]
    off = s2["detail"]["flag_off"]
    assert on["grounding_source"] in {"pack", "teaching"}
    assert off["grounding_source"] in {"oov", "none"}
    assert on["sentence_count"] >= 4
    assert "haven't learned" in off["surface"].lower()
    assert "truth" in on["surface"].lower()


def test_s3_walkthrough_emits_chain_closure(demo_report: dict) -> None:
    s3 = demo_report["scenes"][2]
    assert s3["scene"] == "S3_walkthrough"
    assert s3["detail"]["claim_supported"] is True
    on = s3["detail"]["flag_on"]
    off = s3["detail"]["flag_off"]
    assert on["grounding_source"] == "teaching"
    # The CLOSURE chain hop appears only flag-on.
    assert "reveals memory" in on["surface"].lower()
    assert "reveals memory" not in off["surface"].lower()


def test_s4_determinism_byte_identical_across_reruns(demo_report: dict) -> None:
    s4 = demo_report["scenes"][3]
    assert s4["scene"] == "S4_determinism"
    assert s4["detail"]["all_identical"] is True
    assert s4["detail"]["reruns_per_prompt"] == 3
    per_prompt = s4["detail"]["per_prompt"]
    assert len(per_prompt) == 3
    for entry in per_prompt:
        assert entry["unique_surfaces"] == 1
        assert entry["identical"] is True


def test_demo_does_not_mutate_active_teaching_corpus() -> None:
    """Demo is read-only — re-running it twice must not change corpus bytes."""
    from chat import teaching_grounding as _tg

    before = _tg._CORPUS_PATH.read_bytes() if _tg._CORPUS_PATH.exists() else b""
    run_demo(emit_json=True)
    after = _tg._CORPUS_PATH.read_bytes() if _tg._CORPUS_PATH.exists() else b""
    assert before == after


def test_demo_json_shape_is_stable(demo_report: dict) -> None:
    """Stable JSON contract for downstream consumers."""
    assert set(demo_report.keys()) == {"scenes", "all_claims_supported"}
    for scene in demo_report["scenes"]:
        assert set(scene.keys()) == {"scene", "claim", "detail"}
