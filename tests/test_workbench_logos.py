from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from workbench import logos
from workbench.schemas import LogosMorphologyLinkIssue, SafetyVerdict, to_data


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "language_packs" / "data"
LOGOS_PACK_IDS = [
    "grc_logos_cognition_v1",
    "grc_logos_micro_v1",
    "he_core_cognition_v1",
    "he_logos_micro_v1",
]


def _copy_language_pack_root(tmp_path: Path) -> Path:
    root = tmp_path / "language_packs_data"
    shutil.copytree(DATA_ROOT, root)
    return root


def _rewrite_first_jsonl_object(
    path: Path, mutator: Callable[[dict[str, Any]], None]
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        payload = json.loads(line)
        mutator(payload)
        lines[idx] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _refresh_lexicon_checksum(pack_dir: Path) -> None:
    manifest_path = pack_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checksum"] = hashlib.sha256(
        (pack_dir / "lexicon.jsonl").read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_list_logos_packs_filters_to_the_readonly_logos_universe() -> None:
    packs = logos.list_logos_packs()

    assert [pack.pack_id for pack in packs] == LOGOS_PACK_IDS
    assert "en_core_relations_v3" not in {pack.pack_id for pack in packs}
    assert all(pack.holonomy_case_count == 0 for pack in packs)


def test_overview_counts_and_honest_absent_holonomy() -> None:
    overview = logos.logos_pack_overview("he_logos_micro_v1")

    assert overview.lexicon_count == 9
    assert overview.gloss_count == 9
    assert overview.morphology_count == 9
    assert overview.alignment_edge_count == 11
    assert overview.holonomy_case_count == 0
    assert overview.safety_status is SafetyVerdict.UNKNOWN

    contents = logos.logos_pack_contents("he_logos_micro_v1")
    payload = to_data(contents)
    assert payload["holonomy_cases"] == []
    assert "success" not in payload
    assert "proof" not in payload


def test_contents_project_lexicon_gloss_morphology_and_alignment_rows() -> None:
    contents = logos.logos_pack_contents("he_logos_micro_v1")

    davar = next(row for row in contents.lexicon if row.entry_id == "he-001")
    assert davar.lemma == "דבר"
    assert davar.morphology_id == "he-morph-001"
    assert davar.epistemic_status == "speculative"

    davar_gloss = next(row for row in contents.glosses if row.lemma == "דבר")
    assert davar_gloss.gloss == "word, matter, or spoken thing"
    assert davar_gloss.entry_ids == ["he-001", "he-008"]

    devarim = next(
        row for row in contents.morphology if row.morphology_id == "he-morph-008"
    )
    assert devarim.prefix_chain == []
    assert devarim.stem == "דבר"
    assert devarim.suffix_chain == ["ים"]

    edge = contents.alignment_edges[0]
    expected_edge_id = hashlib.sha256(
        b"he-001|grc-001|cross_lang.logos.utterance"
    ).hexdigest()[:16]
    assert edge.edge_id == expected_edge_id
    assert edge.invalid_target is False
    assert edge.target_pack_id == "grc_logos_micro_v1"


def test_safety_reports_unknown_holonomy_without_calling_it_clear() -> None:
    report = logos.logos_pack_safety("he_logos_micro_v1")

    assert report.checksum_status is SafetyVerdict.CLEAR
    assert report.domain_contract_status is SafetyVerdict.CLEAR
    assert report.missing_holonomy_refs is SafetyVerdict.UNKNOWN
    assert report.verdict is SafetyVerdict.UNKNOWN
    assert report.verdict is not SafetyVerdict.CLEAR
    assert report.dangling_morphology_links == []
    assert report.invalid_alignment_targets == []


def test_dangling_morphology_link_is_listed_without_checksum_noise(
    tmp_path: Path,
) -> None:
    data_root = _copy_language_pack_root(tmp_path)
    pack_dir = data_root / "he_logos_micro_v1"
    _rewrite_first_jsonl_object(
        pack_dir / "lexicon.jsonl",
        lambda row: row.__setitem__("morphology_id", "missing-morph-001"),
    )
    _refresh_lexicon_checksum(pack_dir)

    report = logos.logos_pack_safety("he_logos_micro_v1", data_root=data_root)

    assert report.checksum_status is SafetyVerdict.CLEAR
    assert report.verdict is SafetyVerdict.WARNING
    assert report.dangling_morphology_links == [
        LogosMorphologyLinkIssue(
            entry_id="he-001",
            morphology_id="missing-morph-001",
        )
    ]


def test_checksum_mismatch_is_failed_and_not_clear(tmp_path: Path) -> None:
    data_root = _copy_language_pack_root(tmp_path)
    pack_dir = data_root / "he_logos_micro_v1"
    _rewrite_first_jsonl_object(
        pack_dir / "lexicon.jsonl",
        lambda row: row.__setitem__("surface", "דבר-corrupted"),
    )

    report = logos.logos_pack_safety("he_logos_micro_v1", data_root=data_root)

    assert report.checksum_status is SafetyVerdict.FAILED
    assert report.verdict is SafetyVerdict.FAILED
    assert report.verdict is not SafetyVerdict.CLEAR
    assert any(
        "lexicon_checksum:mismatch" in error for error in report.checksum_errors
    )


def test_invalid_alignment_target_is_listed_without_touching_engine_validators(
    tmp_path: Path,
) -> None:
    data_root = _copy_language_pack_root(tmp_path)
    pack_dir = data_root / "he_logos_micro_v1"
    _rewrite_first_jsonl_object(
        pack_dir / "alignment.jsonl",
        lambda row: row.__setitem__("target_id", "ghost-target"),
    )

    report = logos.logos_pack_safety("he_logos_micro_v1", data_root=data_root)

    assert report.checksum_status is SafetyVerdict.CLEAR
    assert report.verdict is SafetyVerdict.WARNING
    assert [
        (issue.source_id, issue.target_id, issue.relation)
        for issue in report.invalid_alignment_targets
    ] == [("he-001", "ghost-target", "cross_lang.logos.utterance")]


def test_every_collapse_anchor_target_resolves_to_a_declared_entry() -> None:
    """Every ``cross_lang.no_english_collapse`` target across the logos packs
    resolves to a real declared lexicon entry — the substrate genuinely links,
    not suppressed.

    Reconciliation fix: the anchor pack (``en_collapse_anchors_v1``) now declares
    the full referenced anchor set (covenant_love/shalom/tzedek +
    heart/soul/breath/holy/time), so no edge dangles. This is the geometry
    resolving, not the check being bypassed — the relation/prefix carve-out
    stays removed. See docs/handoff/logos-collapse-anchor-reconciliation-2026-06-14.md.
    """
    for pack_id in ("grc_logos_cognition_v1", "he_core_cognition_v1"):
        rows = logos.logos_pack_alignment(pack_id)
        collapse = [r for r in rows if r.relation == "cross_lang.no_english_collapse"]
        assert collapse, f"{pack_id} should declare collapse edges"
        unresolved = [r.target_id for r in collapse if r.invalid_target]
        assert unresolved == [], f"{pack_id} has unresolved collapse anchors: {unresolved}"

        report = logos.logos_pack_safety(pack_id)
        assert report.invalid_alignment_targets == []
        # Resolved, but never CLEAR while holonomy proof is absent (honest ceiling).
        assert report.verdict is not SafetyVerdict.CLEAR

    # A previously-dangling anchor (breath) and a source-concept anchor
    # (covenant_love) both resolve to the anchor pack now.
    by_target = {
        r.target_id: r
        for r in logos.logos_pack_alignment("he_core_cognition_v1")
        if r.relation == "cross_lang.no_english_collapse"
    }
    for anchor in ("en-collapse-breath", "en-collapse-covenant_love"):
        assert by_target[anchor].invalid_target is False
        assert by_target[anchor].target_pack_id == "en_collapse_anchors_v1"


def test_no_algebra_imports_in_workbench_logos_module() -> None:
    tree = ast.parse((REPO_ROOT / "workbench" / "logos.py").read_text(encoding="utf-8"))

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    assert not any(
        name == "algebra" or name.startswith("algebra.") for name in imported
    )
