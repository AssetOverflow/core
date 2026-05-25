"""Executable validation gates for local language packs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from packs.common.runtime_rules import read_jsonl


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gate_schema(pack_dir: Path) -> tuple[bool, str]:
    required = ("lemmas.jsonl", "senses.jsonl", "morphology.jsonl", "probes/basic.jsonl")
    for rel in required:
        path = pack_dir / rel
        if not path.exists():
            return False, f"missing {rel}"
        try:
            read_jsonl(path)
        except json.JSONDecodeError as exc:
            return False, f"{rel}: invalid JSONL: {exc}"
    return True, "ok"


def _gate_lexical(pack_dir: Path) -> tuple[bool, str]:
    seen = set()
    for record in read_jsonl(pack_dir / "lemmas.jsonl"):
        lid = record["lemma_id"]
        if lid in seen:
            return False, f"duplicate lemma_id: {lid}"
        seen.add(lid)
        if not record.get("field_hooks"):
            return False, f"lemma has no field_hooks: {lid}"
    return True, "ok"


def _gate_morphology(pack_dir: Path) -> tuple[bool, str]:
    known = {record["lemma_id"] for record in read_jsonl(pack_dir / "lemmas.jsonl")}
    for record in read_jsonl(pack_dir / "morphology.jsonl"):
        if record["lemma_id"] not in known:
            return False, f"unknown lemma_id in morphology: {record['lemma_id']}"
    return True, "ok"


def _gate_lift(pack_dir: Path) -> tuple[bool, str]:
    lift_rules = _load_module(pack_dir / "lift_rules.py", f"{pack_dir.name}_lift_rules")
    for probe in read_jsonl(pack_dir / "probes" / "basic.jsonl"):
        if probe.get("kind") != "lift":
            continue
        packet = lift_rules.lift(probe["input"])[0]
        payload = json.loads(packet.payload_json)
        expected = probe["expected"]
        for key in ("field_target", "pressure_kind"):
            if key in expected and payload.get(key) != expected[key]:
                return False, f"{probe['probe_id']}: {key} {payload.get(key)!r} != {expected[key]!r}"
    return True, "ok"


def _gate_determinism(pack_dir: Path) -> tuple[bool, str]:
    lift_rules = _load_module(pack_dir / "lift_rules.py", f"{pack_dir.name}_lift_rules_det")
    for probe in read_jsonl(pack_dir / "probes" / "basic.jsonl"):
        if probe.get("kind") == "lift":
            left = lift_rules.lift(probe["input"])[0].payload_json
            right = lift_rules.lift(probe["input"])[0].payload_json
            if left != right:
                return False, f"{probe['probe_id']}: lift is nondeterministic"
    return True, "ok"


def _gate_alignment(pack_dir: Path) -> tuple[bool, str]:
    lemmas = {record["lemma_id"] for record in read_jsonl(pack_dir / "lemmas.jsonl")}
    senses = {record["sense_id"] for record in read_jsonl(pack_dir / "senses.jsonl")}
    for probe in read_jsonl(pack_dir / "probes" / "basic.jsonl"):
        if probe.get("kind") != "alignment":
            continue
        expected = probe["expected"]
        if expected.get("lemma_id") not in lemmas:
            return False, f"{probe['probe_id']}: unknown lemma anchor"
        if expected.get("sense_id") not in senses:
            return False, f"{probe['probe_id']}: unknown sense anchor"
    return True, "ok"


def _gate_coverage(pack_dir: Path) -> tuple[bool, str]:
    covered = {probe["kind"] for probe in read_jsonl(pack_dir / "probes" / "basic.jsonl")}
    required = {"normalize", "lift", "alignment"}
    missing = required - covered
    if missing:
        return False, f"missing probe kind(s): {', '.join(sorted(missing))}"
    return True, "ok"


def validate_pack_dir(pack_dir: Path, *, pack_id: str, language: str) -> dict:
    gates = (
        ("schema", lambda: _gate_schema(pack_dir)),
        ("lexical", lambda: _gate_lexical(pack_dir)),
        ("morphology", lambda: _gate_morphology(pack_dir)),
        ("lift", lambda: _gate_lift(pack_dir)),
        ("determinism", lambda: _gate_determinism(pack_dir)),
        ("alignment", lambda: _gate_alignment(pack_dir)),
        ("coverage", lambda: _gate_coverage(pack_dir)),
    )
    report = {"pack_id": pack_id, "language": language, "active": False, "gates": {}}
    for index, (name, gate_fn) in enumerate(gates):
        passed, reason = gate_fn()
        report["gates"][name] = {"passed": passed, "reason": reason}
        if not passed:
            for remaining_name, _ in gates[index + 1:]:
                report["gates"][remaining_name] = {"passed": False, "reason": "blocked by prior gate failure"}
            return report
    report["active"] = True
    return report
