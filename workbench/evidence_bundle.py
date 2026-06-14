"""D3 shareable evidence bundle — reproducibility as a deliverable.

A turn's evidence, exported as ONE deterministic, content-addressed, citable
artifact.  The ``bundle_digest`` content-addresses the turn's deterministic
cognitive evidence (prompt, surface, trace_hash, grounding / epistemic /
normative state, the Phase-C pipeline + field evidence, and the calibration
leeway verdict).  Journal-position and wall-clock metadata (``turn_id``,
``journal_digest``, the reproducer string) are carried for provenance but
EXCLUDED from the digest, so the same turn content always yields the same
digest — a reviewer can re-run the prompt over a sealed runtime, confirm the
trace_hash, recompute the bundle, and check the digest.

Read-only: a pure projection of an already-persisted journal entry.  No engine
execution, no mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from workbench.schemas import EvidenceBundle, to_data

# Provenance / position / wall-clock fields: carried on the bundle but NOT part
# of the content address, so the digest identifies the cognitive evidence
# rather than where it happened to land in a journal.
_DIGEST_EXCLUDED: frozenset[str] = frozenset(
    {"turn_id", "generated_from", "journal_digest", "replay_reproducer", "bundle_digest"}
)


def _bundle_digest(bundle: EvidenceBundle) -> str:
    payload = to_data(bundle)
    for key in _DIGEST_EXCLUDED:
        payload.pop(key, None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_evidence_bundle(entry: Any) -> EvidenceBundle:
    """Assemble a turn journal entry into a content-addressed evidence bundle."""

    trace_hash = entry.trace_hash
    reproducer = (
        f"core replay turn {entry.turn_id} "
        f"# re-run sealed; expect trace_hash == {trace_hash or 'none'}"
    )
    bundle = EvidenceBundle(
        schema_version="evidence_bundle_v1",
        turn_id=entry.turn_id,
        generated_from="turn_journal",
        trace_hash=trace_hash,
        trace_integrity=entry.trace_integrity or "legacy_unhashed",
        prompt=entry.prompt,
        surface=entry.surface,
        grounding_source=entry.grounding_source,
        epistemic_state=entry.epistemic_state,
        normative_clearance=entry.normative_clearance,
        refusal_emitted=entry.refusal_emitted,
        journal_digest=entry.journal_digest,
        pipeline_record=to_data(entry.pipeline_record),
        field_evidence=to_data(entry.field_evidence),
        leeway_evidence=to_data(entry.leeway_evidence),
        replay_reproducer=reproducer,
        bundle_digest="",  # filled below; excluded from its own computation
    )
    return replace(bundle, bundle_digest=_bundle_digest(bundle))
