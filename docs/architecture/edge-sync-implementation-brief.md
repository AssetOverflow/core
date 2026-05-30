# Edge Sync Implementation Brief

**Status:** Implementation brief  
**Builds on:**
- [`edge-s3-persistence.md`](./edge-s3-persistence.md)
- [`edge-sync-artifact-contract.md`](./edge-sync-artifact-contract.md)

**Goal:** Give the next implementer a narrow, test-first path from architecture contract to code without introducing S3 into the hot path or weakening CORE's epistemic law.

## North-star invariant

```text
Cloud/object storage is a transport and archive boundary.
It is not an epistemic authority and it is not a hot-path dependency.
```

All implementation work must preserve:

1. local reasoning/refusal works with S3 unavailable;
2. downloaded artifacts are inert until verified and activated;
3. signed artifacts prove integrity, not truth;
4. malformed epistemic status defaults to speculative;
5. fleet observations cannot become serving evidence without promotion;
6. hot-path modules do not import an S3 client.

## Recommended implementation sequence

### ES-0 — Contract-only guard

Add tests that encode the architecture rules without touching S3.

Target file:

```text
tests/test_edge_sync_artifact_contract.py
```

Initial tests should operate over pure dataclasses/enums or fixtures. No network, no boto, no object-store dependency.

Prove:

- artifact classes have the expected authority profiles;
- runtime-affecting classes require signatures;
- hot-path-allowed is false for every S3 artifact class;
- fleet observations default to speculative;
- signed does not imply admissible-as-evidence;
- unknown artifact type rejects.

### ES-1 — Pure artifact model

Add a no-I/O model layer.

Suggested module:

```text
core/sync/artifacts.py
```

Suggested types:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArtifactType(str, Enum):
    TRACE = "trace"
    REPLAY_BUNDLE = "replay_bundle"
    SEALED_EVAL_RESULT = "sealed_eval_result"
    FLEET_OBSERVATION_BATCH = "fleet_observation_batch"
    CURRICULUM_BUNDLE = "curriculum_bundle"
    PACK_RELEASE = "pack_release"
    POLICY_RELEASE = "policy_release"
    MODALITY_COMPILER_RELEASE = "modality_compiler_release"
    COLD_VAULT_SNAPSHOT = "cold_vault_snapshot"


@dataclass(frozen=True, slots=True)
class ArtifactAuthority:
    runtime_affecting: bool
    hot_path_allowed: bool
    requires_signature: bool
    requires_activation: bool
    requires_review_or_proof: bool
    default_epistemic_status: str
    admissible_as_evidence: bool
```

Required table behavior:

- `TRACE`, `REPLAY_BUNDLE`, `SEALED_EVAL_RESULT`, `FLEET_OBSERVATION_BATCH` are not runtime-affecting.
- `PACK_RELEASE`, `POLICY_RELEASE`, `MODALITY_COMPILER_RELEASE` are runtime-affecting.
- `COLD_VAULT_SNAPSHOT` is runtime-affecting only through explicit restore/activation.
- All artifact classes are `hot_path_allowed=False`.
- `FLEET_OBSERVATION_BATCH.default_epistemic_status == "speculative"`.
- `admissible_as_evidence=False` by default for imported artifacts.

### ES-2 — Manifest parsing and validation

Add a pure manifest parser/validator.

Suggested module:

```text
core/sync/manifest.py
```

Responsibilities:

- parse dict/JSON into typed manifest;
- reject unknown artifact types;
- reject missing required fields for runtime-affecting artifacts;
- validate authority profile is not weaker than the contract;
- normalize malformed/absent epistemic status to speculative;
- compute and compare content digests through a supplied byte provider or local file bytes.

Do **not** implement S3 access here.

Suggested result type:

```python
@dataclass(frozen=True, slots=True)
class ManifestCheck:
    accepted: bool
    reason: str
```

Failure reasons should be stable strings for tests:

```text
unknown_artifact_type
unsupported_schema_version
missing_signature
hash_mismatch
authority_profile_weakened
runtime_incompatible
malformed_epistemic_status_defaulted
```

### ES-3 — Activation ledger

Add activation state without cloud I/O.

Suggested module:

```text
core/sync/activation.py
```

Responsibilities:

- track active release by artifact type and artifact id/version;
- reject activation before validation passes;
- preserve previous verified release for rollback where applicable;
- emit activation trace metadata;
- never mark artifact claims coherent by activation alone.

Required API shape:

```python
@dataclass(frozen=True, slots=True)
class ActivationDecision:
    activated: bool
    reason: str
    previous_artifact_id: str | None = None
    active_artifact_id: str | None = None
```

Stable reasons:

```text
activated
validation_failed
runtime_incompatible
not_runtime_affecting
rollback_activated
```

### ES-4 — Local sync journal

Add a local-only journal that records pending uploads/downloads and retry state.

Suggested module:

```text
core/sync/journal.py
```

Responsibilities:

- append pending upload records;
- append pending download records;
- mark acknowledged/completed/rejected;
- preserve failure reason;
- keep hot path independent from upload success.

This can be file-backed later. First version may be pure in-memory or JSONL-backed behind an interface.

Required invariant:

```text
upload failure must not block local reasoning/refusal/action safety.
```

### ES-5 — Object store adapter seam

Only after ES-0 through ES-4 are green, introduce a narrow adapter seam.

Suggested module:

```text
core/sync/object_store.py
```

Interface only at first:

```python
class ObjectStore(Protocol):
    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
