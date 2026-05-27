# Tier 1.5 (FrameClaim) + Tier 2 W5 — Brief Pack

**Status:** Two parallel briefs. Both branch off latest `origin/main`. Zero file
overlap — safe to dispatch concurrently.

**Goal:** Close the **compounding** gap. Tier 1 emits proposals; the
LexicalClaim handler is live but `audit_brief_11.json` carries 0 lexical
refusals. **FrameClaim** is the next handler — turns 4 of the 8 currently-501
proposals into actual GSM8K admissions on ratify. In parallel, ship the **Tier
2 schema substrate** so the intensional-layer work has a foundation when we
re-scope W6+ after FrameClaim proves the ratification → admission path.

**Bundling rule:** [[feedback-batch-during-research]] — two PRs, each a
coherent solution.

---

## Why these two, not more

After #386 (Tier 1 tightening) the proposal distribution is:

| change_kind | Count | Handler today |
|---|---|---|
| `vocabulary_addition` | 0 | LexicalClaim ✅ live |
| `frame_reclassification` | 2 (4 cases) | **FrameClaim** — this brief |
| `matcher_extension` | 3 (17 cases) | No handler — needs separate scoping ADR |
| `injector_sub_shape` | 3 (24 cases) | No handler — needs separate scoping ADR |

FrameClaim is the **next-highest-leverage** handler with a complete scoping ADR
already on main (ADR-0168 + ADR-0168.1). The other two change_kinds need new
ADRs before implementation.

Tier 2 W5 is pure schema. It does NOT require FrameClaim to ship first. But
W6 (recognizer) + W7 (two-arm test-and-learn) DO benefit from FrameClaim
being live — Arm 2 ("known-good preservation") needs handlers that actually
move rows from refused to admitted. So we ship W5 substrate now and defer
W6+ until FrameClaim is the ground-truth handler the two-arm loop verifies
against.

---

## Brief F1 — Tier 1.5: FrameClaim ratification handler

**Operator profile:** Opus (load-bearing wrong=0 surface; case 0050 hazard
zone)
**Branch:** `feat/adr-0168-frameclaim-handler`
**Base:** `origin/main`

### Outcome

Two new modules and the proposal→handler wiring:

1. **`teaching/math_frame_proposal.py`** — `MathFrameClaimProposal`
   dataclass per ADR-0168.1 §"Data shape":

   ```python
   @dataclass(frozen=True, slots=True)
   class MathFrameClaimProposal:
       proposal_id: str
       claim_signature: str
       surface_form: str
       frame_category: str  # must be in SAFE_FRAME_CATEGORIES
       polarity: Literal["affirms", "falsifies"]
       evidence: tuple[MathReaderRefusalEvidence, ...]
       replay_evidence: AdmissibilityReplayEvidence | None
       review_state: Literal["pending", "accepted", "rejected", "withdrawn"]
       operator_note: str
       provenance: MathProposalProvenance | None

   def canonical_bytes(p: MathFrameClaimProposal) -> bytes: ...
   def compute_claim_signature(surface_form, frame_category, polarity, audit_digest, refusal_category) -> str: ...
   def build_frame_proposal(...) -> MathFrameClaimProposal: ...
   ```

2. **`teaching/math_frame_ratification.py`** — the ratification handler.
   Modeled exactly on `teaching/math_lexical_ratification.py` (the W2-D
   template). Mutates ONLY:
   - reviewed frame-category registries (e.g. a frame_opener JSON file under
     `language_packs/data/en_core_math_v1/frames/`)
   - reviewed verb→frame mappings (same dir)
   - proposal-layer artifacts

   Does NOT touch:
   - compiled artifacts (`lexicon.jsonl`, manifest)
   - solver / parser / decomposer / runtime
   - graph verifier semantics

3. **Workbench dispatch wire** — `workbench/readers.py` currently 501s
   `frame_reclassification`. Wire it through to
   `teaching.math_frame_ratification.ratify_frame_claim()`. The 501 path
   stays for `matcher_extension` and `injector_sub_shape` (no handlers yet).

### Hard requirements

