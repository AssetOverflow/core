"""
Demo 03 — Architectural Determinism (Not Seeded Randomness)

Claim
-----
Three independently constructed ChatRuntime instances on the same input
produce byte-identical JSONL audit records for the fields that are
architecturally determined: versor_condition, vault_hits, dialogue_role,
stub_path, safety_upheld, ethics_upheld, flagged.

This is not seeded randomness.  There is no random seed being fixed.
There is no temperature=0.  The determinism comes from:
  - CGA nearest-node selection is a deterministic argmax over an exact
    inner product scan
  - versor_condition is a deterministic norm of a deterministic field
  - The identity/safety/ethics check predicates are pure functions
  - The JSONL serialiser uses sort_keys=True and fixed separators

Why a transformer wrapper cannot reproduce this
-----------------------------------------------
A transformer at temperature=0 produces deterministic output but that
determinism is from greedy decoding — a degenerate limit of a stochastic
process.  CORE's determinism is structural: the generation walk is
a deterministic function of the initial field state and the vocab metric.
There is no probability distribution being collapsed.  The audit record
reflects this: it carries the versor_condition of the final field state
— a geometric invariant — not a log-probability.

Evidence produced
-----------------
1. Three audit lines parsed from three independent runtime instances
2. versor_condition identical across all three (geometric invariant)
3. vault_hits, dialogue_role, stub_path, safety_upheld, ethics_upheld,
   flagged all identical
4. SHA-256 hash of the deterministic fields identical
"""

from __future__ import annotations

import hashlib
import json
import sys


_DETERMINISTIC_FIELDS = (
    "versor_condition",
    "vault_hits",
    "dialogue_role",
    "stub_path",
    "safety_upheld",
    "ethics_upheld",
    "flagged",
)


def _deterministic_hash(record: dict) -> str:
    payload = {k: record[k] for k in _DETERMINISTIC_FIELDS if k in record}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def run() -> dict:
    from chat.runtime import ChatRuntime
    from chat.telemetry import JsonlBufferSink

    INPUT = "light is truth"

    records = []
    hashes = []

    for instance_id in range(3):
        rt = ChatRuntime()
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat(INPUT)
        lines = sink.lines
        # Take the last emitted line (the main-path turn event)
        if lines:
            record = json.loads(lines[-1])
            records.append(record)
            hashes.append(_deterministic_hash(record))
        else:
            records.append({})
            hashes.append("")

    all_hashes_equal = len(set(hashes)) == 1 and hashes[0] != ""

    field_evidence = {}
    for field in _DETERMINISTIC_FIELDS:
        values = [r.get(field) for r in records]
        field_evidence[field] = {
            "values": values,
            "identical": len(set(str(v) for v in values)) == 1,
        }

    passed = all_hashes_equal and all(
        field_evidence[f]["identical"] for f in _DETERMINISTIC_FIELDS if f in field_evidence
    )

    result = {
        "demo": "03_deterministic_audit",
        "claim": "Three independent ChatRuntime instances produce byte-identical audit records (architectural determinism, not seeded randomness)",
        "evidence": {
            "instances": 3,
            "input": INPUT,
            "deterministic_field_hashes": hashes,
            "all_hashes_equal": all_hashes_equal,
            "per_field": field_evidence,
        },
        "passed": passed,
    }
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)
