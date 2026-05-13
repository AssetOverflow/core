"""
Validators for the Koine Greek depth pack.
Same gate structure as en and he. Greek-specific gate notes inline.
"""

from __future__ import annotations
import json
from pathlib import Path

PACK_DIR = Path(__file__).parent


def _gate_schema() -> tuple[bool, str]:
    return False, "not yet wired"


def _gate_lexical() -> tuple[bool, str]:
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
    # Greek lift requires tense-aspect-voice-mood and article resolution in analysis.
    return False, "el:lift() not yet implemented — requires tense/aspect/voice/mood/article in LinguisticAnalysis"


def _gate_readback() -> tuple[bool, str]:
    return False, "el:readback() not yet implemented — must produce fully inflected and accented Greek"


def _gate_determinism() -> tuple[bool, str]:
    return False, "depends on lift and readback"


def _gate_alignment() -> tuple[bool, str]:
    return False, "anchors() not yet implemented"


def _gate_coverage() -> tuple[bool, str]:
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
    report = {"pack_id": "el", "active": False, "gates": {}}
    for name, gate_fn in GATES:
        passed, reason = gate_fn()
        report["gates"][name] = {"passed": passed, "reason": reason}
        if not passed:
            for remaining_name, _ in GATES[GATES.index((name, gate_fn)) + 1:]:
                report["gates"][remaining_name] = {"passed": False, "reason": "blocked by prior gate failure"}
            return report
    report["active"] = True
    return report


if __name__ == "__main__":
    import pprint
    pprint.pprint(validate_pack())
