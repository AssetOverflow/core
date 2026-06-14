"""C2-b — the contemplation loop as a typed staged projection.

The reader turns each scene into a canonical loop stage (cold attempt → engine
enrichment → engine-authored proposal → operator ratifies → grounded) and pulls
the connective ids (proposal/candidate/state/grounding) out of the raw detail so
the UI renders a process, not a JSON dump.
"""

from __future__ import annotations

import pytest

from workbench import readers


class TestStageRole:
    @pytest.mark.parametrize(
        "scene_id,role",
        [
            ("S1_cold_session", "cold_attempt"),
            ("S2_checkpoint_enrichment", "engine_enrichment"),
            ("S3_engine_authored_proposal", "engine_proposal"),
            ("S4_operator_ratifies", "operator_ratifies"),
            ("S5_grounded_session", "grounded"),
        ],
    )
    def test_canonical_arc_ids_map_to_roles(self, scene_id: str, role: str) -> None:
        assert readers._contemplation_stage_role(scene_id) == role

    def test_unknown_scene_id_falls_back_to_other(self) -> None:
        # Honest closed set: anything outside the arc is "other", never guessed.
        assert readers._contemplation_stage_role("S9_unmapped_thing") == "other"
        assert readers._contemplation_stage_role("") == "other"


class TestSceneProjection:
    def test_connective_ids_are_pulled_from_detail(self) -> None:
        report = {
            "scenes": [
                {
                    "scene": "S1_cold_session",
                    "claim": "cold",
                    "detail": {"grounding_source": "none"},
                },
                {
                    "scene": "S2_checkpoint_enrichment",
                    "claim": "enrich",
                    "detail": {"candidate_id": "cand-123"},
                },
                {
                    "scene": "S3_engine_authored_proposal",
                    "claim": "propose",
                    "detail": {"proposal_id": "prop-456", "state": "pending"},
                },
            ]
        }
        scenes = readers._contemplation_scenes(report)
        s1, s2, s3 = scenes
        assert (s1.stage_role, s1.grounding_source) == ("cold_attempt", "none")
        assert (s2.stage_role, s2.candidate_id) == ("engine_enrichment", "cand-123")
        assert s3.stage_role == "engine_proposal"
        assert s3.proposal_id == "prop-456"
        assert s3.proposal_state == "pending"
        # Absent ids stay None, never empty strings.
        assert s1.proposal_id is None and s1.candidate_id is None

    def test_detail_is_preserved_for_the_inspector(self) -> None:
        report = {"scenes": [{"scene": "S1_cold_session", "claim": "c", "detail": {"x": 1}}]}
        (scene,) = readers._contemplation_scenes(report)
        assert scene.detail == {"x": 1}

    def test_non_dict_scene_is_skipped(self) -> None:
        report = {"scenes": ["not a scene", {"scene": "S1_cold_session", "claim": "c"}]}
        scenes = readers._contemplation_scenes(report)
        assert len(scenes) == 1
        assert scenes[0].stage_role == "cold_attempt"
