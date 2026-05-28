# ADR-0174 — Held-Hypothesis Comprehension with Lookback and In-Loop Contemplation

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Parent:** [ADR-0164 — Incremental Comprehension Reader](./ADR-0164-incremental-comprehension-reader.md)
**Companions:** [ADR-0165 — Regex Scope Rule](./ADR-0165-regex-scope-rule.md), [ADR-0163 — Path to GSM8K mastery](./ADR-0163-gsm8k-path-to-mastery.md), [ADR-0150/0152/0155/0161 — Contemplation / HITL corridor](./), [ADR-0170 — Injector Contract Widening](./ADR-0170-injector-contract-widening.md), [ADR-0172 — Math-Corpus Decomposition](./ADR-0172-math-corpus-decomposition-mechanism.md)
**Extends:** [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) (lexicon, categories, deterministic per-token reading — all preserved)
**Deprecates:**
- The per-category injector dispatch table at `generate/recognizer_anchor_inject.py:233` (ADR-0170 W2 and subsequent D.2.x extensions) as the **runtime admission path**. The injectors become hypothesis-emitters within the held-hypothesis reader; they no longer route admission via category lookup.
- The legacy regex parser at `generate/math_parser.py` as a **parallel runtime path**. It survives only as the offline measurement-comparison baseline (`--legacy-parser` flag per CLEANUP-C2 brief).

---

## Context — what ADR-0164 shipped, why the score hasn't moved

ADR-0164 correctly diagnosed the regex sentence-template trap and prescribed the right substrate: an operational lexicon, a closed category set, a deterministic shift-reduce reader over categories. Phases 1 and 2 shipped. The reader is wired (`generate/comprehension/lifecycle.py`, `generate/comprehension/state.py`, 2,700 lines combined) and the flag is on in the current train_sample run (`use_reader: true`).

The eval is unchanged: `correct=3, refused=47, wrong=0` on `evals/gsm8k_math/train_sample/v1`, byte-identical to the regex-only baseline. Reader-trace inspection confirms the reader fires on every problem and produces a `ReaderRefusal` on the first unknown-word or unexpected-category token, then falls through to the regex pipeline which also refuses.

Three causes, in priority order:

1. **All-or-nothing refusal at the token level.** `apply_word(state, ps, token)` returns `state | ReaderRefusal`. The first unknown word or unexpected category collapses the entire comprehension. There is no state representing "I do not yet know what role this token plays; I will hold the question open and continue reading." A natural-language reader without held hypotheses cannot read natural language.

2. **No lookback re-evaluation.** Even when `apply_word` succeeds, the commitment is final. The reader cannot undo a category assignment when a later token reveals the prior commitment was wrong. "She studied for 2 hours on Wednesday and three times as long on Thursday" — the temporal-aggregation reading of "for 2 hours" should be open until the second clause arrives; the reader currently locks it as a quantity at the first sentence boundary.

3. **Recovery lives offline.** When the reader refuses, the path to learning the missing word is: refusal → audit row → contemplation lane (offline) → workbench → HITL ratify → next session. This is correct for **durable** learning but wrong for **the current problem**. A reader that cannot ask "what would I need to know to finish this read" within the read itself cannot solve problems whose answer is one inference away.

The result: each accepted category, each new lexicon entry, each new D.2.x injector lifts the eval by 0–2 cases. The `correct` count rises monotonically and slowly; the architecture overfits to GSM8K sentence shapes one shape at a time. This is the **library-of-founds** trap the project thesis explicitly forbids.

---

## Diagnosis — single-committed state cannot model partial understanding

A natural-language reader observes a token, hypothesizes its role *given everything else*, and revises that hypothesis as more tokens arrive. The hypothesis space narrows with reading. At sentence end (or problem end), the surviving hypothesis is admitted.

ADR-0164's reader is structurally **single-committed**: at every token, exactly one `ProblemReadingState` exists. Disambiguation must complete at the moment of token consumption, because there is nowhere to *defer* an interpretation. When deferral is impossible, the reader compensates with strict expectation-matching, and when expectation matching fails, the reader refuses.

