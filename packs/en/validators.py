"""
Validators for the English base pack.

Runs all eight gates in sequence and returns a ValidationReport.
A gate failure halts further validation — the pack is not partially active.

Gate status reflects current implementation reality.
Do not mark a gate True until it passes programmatically.
"""

from __future__ import annotations
import json
from pathlib import Path

PACK_DIR = Path(__file__).parent


def _gate_schema() -> tuple[bool, str]:
    """Validate all .jsonl files against their JSON Schema counterparts."""
    # Requires: jsonschema library and schema files under packs/common/schema/
    # Status: schema files exist; validation runner not yet wired.
    return False, "not yet wired"


def _gate_lexical() -> tuple[bool, str]:
    """Check lemma_id uniqueness and field_hook validity."""
    seen = set()
    for line in (PACK_DIR / "lemmas.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        lid = record["lemma_id"]
        if lid in seen:
            return False, f"duplicate lemma_id: {lid}"
        seen.add(lid)
    return True, "ok"


def _gate_morphology() -> tuple[bool, str]:
    """Check all morphology records reference a known lemma_id."""
    known = set()
    for line in (PACK_DIR / "lemmas.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            known.add(json.loads(line)["lemma_id"])
    for line in (PACK_DIR / "morphology.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["lemma_id"] not in known:
            return False, f"unknown lemma_id in morphology: {record['lemma_id']}"
    return True, "ok"


def _gate_lift() -> tuple[bool, str]:
    """Run lift probes. Blocked on lift() implementation."""
    return False, "lift() not yet implemented"


def _gate_readback() -> tuple[bool, str]:
    """Run readback probes. Blocked on readback() implementation."""
    return False, "readback() not yet implemented"


def _gate_determinism() -> tuple[bool, str]:
    """Verify normalize() and lift() are deterministic. Blocked on both."""
    return False, "normalize() and lift() not yet implemented"


def _gate_alignment() -> tuple[bool, str]:
    """Check anchors() returns the required trilingual anchor set."""
    return False, "anchors() not yet implemented"


def _gate_coverage() -> tuple[bool, str]:
    """Run all probes in probes/. Blocked on lift and readback."""
    return False, "depends on lift and readback gates"


GATES = [
    ("schema", _gate_schema),
    ("lexical", _gate_lexical),
    ("morphology", _gate_morphology),
    ("lift", _gate_lift),
    ("readback", _gate_readback),
    ("determinism", _gate_determinism),
    ("alignment", _gate_alignment),
    ("coverage", _gate_coverage),
]


def validate_pack() -> dict:
    """Run all eight gates. Returns a report with pass/fail and reason per gate."""
    report = {"pack_id": "en", "active": False, "gates": {}}
    for name, gate_fn in GATES:
        passed, reason = gate_fn()
        report["gates"][name] = {"passed": passed, "reason": reason}
        if not passed:
            # Gate failure halts further validation.
            for remaining_name, _ in GATES[GATES.index((name, gate_fn)) + 1:]:
                report["gates"][remaining_name] = {"passed": False, "reason": "blocked by prior gate failure"}
            return report
    report["active"] = True
    return report


if __name__ == "__main__":
    import pprint
    pprint.pprint(validate_pack())