- **`SAFE_FRAME_CATEGORIES`** allowlist (final, per ADR-0168 §"Initial safe
  category scope"):
  ```python
  SAFE_FRAME_CATEGORIES: Final[frozenset[str]] = frozenset({
      "increment_frame",
      "decrement_frame",
      "transfer_frame",
      "remainder_frame",
  })
  ```
  Any other category → `WrongFrameCategory` exception. Pin in a test.

- **Case 0050 hazard pin** — mandatory. Ratifying any frame in this initial
  scope MUST NOT admit case 0050. Pin in a test that mutates pack state,
  runs the math reader on case 0050, and asserts it remains refused at
  `sentence_index=0`. (Mirror `tests/test_math_lexical_ratification.py`'s
  hazard pin.)

- **Replay obligations** (ADR-0168 §"Replay obligations"):
  - Deterministic claim signature: equivalent refusals → identical
    `claim_signature`
  - Cross-process replay equivalence: same proposal byte-identical across
    `uv run python -c "..."` subprocess
  - Queue-order independence: ratify two proposals in either order →
    identical resulting pack state
  - Duplicate idempotency: ratifying the same proposal twice → second call
    is a no-op (raises `AlreadyRatified`)

- **Refusal stability** (ADR-0168 §"Refusal stability"): every case that
  currently refuses MUST either (a) continue refusing or (b) become
  correctly admitted. NO case may become partially admitted, ambiguously
  admitted, or non-deterministically admitted. Pin via a refusal-stability
  test that runs the full `audit_brief_11.json` corpus before AND after
  ratifying a synthetic FrameClaim and asserts no case enters a partial
  state.

- **Partition guarantee**: FrameClaim is math-domain only. Cognition
  TeachingChainProposal flow MUST NOT see math FrameClaims and vice versa.
  Pin in a test.

- **No corpus laundering** (ADR-0168.1): MathReaderRefusalEvidence must NOT
  be passed as `source="corpus"` evidence anywhere. The FrameClaim adapter
  has its own evidence floor.

- **Evidence-tampering rejection**: `evidence_hash` must validate against
  the proposal's evidence list at ratification time. Tampering → reject.

### Tests (`tests/test_math_frame_ratification.py`)

Modeled on `tests/test_math_lexical_ratification.py`:

1. `test_safe_categories_allowlist_pinned` — exactly the 4 categories,
   nothing else
2. `test_unsafe_category_rejected_with_wrong_category` — passing
   `comparison_frame` → `WrongFrameCategory`
3. `test_claim_signature_canonicalization_deterministic` — same inputs →
   identical signature
4. `test_claim_signature_replay_equivalence_cross_process` — subprocess
   verification
5. `test_ratification_advances_pending_proposal` — happy-path
6. `test_duplicate_ratification_raises_already_ratified` — idempotency
7. `test_evidence_tampering_rejected` — modified evidence → reject
8. `test_case_0050_hazard_pin` — case 0050 stays refused after ratifying
   any synthetic FrameClaim in scope
9. `test_refusal_stability_audit_brief_11` — full corpus refusal-stability
   sweep
10. `test_partition_cognition_proposals_not_seen` — cross-domain isolation
11. `test_audit_evidence_not_laundered_as_corpus` — evidence-floor
    discipline
12. `test_queue_order_independence` — A→B ratify == B→A ratify
13. `test_workbench_dispatch_frame_reclassification` — workbench route
    actually fires the handler (not 501)
14. `test_recognized_but_uninjectable_does_not_regress` — the existing
    hazard pin from ADR-0167-FOLLOWUPS §1

### Deliverables

- `teaching/math_frame_proposal.py` (new file, ≤300 lines)
- `teaching/math_frame_ratification.py` (new file, ≤400 lines —
  W2-D-shaped)
- `workbench/readers.py` — wire `frame_reclassification` dispatch
- `language_packs/data/en_core_math_v1/frames/.gitkeep` if the dir doesn't exist (the
  ratification handler mutates files under here)