The same problem manifests three ways:

- **Ambiguous categories must commit immediately.** "Tina makes" — `makes` could open an `accumulation_verb` frame, an `aggregate_modifier` (as in "makes total"), or a copular construction ("makes Tina happy"). The reader must pick one. Picking wrong means refusing later; picking right means refusing on the next ambiguous token.
- **Unknown words refuse rather than narrow.** A token absent from the lexicon emits `ReaderRefusal(unknown_word, position)`. The legitimate alternative — "this is an unknown word at position N; my hypothesis set narrows to interpretations that don't depend on this word's category" — is not representable.
- **End-of-sentence finalization is binary.** `finalize(state) → graph | Refusal`. There is no "I have two complete hypotheses; let downstream constraints eliminate one." The held-hypothesis behavior already lives at the candidate-graph layer (Cartesian product over per-sentence choices + constraint elimination via `_initial_admissible` / `roundtrip_admissible`); it should live at the reader.

ADR-0164's `apply_word(state, ps, token) → state | Refusal` is the right *shape* but the wrong *cardinality*. Promote it to `apply_word(state, ps, token) → state'` where `state'.open_hypotheses` is a small ranked set, and refusal is what happens when the set becomes empty.

---

## Decision — held-hypothesis comprehension

Replace single-committed `ProblemReadingState` with a **held-hypothesis** model in which the reader carries a small ranked set of open interpretations and applies three operators per token:

1. **EMIT** — the token extends every compatible hypothesis (existing reader behavior, but applied to each hypothesis in the set).
2. **ELIMINATE** — hypotheses whose constraints are violated by the new token are removed. Constraints are the existing admissibility predicates (`_initial_admissible`, `roundtrip_admissible`, unit-grounding, verb-kind whitelist) applied to the in-flight hypothesis, not just the finalized candidate.
3. **HOLD** — when the token does not commit a category but narrows the role for some hypotheses, those hypotheses survive at lower confidence; uncommitted hypotheses are retained.

At sentence end (and problem end), the surviving hypothesis set drives admission:

- **|surviving| = 0** → refuse with the union of elimination reasons.
- **|surviving| = 1** → admit (existing graph emission path, unchanged).
- **|surviving| ≥ 2** → invoke **in-loop contemplation** to synthesize an elimination sub-question; on resolution, eliminate further; if still ≥ 2 at problem end, refuse with `ambiguous: <N> surviving interpretations` (preserves wrong = 0).

### Four components

#### 1. Held-hypothesis state (immutable, frozen-dataclass)

```text
ProblemReadingState:
  entities:               tuple[EntityRef, ...]
  quantities:             tuple[QuantityRef, ...]
  open_hypotheses:        tuple[Hypothesis, ...]    # NEW — ranked, ≤ HYPOTHESIS_CAP
  pronoun_history:        tuple[PronounRef, ...]
  sentence_index:         int
  source_text_offset:     int
  unknown_held:           tuple[UnknownHeld, ...]   # NEW — tokens awaiting resolution

Hypothesis:
  candidate:              CandidateInitial | CandidateOperation | CandidateUnknown
  category_assignments:   tuple[CategoryAssignment, ...]   # per-token category trace
  constraint_state:       ConstraintState                  # what's been verified
  confidence_rank:        int                              # 0 = best; ties broken by appearance order
  unresolved:             tuple[UnresolvedSlot, ...]       # what we still need

UnknownHeld:
  token:                  str
  position:               int
  narrowed_categories:    frozenset[Category]              # hypotheses that survived this unknown
```

`HYPOTHESIS_CAP` is a small constant (3 or 4). The cap is not a heuristic limit on capability — it is a structural assertion that **a coherent sentence has at most a few plausible parses**. Exceeding the cap is a signal that the read has lost coherence; the reader refuses.

