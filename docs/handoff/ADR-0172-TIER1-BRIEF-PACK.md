# ADR-0172 Tier 1 — Brief Pack

**Goal:** Land the math-domain Learning Arc analog. Engine reads
`audit_brief_11.json`, decomposes it into structural commonalities,
emits `MathReaderRefusalShapeProposal` records (each carrying a
`ReasoningTrace`) for HITL review.

**Scope:** Tier 1 only (extensional contemplation). Tier 2
(intensional + two-arm test-and-learn) and Loop 3 (verdict feedback)
ship later. Reference: `docs/decisions/ADR-0172-math-corpus-decomposition-mechanism.md`
(on `origin/main`).

**Bundling rule:** Per Shay 2026-05-27 — during research/solutions-finding
phases, batch chunks locally; one PR per coherent solution, not per
file. **Each WAVE below is one PR.** Within a wave, parallel briefs
land on the same branch.

---

## Dependency DAG

```
Wave A (parallel)            Wave B (parallel)        Wave C        Wave D
─────────────────            ────────────────         ──────        ──────
[A1] W0 ReasoningTrace ──┐
                         ├─→ [B1] W0.1 trace replay test
                         │                            ├─→ [C1] W3 ──┐
[A2] W1 ShapeProposal ───┤                            │  CLI lane   ├─→ [D1] W4
                         └─→ [B2] W2 Decomposer ──────┘             │   Workbench
                                                                    │   integration
                                                                    │   + e2e
```

**Wave A** can launch immediately on origin/main once #377 (ADR-0170 W2) merges.
**Wave B** launches once Wave A's branch is pushed (B1 and B2 can branch off
A's tip in parallel).
**Wave C** launches when Wave B's branch is pushed.
**Wave D** launches when Wave C's branch is pushed.

Total wall-clock: 4 PRs if waves serialize, 2 PRs if A+B and C+D are bundled
(see "Bundling options" at bottom).

---

## Worktree hygiene

