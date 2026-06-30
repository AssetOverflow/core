# SESSION-2026-05-27 — ADR-0167 parallel-dispatch (audit-as-teaching-evidence)

**Date:** 2026-05-27
**Author:** Shay
**Companion ADR:** [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md)
**Parent session:** [SESSION-2026-05-26 (Brief 11 comprehension reader)](./SESSION-2026-05-26-comprehension-reader.md)
**Anchor:** [[thesis-decoding-not-generating]]

---

## What happened

Brief 11's closure pass landed across the day (11A→11B→11D merged; 11C
absorbed into ADR-0167 W3-A). Mid-day, while reviewing the Brief 11B
audit taxonomy, a question surfaced:

> See, if it has this kind of information, can't it also be used to help
> it try and (re)solve problems?

That observation — that the refusal taxonomy is itself a queue of
*teachable moments*, not just a diagnostic dump — became ADR-0167. By
end of day, the ADR + the LexicalClaim-first implementation slice were
mostly landed (W1-A + W2-A/B/C/D merged; W3-A in flight with Opus 4.7).

## The architectural pivot

The temptation was a refusal-class dispatch table:
`missing_operator → specialised handler`. Reader hits
`multi_quantity_composition`? Route to a frame-splitter. Hits
`fraction_percentage_literal`? Route to a fraction subroutine. That
direction was rejected explicitly in the ADR (§"Why this is not a
refusal-class dispatch table") because it is library-of-handlers — the
same anti-pattern regex sentence templates represented, which
[[adr-0164-comprehension-reader]] retired.

The right direction came from the thesis: the engine doesn't store
another found thing; it *surfaces what it failed to find* in a shape the
operator can teach against. The audit taxonomy is the queue; the
existing contemplation/HITL teaching corridor is the resolution path. No
new mechanism — wire the math reader's evidence into the same loop
cognition already uses.

## The dispatch experiment

ADR-0167's implementation was a clean target for the parallel-agent
pattern: 6 PRs across 3 waves, 5 model operators matched to brief shape.

| Wave | PR | Brief | Operator | Why this model |
|---|---|---|---|---|
| W1 | #350 | MathReaderRefusalEvidence schema | Opus 4.6/4.7 | Foundation; must be right first time |
| W2 | #352 | Audit→evidence adapter | GPT-5.3-Codex | Mechanical type-A→type-B + tests |
| W2 | #353 | Lexical claim signature + dedup | Sonnet 4.6 | Pure-Python tight-scope normalisation |
| W2 | #351 | Domain discriminator + audit | Gemini | Long-context survey of every call site |
| W2 | #354 | LexicalClaim ratification handler | GPT-5.5 | Highest-stakes; GitHub-connector review coordination |
| W3 | (open) | E2E determinism + cognition regression | Opus 4.7 | Integration verification; deep reasoning |

Briefs lived in `tmp/wave2.md` and `tmp/wave3.md`. Each operator pointed
to their section header. Shared constraints (worktree isolation,
wrong=0, ADR-0166, uv, explicit staging) at the top of each wave doc.

## What worked

**Brief-shape matching.** Earlier sessions mixed agents poorly — feedback
captured in [[feedback-shay-workstyle]] and the new
[[feedback-parallel-dispatch-pattern]] memory entry. This time the
mapping was deliberate: Opus to load-bearing schema, Codex to mechanical
wiring, Gemini to long-context surveys, Sonnet to tight-scope normalisation,
GPT-5.5 to high-stakes pack-mutation. Result: 5/5 briefs produced
usable work, 4 needed no handler intervention, 1 (Codex) tapped out at
rate limits but had finished implementation — handler finished the
commit+push+PR mechanically.

**Single monitor on terminal CI state.** Earlier polling-loop monitors
spammed every 60 seconds with `pending`. The fix: `until` loop in the
Monitor command, emit only when state is no longer pending. One event
per PR completion, no noise.

**Wave-N dispatches AFTER wave-(N-1) merges to main.** Briefly tested
the alternative (Gemini accidentally merged W1-A's branch into its W2-C
branch because W1-A wasn't yet on main); harmless this time but the
discipline is to wait. Memory entry pins this.

## What surfaced as load-bearing

**Case `gsm8k-train-sample-v1-0050` is the canary.** During Brief 11B I
tried the naive `pre_frame_filler_sentence` fix (drain
`statement_terminator` at pre-frame). It lifted 2 cases to admitted, but
case 0050 silently produced a partial graph that would project to the
wrong answer. The fix was rejected per Brief 11 §"correct-count greed,"
and the hazard is now pinned across the test suite — see
[[feedback-wrong-zero-hazard-case-0050]]. W2-D's `SAFE_CATEGORIES =
{"drain_token"}` allowlist extends the same defence: frame-opener
categories cannot be ratified through LexicalClaim because reclassifying
a verb like `does` to `accumulation_verb` would re-introduce the hazard.

**The thesis answer to "can it use the taxonomy to resolve?"** The
right wire is *into the teaching corridor*, not *into the runtime*. The
engine learns from its own refusal data through reviewed correction —
the loop the thesis demands. ADR-0167 is what makes that loop concrete
for the math domain.

## What's deferred

- **Four non-lexical sub-types** (FrameClaim / CompositionClaim /
  ReferenceClaim / SlotClaim) — separate ADRs, follow-up scope.
- **Workbench v1 rendering of math candidates** — ADR-0167 §Q4.
- **Two partition risks Gemini flagged** in the W2-C audit:
  contemplation pack indexing (`teaching/contemplation.py` uses
  hardcoded cognition pack/corpus indexes), and replay gate default in
  `teaching/proposals.py`. Both need follow-up but don't block the
  LexicalClaim slice.

## What closes the day

When W3-A merges:

- The LexicalClaim slice is operational end-to-end (refusal → evidence
  → signature → ratification → row movement, with cognition regression
  holding green and case 0050 hazard pinned)
- 11C (the capability snapshot) closes as a side effect of W3-A's
  Deliverable 2
- The thesis claim — *the engine teaches itself in the math domain
  through reviewed correction* — becomes a green test (`tests/
  test_math_evidence_e2e.py::test_lexical_ratification_advances_unknown_word_row`)

Brief 11 closes alongside W3-A. The next session can pick up either a
non-lexical sub-type ADR, the workbench wiring, the cognition pack
indexing partition, or continued GSM8K operator closure — Brief 11D
already named those candidates.

---

## Cross-references

- [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md) — the scoping ADR
- `docs/handoff/ADR-0167-PARALLEL-WORK-PLAN.md` — the 3-wave / 6-PR dispatch plan
- `docs/handoff/BRIEF-11-phase-2-reader-closure-and-capability-snapshot.md` — Brief 11 with EOD status footer
- `docs/handoff/ADR-0167-W2C-cross-domain-audit.md` — Gemini's audit (5 construction / 8 consumption sites)
- `evals/gsm8k_math/train_sample/v1/audit_brief_11.md` — the bottleneck table the wire is built around
- `tmp/wave2.md` / `tmp/wave3.md` — the dispatch briefs (kept in-repo as the parallel-agent playbook for future waves)
