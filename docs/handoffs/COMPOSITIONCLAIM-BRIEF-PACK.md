# CompositionClaim Wave + Heuristic Tightening — Brief Pack

**Goal:** Build the next Tier 1.5 handler (CompositionClaim) covering the
**20 highest-leverage refusals** in `audit_brief_11.json`
(`quantity_extraction` 12 + `multi_quantity_composition` 8), then tighten
the decomposer dispatch heuristic so the workbench stops emitting
handler-mismatched proposals.

**Context.** End-to-end demo on 2026-05-27 revealed PR #386's dispatch
heuristic is too aggressive — both `frame_reclassification` proposals
from the audit are semantic mismatches for FrameClaim's
SAFE_FRAME_CATEGORIES (which are quantity/ownership frames, not
structural decompositions). HITL caught it (architecture working as
designed) but the operator burden is high. Build the next genuine
handler (CompositionClaim) AND fix the heuristic to stop emitting
proposals whose dispatch can never be ratified.

**Bundling rule:** [[feedback-batch-during-research]]. Three briefs,
two PRs:
- **PR-α (CC-1):** ADR-0169 + ADR-0169.1 doctrine docs only
- **PR-β (CC-2 + CC-3 bundled):** CompositionClaim impl + heuristic
  tightening + new `change_kind` Literal extension

CC-3 must bundle with CC-2 because the new `composition_reclassification`
change_kind is what CC-3 routes to.

---

## Dependency DAG

```
PR-α: CC-1 (ADR-0169 + 0169.1 docs)
       │
       └→ PR-β: CC-2 (handler impl) + CC-3 (heuristic tightening)
```

CC-1 ships first because CC-2 references the ratified doctrine.

---

## Brief CC-1 — ADR-0169 CompositionClaim doctrine + adapter

**Operator profile:** Opus (substantial design work; load-bearing for
wrong=0 hazard scope)
**Branch:** `docs/adr-0169-compositionclaim-doctrine`
**Base:** `origin/main`
**Style:** Pure docs PR. No runtime mutation.

### Outcome

Two new ADRs, modeled on ADR-0168 + ADR-0168.1:

1. **`docs/decisions/ADR-0169-compositionclaim-ratification.md`** — the
   doctrine. Same section structure as ADR-0168:
   - Status / Date / Author / Parent (ADR-0167) / Related
   - Context — why CompositionClaim is qualitatively different from
     LexicalClaim AND from FrameClaim
   - Prior ADR compatibility audit (matrix vs ADR-0056, 0057, 0114a,
     0164, 0165, 0166, 0167, 0168) — confirm each compatibility result
   - Decision — CompositionClaim is permitted only as a deterministic,
     replay-equivalent, operator-reviewed proposal surface with explicit
     hazard pins and category allowlists
   - Definition of a CompositionClaim — canonical shape:
     `(surface_pattern, composition_category, polarity)`
   - Why CompositionClaim is dangerous — arithmetic chains are upstream
     of solver invocation; wrong composition admits arithmetic errors,
     not noise
   - **Initial safe category scope** — propose the initial allowlist;
     `multiplicative_composition` (`each <count>` × `<one_unit_cost>`),
     `additive_composition` (sum of independent named quantities),
     `subtractive_composition` (initial − removed). Defer the rest
     (distributive, ratio, comparative) until proven.
   - Mutation boundary — may mutate reviewed composition-pattern
     registries; may NOT mutate solver / parser / decomposer / graph
     verifier semantics
   - Replay obligations — claim-signature determinism, replay
     equivalence, queue-order independence, idempotency
   - Refusal stability — previously-refusing cases may only transition
     to (a) correctly admitted or (b) still refused. NO ambiguous /
     partial / non-deterministic admissions.
   - Partition guarantees — math-domain only; cross-domain prohibited
   - Refusal-first doctrine — `refuse > speculate` preserved
   - Non-goals — list explicitly
   - Sequencing — ADR-0166 Q1/Q2/Q3 answered
   - Acceptance gates for implementation PR

