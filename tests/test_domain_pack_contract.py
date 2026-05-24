from __future__ import annotations

import json

from language_packs.domain_contract import parse_domain_contract, validate_domain_contract_pack


def test_absent_domain_contract_is_valid_noop() -> None:
    result = parse_domain_contract({"pack_id": "plain_pack"}, pack_id="plain_pack")

    assert result.present is False
    assert result.valid is True
    assert result.contract is None


def test_missing_manifest_is_valid_absent_noop(tmp_path) -> None:
    result = validate_domain_contract_pack("missing_pack", data_root=tmp_path)

    assert result.present is False
    assert result.valid is True
    assert result.errors == ()
    assert result.contract is None


def test_valid_domain_contract_parses_optional_axioms_rules() -> None:
    result = parse_domain_contract(
        {
            "domain_contract_version": 1,
            "domain_id": "mathematics_logic",
            "axioms": "axioms/math_logic_v1.jsonl",
            "rules": None,
            "teaching_chains": ["math_logic_chains_v1"],
            "eval_lanes": [
                {
                    "lane": "mathematics_logic",
                    "version": "v1",
                    "splits": ["dev", "public", "holdout"],
                }
            ],
            "reviewers": ["logic_reviewer"],
            "known_gaps": ["gap:mathematics_logic_transitive_chains_below_threshold"],
            "provenance": "adr-0090:reviewed:2026-05-21",
        },
        pack_id="math_logic_seed_v1",
    )

    assert result.present is True
    assert result.valid is True
    assert result.errors == ()
    assert result.contract is not None
    assert result.contract.axioms == "axioms/math_logic_v1.jsonl"
    assert result.contract.rules is None


def test_domain_contract_rejects_unsafe_paths_and_marks_unknown_domain_scope_boundary() -> None:
    result = parse_domain_contract(
        {
            "domain_contract_version": 1,
            "domain_id": "not_a_domain",
            "axioms": "../escape.jsonl",
            "rules": "/tmp/rules.jsonl",
            "provenance": "",
        },
        pack_id="bad_pack",
    )

    assert result.valid is False
    assert "scope_boundary:domain_id:unknown" in result.errors
    assert "domain_id:unknown" not in result.errors
    assert "axioms:unsafe_path" in result.errors
    assert "rules:unsafe_path" in result.errors
    assert "provenance:required" in result.errors


def test_validate_domain_contract_pack_reads_manifest(tmp_path) -> None:
    pack_dir = tmp_path / "pack_v1"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        json.dumps(
            {
                "domain_contract_version": 1,
                "domain_id": "physics",
                "axioms": None,
                "rules": None,
                "teaching_chains": [],
                "eval_lanes": [],
                "reviewers": [],
                "known_gaps": ["gap:physics_pack_absent"],
                "provenance": "adr-0090:reviewed:2026-05-21",
            }
        ),
        encoding="utf-8",
    )

    result = validate_domain_contract_pack("pack_v1", data_root=tmp_path)

    assert result.present is True
    assert result.valid is True
    assert result.contract is not None
    assert result.contract.domain_id == "physics"