State remains immutable and canonical-bytes-serializable; the existing `trace_hash` deterministic-replay contract from ADR-0164 is preserved.

#### 2. Lookback re-evaluation operator

A new operator on hypothesis state:

```text
reevaluate(hypotheses, new_token, position) -> (refined_hypotheses, eliminations)
```

When a token arrives that resolves an earlier ambiguity, `reevaluate` walks the hypothesis set and:

- For each hypothesis, recomputes the category assignment of any *prior* token whose role depended on the now-resolved ambiguity.
- Records the recomputation in `category_assignments` (so the trace is auditable: "token N was originally `accumulation_verb`, reassigned to `aggregate_modifier` after token M=`total`").
- Eliminates hypotheses whose recomputed assignments violate existing constraints.

Lookback is **bounded**: it walks only back to the last token whose category was contested in the hypothesis set, never the whole sentence. The bound is structural — uncontested tokens contribute no recomputation work — not a heuristic cap.

#### 3. Continuous constraint propagation

The candidate-graph layer's admissibility check already enforces grounding (`roundtrip_admissible`) and consistency (`_initial_admissible`). Today these run only on **finalized** candidates at the end of `parse_and_solve`. Move them inside the reader so they fire per-token:

- After every `EMIT`, run the in-flight constraint check against the partial hypothesis. A hypothesis whose partial state already violates a constraint cannot become valid by adding more tokens — eliminate immediately.
- The check is conservative: it only fires when the relevant slots are populated. An incomplete `CandidateOperation` with a verb but no value token does not trigger value-grounding; once the value token arrives, the check fires and eliminates the hypothesis if the value doesn't ground.

This is **process of elimination during reading**, not pattern-match-then-verify after reading. The set narrows token-by-token via real constraint failures, not via expectation-matching heuristics.

#### 4. In-loop contemplation

When the surviving hypothesis set is ambiguous (`|surviving| ≥ 2`) or empty (`|surviving| = 0` with held unknowns), the reader invokes contemplation **inside the read**, not as an offline batch job.

```text
contemplate(state, residual) -> Resolution | None

Resolution:
  kind:            "eliminate" | "admit_unknown"
  target_hypothesis_id: int               # which hypothesis to refine
  sub_question:    str                    # the question the reader is asking itself
  source:          "vault" | "pack" | "audit_history"
  evidence:        tuple[EvidenceRef, ...]
```

The contemplation function consults — in this order — the vault (prior session memory), the active language packs (the cognition / relations / math packs), and the audit-history of prior reader refusals on the same word or shape. It returns `Resolution` only when the evidence is unambiguous; ambiguous evidence returns `None` and the reader refuses cleanly.

`contemplate` does not invoke an LLM, does not sample, does not normalize. It is a deterministic search over already-ratified evidence. The thesis discipline (`thesis-decoding-not-generating`) is enforced: the engine finds the resolution that already exists in its memory, or it refuses.

The in-loop call site is a single addition to `finalize()`:

```text
def finalize(ps: ProblemReadingState) -> MathProblemGraph | ReaderRefusal:
    survivors = ps.open_hypotheses
    if not survivors:
        return ReaderRefusal(union of elimination reasons)
    if len(survivors) == 1:
        return survivors[0].to_graph()
    # |survivors| ≥ 2
    resolution = contemplate(ps, residual=survivors)
    if resolution is None:
        return ReaderRefusal(f"ambiguous: {len(survivors)} surviving interpretations")
    return apply_resolution(ps, resolution).to_graph()
```

### What this collapses

Three parallel parsing systems become one reader with hypothesis state:

| Module | Today's role | After ADR-0174 |
|---|---|---|
| `generate/math_parser.py` | Regex sentence-template parser (legacy) | **Removed from runtime.** Survives only as offline baseline behind `--legacy-parser`. |
| `generate/math_candidate_graph.py::parse_and_solve` | Recognizer-driven Cartesian-product parser | The held-hypothesis admission orchestrator. The Cartesian product, the per-sentence-choices accumulator, and the elimination passes move *inside* the reader; this module becomes the thin admission/solve dispatcher. |
| `generate/comprehension/lifecycle.py` | All-or-nothing reader (Phase 1+2 shipped, inert) | **The reader.** Hosts `open_hypotheses`, `reevaluate`, in-loop `contemplate` integration. |
| `generate/recognizer_anchor_inject.py` | Per-category injector dispatch table | **Hypothesis emitters.** The category-keyed lookup is removed; injectors become functions the reader calls to *propose* hypotheses from a recognized anchor. The category tag becomes a property of the emitted hypothesis, not a routing key. |

Lines saved (approximate, conservative): ~1,800 from `math_parser.py` removal, ~400 from injector dispatch elimination, ~300 from duplicated per-sentence-choice scaffolding in `math_candidate_graph.py`. The reader grows by an estimated ~600 lines for hypothesis state + `reevaluate` + `contemplate` integration. **Net: ~1,900 lines removed.**

---

## Constraints (non-negotiable)

1. **`wrong = 0` at every phase, every round, every split.** Held hypotheses do not weaken admissibility — they relocate the elimination work earlier in the pipeline. The existing `_initial_admissible`, `roundtrip_admissible`, multi-branch-disagreement check, and the case-0050 hazard pin all remain in force. A hypothesis that survives the reader is admitted by the same predicates that admit a candidate today.

2. **No hidden normalization, stochastic fallback, or best-guess.** `contemplate` is deterministic search over ratified evidence; it returns `Resolution | None`, never a softmax distribution. Ambiguity that contemplation cannot resolve is a refusal, not a guess. `HYPOTHESIS_CAP` is a structural assertion about coherent reads, enforced by refusal — not a probability cutoff.

3. **No regex sentence-templates.** ADR-0165 is preserved verbatim. Regex remains allowed only at the lexeme level (currency literal, fraction literal, percentage literal, time-unit noun). Any regex matching across word combinations remains forbidden.

4. **Lexicon and category set remain closed and ADR-tracked.** ADR-0164's lexicon discipline carries forward unchanged. New categories or new composition rules continue to require an ADR. Held-hypothesis reading is a new *use* of the existing categories, not an expansion of the category set.

5. **Deterministic replay.** Identical input → byte-equal hypothesis trace. The `trace_hash` contract from CLAUDE.md §Runtime Surface Contract is extended to cover `open_hypotheses` serialization. The replay-equivalence gate (ADR-0172 W0-1) catches any non-determinism.

6. **In-loop contemplation has the same trust boundary as offline contemplation.** It reads from vault, packs, and audit history. It never mutates them in-session. Any ratification that needs to happen still rides the existing HITL corridor (ADR-0150/0152/0155/0161). The in-loop call is read-only; the offline call writes proposals.

---

## What's deprecated, what's preserved

### Deprecated by this ADR

- **Per-category injector dispatch** (`generate/recognizer_anchor_inject.py:233 _INJECTORS`). The category-keyed lookup table is removed. Injector functions (`inject_discrete_count_statement`, etc.) survive as **hypothesis-emitter helpers** called by the reader from per-token context, but they no longer route admission via category dispatch. The widening pattern (ADR-0170) is preserved as the *type* the emitter returns; the per-category dispatch *as the admission mechanism* is replaced.
- **Legacy regex parser as a runtime path** (`generate/math_parser.py`). Removed from the runtime pipeline; the file survives only to back the `--legacy-parser` baseline flag in `evals/gsm8k_math/runner.py` (CLEANUP-C2). Once Phase 3 of this ADR is met, the baseline comparison can be retired and the file deleted entirely.
- **All-or-nothing `ReaderRefusal` on first unknown-word or unexpected-category** in `generate/comprehension/lifecycle.py`. Replaced by `UnknownHeld` and hypothesis narrowing.

### Preserved in full