Every brief opens with:

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin main
git worktree add /tmp/wt-<slug> origin/main  # or off Wave-X tip for waves B/C/D
cd /tmp/wt-<slug>
```

**Never** `git add -A`. Stage explicit files only. `engine_state/*` are
runtime artifacts — never commit.

---

## Brief A1 — W0: `ReasoningTrace` substrate

**Operator profile:** Opus (foundation schema; load-bearing for all
downstream waves)
**Branch:** `feat/adr-0172-w0-reasoning-trace`
**Base:** `origin/main` (post-#377 merge)

### Outcome

A new module `teaching/math_reasoning_trace.py` defines:

```python
@dataclass(frozen=True)
class ReasoningStep:
    step_index: int
    step_kind: Literal[
        "observation", "grouping", "abstraction", "hypothesis",
        "test_design", "test_application", "test_result", "conclusion",
    ]
    input_pointers: tuple[str, ...]   # IDs of prior steps / evidence rows
    claim: str
    justification: str
    output_payload: object            # JSON-serializable; type-discriminated by step_kind

@dataclass(frozen=True)
class ReasoningTrace:
    trace_id: str                     # content hash of canonical bytes
    steps: tuple[ReasoningStep, ...]

def canonical_bytes(trace: ReasoningTrace) -> bytes: ...
def compute_trace_id(steps: tuple[ReasoningStep, ...]) -> str: ...
def build_trace(steps: list[ReasoningStep]) -> ReasoningTrace:
    """Validates step_index continuity, sorts, computes trace_id."""
```

### Hard requirements

- Canonical-bytes serialization: stable JSON ordering (sorted keys,
  no whitespace, UTF-8, deterministic float repr if any).
- `compute_trace_id` = `hashlib.sha256(canonical_bytes(...)).hexdigest()`.
- `build_trace` enforces `step_index` starts at 0, monotonic +1,
  no gaps. Raises `ValueError` on violation.
- `output_payload` must be JSON-serializable. Validate at construction.
- Tier 1 step_kinds used: `observation`, `grouping`, `hypothesis`,
  `conclusion`. The other four (`abstraction`, `test_design`,
  `test_application`, `test_result`) are reserved for Tier 2; the
  schema admits them but no Tier 1 code path emits them yet.

### Tests (`tests/test_adr_0172_w0_reasoning_trace.py`)

1. `test_step_index_must_start_at_zero` — passing `step_index=1` first → ValueError.
2. `test_step_index_must_be_monotonic` — `[0, 2]` → ValueError.
3. `test_canonical_bytes_stable_across_runs` — same steps → byte-identical.
4. `test_trace_id_changes_when_claim_changes` — sensitivity check.
5. `test_trace_id_invariant_to_dict_insertion_order` — payload dict key ordering doesn't shift id.
6. `test_non_json_serializable_payload_rejected` — `set()` payload → ValueError.
7. `test_all_eight_step_kinds_accepted` — schema admits all Literal members.
8. `test_empty_trace_rejected` — `build_trace([])` → ValueError.

### Forbidden

- Any runtime hook into the cognitive pipeline (W0 is schema-only).
- Importing anything from `chat/`, `field/`, `generate/`, `algebra/`.
- Floating-point usage in canonical bytes (use int / str only).

### Deliverable

- `teaching/math_reasoning_trace.py` (new file, ≤200 lines)
- `tests/test_adr_0172_w0_reasoning_trace.py` (new file)
- `core test --suite teaching -q` green

---

## Brief A2 — W1: `MathReaderRefusalShapeProposal` schema

**Operator profile:** Sonnet (schema mirror of cognition's
`teaching/proposals.py`; bounded scope)
**Branch:** `feat/adr-0172-w1-shape-proposal` (separate worktree from A1)
**Base:** `origin/main` (post-#377 merge)
**Runs concurrent with A1** — no shared files.

### Outcome

A new module `teaching/math_contemplation_proposal.py` defines:

```python
@dataclass(frozen=True)
class MathReaderRefusalShapeProposal:
    proposal_id: str
    domain: Literal["math"]
    shape_category: ShapeCategory              # from evals.refusal_taxonomy.shape_categories
    structural_commonality: str
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...]  # ≥2; from teaching/audit_evidence.py
    proposed_change_kind: Literal[
        "matcher_extension",
        "injector_sub_shape",
        "vocabulary_addition",
        "frame_reclassification",
    ]
    proposed_change_payload: object            # JSON-serializable; discriminated by change_kind
    wrong_zero_assertion: str
    replay_equivalence_hash: str
    reasoning_trace: ReasoningTrace             # from W0

def canonical_bytes(p: MathReaderRefusalShapeProposal) -> bytes: ...
def compute_proposal_id(...) -> str: ...
def build_proposal(...) -> MathReaderRefusalShapeProposal:
    """Validates evidence ≥2, payload JSON-serializable, hashes."""
```

### Hard requirements

- `proposal_id = sha256(canonical_bytes(...))` minus the proposal_id
  field itself (chicken-and-egg: hash the content, not the id).
- `build_proposal` enforces `len(evidence_pointers) >= 2` (raises ValueError).
- `domain == "math"` enforced as Literal; `ShapeCategory` validated as enum member.
- `wrong_zero_assertion` non-empty (≥40 chars, soft pin: ValueError if empty).
- `replay_equivalence_hash` matches ADR-0057's existing replay-equivalence
  contract format — copy the convention from `teaching/proposals.py`.
- `reasoning_trace` field is mandatory (carries W0 trace).

### Tests (`tests/test_adr_0172_w1_shape_proposal.py`)

1. `test_minimum_two_evidence_rows` — passing 1 evidence row → ValueError.
2. `test_canonical_bytes_stable` — same input → byte-identical output.
3. `test_proposal_id_determinism` — same content → same id.
4. `test_change_kind_literal_enforced` — invalid `change_kind` rejected.
5. `test_change_payload_must_be_json_serializable` — `set()` → ValueError.
6. `test_wrong_zero_assertion_required` — empty string → ValueError.
7. `test_reasoning_trace_required` — `None` trace → ValueError.
8. `test_all_four_change_kinds_round_trip` — schema admits all Literal members.

### Cross-references the operator must read first

- `teaching/proposals.py` — the cognition `TeachingChainProposal` (template)
- `teaching/audit_evidence.py` — `MathReaderRefusalEvidence` shape (ADR-0167)
- `evals/refusal_taxonomy/shape_categories.py` — `ShapeCategory` enum

### Forbidden

- Any runtime hook into ingest, gate, vault, or solver.
- Importing W0 from a relative path — use `from teaching.math_reasoning_trace import ReasoningTrace`.
- Inventing a new `change_kind` not listed in the ADR.

### Deliverable

- `teaching/math_contemplation_proposal.py` (new file, ≤250 lines)
- `tests/test_adr_0172_w1_shape_proposal.py` (new file)
- `core test --suite teaching -q` green

---

## Brief B1 — W0.1: Trace replay-equivalence

**Operator profile:** Codex (mechanical determinism test)
**Branch:** `feat/adr-0172-w0-1-trace-replay-equivalence`
**Base:** Tip of Wave A (after A1 + A2 merge or fast-forward locally).
**Runs concurrent with B2** — no shared files.

### Outcome

Pin the W0 contract: same input → byte-identical `ReasoningTrace`.

### Tests (`tests/test_adr_0172_w0_1_trace_replay_equivalence.py`)

1. `test_build_trace_replay_equivalence_minimal` — 2 steps, run 100 times → all identical bytes.
2. `test_build_trace_payload_dict_key_order_invariance` — `{"a":1,"b":2}` and `{"b":2,"a":1}` payloads → same trace_id.
3. `test_build_trace_under_process_restart` — write canonical bytes to a tmp file in one process,
   re-derive in a second process via `uv run python -c "..."`, assert byte-identical.
4. `test_trace_id_collision_resistance` — 1000 random-but-deterministic step sequences,
   no id collisions (sanity check on hash quality).
5. `test_canonical_bytes_no_floating_point` — assert no `float` instance appears in
   any canonical-byte payload across the test corpus (regex `[0-9]+\.[0-9]+` absent).

### Deliverable

- `tests/test_adr_0172_w0_1_trace_replay_equivalence.py` (new file)
- No production changes. Pure pinning.

---

## Brief B2 — W2: Audit-corpus decomposer

**Operator profile:** Opus (load-bearing logic; the cognition decomposer
analog. Get it right.)
**Branch:** `feat/adr-0172-w2-decomposer`
**Base:** Tip of Wave A.
**Runs concurrent with B1** — no shared files.

### Outcome

A new module `teaching/math_contemplation.py` defines:

```python
def decompose_audit(audit_path: Path) -> tuple[MathReaderRefusalShapeProposal, ...]:
    """
    Read audit_brief_11.json, group refusal rows by
    (refusal_reason, missing_operator), emit one
    MathReaderRefusalShapeProposal per group with ≥2 evidence rows.
    Naive algorithm per ADR-0172 §"Six open questions" #1.
    """
```

### Algorithm (verbatim from ADR)

1. Parse `audit_path` (expect `evals/gsm8k_math/train_sample/v1/audit_brief_11.json`).
2. Group rows by `(refusal_reason, missing_operator)` tuple.
3. For each group with `≥2` rows:
   a. Build evidence list: `MathReaderRefusalEvidence` for each row (use `teaching/audit_evidence.py` helpers).
   b. Build `ReasoningTrace` with 4 steps:
      - step 0: `observation` — "N refusal rows share (refusal_reason, missing_operator)"
      - step 1: `grouping` — encode group key as payload
      - step 2: `hypothesis` — pick `proposed_change_kind` by heuristic (see below)
      - step 3: `conclusion` — restate the proposed change.
   c. Derive `proposed_change_kind` heuristic:
      - `refusal_reason == "lexicon_entry"` → `vocabulary_addition`
      - `refusal_reason == "narrowness_violation"` → `matcher_extension`
      - `refusal_reason == "frame_unrecognized"` → `frame_reclassification`
      - else → `injector_sub_shape`
   d. Build `MathReaderRefusalShapeProposal` with placeholder
      `proposed_change_payload` (a dict of the group's modal anchor shape)
      and `wrong_zero_assertion`: "Proposal is evidence-only; ratification
      handler is the wrong=0 surface, not this proposal."
4. Sort output proposals by `proposal_id` for determinism.
5. Return tuple.

### Determinism contract (CRITICAL)

- Group iteration order MUST be sorted by `(refusal_reason, missing_operator)`.
- Evidence list per group MUST be sorted by `case_id`.
- Reasoning step payload dicts MUST use sorted keys.
- Same `audit_brief_11.json` → byte-identical proposal stream across reruns.

### Tests (`tests/test_adr_0172_w2_decomposer.py`)

1. `test_decompose_audit_emits_at_least_one_proposal` — on the real audit file.
2. `test_decompose_audit_deterministic_across_reruns` — run 10x, assert all outputs identical.
3. `test_decompose_audit_minimum_evidence_threshold` — groups with 1 row do NOT emit.
4. `test_decompose_audit_change_kind_dispatch` — synthetic 4-row audit with
   one row per heuristic branch; assert each emits the expected `change_kind`.
5. `test_decompose_audit_reasoning_trace_has_four_steps` — every emitted proposal carries a 4-step trace.
6. `test_decompose_audit_evidence_sorted_by_case_id` — synthetic audit with out-of-order case_ids; assert sorted in output.
7. `test_decompose_audit_proposal_ids_sorted` — output tuple is sorted by proposal_id.
8. `test_decompose_audit_empty_file_returns_empty_tuple` — `[]` input → `()` output.
9. `test_decompose_audit_no_runtime_mutation` — assert no file is written, no global state touched.

### Forbidden

- Auto-applying any proposal. Pure read-only decomposition.
- Writing to `teaching/math_proposals/*` (that's W3's job).
- Importing from `chat/`, `field/`, `generate/`, `algebra/`. Decomposer
  is teaching-layer code only.
- Mutating the input audit file.

### Deliverable

- `teaching/math_contemplation.py` (new file, ≤350 lines)
- `tests/test_adr_0172_w2_decomposer.py` (new file)
- `core test --suite teaching -q` green

---

## Brief C1 — W3: `core eval math-contemplation` CLI lane

**Operator profile:** Sonnet (CLI plumbing, well-bounded)
**Branch:** `feat/adr-0172-w3-cli-lane`
**Base:** Tip of Wave B.

### Outcome

A new CLI subcommand:

```bash
core eval math-contemplation [--audit-path PATH] [--output PATH]
```

- Reads audit file (default: `evals/gsm8k_math/train_sample/v1/audit_brief_11.json`).
- Calls `decompose_audit()` from W2.
- Writes proposals to `teaching/math_proposals/proposals.jsonl` (default).
- Prints summary: N proposals emitted, by `change_kind` breakdown.

### Hard requirements

- Output file is JSONL: one proposal per line, canonical-bytes-encoded.
- Output is sorted by proposal_id (matches W2's order).
- Re-running the command on the same audit overwrites with identical bytes
  (idempotent).
- Exit code 0 on success, 1 on audit-file-not-found, 2 on parse error.
- Output path validated (no traversal — apply `language_packs/compiler.py::_validate_pack_id` pattern).

### CLI wiring

- Locate `core/cli.py` (or wherever `core eval cognition` is registered).
- Mirror that subcommand structure exactly.
- Register as `core eval math-contemplation`.

### Tests (`tests/test_adr_0172_w3_cli_lane.py`)

1. `test_cli_emits_jsonl_to_default_path` — invoke via `subprocess.run`, check file exists.
2. `test_cli_idempotent` — run twice, assert second-run file is byte-identical to first.
3. `test_cli_rejects_path_traversal` — `--output ../../etc/passwd` → exit 2.
4. `test_cli_missing_audit_exit_1` — bogus `--audit-path` → exit 1.
5. `test_cli_summary_stdout_format` — assert summary line matches expected format (regex).

### Deliverable

- CLI subcommand wired in `core/cli.py` (or sibling).
- `teaching/math_proposals/.gitkeep` (so the dir exists; proposals.jsonl is gitignored).
- `.gitignore` entry for `teaching/math_proposals/proposals.jsonl`.
- `tests/test_adr_0172_w3_cli_lane.py` (new file).
- `core test --suite runtime -q` green.

### Forbidden

- Auto-applying any proposal (CLI is read+emit, no ratification side-effect).
- Modifying the audit file.
- Writing proposals outside `teaching/math_proposals/` (path-scoped).

---

## Brief D1 — W4: Workbench integration + e2e

**Operator profile:** Sonnet (UI/workbench wiring; bounded)
**Branch:** `feat/adr-0172-w4-workbench`
**Base:** Tip of Wave C.

### Outcome

The workbench (ADR-0160) renders math proposals alongside cognition
proposals. The two proposal streams remain partitioned by
`domain` discriminator.

### Hard requirements

- Workbench reads from `teaching/math_proposals/proposals.jsonl` (W3's output).
- Math proposals render with `domain: math` badge (visible distinction
  from `domain: cognition`).
- Operator can `ratify` / `reject` a math proposal. Ratification routes to
  the existing handler dispatch (LexicalClaim for `vocabulary_addition`,
  FrameClaim for `frame_reclassification`, etc. per ADR-0167-FOLLOWUPS §1).
  If a handler doesn't exist yet (e.g. `matcher_extension` has no handler
  on `main` yet), emit a clear "handler not yet implemented" message and
  refuse the action — do NOT silently no-op.
- The proposal's `reasoning_trace` is rendered in expandable form (per-step claims visible).

### e2e test (`tests/test_adr_0172_w4_workbench_e2e.py`)

1. `test_workbench_loads_math_proposals_from_jsonl` — write a fixture jsonl, assert workbench reads it.
2. `test_workbench_renders_domain_badge` — math proposal carries math badge.
3. `test_workbench_ratify_routes_to_lexical_claim_handler` — ratifying a `vocabulary_addition` proposal calls LexicalClaim handler.
4. `test_workbench_rejects_unhandled_change_kind_loudly` — `matcher_extension` ratify → explicit error, no silent no-op.
5. `test_workbench_renders_reasoning_trace_steps` — all 4 trace steps visible.
6. `test_workbench_no_cognition_math_cross_contamination` — math proposals don't appear in cognition queue and vice versa.

### Workbench files to inspect first

- `chat/workbench.py` (or wherever ADR-0160's workbench lives — grep for `cognition_proposals`)
- ADR-0160 itself (`docs/decisions/ADR-0160-*.md`)
- ADR-0167-FOLLOWUPS §1 for the handler dispatch table

### Forbidden

- Auto-ratifying any proposal.
- Reading proposals from anywhere other than `teaching/math_proposals/`.
- Writing to the cognition proposal queue from math handlers.

### Deliverable

- `chat/workbench.py` (or sibling) updated.
- `tests/test_adr_0172_w4_workbench_e2e.py` (new file).
- `core test --suite teaching -q` and `core test --suite runtime -q` green.
- `core eval math-contemplation` works end-to-end and proposals appear in workbench.

---

## Bundling options (operator choice)

**Option 1 — Maximum parallelism (4 PRs):**
- Wave A (PR-α): A1 + A2 bundled (W0 + W1 schemas). Two operators, one branch.
- Wave B (PR-β): B1 + B2 bundled (W0.1 trace test + W2 decomposer). Two operators, one branch.
- Wave C (PR-γ): C1 alone (W3 CLI).
- Wave D (PR-δ): D1 alone (W4 workbench).

**Option 2 — Substrate-first (2 PRs):** (recommended for first attempt)
- PR-α: A1 + A2 + B1 (all schema work + replay test). One operator can do all three
  sequentially since they're tight + closely coupled.
- PR-β: B2 + C1 + D1 (decomposer + CLI + workbench). The full materialization
  of the substrate into the user-facing lane.

**Option 3 — All-in-one (1 PR):**
- Single PR shipping W0 through W4. Largest reviewable surface but lowest
  CI thrash. Best if a single operator (Opus) drives the whole chunk.

**Shay's call:** Per "batch during research" rule (2026-05-27), Option 2 or
Option 3 minimizes CI churn. Option 1 maximizes wall-clock if multiple
operators are available simultaneously.

---

## Anti-regression invariants (all waves)

- `wrong == 0` on `core eval gsm8k_math` — unaffected (W0–W4 are
  teaching-layer evidence-only).
- ADR-0166 — no new eval lanes. The `core eval math-contemplation`
  lane is a *teaching-corpus decomposition lane*, not a capability
  measurement lane.
- ADR-0057 replay-equivalence — W0 traces and W2 proposals inherit
  the byte-identical-replay contract.
- ADR-0167-FOLLOWUPS — Tier 1 proposals route to existing handler
  dispatch, do not invent new handlers.
- `engine_state/*` — never committed.
- Pinned-lane SHAs — Tier 1 should not require updates (no canonical
  lane changes). If a wave needs a pin update, it's a signal to
  re-scope.

---

## Memory pointers (must read before starting any wave)

- `feedback-batch-during-research` — bundle chunks; one PR per coherent solution
- `feedback-no-self-dispatch-of-subagents` — Shay dispatches operators; brief author does NOT call Agent tool
- `feedback-wrong-zero-hazard-case-0050` — the canary; every wave verifies it stays refused
- `feedback-parallel-agent-worktrees` — each parallel brief opens with `git worktree add`
- `feedback-cleanup-as-you-find` — any dead code revealed mid-implementation is removed in the same PR
- `feedback-adr-cross-reference-discipline` — grep all ADRs + codebase for inner mechanisms before reinventing

---

## What ships when Tier 1 lands

The math-domain Learning Arc closes:

```
math refusal → audit row → engine decomposes → engine PROPOSES
  shape change → HITL ratifies → handler materializes → next session
  admits what was previously refused
```

That's the same loop cognition closed on 2026-05-25. Tier 2 (intensional
+ two-arm test-and-learn) and Loop 3 (verdict feedback) extend the
arc into structural-equivalence-class learning. Tier 1 is the
substrate they ride on.