- `tests/test_math_frame_ratification.py` (new file, 14 tests above)
- `core/cli.py` — add the test file to the `teaching` suite tuple
  (mirror W2's wiring at line ~68)
- `core test --suite teaching -q` green
- `core test --suite runtime -q` green

### Forbidden

- Mutating `lexicon.jsonl` or any compiled artifact
- Adding `gained` to any frame category (delta-of-attribute hazard per
  [[feedback-wrong-zero-hazard-case-0050]])
- Auto-accepting any proposal — review must be explicit
- Inventing categories outside `SAFE_FRAME_CATEGORIES`
- Importing from `chat/`, `field/`, `generate/`, `algebra/`
- Touching `injector_sub_shape` or `matcher_extension` dispatch (keep them
  501)

### Reads required before starting

- `docs/decisions/ADR-0168-frameclaim-ratification.md` (full doctrine)
- `docs/decisions/ADR-0168.1-math-frameclaim-proposal-adapter.md` (data
  shape + evidence floor)
- `teaching/math_lexical_ratification.py` (the W2-D template — every
  pattern in F1 should mirror this)
- `tests/test_math_lexical_ratification.py` (the test pattern)
- `workbench/readers.py` — find the `frame_reclassification` 501 dispatch site
- `docs/handoff/ADR-0167-FOLLOWUPS.md §1` — the dispatch table this PR
  retires for `FrameClaim`

---

## Brief T2-W5 — Tier 2: `MathReaderInferenceProposal` schema

**Operator profile:** Sonnet (pure dataclass + canonical-bytes; analogous to
ADR-0172 W1)
**Branch:** `feat/adr-0172-w5-inference-proposal`
**Base:** `origin/main`
**Runs concurrent with F1** — zero file overlap.

### Outcome

A new module `teaching/math_inference_proposal.py` defines:

```python
@dataclass(frozen=True)
class TwoArmResult:
    arm: Literal["arm1_held_out", "arm2_known_good"]
    outcome: Literal["PASS", "REJECT", "NEUTRAL"]
    cases_total: int
    cases_passed: int  # admitted with correct answer
    cases_changed_answer: int  # for arm2; must be 0 for PASS
    cases_no_admit: int
    case_verdict_table: tuple[tuple[str, str], ...]  # (case_id, verdict) sorted by case_id

@dataclass(frozen=True)
class MathReaderInferenceProposal:
    proposal_id: str
    domain: Literal["math"]
    inference_id: str  # human-readable, e.g. "math.inferential.acquisition_to_initial_state"
    structural_claim: str  # the canonical-form equivalence statement
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...]  # ≥3 cases
    arm1_held_out_result: TwoArmResult
    arm2_known_good_result: TwoArmResult
    wrong_zero_assertion: str
    replay_equivalence_hash: str
    reasoning_trace: ReasoningTrace  # ≥6 steps (observation → grouping → abstraction → hypothesis → test_design → test_application → test_result → conclusion)
    ratification_effect_kind: Literal["canonicalization_bridge"]
    ratification_effect_payload: object  # JSON-serializable; describes the bridge

def canonical_bytes(p: MathReaderInferenceProposal) -> bytes: ...
def compute_proposal_id(...) -> str: ...
def build_inference_proposal(...) -> MathReaderInferenceProposal: ...
def to_jsonl_record(p) -> dict: ...  # self-contained, mirrors W1's pattern post-#386
def from_jsonl_record(d) -> MathReaderInferenceProposal: ...
```

### Hard requirements

- **Both arms required**: `build_inference_proposal` rejects construction
  if either `arm1` or `arm2` is `REJECT`. The proposal schema itself
  cannot represent a "surface to HITL" state where either arm failed —
  that filtering happens upstream in W7. Pin this in tests.
- **Evidence floor**: `len(evidence_pointers) >= 3` (raises ValueError on
  fewer). Higher than W1's ≥2 floor — intensional claims need more signal.
- **`reasoning_trace.steps` ≥ 6**: must include at minimum `observation`,
  `grouping`, `abstraction`, `hypothesis`, `test_design`, `test_application`,
  `test_result`, `conclusion` step_kinds. Pin in a test.
- **`arm2.cases_changed_answer == 0` when `arm2.outcome == "PASS"`**:
  enforced at construction. A "PASS" Arm 2 means NO currently-correct
  outcome changed.
- **`ratification_effect_kind == "canonicalization_bridge"`**: the only
  effect Tier 2 emits. Other kinds reserved for future use.
- **JSONL self-containment**: `to_jsonl_record()` mirrors the post-#386
  pattern from `math_contemplation_proposal.py` — full evidence inline,
  full trace inline, `proposal_id` included. The workbench reads via
  `from_jsonl_record()`, no decomposer coupling.
- **No floats in canonical bytes** (same discipline as W0 / W1).

### Tests (`tests/test_adr_0172_w5_inference_proposal.py`)

1. `test_minimum_three_evidence_rows`
2. `test_reasoning_trace_minimum_six_steps`
3. `test_arm1_reject_blocks_construction`
4. `test_arm2_reject_blocks_construction`
5. `test_arm2_pass_requires_zero_changed_answer`
6. `test_canonical_bytes_stable`
7. `test_proposal_id_determinism`
8. `test_to_from_jsonl_record_roundtrip`
9. `test_ratification_effect_kind_literal_enforced`
10. `test_wrong_zero_assertion_required`
11. `test_no_floats_in_canonical_bytes`

### Deliverables

- `teaching/math_inference_proposal.py` (new file, ≤300 lines)
- `tests/test_adr_0172_w5_inference_proposal.py` (new file, 11 tests)
- `core/cli.py` — add the test file to the `teaching` suite tuple
- `core test --suite teaching -q` green

### Forbidden

- Implementing the recognizer (W6) or two-arm loop (W7) — schema only
- Wiring into the workbench (W8)
- Adding new step_kinds to `ReasoningTrace` (the 8 already exist)
- Any runtime hook

### Reads required before starting

- `docs/decisions/ADR-0172-math-corpus-decomposition-mechanism.md` §"Tier 2"
- `teaching/math_contemplation_proposal.py` — the Tier 1 W1 schema +
  post-#386 to_jsonl_record/from_jsonl_record pattern (mirror this exactly)
- `teaching/math_reasoning_trace.py` — the trace substrate

---

## Anti-regression invariants (both briefs)

- `wrong == 0` on `core eval gsm8k_math` — unaffected by F1 (handler is
  proposal-only mutation, no runtime hot-path) and unaffected by W5
  (schema only).
- ADR-0166 — no new eval lanes.
- ADR-0057 replay-equivalence — F1 and W5 both inherit.
- Pinned-lane SHAs — should not require updates.
- `engine_state/*` — never committed.

---

## Memory pointers (read before starting)

- [[feedback-batch-during-research]] — one PR per coherent solution
- [[feedback-no-self-dispatch-of-subagents]] — operator dispatches, not Agent tool
- [[feedback-wrong-zero-hazard-case-0050]] — F1's mandatory pin
- [[feedback-parallel-agent-worktrees]] — worktree per brief
- [[feedback-cleanup-as-you-find]] — dead code in same PR
- [[feedback-production-line-pattern]] — the dispatch protocol
- [[milestone-adr-0172-tier1-2026-05-27]] — what Tier 1 shipped

---

## What ships when both land

**F1 (FrameClaim handler):**
- First non-lexical ratification handler live
- 2 of 8 Tier 1 proposals (`frame_reclassification`, covering 4 cases)
  become real GSM8K admissions on operator ratify
- The compounding loop closes for frame-opener teaching
- Establishes the W2-D-shaped template for CompositionClaim /
  ReferenceClaim / SlotClaim follow-ons (lower-priority items in
  ADR-0167-FOLLOWUPS §1)

**W5 (Inference proposal schema):**
- Tier 2 substrate in place; W6/W7/W8/W9 can ship without re-doing
  schema work
- Two-arm test-and-learn contract pinned at the type level — Arm 1 and
  Arm 2 must both PASS or be NEUTRAL; REJECT in either arm cannot
  construct
- ReasoningTrace step_kinds for Tier 2 (`abstraction`, `test_design`,
  `test_application`, `test_result`) move from "reserved" to "load-bearing"

**Together:** the math-domain Learning Arc closes its compounding loop for
the first time (F1), AND the next architectural layer's substrate is ready
to receive intensional proposals (W5). Tier 2 W6+ then has ground truth
to validate against.