2. **`docs/decisions/ADR-0169.1-math-compositionclaim-proposal-adapter.md`**
   — the adapter pattern (analogous to ADR-0168.1):
   - Why ADR-0057's reviewed-evidence floor requires a math-specific
     proposal type
   - Data shape — `MathCompositionClaimProposal` frozen dataclass:
     ```python
     @dataclass(frozen=True, slots=True)
     class MathCompositionClaimProposal:
         proposal_id: str
         claim_signature: str
         surface_pattern: str  # the regex / structural pattern matched
         composition_category: str  # must be in SAFE_COMPOSITION_CATEGORIES
         polarity: Literal["affirms", "falsifies"]
         evidence: tuple[MathReaderRefusalEvidence, ...]
         replay_evidence: AdmissibilityReplayEvidence | None
         review_state: Literal["pending", "accepted", "rejected", "withdrawn"]
         operator_note: str
         provenance: MathProposalProvenance | None
     ```
   - Trip-wires that close the ADR-0057 compatibility gap

### Hard requirements

- No runtime code in this PR. Pure ADR authoring.
- Must explicitly state the **initial SAFE_COMPOSITION_CATEGORIES** so
  CC-2 has a fixed allowlist to implement against.
- Must explicitly enumerate **case 0050 hazard pin** in the acceptance
  gates section.
- Cross-reference `docs/handoff/ADR-0167-FOLLOWUPS.md §1` priority hint
  (CompositionClaim is named there as 8+11 = 19 cases; the actual count
  in `audit_brief_11.json` is 20 — note the correction).

### Deliverables

- `docs/decisions/ADR-0169-compositionclaim-ratification.md`
- `docs/decisions/ADR-0169.1-math-compositionclaim-proposal-adapter.md`
- No code changes. No test changes.

### Reads required before starting

- `docs/decisions/ADR-0168-frameclaim-ratification.md` (the exact
  template — every section in ADR-0169 should mirror this structure)
- `docs/decisions/ADR-0168.1-math-frameclaim-proposal-adapter.md` (the
  adapter template)
- `docs/handoff/ADR-0167-FOLLOWUPS.md §1` (priority hint context)
- `docs/decisions/ADR-0172-math-corpus-decomposition-mechanism.md`
  (Tier 1.5 context — why CompositionClaim is the next handler)
- The 20 audit rows under `quantity_extraction` + `multi_quantity_composition`
  in `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` (the data
  the doctrine must cover)

---

## Brief CC-2 — CompositionClaim handler implementation

**Operator profile:** Opus (load-bearing wrong=0 surface; ratification
handler discipline)
**Branch:** `feat/adr-0169-compositionclaim-handler`
**Base:** `origin/main` (post-PR-α merge)

### Outcome

Three new/modified modules and the dispatch wire:

1. **`teaching/math_composition_proposal.py`** — `MathCompositionClaimProposal`
   dataclass per ADR-0169.1 §"Data shape", with canonical_bytes,
   compute_claim_signature, build_composition_proposal. Mirror the
   `teaching/math_frame_proposal.py` structure exactly.

2. **`teaching/math_composition_ratification.py`** —
   `apply_composition_claim()` handler. Mirror
   `teaching/math_frame_ratification.py` exactly. Mutates ONLY
   `language_packs/data/en_core_math_v1/compositions/{category}.jsonl`
   files. Does NOT touch solver / parser / decomposer / runtime.

3. **`workbench/readers.py`** — extend `_HANDLER_DISPATCH`:
   ```python
   _HANDLER_DISPATCH: dict[str, str] = {
       "vocabulary_addition": "LexicalClaim",
       "frame_reclassification": "FrameClaim",
       "composition_reclassification": "CompositionClaim",  # NEW
   }
   ```
   Plus a `suggested_cli` branch for `CompositionClaim`.

4. **`teaching/math_contemplation_proposal.py`** — extend the
   `proposed_change_kind` Literal:
   ```python
   proposed_change_kind: Literal[
       "matcher_extension",
       "injector_sub_shape",
       "vocabulary_addition",
       "frame_reclassification",
       "composition_reclassification",  # NEW
   ]
   ```
   And update `to_jsonl_record` / `from_jsonl_record` to round-trip the
   new kind (canonical_bytes is unchanged — it already serializes any
   string).

### Hard requirements