- **ADR-0164's operational lexicon and category set.** The work that went into `en_core_math_v1` lexicon, category definitions, and shift-reduce composition rules is the foundation this ADR builds on. Held hypotheses use exactly the same categories and the same lexicon entries.
- **The binding graph and solver substrate** (ADR-0116/0117/0132/0133/0134/0135). Downstream consumption is unchanged.
- **The HITL corridor** (ADR-0150/0152/0155/0161). Offline contemplation, proposal generation, ratification, and pack-mutation all preserved. In-loop contemplation is additive, not replacement.
- **`wrong = 0` doctrine** and the replay-equivalence gate.
- **The composition registry and frame registry consumers** (ADR-0168/0169). These are constraint sources the held-hypothesis reader consults; they remain unchanged.
- **The capability-axis lanes** (G1–G5, S1) and the math contemplation corpus (ADR-0172). They continue to validate the downstream substrate and act as regression nets.

### Untouched but adjacent

- **The recognizer registry / matcher set** (`generate/recognizer_match.py`, `generate/recognizer_registry.py`). Matchers continue to publish anchors; the difference is that anchors feed hypothesis emitters per-token rather than dispatch-table injectors. The HITL pathway that grows the recognizer registry (ADR-0163.C/D) is unchanged.
- **The reader-question hybrid path** (ADR-0164.2 / ADR-0164.3 pronoun + cross-sentence). These become first-class hypothesis-producers within the held-hypothesis state.

---

## Phasing

### Phase 1 — Held-hypothesis state primitive

Implement `Hypothesis`, `UnknownHeld`, and the `open_hypotheses` field on `ProblemReadingState`. Refactor `apply_word` to operate on the hypothesis set (single hypothesis → tuple of 1, behavior preserved). No new admission behavior; the change is structural.