```

Important: no production hot-path module may import this adapter.

Add an architectural test that fails if known hot-path packages import `core.sync.object_store` or a concrete S3 SDK.

### ES-6 — S3 implementation behind optional dependency

Concrete S3 adapter should be optional and late.

Suggested module:

```text
core/sync/s3_store.py
```

Rules:

- optional dependency only;
- no import at module import time from hot paths;
- no credentials in repo;
- retries/timeouts configured externally;
- errors map to typed sync failure reasons;
- object store unavailable never mutates active release state.

## Proposed tests

### `test_artifact_authority_profiles_are_closed`

Asserts every known artifact class has an authority profile and no artifact is hot-path allowed.

### `test_runtime_affecting_artifacts_require_signature`

Asserts pack, policy, modality compiler, and cold-vault restore artifacts require signatures before activation.

### `test_signed_does_not_imply_evidence`

A signed fleet observation remains speculative and not admissible as evidence.

### `test_malformed_epistemic_status_defaults_speculative`

Manifest or imported entry with malformed epistemic status becomes speculative, never coherent.

### `test_downloaded_artifact_is_inert_until_activated`

Parsing/downloading a manifest does not change active release state.

### `test_hash_mismatch_rejected`

Digest mismatch returns `hash_mismatch` and activation is blocked.

### `test_authority_profile_cannot_weaken_contract`

Manifest claiming `hot_path_allowed=true` or `admissible_as_evidence=true` for fleet observations is rejected.

### `test_s3_unavailable_preserves_current_release`

Object-store failure does not clear active pack/policy release.

### `test_hot_path_has_no_object_store_imports`

Static test over known hot-path modules/packages ensures they do not import `boto3`, S3 adapters, or `core.sync.object_store`.

Initial hot-path candidates:

```text
algebra/
chat/
generate/
vault/
core/physics/
```

This list may be refined, but the principle must remain.

### `test_activation_writes_audit_record`

Every activation decision emits trace/audit metadata with artifact id, digest, previous active release, new active release, and reason.

## Data flow

### Upload flow

```text
local trace/replay/practice artifact
  -> local journal append
  -> object-store upload attempt
  -> ack or retry state
  -> no effect on hot path
```

### Download flow

```text
manifest discovered
  -> manifest parse
  -> schema/type check
  -> download object
  -> digest check
  -> signature check
  -> compatibility check
  -> activation decision
  -> audit trace
  -> local active release update
```

### Fleet learning flow

```text
fleet observations
  -> S3 archive
  -> offline aggregation
  -> candidate proposal
  -> proof/review/ratification
  -> signed release artifact
  -> edge verification
  -> activation
```

No shortcut may skip proposal/proof/review.

## Explicit non-goals for first implementation

Do not implement yet:

- cloud credentials;
- actual bucket naming policy;
- fleet aggregation logic;
- pack compiler changes;
- runtime activation of real packs;
- motor/safety integration;
- background daemon or scheduler;
- multipart upload;
- object-lock enforcement.

The first implementation should be contract and local validation only.

## Suggested PR stack

### PR 1 — Contract model and tests

Files:

```text
core/sync/__init__.py
core/sync/artifacts.py
tests/test_edge_sync_artifact_contract.py
```

No I/O. No S3. No runtime integration.

### PR 2 — Manifest parser/validator

Files:

```text
core/sync/manifest.py
tests/test_edge_sync_manifest.py
```

No S3. Digest validation can operate on supplied bytes.

### PR 3 — Activation ledger

Files:

```text
core/sync/activation.py
tests/test_edge_sync_activation.py
```

Proves downloaded artifacts are inert until activated and activation does not confer coherence.

### PR 4 — Local journal

Files:

```text
core/sync/journal.py
tests/test_edge_sync_journal.py
```

Proves upload/download failures do not block or clear local state.

### PR 5 — Adapter seam

Files:

```text
core/sync/object_store.py
tests/test_edge_sync_hot_path_imports.py
```

Interface only. Static hot-path import guard.

### PR 6 — Optional S3 adapter

Files:

```text
core/sync/s3_store.py
tests/test_edge_sync_s3_store.py
```

Optional dependency, mocked tests only. No credentials, no live network in CI.

## Implementation discipline

- Prefer pure functions and dataclasses until the contract is proven.
- No live network in tests.
- No S3 import in hot-path modules.
- No artifact becomes coherent by storage, signature, or activation alone.
- Any schema expansion must keep malformed/unknown statuses safe-by-default.
- Every rejection reason should be stable enough for tests and audit logs.
- Add code only after the contract tests define the failure mode.

## Summary

The next implementation should make the S3/edge boundary enforceable without entangling CORE's live cognition with cloud storage.

Correct first milestone:

```text
A runtime-affecting artifact can be parsed, rejected, verified, and activated locally under tests — with no S3 client, no network, no hot-path dependency, and no epistemic promotion by accident.
```

That gives CORE the cloud/fleet persistence path while preserving the edge-native truth-seeking substrate.