- **`SAFE_COMPOSITION_CATEGORIES`** allowlist (from ADR-0169 §"Initial
  safe category scope"):
  ```python
  SAFE_COMPOSITION_CATEGORIES: Final[frozenset[str]] = frozenset({
      "multiplicative_composition",
      "additive_composition",
      "subtractive_composition",
  })
  ```
  Any other category → `WrongCompositionCategory` exception.

- **Case 0050 hazard pin** mandatory (mirror
  `tests/test_math_frame_ratification.py::test_case_0050_hazard_pin`).
  Pin in `tests/test_math_composition_ratification.py`.

- **All replay obligations from ADR-0169** must be mechanically pinned:
  - Deterministic claim signature
  - Cross-process replay equivalence (subprocess test)
  - Queue-order independence (A→B == B→A ratify)
  - Duplicate idempotency (`AlreadyRatified` on second call)
  - Evidence-tampering rejection

- **Refusal stability** across the full `audit_brief_11.json` corpus —
  before/after ratifying a synthetic CompositionClaim, no case enters a
  partial/ambiguous state.

- **Partition** — cognition TeachingChainProposal flow MUST NOT see
  math CompositionClaims and vice versa.

- **No corpus laundering** — audit evidence is NOT
  `source="corpus"`. Adapter has its own evidence floor.

- **`composition_reclassification` Literal extension is the ONLY
  schema-level change** to `MathReaderRefusalShapeProposal`. No other
  fields change.

### Tests (`tests/test_math_composition_ratification.py`)

Mirror `tests/test_math_frame_ratification.py` exactly:

1. `test_safe_categories_allowlist_pinned` — exactly the 3 categories
2. `test_unsafe_category_rejected_with_wrong_category` — e.g.
   `distributive_composition` → `WrongCompositionCategory`
3. `test_claim_signature_canonicalization_deterministic`
4. `test_claim_signature_replay_equivalence_cross_process`
5. `test_ratification_advances_pending_proposal`
6. `test_duplicate_ratification_raises_already_ratified`
7. `test_evidence_tampering_rejected`
8. `test_case_0050_hazard_pin`
9. `test_refusal_stability_audit_brief_11`
10. `test_partition_cognition_proposals_not_seen`
11. `test_audit_evidence_not_laundered_as_corpus`
12. `test_queue_order_independence`
13. `test_workbench_dispatch_composition_reclassification` — routes to
    `CompositionClaim`, not 501
14. `test_proposal_change_kind_literal_accepts_composition_reclassification`
15. `test_jsonl_round_trip_with_composition_reclassification` — extends
    the W1 round-trip test for the new kind

### Deliverables

- `teaching/math_composition_proposal.py` (new file)
- `teaching/math_composition_ratification.py` (new file)
- `workbench/readers.py` — extend `_HANDLER_DISPATCH` + `suggested_cli`
- `teaching/math_contemplation_proposal.py` — Literal extension +
  serializer round-trip
- `language_packs/data/en_core_math_v1/compositions/.gitkeep` (new dir)
- `tests/test_math_composition_ratification.py` (new file, 15 tests)
- `tests/test_adr_0172_w1_shape_proposal.py` — add round-trip test for
  `composition_reclassification`
- `core/cli.py` — add test file to `teaching` suite tuple
- `core test --suite teaching -q` AND `core test --suite runtime -q`
  green

### Forbidden

- Mutating any compiled artifact
- Inventing categories outside `SAFE_COMPOSITION_CATEGORIES`
- Touching `matcher_extension` or `injector_sub_shape` dispatch
- Importing from `chat/`, `field/`, `generate/`, `algebra/`
- Removing the existing `frame_reclassification` dispatch entry

---

## Brief CC-3 — Decomposer heuristic tightening

**Operator profile:** Same operator as CC-2 (bundled in same PR — needs
the new `composition_reclassification` Literal value from CC-2)
**Bundled into PR-β** with CC-2.

### Outcome

Two changes to `teaching/math_contemplation.py::decompose_audit()`:

1. **Add CompositionClaim routes** — extend the pair-based dispatch
   table to route the 20 composition cases:
   ```python
   (incomplete_operation, quantity_extraction)         → composition_reclassification  # was injector_sub_shape
   (incomplete_operation, multi_quantity_composition)  → composition_reclassification  # was injector_sub_shape
   ```

2. **Remove the over-aggressive frame_reclassification routes** —
   demonstrated at the 2026-05-27 end-to-end demo to be handler
   mismatches:
   ```python
   (unexpected_category, multi_subject_sentence)       → injector_sub_shape  # was frame_reclassification — WRONG: needs ReferenceClaim/CompositionClaim, not FrameClaim
   (unexpected_category, descriptive_frame_question)   → injector_sub_shape  # was frame_reclassification — WRONG: needs SlotClaim, not FrameClaim
   ```
   These go back to `injector_sub_shape` (the catch-all) until
   SlotClaim / ReferenceClaim handlers ship. Add an inline comment
   explaining why.

### Hard requirements

- Hypothesis step in the reasoning trace MUST be updated to reflect
  the new dispatch table — the justification text in the
  `hypothesis` step is the operator-facing audit of the heuristic.
- Re-running `core eval math-contemplation` post-merge MUST yield:
  - 2 `composition_reclassification` proposals (covering 20 cases)
  - 3 `matcher_extension` proposals (unchanged)
  - 0 `frame_reclassification` proposals from this audit (the
    aggressive routes are gone; no real frame_opener refusals in
    `audit_brief_11.json` exist)
  - 3 `injector_sub_shape` proposals (the multi_subject_sentence and
    descriptive_frame_question cases land here pending SlotClaim /
    ReferenceClaim)

  Verify this in the PR body.

### Tests

Update `tests/test_adr_0172_w2_decomposer.py`:
- `test_decompose_audit_change_kind_dispatch` — extend with assertions
  for the new routes + the demoted frame_reclassification routes
- Add `test_quantity_extraction_routes_to_composition_reclassification`
- Add `test_multi_quantity_composition_routes_to_composition_reclassification`
- Add `test_multi_subject_sentence_routes_to_injector_sub_shape`
- Add `test_descriptive_frame_question_routes_to_injector_sub_shape`

### Forbidden

- Adding new change_kinds beyond `composition_reclassification`
- Changing the heuristic for any pair not listed above
- Touching the LexicalClaim or FrameClaim dispatch

---

## Anti-regression invariants (all three briefs)

- `wrong == 0` on `core eval gsm8k_math` — preserved
- ADR-0166 — no new eval lanes
- ADR-0057 replay-equivalence — inherited
- Pinned-lane SHAs — should not require updates
- `engine_state/*` — never committed
- Case 0050 hazard — pinned in CC-2's test suite

---

## Memory pointers

- [[feedback-batch-during-research]] — bundling justification
- [[feedback-no-self-dispatch-of-subagents]] — Shay dispatches
- [[feedback-wrong-zero-hazard-case-0050]] — CC-2 mandatory pin
- [[feedback-parallel-agent-worktrees]] — fresh worktree per brief
- [[feedback-cleanup-as-you-find]] — remove dead frame_reclassification
  test fixtures touched by CC-3
- [[feedback-production-line-pattern]] — dispatch protocol
- [[milestone-adr-0172-tier1-2026-05-27]] — Tier 1 milestone
- [[adr-0167-audit-as-evidence-wave]] — parent ADR

---

## What ships when both PRs land

- **CC-1 (ADR-0169 doctrine):** Doctrine on main; CompositionClaim
  becomes the next ratifiable surface scope; sub-type follow-on queue
  in ADR-0167-FOLLOWUPS §1 advances.
- **CC-2 (handler):** First handler that can actually ratify the
  highest-leverage refusals (20 of 47). Workbench `POST
  /math-proposals/{id}/ratify` on the 2 composition_reclassification
  proposals returns 200/routed with a real `apply_composition_claim()`
  command.
- **CC-3 (heuristic tightening):** Workbench stops emitting
  handler-mismatched proposals. The 2 previously-misrouted
  frame_reclassification proposals now route to injector_sub_shape
  (still 501 until SlotClaim/ReferenceClaim ship, but the dispatch is
  honest).

**Together:** the compounding loop runs for real on 20 of 47 audit
refusals. Run `core eval math-contemplation`, ratify either
`composition_reclassification` proposal, execute the suggested CLI,
re-run `core eval gsm8k_math` — those previously-refused cases admit.
