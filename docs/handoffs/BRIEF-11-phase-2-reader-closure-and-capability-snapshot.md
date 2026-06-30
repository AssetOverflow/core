# Brief 11 — Phase 2 Reader Closure and Capability Snapshot

**Status:** Active handoff
**Date:** 2026-05-27
**Branch:** `docs/brief-11-handoff`
**Scope:** Private repo planning and execution handoff only. No public-safe disclosure. No runtime claim is made by this document.

---

## Thesis

Brief 11 should close the current comprehension-reader corridor before widening measurement or domain scope.

The latest project state establishes three facts that must govern sequencing:

1. `gsm8k_math` is not blocked by a lack of eval lanes. It is blocked by incomplete statement understanding.
2. The ADR-0164 reader is the correct replacement path for the brittle ADR-0163 recognizer/injector surface.
3. ADR-0166 now forbids authoring new canonical eval lanes ahead of the capability they measure.

Therefore Brief 11 is not "make more benchmarks." Brief 11 is the bounded closure pass that turns the Phase 2 reader line into a reliable capability snapshot, then tells the next operator exactly what can safely happen after it.

---

## Current operating facts

Recent PR descriptions and session logs show the corridor clearly:

- Phase 1 reader coexistence is additive and flag-gated. With the flag off, behavior should remain byte-identical.
- Phase 1 handles question sentences; statement sentences remained on the regex parser.
- Phase 2 statement-frame work is the dominant path because most refused cases are caused by recognized-but-skipped statements / incomplete solver graphs.
- Wrong-answer protection is currently more important than raising correct count by unsafe partial admission. The wrong=0 guard must remain non-negotiable.
- Main has ADR-0166, which states that measurement follows capability, not the other way around.

Brief 11 must preserve those facts instead of drifting back into lane proliferation or superficial UI/demo work.

---

## Goal

Produce a mechanically useful handoff for the next engineering pass after Brief 10 / Phase 2 reader work:

1. Define the closure gates for the Phase 2 statement reader.
2. Define the capability snapshot that should be run immediately after closure.
3. Define the no-go boundaries that prevent unsafe widening.
4. Define the next branch/PR sequence so a lead engineer can continue without re-litigating the strategy.

---

## Non-goals

Brief 11 does not:

- add new OOD eval lanes;
- claim expert-level GSM8K capability;
- relax wrong=0;
- bypass the reader with broader regex patches;
- add public-facing disclosure material;
- promote any audit/expert/demo tier;
- mutate seed packs or teaching stores as a side effect of chat/runtime smoke tests.

---

## Acceptance gates

### Gate 1 — Reader completeness delta

Run the canonical GSM8K train-sample measurement with the reader path enabled and disabled.

Required outputs:

- baseline regex-only result;
- reader-enabled result;
- refused/correct/wrong counts;
- per-case refusal reason taxonomy;
- explicit list of cases fixed by Phase 2 statement frames;
- explicit list of cases still refused and why.

Hard invariant:

- `wrong == 0` must hold.

If `correct` rises while `wrong > 0`, the PR is not a success. It is a regression with useful diagnostics.

### Gate 2 — Recognized-skipped statement audit

For every still-refused case where the reader recognized tokens but did not inject a complete graph, emit a compact audit row:

```text
case_id | sentence_index | recognized_terms | skipped_frame | missing_operator | refusal_reason
```

This is the main Brief 11 artifact because it turns the remaining GSM8K bottleneck into queued capability work instead of guesswork.

### Gate 3 — Graph completeness proof

For every admitted case, prove the solver graph is complete before candidate projection:

- all quantities have owners or intentionally anonymous scope;
- all units are canonicalized;
- operations are typed;
- question target slot resolves to an entity/unit/kind;
- no recognized-but-uncommitted frame is present.

This gate is the successor to the wrong=0 guard. The guard catches unsafe admission; graph completeness prevents unsafe admission from being attempted.

### Gate 4 — Determinism and trace stability

Run the reader-enabled measurement twice with identical input and config.

Required:

- identical case outcomes;
- identical trace hashes where applicable;
- stable refusal taxonomy ordering;
- no nondeterministic iteration over entity registries, frame sets, or lexicon categories.

### Gate 5 — Feature-flag hygiene

The reader path must remain explicitly controlled until the capability snapshot justifies default-on behavior.

Required:

- flag-off path remains byte-compatible with current main expectations;
- flag-on path produces trace evidence that reader code actually executed;
- fallback behavior is explicit: reader refusal may fall through only when doing so cannot hide a recognized-skipped statement.

### Gate 6 — Capability snapshot, not promotion

After the above gates pass, run the existing relevant lanes / tables to populate the current capability snapshot.

Allowed:

- rerun existing GSM8K / capability-axis lanes;
- update current metric artifacts;
- populate existing TBD rows only where the lane already exists and produces signal.

Forbidden:

- adding new canonical lanes just to make the table look complete;
- treating a snapshot as expert promotion;
- merging a measurement PR that conceals capability absence behind aggregate numbers.

---

## Recommended branch / PR sequence

### PR 11A — Reader Phase 2 closure audit

**Branch:** `feat/brief-11-reader-closure-audit`

Deliverables:

- audit artifact for recognized-skipped statement cases;
- per-case refusal taxonomy;
- graph-completeness assertion helpers;
- tests around incomplete graph refusal.

Exit condition:

