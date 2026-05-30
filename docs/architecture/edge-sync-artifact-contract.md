# Edge Sync Artifact Contract

**Status:** Design contract  
**Builds on:** [`docs/architecture/edge-s3-persistence.md`](./edge-s3-persistence.md)  
**Scope:** Artifact classes, manifest shape, authority boundaries, sync failure semantics, and future proof obligations for CORE edge/cloud synchronization.  
**Non-goal:** This document does not introduce a runtime dependency on S3/object storage and does not implement a sync client.

## Purpose

The S3 persistence architecture defines where cloud/object storage belongs:

```text
Edge = thinking, acting, refusing, remembering hot.
S3   = preserving, auditing, syncing, distributing, training cold.
```

This contract defines what is allowed to cross that boundary and what authority, if any, each artifact has after crossing.

The load-bearing invariant:

```text
Downloaded != activated.
Activated  != coherent.
Signed     != true.
```

Integrity, provenance, epistemic status, and runtime authority are separate axes. They must never collapse into one another.

## Core rule

S3-compatible storage may preserve and distribute artifacts. It does not grant epistemic admissibility.

Any artifact imported from cloud/object storage enters CORE under the same truth-seeking schema as any other input:

- malformed or absent epistemic status defaults to speculative;
- source prestige, fleet frequency, or signature presence is not coherence;
- runtime-affecting artifacts require signature/hash/schema verification before activation;
- learning artifacts may inform sealed practice, but do not mutate serving knowledge directly;
- serving evidence still requires the reviewed/proven mutation path.

## Artifact classes

Each artifact class has a fixed authority profile. Implementations may add fields, but they must not weaken these defaults without a follow-on ADR or explicitly ratified contract update.

| Artifact class | Runtime-affecting | Hot-path allowed | Signature required | Review/proof required before serving influence | Epistemic default |
|---|---:|---:|---:|---:|---|
| `trace` | No | No | Recommended | No; audit input only | `speculative` |
| `replay_bundle` | No | No | Recommended | No; audit/proof input only | `speculative` |
| `sealed_eval_result` | No | No | Recommended | Yes, before claims/promotion | `speculative` |
| `fleet_observation_batch` | No | No | Recommended | Yes, before evidence use | `speculative` |
| `curriculum_bundle` | No direct effect | No | Required if distributed to devices | Yes, before pack/runtime mutation | `speculative` |
| `pack_release` | Yes | Pull-only, activation-gated | Required | Yes; release process must prove/review | as manifest declares, never implicit |
| `policy_release` | Yes | Pull-only, activation-gated | Required | Yes; release process must prove/review | as manifest declares, never implicit |
| `modality_compiler_release` | Yes | Pull-only, activation-gated | Required | Yes; compiler changes are runtime-affecting | as manifest declares, never implicit |
| `cold_vault_snapshot` | Yes during explicit restore | No live hot path | Required | Yes; restore is an activation event | preserved per entry, malformed => speculative |

### Prohibited implication

No artifact class may imply:

```text
stored in S3 => reviewed
signed       => true
downloaded   => active
popular      => coherent
fleet-seen   => admissible
```

## Manifest schema

Every artifact that is distributed or consumed by automation should have a manifest. Runtime-affecting artifacts must have one.

Minimal manifest:

```json
{
  "schema_version": 1,
  "artifact_id": "...",
  "artifact_type": "pack_release",
  "artifact_version": "...",
  "created_at_utc": "...",
  "producer": {
    "type": "human|runtime|ci|fleet_aggregator",
    "id": "..."
  },
  "content": {
    "uri": "s3://bucket/path/object.zst",
    "digest": "sha256:...",
    "size_bytes": 0,
    "compression": "zstd|none",
    "media_type": "application/jsonl|application/zstd|application/octet-stream"
  },
  "authority": {
    "runtime_affecting": true,
    "hot_path_allowed": false,
    "requires_signature": true,
    "requires_activation": true,
    "requires_review_or_proof": true
  },
  "epistemic": {
    "default_status": "speculative",
    "admissible_as_evidence": false,
    "promotion_required": true
  },
  "compatibility": {
    "min_runtime_version": "...",
    "max_runtime_version": null,
    "requires_capabilities": []
  },
  "provenance": {
    "source_trace_ids": [],
    "source_eval_run_ids": [],
    "source_pack_digests": []
  },
  "signature": {
    "algorithm": "...",
    "key_id": "...",
    "signature": "..."
  }
}
```

### Required manifest checks

Before a runtime-affecting artifact may be activated, the edge runtime or release manager must verify:

1. manifest schema version is supported;
2. artifact type is known;
3. content digest matches downloaded bytes;
4. signature is valid for the manifest and/or content according to release policy;
5. runtime compatibility is satisfied;
6. artifact class authority profile is not weakened by the manifest;
7. activation is recorded as an auditable trace;
8. previous verified release remains available for rollback where applicable.

## Activation contract

A downloaded object is inert until activated.

Activation is the explicit transition:

```text
downloaded + verified + compatible + authorized => active local release
```

Activation does not mean the artifact's claims are automatically `COHERENT`. It means the artifact is now allowed to participate according to its artifact class.

Examples:

- A `pack_release` may contain coherent entries only where the pack itself declares and proves the review status required by pack policy.
- A `policy_release` may constrain actions after activation, but the signature only proves the policy bundle came from an authorized release process.
- A `fleet_observation_batch` remains speculative learning input even when signed and downloaded.
- A `cold_vault_snapshot` preserves per-entry epistemic statuses; malformed or missing statuses default to speculative.

## Sync failure semantics

Sync failures must preserve edge safety.

| Failure | Required behavior |
|---|---|
| S3 unavailable | Continue local operation using last verified local state. |
| Upload failure | Retain local journal for retry; do not block hot path. |
| Download failure | Keep current active release; do not partially activate. |
| Hash mismatch | Reject object; log trace; keep current active release. |
| Invalid signature | Reject object; log trace; keep current active release. |
| Unknown artifact type | Reject unless explicitly configured as non-runtime archival input. |
| Unsupported schema | Reject or quarantine; never activate silently. |
| Compatibility failure | Reject activation; keep current active release. |
| Partial download | Discard or quarantine; never activate. |
| Clock skew | Do not grant authority based solely on local time; preserve trace. |

## Authority model

Artifacts have four independent authority axes:

1. **Integrity** — bytes match digest/signature.
2. **Compatibility** — runtime can safely parse and understand the artifact.
3. **Activation** — artifact is allowed to participate in local runtime behavior.
4. **Epistemic admissibility** — artifact claims may be used as evidence.

These axes are intentionally separate.

```text
Integrity does not imply activation.
Activation does not imply coherence.
Coherence does not imply permanence.
```

## Edge hot-path prohibition

The following decisions must not require S3/object storage round trips:

- stop/continue safety decisions;
- collision or force-limit decisions;
- active vault recall;
- current-field propagation;
- customer-facing refusal/answer generation;
- immediate policy/action gate evaluation;
- active contradiction checks required for current action;
- motor-control or embodied reflex loops.

If the edge runtime cannot decide safely without S3, it must choose the safe local fallback: refuse, ask, observe-only, stop, or escalate according to action class.

## Learning and fleet aggregation

Fleet artifacts may feed sealed practice and offline aggregation.

They may not directly mutate serving knowledge.

Correct flow:

```text
fleet traces / observations
  -> S3 archival
  -> offline aggregation
  -> candidate proposal
  -> proof / review / ratification
  -> signed release
  -> edge download
  -> verification
  -> activation
```

Incorrect flow:

```text
fleet observation
  -> S3
  -> runtime fact
```

The incorrect flow is an epistemic-corruption path and must be rejected.

## Required metadata by artifact class

### `trace`

Required:

- `trace_id`
- `runtime_version`
- `timestamp_utc`
- `field_state_digest_before`
- `field_state_digest_after` when available
- input source digests
- selected decision/action/refusal
- epistemic states involved
- safety gate result where applicable

### `replay_bundle`

Required:

- `replay_hash`
- source `trace_id` or eval run id
- runtime/version metadata
- pack/policy manifest digests
- deterministic replay inputs
- expected replay verdict

### `sealed_eval_result`

Required:

- lane id
- run id
- case count
- verdict counts
- wrong/refusal/correct counts where applicable
- timing summary when measured
- runtime version
- input dataset digest

### `fleet_observation_batch`

Required:

- producing robot/site/fleet ids where applicable
- capture time range
- source modalities
- per-observation provenance
- epistemic default = speculative
- no direct admissibility flag unless produced by a reviewed/proven release process

### `pack_release` / `policy_release` / `modality_compiler_release`

Required:

- signed manifest
- content digest
- schema version
- runtime compatibility
- release notes or proof summary
- rollback reference where applicable
- activation trace requirement

### `cold_vault_snapshot`

Required:

- snapshot id
- source runtime/device id
- vault schema version
- per-entry epistemic status
- per-entry digest or snapshot digest
- restore policy
- explicit restore activation trace

## Future implementation targets

This contract should eventually be enforced by code. Likely targets:

```text
core/sync/artifacts.py
core/sync/manifest.py
core/sync/verify.py
core/sync/journal.py
core/sync/activation.py
tests/test_edge_sync_artifact_contract.py
```

No implementation path may introduce S3 as a dependency of active recall, active reasoning, refusal, or safety gating.

## Future proof obligations

A code implementation should include tests that fail if:

1. an unsigned runtime-affecting artifact activates;
2. a hash-mismatched artifact activates;
3. a downloaded artifact becomes active before verification;
4. a signed fleet observation becomes admissible evidence by signature alone;
5. malformed epistemic status imports as coherent;
6. S3 unavailability blocks local refusal/reasoning;
7. download failure clears the last verified local release;
8. hot-path code imports the S3 client directly;
9. a cold vault restore drops or upgrades per-entry epistemic status;
10. activation occurs without an auditable trace.

## Summary

This contract turns edge/S3 separation into an authority model.

```text
S3 may store.
S3 may distribute.
S3 may preserve evidence.
S3 may not decide truth.
S3 may not sit in the hot path.
S3 may not mutate serving knowledge directly.
```

Truth still enters by proof, review, coherence, replay, and ratified mutation paths — never by storage location, signature, popularity, or fleet frequency.
