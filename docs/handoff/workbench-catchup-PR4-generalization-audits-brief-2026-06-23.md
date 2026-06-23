# Workbench Catch-up PR-4 Brief — Generalization Audit Governance Surface

**Target PR title:** `feat(workbench): expose generalization audit summaries`
**Follow-up UI title:** `feat(workbench-ui): add generalization audit view`
**Base:** after construction read model/UI work unless explicitly parallelized
**Scope:** read-only benchmark governance summaries; no raw benchmark items

## Goal

Make the new generalization audit infrastructure visible in Workbench without
violating benchmark policy.

The Workbench must show aggregate audit posture:

```text
manifest policy
license/checksum/cache status
aggregate report counts
residual/candidate/replay histograms
report pin vs ephemeral local output distinction
audit-only / no-patch-target disclosure
```

It must never show raw sealed benchmark examples.

## Governing policy

Generalization benchmark datasets are audit/test-only instruments. They must not
be used as training material, direct capability patches, or pack/policy mutation
targets. Sealed/raw items must not appear in source, diffs, logs, or UI-exported
artifacts.

Workbench may show:

- manifest metadata;
- cache verification status;
- license/checksum status;
- aggregate report counts;
- aggregate histograms;
- report source digest;
- policy warnings.

Workbench must not show:

- raw prompt text;
- raw answer text;
- sealed item content;
- item-level examples from sealed splits;
- patch suggestions derived directly from benchmark errors.

## Backend endpoints

Add read-only endpoints:

```text
GET /generalization/manifests
GET /generalization/cache
GET /generalization/reports
GET /generalization/reports/<dataset>/<split>
```

If the local cache is absent, return a status payload; do not attempt downloads.

## Backend schemas

Recommended dataclasses:

```python
@dataclass(frozen=True, slots=True)
class GeneralizationManifestSummary:
    dataset: str
    manifest_path: str
    split_names: list[str]
    license: str | None
    checksum_status: Literal["verified", "missing", "mismatch", "unknown"]
    sealed_splits: list[str]
    policy_version: str

@dataclass(frozen=True, slots=True)
class GeneralizationCacheStatus:
    dataset: str
    cache_path: str
    present: bool
    verified: bool
    reason: str | None

@dataclass(frozen=True, slots=True)
class GeneralizationAuditReportView:
    policy_version: str
    dataset: str
    split: str
    n_items: int
    correct: int
    wrong: int
    refused: int
    unsupported: int
    candidate_attempts: int
    binding_failures: int
    replay_refusals: int
    sealed_trace_dispositions: list[tuple[str, int]]
    dominant_residual_kinds: list[tuple[str, int]]
    reason_codes: list[str]
    source_path: str | None
    source_digest: str | None
    report_kind: Literal["committed_pin", "ephemeral_local", "rebaseline_candidate", "unknown"]
```

## Evals UI shape

Add internal tabs to `/evals`:

```text
Lanes
Generalization Audits
Report Pins
```

Do not add a new route unless the view becomes too large.

### Generalization Audit Card

Each dataset/split card must show:

```text
Dataset
Split
Policy version
License status
Checksum/cache status
N items
Correct / wrong / refused / unsupported
Candidate attempts
Binding failures
Replay refusals
Dominant residual kinds
Sealed trace dispositions
Reason codes
Source digest
```

### Required banner

```text
Audit-only. No raw sealed items are exposed here. Benchmark failures are diagnosis signals, not direct mutation targets.
```

### Report pin distinction

Every report view must classify itself:

```text
Committed report pin
Ephemeral local output
Governed rebaseline candidate
Unknown
```

Live/ephemeral output must not look equivalent to committed report truth.

## Tests to add/run locally

Backend:

```bash
uv run python -m pytest -q tests/test_generalization_manifest_policy.py tests/test_generalization_cache_verifier.py tests/test_generalization_audit_runner.py tests/test_workbench_generalization_readers.py
```

Frontend:

```bash
cd workbench-ui
pnpm test
pnpm build
```

Focused UI tests:

- `Generalization Audits` tab exists under `/evals`.
- Empty cache state does not error and does not suggest downloading from UI.
- Audit-only banner appears.
- Raw item fields are not rendered.
- Non-zero wrong count is visible, not hidden behind success styling.
- Committed vs ephemeral report classification is visible.

## Non-goals

- No dataset download from Workbench.
- No raw benchmark item inspection.
- No sealed holdout execution from UI.
- No report rebaseline mutation.
- No capability patch recommendation.
- No pack/policy/operator mutation.
