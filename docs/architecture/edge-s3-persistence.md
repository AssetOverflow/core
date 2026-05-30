# Edge S3 Persistence Architecture

**Status:** Design note  
**Scope:** CORE edge/runtime persistence, fleet trace archival, signed pack distribution, replay artifacts, and cold-storage synchronization.  
**Non-goal:** S3/object storage is not part of the active cognition, recall, safety, or motor-control hot path.

## Decision

CORE's real-time intelligence stays edge-local. S3-compatible object storage is used as the cloud-side persistence and distribution layer for immutable artifacts, fleet-scale learning inputs, audits, and signed releases.

The split is deliberate:

```text
Edge = thinking, acting, refusing, remembering hot.
S3   = preserving, auditing, syncing, distributing, training cold.
```

Object storage may preserve and distribute evidence. It must not become an authority source that bypasses CORE's epistemic law.

## Why this matters

CORE is designed to run primarily at the edge: local substrate, local vault recall, local action gates, local refusal, local traces, and local safety boundaries. That edge-native posture is essential for robotics, retail/commercial deployments, privacy-sensitive domains, and disconnected or degraded-network environments.

S3 is valuable because a fleet still needs durable storage, audit replay, signed releases, and large-scale curriculum aggregation. The correct role for S3 is therefore cold/nearline persistence, not active cognition.

## Architecture

```text
Robot / edge runtime
  ├─ active field state
  ├─ hot local vault
  ├─ local pack cache
  ├─ local policy/action gates
  ├─ local safety controller integration
  ├─ local trace journal
  └─ sync agent
        ↓ append / pull signed releases
S3-compatible object storage
  ├─ traces/
  ├─ replay-artifacts/
  ├─ sealed-evals/
  ├─ packs/
  ├─ curriculum/
  ├─ fleet-observations/
  ├─ audit/
  ├─ releases/
  └─ cold-vault-backups/
```

The edge runtime must remain capable of safe local operation without a live S3 round trip.

## S3 responsibilities

S3-compatible storage is appropriate for:

| Use | Purpose |
|---|---|
| Immutable trace archive | Preserve turn/action evidence for replay and audit. |
| Replay artifacts | Store proof bundles, field digests, recall digests, and decision traces. |
| Sealed eval outputs | Persist lane results, comparison artifacts, and timing reports. |
| Pack distribution | Publish signed, versioned packs to edge devices. |
| Curriculum storage | Hold practice corpora, modality corpora, and offline learning inputs. |
| Fleet telemetry snapshots | Aggregate non-hot-path observations for later analysis. |
| Audit/compliance | Preserve append-only evidence for review and accountability. |
| Cold vault backups | Restore edge devices after hardware failure without making S3 the hot vault. |

S3 is not appropriate for:

- real-time vault recall;
- active field propagation;
- motor-control loops;
- safety vetoes;
- immediate perception/action decisions;
- active contradiction checks needed for a current action;
- direct unreviewed knowledge mutation.

## Object model

Objects should be append-first and content-addressable where practical.

Recommended layout:

```text
s3://<bucket>/traces/<site_id>/<robot_id>/<yyyy-mm-dd>/<trace_id>.jsonl.zst
s3://<bucket>/replay-artifacts/<site_id>/<robot_id>/<yyyy-mm-dd>/<replay_hash>.bundle.zst
s3://<bucket>/sealed-evals/<lane>/<run_id>/result.json
s3://<bucket>/fleet-observations/<site_id>/<yyyy-mm-dd>/<batch_id>.jsonl.zst
s3://<bucket>/releases/packs/<pack_id>/<version>/manifest.json
s3://<bucket>/releases/packs/<pack_id>/<version>/pack.zst
s3://<bucket>/releases/packs/<pack_id>/<version>/signature.sig
s3://<bucket>/cold-vault-backups/<site_id>/<robot_id>/<snapshot_id>.bundle.zst
```

Every release object that can influence runtime behavior must be referenced by a signed manifest. Runtime devices pull releases only after signature, hash, schema, and compatibility checks pass.

## Trace schema sketch

A trace object should preserve enough information for deterministic replay and audit without requiring S3 to be present during the live decision.

Minimum fields:

```json
{
  "schema_version": 1,
  "trace_id": "...",
  "robot_id": "...",
  "site_id": "...",
  "timestamp_utc": "...",
  "runtime_version": "...",
  "pack_manifest_digests": ["..."],
  "input_sources": [
    {
      "source_id": "front_camera",
      "source_type": "vision",
      "capture_digest": "...",
      "timestamp_utc": "..."
    }
  ],
  "field_state_digest_before": "...",
  "vault_recall_digests": ["..."],
  "candidate_actions": ["..."],
  "selected_action": "...",
  "decision": "act|refuse|ask|escalate|observe_only",
  "decision_reason": "...",
  "epistemic_states": ["..."],
  "safety_gate_result": "cleared|blocked|escalated",
  "field_state_digest_after": "...",
  "replay_hash": "..."
}
```

The exact schema may evolve, but the invariant does not: replay-critical claims must carry provenance, status, and digests.

## Epistemic law for S3 objects

S3 is storage, not truth.

Objects loaded from S3 must enter CORE under the same epistemic discipline as any other input:

- unknown or malformed status defaults to speculative;
- content provenance is preserved;
- source prestige or fleet frequency is not sufficient for coherence;
- signed release status proves integrity, not truth;
- contested or falsified objects must not become admissible evidence;
- unreviewed fleet observations are learning inputs, not runtime facts;
- runtime mutation still flows through the single reviewed/proven path.

A fleet upload may become evidence only after the appropriate review, proof, or ratification corridor promotes it.

## Sync model

The edge sync agent has two directions:

### Upload

- append local traces;
- append replay bundles;
- append sealed practice outcomes;
- append non-hot-path telemetry snapshots;
- upload cold vault snapshots when configured.

Upload failure must not block safe local operation. The local journal should retain unsynced artifacts until acknowledged or until a configured retention boundary is reached.

### Download

- fetch signed pack releases;
- fetch signed policy bundles;
- fetch approved curriculum/practice bundles;
- fetch restore snapshots only during explicit recovery flows.

Download failure must not weaken local safety. The device continues using the last verified local release.

## Security and integrity requirements

Runtime-affecting S3 artifacts require:

1. content hash in manifest;
2. manifest signature;
3. schema version check;
4. runtime compatibility check;
5. monotonic release/version rule where applicable;
6. local verification before activation;
7. append-only audit trail for activation decisions.

Audit-critical buckets should enable versioning and, where operationally appropriate, object lock / retention policies.

## Robotics / embodied autonomy implications

For humanoid or commercial robots, S3 must never sit between perception and immediate safe action. A robot cannot wait on object storage to decide whether to stop, refuse, avoid a person, or keep force within bounds.

Correct split:

```text
Hot path:
  sensors → modality compiler → local field → local recall → local gate → local action/safety

Cold path:
  traces/practice/fleet observations → S3 → offline aggregation → proof/review → signed release → edge pull
```

This preserves edge autonomy while still allowing fleet learning and auditability.

## Failure modes guarded against

| Failure mode | Guardrail |
|---|---|
| S3 outage blocks robot safety | Edge runtime remains locally safe and operational. |
| Fleet observation becomes truth by frequency | S3 objects enter as speculative unless ratified. |
| Malicious object mutation | Signed manifests, hashes, versioning, local verification. |
| Practice contaminates serving | Practice uploads become proposals/signals, not runtime facts. |
| Stale cloud state overrides local perception | Hot path prefers current local evidence and safety gates. |
| Audit gaps | Append-first trace/replay archival with digests. |
| Hidden knowledge mutation | S3 imports still pass through the one mutation/proposal path. |

## Acceptance criteria for implementation

An implementation of this architecture should prove:

1. the runtime can complete local recall/reasoning/refusal with S3 unavailable;
2. S3 download failures preserve the last verified pack/policy release;
3. unsigned or hash-mismatched packs are rejected;
4. uploaded traces contain enough digests for replay validation;
5. fleet observations are not admissible as evidence without promotion;
6. object versioning or content-addressing prevents silent overwrite of meaning;
7. sync retries do not block motor/safety hot paths;
8. activation of a downloaded release is itself logged as an auditable trace.

## Summary

S3-compatible object storage is the right cloud-side complement to CORE's edge-native architecture. It preserves evidence, distributes signed knowledge artifacts, supports fleet learning, and enables audit/replay. It must remain outside the hot path and outside epistemic admission authority.

The governing rule is simple:

```text
Edge thinks and acts.
S3 remembers and distributes.
Truth still enters only by proof.
```