**Acceptance:**
- All existing reader tests pass byte-identical (the single-hypothesis case is exactly today's behavior).
- `test_reader_coexistence.py` continues to assert `wrong = 0` on the 50-case train_sample.
- `trace_hash` invariant verified on `train_sample/v1`.

### Phase 2 — Continuous constraint propagation

Hoist `_initial_admissible` and `roundtrip_admissible` from the candidate-graph layer into per-token in-flight checks within the reader. Hypotheses violating constraints are eliminated immediately, not at end of `parse_and_solve`.

**Acceptance:**
- Train_sample score: no decrease (`correct ≥ 3, wrong = 0` minimum).
- Some refusal reasons shift from `no admissible candidate` to early in-reader elimination (visible in `reader_trace`); the total count is preserved or improves.
- Holdout split unchanged within ±1 case.

### Phase 3 — Lookback re-evaluation

Implement `reevaluate` operator and wire it into `apply_word`. Hypotheses can have prior category assignments refined when later tokens disambiguate.

**Acceptance:**
- The 21 currently-empty `discrete_count_statement` anchors (pronoun subject, compound clause) are revisited: when the question sentence resolves the pronoun, the held statement can be reevaluated. Target: ≥ 5 of these cases admit cleanly.
- `correct ≥ 8` on train_sample, `wrong = 0`.

### Phase 4 — In-loop contemplation

Wire `contemplate` into `finalize()`. The function consults vault + packs + audit history for deterministic resolution of ambiguous hypothesis sets.

**Acceptance:**
- `correct ≥ 15` on train_sample, `wrong = 0` (passes ADR-0163 Round-1 exit comfortably).
- In-loop contemplation events are observable in the reader trace and replay-equivalent (re-running the same input yields the same contemplation call sequence).
- No case where in-loop contemplation introduces a wrong answer that offline-only contemplation would not.

### Phase 5 — Remove parallel parsers

Delete `generate/math_parser.py`'s runtime invocation paths. Remove the per-category injector dispatch table; injectors become inlined hypothesis emitters. Collapse the duplicate per-sentence-choices scaffolding in `math_candidate_graph.py`.

**Acceptance:**
- `correct ≥ 25` on train_sample, `wrong = 0` (passes ADR-0163 Round-2 exit).
- Net line count reduction matches the estimate (~1,900 lines).
- The capability-axis lanes G1–G5, S1 remain at 100% `wrong = 0`.

### Phase 6 — Scale

Per ADR-0163 §Phase F: public, dev, holdout. No changes to that scope from this ADR.

---

## Acceptance criteria for this ADR (Proposed → Accepted)

This ADR moves to **Accepted** when:

1. Phase 1 acceptance is met: held-hypothesis state primitive lands, all existing tests pass, `trace_hash` invariant holds.
2. A prototype of the lookback `reevaluate` operator exists with at least one test demonstrating prior-token category reassignment under a later disambiguating token.
3. A prototype of in-loop `contemplate` exists with at least one test showing deterministic vault-consultation resolving an ambiguous hypothesis set on a curated case.
4. Capability-axis lanes G1–G5, S1 remain at 100% `wrong = 0`.
5. `verify pinned lane SHAs` continues to pass.
6. Cross-references to ADR-0164 (lexicon and category preservation), ADR-0165 (regex scope), and ADR-0172 (replay-equivalence) reviewed and confirmed unchanged.

---

## Open questions (resolve before Phase 1 PR)

1. **HYPOTHESIS_CAP value.** Initial proposal: 4 (matches the candidate-graph layer's empirical observation that GSM8K sentences rarely admit more than 3 distinct readings before a constraint eliminates one). Should be set by measurement after Phase 1 lands the data collection.
2. **Lookback walk bound.** Whether to bound by token-distance (e.g., re-evaluate at most 10 tokens back) or by category-contest (re-evaluate only tokens whose category was contested in the hypothesis set). Proposal: category-contest, because it is structural and cannot mask a real ambiguity behind a numeric cap.
3. **Contemplation evidence-ordering precedence.** When vault, packs, and audit history all return candidate resolutions, the ordering matters for determinism. Proposal: vault > packs > audit history, mirroring the existing offline contemplation precedence in `teaching/contemplation.py`. Confirm against the audit-history schema before Phase 4.
4. **Sub-ADR for hypothesis emitters.** The per-category injector functions becoming hypothesis emitters may warrant its own sub-ADR (ADR-0174.1) given the surface area touched. Decide after Phase 1 lands and the call surface is concrete.
5. **Eval set adequacy.** The 50-case `train_sample/v1` may be too narrow to validate the held-hypothesis approach; some of the architecture's value (lookback, in-loop contemplation) only manifests on multi-step problems with cross-sentence ambiguity. May need a curated 20-case sub-corpus exercising specifically these patterns before Phase 3 measurement.

---

## Cross-references

- **Parent**: [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) — lexicon, categories, deterministic reader; this ADR extends without replacing.
- **Constraint scope**: [ADR-0165](./ADR-0165-regex-scope-rule.md) — preserved verbatim.
- **Eval target**: `evals/gsm8k_math/train_sample/v1/report.json`, `evals/gsm8k_math/train_sample/v1/README.md` (§ADR-0164 Reader — Zero-Delta Diagnosis).
- **Substrate this builds on**: `generate/comprehension/lifecycle.py`, `generate/comprehension/state.py`, `generate/recognizer_anchor_inject.py`, `generate/math_candidate_graph.py`, `generate/math_roundtrip.py`.
- **Cleanup briefs touching the deprecated paths**: `docs/handoff/CLEANUP-C2-run-lane-migration.md`, `docs/handoff/CLEANUP-C4-compositions-compile.md`.
- **Thesis anchor**: [[thesis-decoding-not-generating]] — every change in this ADR must pass the "teach the engine to find, not store another found thing" gate.
- **HITL corridor preserved**: ADR-0150 (contemplation), ADR-0152 (proposal), ADR-0155 (review), ADR-0161 (HITL queue), ADR-0172 (math-corpus decomposition).
- **Anti-overfitting obligations**: ADR-0114a — held-hypothesis reads are evaluated against the same obligations as the existing pipeline; perturbation, OOD ratio, depth curve, and adversarial axes all apply.