- measurement identifies the exact remaining missing operators without raising `wrong`.

### PR 11B — Reader closure fixes

**Branch:** `feat/brief-11-reader-closure-fixes`

Deliverables:

- minimal statement-frame fixes for the highest-leverage missing operators;
- no broad regex expansion unless proven temporary and fenced;
- deterministic tests for each newly admitted case;
- updated measurement artifact.

Exit condition:

- correct count improves or refusal taxonomy shrinks, while `wrong == 0`.

### PR 11C — Existing-lane capability snapshot

**Branch:** `eval/brief-11-capability-snapshot`

Deliverables:

- rerun existing relevant lanes only;
- update metric ledgers / result JSONs;
- summarize what changed after the reader closure;
- explicitly list deferred lanes that remain blocked by missing capability.

Exit condition:

- snapshot numbers are reproducible and do not claim promotion.

### PR 11D — Next capability proposal

**Branch:** `docs/brief-11-next-capability-proposal`

Deliverables:

- a concise proposal selecting the next capability after GSM8K reader closure;
- must pass ADR-0166's three-question test before any new lane is authored;
- should compare: continued GSM8K operator closure, cross-domain reader generalization, tool-use trace integration, and Workbench demo hardening.

Exit condition:

- lead engineer has a yes/no decision artifact, not another sprawling roadmap.

---

## Failure modes to avoid

### 1. Correct-count greed

Raising correct count by allowing incomplete graph admission violates the project. Any such result should be treated as a failed experiment, not progress.

### 2. Regex relapse

ADR-0165 exists because regex can be useful at boundaries but dangerous as a semantic substitute. Brief 11 should not broaden regex to impersonate reader comprehension.

### 3. Eval surface inflation

New lanes before capability will generate uniform refusals and strategic noise. ADR-0166 forbids this.

### 4. Snapshot-as-promotion

A capability snapshot is a diagnostic state report. It is not an expert promotion, investor claim, or public disclosure.

### 5. Hidden side effects

Reader measurement must not mutate teaching stores, seed packs, runtime state, or public-facing artifacts unless the PR explicitly declares and tests those mutations.

---

## Minimum evidence package for the final Brief 11 PR

The final PR in this sequence should include:

```text
- command(s) run
- environment/config flags
- baseline result path
- reader-enabled result path
- before/after correct/refused/wrong table
- still-refused taxonomy
- fixed-case taxonomy
- graph completeness assertion summary
- determinism rerun summary
- explicit deferred-work list
```

Suggested table:

| Mode | Correct | Refused | Wrong | Notes |
|---|---:|---:|---:|---|
| regex-only baseline | TBD | TBD | TBD | current main behavior |
| reader Phase 1 | TBD | TBD | TBD | question-frame reader only |
| reader Phase 2 closure | TBD | TBD | TBD | statement-frame reader path |

---

## Definition of done

Brief 11 is done when the repo has a reproducible, reviewed capability snapshot after Phase 2 reader closure and a precise backlog of remaining missing operators.

It is not done merely because a document exists. This document is the operator handoff; the engineering sequence above is the work.

---

## Status update — 2026-05-27 EOD

The Brief 11 sequence landed across the day. Completion path:

| Sub-brief | Status | PR(s) | Notes |
|---|---|---|---|
| 11A — reader closure audit infrastructure | ✅ Merged | #343 | `generate/comprehension/audit.py` + 18 audit tests |
| 11B-step-1 — per-case audit artifact + extended taxonomy | ✅ Merged | #345 | 3 new missing-operator labels close the None-operator gap |
| 11B-step-2 — verb-vocabulary analysis (docs-only) | ✅ Merged | #347 | All "unknown verbs" found to be lexicon-present; pre_frame_filler is structural |
| 11B-step-2 — lexicon-entry closure | ✅ Merged | #348 | 12 drain_token lemmas + 1 alias; `unknown_word` row 11→5; wrong=0 preserved |
| 11C — capability snapshot rerun | ✅ Absorbed | (in W3-A) | Folded into ADR-0167 W3-A's Deliverable 2 (post-W2 baseline section in `audit_brief_11.md`) |
| 11D — next-capability proposal | ✅ Merged | #346 | Candidate A (continued GSM8K closure) recommended |
| 11D — Candidate E (audit-as-evidence) | ✅ Merged | #349 | ADR-0167 scoping ADR + parallel work plan |

The bottleneck table after 11B-step-2 lexicon closure (current post-Brief-11
baseline; W3-A will produce the post-ADR-0167-LexicalClaim baseline):

| refusal_reason | count | Δ vs 11B-step-1 |
|---|---:|---:|
| incomplete_operation | 20 | +2 |
| unexpected_category | 17 | +3 |
| unknown_word | 5 | **−6** |
| unattached_quantity | 4 | +1 |
| unresolved_pronoun | 3 | 0 |
| no_question_target | 1 | 0 |

`wrong == 0` held throughout. Case `gsm8k-train-sample-v1-0050` remains
refused at sentence_index=0 (pinned by multiple test suites).

**Next:** ADR-0167 W3-A closes the LexicalClaim slice with an e2e test
that walks the full loop (refusal → evidence → ratification → row-moves),
plus a cognition-corridor regression pass. After W3-A, Brief 11 closes
and the engine can ratify math-domain lexical claims from its own
refusal evidence through the existing HITL teaching corridor.
