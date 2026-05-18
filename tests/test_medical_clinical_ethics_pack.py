"""ADR-0044 — worked-example domain ethics pack end-to-end.

Locks in the load-bearing claims of the domain-pack worked example:

1. The pack ratifies through the formation pipeline (self-sealed
   `MasteryReport` with matching `mastery_report_sha256`).
2. The pack loads in production mode (i.e. the sealed report verifies).
3. Selecting the pack via `RuntimeConfig(ethics_pack=...)` composes its
   commitments into the runtime manifold boundary set without losing
   the universal safety floor.
4. `refusal_commitments` and `hedge_commitments` are mutually exclusive
   and only cite known commitment ids.
"""
from __future__ import annotations

import json
from pathlib import Path

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.ethics.loader import load_ethics_pack
from packs.safety.loader import load_safety_pack


PACK_ID = "medical_clinical_ethics_v1"
PACK_PATH = Path("packs/ethics") / f"{PACK_ID}.json"
REPORT_PATH = Path("packs/ethics") / f"{PACK_ID}.mastery_report.json"


class TestPackRatified:
    def test_pack_file_exists(self) -> None:
        assert PACK_PATH.is_file()
        assert REPORT_PATH.is_file()

    def test_mastery_report_sha_is_set(self) -> None:
        pack = json.loads(PACK_PATH.read_text())
        assert pack["mastery_report_sha256"]
        assert len(pack["mastery_report_sha256"]) == 64

    def test_loader_accepts_ratified_pack(self) -> None:
        pack = load_ethics_pack(PACK_ID)
        assert pack.pack_id == PACK_ID
        assert pack.domain == "medical"


class TestDomainCommitments:
    def test_six_domain_commitments(self) -> None:
        pack = load_ethics_pack(PACK_ID)
        assert len(pack.commitment_ids) == 6
        assert "no_dosing_recommendation" in pack.commitment_ids
        assert "no_emergency_triage_authority" in pack.commitment_ids
        assert "defer_diagnosis_to_clinician" in pack.commitment_ids

    def test_refusal_and_hedge_are_disjoint(self) -> None:
        pack = load_ethics_pack(PACK_ID)
        overlap = pack.refusal_commitments & pack.hedge_commitments
        assert overlap == frozenset(), overlap

    def test_remediation_lists_are_subsets_of_commitments(self) -> None:
        pack = load_ethics_pack(PACK_ID)
        known = set(pack.commitment_ids)
        assert set(pack.refusal_commitments) <= known
        assert set(pack.hedge_commitments) <= known


class TestRuntimeComposition:
    def test_manifold_includes_safety_floor_and_medical_commitments(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(ethics_pack=PACK_ID))
        boundary_ids = set(rt.identity_manifold.boundary_ids)
        safety = load_safety_pack()
        # Safety floor unioned in.
        for safety_id in safety.boundary_ids:
            assert safety_id in boundary_ids, safety_id
        # Medical commitments unioned in.
        medical_pack = load_ethics_pack(PACK_ID)
        for c in medical_pack.commitment_ids:
            assert c in boundary_ids, c

    def test_default_general_does_not_include_medical_commitments(self) -> None:
        """Pack swap is visible — default pack must not carry the medical floor."""
        rt = ChatRuntime(config=RuntimeConfig(ethics_pack="default_general_ethics_v1"))
        boundary_ids = set(rt.identity_manifold.boundary_ids)
        assert "no_dosing_recommendation" not in boundary_ids
        assert "no_emergency_triage_authority" not in boundary_ids
