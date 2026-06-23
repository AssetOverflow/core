# Workbench Catch-up PR-2 Brief — Construction Evidence Read Model

**Target PR title:** `feat(workbench): expose construction evidence read model`  
**Base:** fresh `origin/main` after the docs catch-up PR merges  
**Scope:** backend read-only schemas + API endpoint only  

## Goal

Expose the proposal-first construction seam to Workbench as deterministic,
read-only evidence for a journaled turn.

The surface to expose is:

```text
surface/process cue
-> ConstructionProposal(status="proposed")
-> exact spans / mention bindings / bound relations
-> ContractAssessment
-> diagnostic runnable/refused
```

This PR must not create the frontend tab. It only creates the read model that the
frontend can consume in the next PR.

## Why

Trace currently exposes pipeline, field, bundle, surfaces, grounding, verdicts,
metadata, and raw turn evidence. It does not expose the new proposal-first
construction substrate. That makes the Workbench lag the kernel.

The demo-critical distinction is:

```text
Proposal != Runnable
ContractAssessment determines runnable/refused
Diagnostic only
Serving disallowed
```

## Required files to inspect first

- `workbench/api.py`
- `workbench/schemas.py`
- `workbench/readers.py`
- `workbench/journal.py`
- `workbench/pipeline_record.py`
- `generate/construction_affordances.py`
- `generate/problem_frame_contracts.py`
- `generate/problem_frame.py`
- `generate/kernel_facts.py`
- `workbench-ui/src/types/api.ts`
- `scripts/dump-api-schemas.py`
- existing API tests under `tests/` and `workbench-ui/src/api/`

## Backend endpoint

Add:

```text
GET /trace/<turn_id>/construction
```

Response envelope is normal `ok(...)` / `error(...)` through `WorkbenchApi`.

## Proposed schema

Add Python dataclasses in `workbench/schemas.py`:

```python
@dataclass(frozen=True, slots=True)
class SourceSpanView:
    start: int
    end: int
    text: str

@dataclass(frozen=True, slots=True)
class RoleObligationView:
    role: str
    required: bool
    description: str

@dataclass(frozen=True, slots=True)
class ConstructionProposalView:
    family_id: str
    relation_type: str
    candidate_organ: str
    status: Literal["proposed"]
    evidence_spans: list[SourceSpanView]
    role_obligations: list[RoleObligationView]
    diagnostic_only: bool
    serving_allowed: bool

@dataclass(frozen=True, slots=True)
class MentionView:
    mention_id: str
    kind: str
    surface: str
    span: SourceSpanView
    fact_id: str | None = None

@dataclass(frozen=True, slots=True)
class MentionBindingView:
    binding_type: str
    source_mention_id: str
    target_mention_id: str
    evidence_spans: list[SourceSpanView]

@dataclass(frozen=True, slots=True)
class BoundRelationRoleView:
    role: str
    target_id: str
    evidence_spans: list[SourceSpanView]

@dataclass(frozen=True, slots=True)
class BoundRelationView:
    relation_type: str
    roles: list[BoundRelationRoleView]
    evidence_spans: list[SourceSpanView]

@dataclass(frozen=True, slots=True)
class ContractAssessmentView:
    candidate_organ: str
    family_id: str | None
    missing_bindings: list[str]
    unresolved_hazards: list[str]
    runnable: bool
    explanation: str
    evidence_spans: list[SourceSpanView]

@dataclass(frozen=True, slots=True)
class ConstructionEvidence:
    schema_version: Literal["construction_evidence_v1"]
    turn_id: int
    status: PipelineEvidenceStatus
    missing_reason: str | None
    problem_text: str | None
    proposals: list[ConstructionProposalView]
    mentions: list[MentionView]
    bindings: list[MentionBindingView]
    bound_relations: list[BoundRelationView]
    contract_assessments: list[ContractAssessmentView]
    diagnostic_only: bool
    serving_allowed: bool
```

Mirror the same shape in `workbench-ui/src/types/api.ts`.

## Reader behavior

Add a read function in `workbench/readers.py`, likely:

```python
def read_construction_evidence(entry: TurnJournalEntry) -> ConstructionEvidence:
    ...
```

Preferred behavior:

1. If the journaled turn carries a persisted problem frame or construction detail,
   project it losslessly into the read model.
2. If not persisted, return:

```python
ConstructionEvidence(
    schema_version="construction_evidence_v1",
    turn_id=entry.turn_id,
    status="missing_evidence",
    missing_reason="construction evidence was not persisted for this turn",
    problem_text=None,
    proposals=[],
    mentions=[],
    bindings=[],
    bound_relations=[],
    contract_assessments=[],
    diagnostic_only=True,
    serving_allowed=False,
)
```

Do not reconstruct ProblemFrames from prose inside the reader. This endpoint is a
projection, not a parser or runner.

## API dispatch

In `workbench/api.py`, add before the generic `/trace/<turn_id>` branch:

```python
if method == "GET" and path.startswith("/trace/") and path.endswith("/construction"):
    ...
```

The path should load the journal entry exactly like pipeline/field/bundle routes.

## Hard constraints

- No mutation.
- No replay execution.
- No candidate operator execution.
- No search.
- No solving.
- No serving dispatch.
- No hidden reconstruction from raw problem text.
- No fabricated problem frame when evidence is absent.
- Exact spans only: if span data exists, `problem_text[start:end] == span.text` must hold or the reader must mark/refuse the row rather than silently repair it.

## Tests to add/run when local execution is available

Backend tests:

```bash
uv run python -m pytest -q tests/test_workbench_api.py tests/test_workbench_construction_evidence.py
```

Frontend/schema checks after TS mirror:

```bash
cd workbench-ui
pnpm test
pnpm build
```

Suggested new tests:

- `/trace/<id>/construction` returns `missing_evidence` for legacy turns without construction records.
- endpoint rejects non-integer turn ids with `not_found`.
- endpoint returns normal JSON error envelope for missing turn.
- exact span projector preserves `start`, `end`, `text` without normalization.
- TS schema snapshot reflects Python schema.

## Non-goals

- No frontend tab.
- No route registry changes.
- No proposal ratification changes.
- No generalization audit work.
- No CORE-Logos Studio.
- No practice trace reader.
