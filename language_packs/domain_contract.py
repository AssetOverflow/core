"""ADR-0091 domain-pack contract validation.

This module is intentionally read-only. It validates optional manifest
metadata that links a language pack to capability-ledger evidence, but it
does not mutate packs and it does not promote capability status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ALLOWED_SPLITS = {"dev", "public", "holdout"}
_KNOWN_DOMAIN_IDS = {
    "systems_software",
    "mathematics_logic",
    "physics",
    "hebrew_greek_textual_reasoning",
    "philosophy_theology",
}
_SCOPE_BOUNDARY_PREFIX = "scope_boundary"


@dataclass(frozen=True, slots=True)
class DomainEvalLane:
    lane: str
    version: str
    splits: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DomainPackContract:
    domain_contract_version: int
    domain_id: str
    axioms: str | None
    rules: str | None
    teaching_chains: tuple[str, ...] = field(default_factory=tuple)
    eval_lanes: tuple[DomainEvalLane, ...] = field(default_factory=tuple)
    reviewers: tuple[str, ...] = field(default_factory=tuple)
    known_gaps: tuple[str, ...] = field(default_factory=tuple)
    provenance: str = ""


@dataclass(frozen=True, slots=True)
class DomainContractValidation:
    pack_id: str
    present: bool
    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    contract: DomainPackContract | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "present": self.present,
            "valid": self.valid,
            "errors": list(self.errors),
            "contract": _contract_as_dict(self.contract) if self.contract else None,
        }


def _contract_as_dict(contract: DomainPackContract | None) -> dict[str, Any] | None:
    if contract is None:
        return None
    return {
        "domain_contract_version": contract.domain_contract_version,
        "domain_id": contract.domain_id,
        "axioms": contract.axioms,
        "rules": contract.rules,
        "teaching_chains": list(contract.teaching_chains),
        "eval_lanes": [
            {"lane": lane.lane, "version": lane.version, "splits": list(lane.splits)}
            for lane in contract.eval_lanes
        ],
        "reviewers": list(contract.reviewers),
        "known_gaps": list(contract.known_gaps),
        "provenance": contract.provenance,
    }


def _as_string_tuple(value: object, *, field_name: str, errors: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        errors.append(f"{field_name}:must_be_list")
        return ()
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field_name}[{idx}]:must_be_nonempty_string")
            continue
        out.append(item.strip())
    return tuple(out)


def _optional_path(value: object, *, field_name: str, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name}:must_be_null_or_nonempty_string")
        return None
    if Path(value).is_absolute() or ".." in Path(value).parts:
        errors.append(f"{field_name}:unsafe_path")
        return None
    return value.strip()


def parse_domain_contract(manifest: dict[str, Any], *, pack_id: str) -> DomainContractValidation:
    if "domain_contract_version" not in manifest:
        return DomainContractValidation(pack_id=pack_id, present=False, valid=True)

    errors: list[str] = []
    version_raw = manifest.get("domain_contract_version")
    if version_raw != 1:
        errors.append("domain_contract_version:unsupported")
        version = 0
    else:
        version = 1

    domain_id = manifest.get("domain_id")
    if not isinstance(domain_id, str) or not domain_id.strip():
        errors.append("domain_id:required")
        domain_id_s = ""
    else:
        domain_id_s = domain_id.strip()
        if domain_id_s not in _KNOWN_DOMAIN_IDS:
            errors.append(f"{_SCOPE_BOUNDARY_PREFIX}:domain_id:unknown")

    axioms = _optional_path(manifest.get("axioms"), field_name="axioms", errors=errors)
    rules = _optional_path(manifest.get("rules"), field_name="rules", errors=errors)
    teaching_chains = _as_string_tuple(
        manifest.get("teaching_chains"), field_name="teaching_chains", errors=errors
    )
    reviewers = _as_string_tuple(manifest.get("reviewers"), field_name="reviewers", errors=errors)
    known_gaps = _as_string_tuple(manifest.get("known_gaps"), field_name="known_gaps", errors=errors)

    eval_lanes: list[DomainEvalLane] = []
    raw_lanes = manifest.get("eval_lanes")
    if raw_lanes is None:
        raw_lanes = []
    if not isinstance(raw_lanes, list):
        errors.append("eval_lanes:must_be_list")
    else:
        for idx, raw in enumerate(raw_lanes):
            if not isinstance(raw, dict):
                errors.append(f"eval_lanes[{idx}]:must_be_object")
                continue
            lane = raw.get("lane")
            version_s = raw.get("version")
            splits_raw = raw.get("splits")
            if not isinstance(lane, str) or not lane.strip():
                errors.append(f"eval_lanes[{idx}].lane:required")
                continue
            if not isinstance(version_s, str) or not version_s.strip():
                errors.append(f"eval_lanes[{idx}].version:required")
                continue
            splits = _as_string_tuple(splits_raw, field_name=f"eval_lanes[{idx}].splits", errors=errors)
            unknown = sorted(set(splits) - _ALLOWED_SPLITS)
            if unknown:
                errors.append(f"eval_lanes[{idx}].splits:unknown:{','.join(unknown)}")
            eval_lanes.append(DomainEvalLane(lane=lane.strip(), version=version_s.strip(), splits=splits))

    provenance = manifest.get("provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        errors.append("provenance:required")
        provenance_s = ""
    else:
        provenance_s = provenance.strip()

    contract = DomainPackContract(
        domain_contract_version=version,
        domain_id=domain_id_s,
        axioms=axioms,
        rules=rules,
        teaching_chains=teaching_chains,
        eval_lanes=tuple(eval_lanes),
        reviewers=reviewers,
        known_gaps=known_gaps,
        provenance=provenance_s,
    )
    return DomainContractValidation(
        pack_id=pack_id,
        present=True,
        valid=not errors,
        errors=tuple(errors),
        contract=contract,
    )


def validate_domain_contract_pack(pack_id: str, *, data_root: Path | None = None) -> DomainContractValidation:
    root = data_root or Path(__file__).resolve().parent / "data"
    manifest_path = root / pack_id / "manifest.json"
    if not manifest_path.exists():
        return DomainContractValidation(
            pack_id=pack_id,
            present=False,
            valid=True,
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DomainContractValidation(
            pack_id=pack_id,
            present=False,
            valid=False,
            errors=("manifest:invalid_json",),
        )
    if not isinstance(manifest, dict):
        return DomainContractValidation(
            pack_id=pack_id,
            present=False,
            valid=False,
            errors=("manifest:must_be_object",),
        )
    return parse_domain_contract(manifest, pack_id=pack_id)
