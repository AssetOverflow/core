# Learning-Loop Demo — Cold Turn to Grounded Surface, End-to-End

**Date:** 2026-05-18
**Runner:** `evals/learning_loop/run_demo.py`
**CLI:** `core demo learning-loop` (`--json` for machine-readable output)
**Contract tests:** `tests/test_learning_loop_demo.py` (7 passing)
**Reference ADRs:** [0055](../decisions/ADR-0055-inter-session-memory-discovery-promotion.md), [0056](../decisions/ADR-0056-contemplation-loop-c1.md), [0057](../decisions/ADR-0057-teaching-chain-proposal-review.md)

![learning-loop demo](assets/learning_loop.gif)

## Headline claim

> A single deterministic prompt, `"Why does thought exist?"`, produces:
>
> - **Before** the loop runs: `[none] I don't know — insufficient grounding for that yet.`
> - **After** one operator accept: `[teaching] thought — teaching-grounded (cognition_chains_v1): cognition.thought; logos.internal. thought reveals meaning (cognition.meaning). No session evidence yet.`
>
> The active corpus on disk is byte-identical pre/post. The change lives entirely in a transient corpus the demo writes to and then swaps the runtime's `_CORPUS_PATH` to — the same pattern the replay-equivalence gate uses.

## What CORE has that other systems do not

| Property | Continuous pre-training / RLHF | CORE learning loop |
|---|---|---|
| **Per-fact provenance** | None (gradient updates are diffuse) | `Provenance(adr_id, source, review_date, raw)` on every appended chain |
| **Replay-equivalence guarantee** | Offline eval at checkpoint cadence | Inline gate runs the full cognition lane on every admission |
| **Audit trail** | Training logs | `ProposalLog` events: `created` → `replay` → `transition` → `accepted_corpus_append` |
| **Replayable across runs** | No (stochastic; weight checkpoints diverge) | SHA-256 deterministic `proposal_id`; bit-identical artifacts (see [`teaching_loop_bench.md`](teaching_loop_bench.md)) |
| **Operator gate** | Implicit (deployment cadence) | Explicit `core teaching review <id> --accept --review-date YYYY-MM-DD` |
| **Roll-back semantics** | Restore checkpoint | `core teaching supersede <chain_id>` (append-only at disk; active view derived) |

This is the architecture deployments that need to answer *"why did the
system say this today that it would not have said yesterday?"* require.

## Trust boundary

The demo writes only to a tempdir-scoped transient corpus. The active
teaching corpus on disk is byte-identical pre/post. The swap pattern:

```python
real_path = _tg._CORPUS_PATH
try:
    _tg._CORPUS_PATH = transient
    _tg._corpus_index.cache_clear()
    rt2 = ChatRuntime()
    response = rt2.chat("Why does thought exist?")
finally:
    _tg._CORPUS_PATH = real_path
    _tg._corpus_index.cache_clear()
```

This is the same mechanism `teaching/replay.py:_swap_corpus_path` uses
during the replay-equivalence gate.  No clock-time read anywhere in
the loop.

## Five scenes

| Scene | What runs | Trust property |
|---|---|---|
| **S1.  Cold turn** | Real `ChatRuntime.chat("Why does thought exist?")` | No `(thought, cause)` chain exists → universal disclosure; `grounding_source=none`. |
| **S2.  Discovery emission** | Discovery sink + contemplation enrich the candidate | Active corpus untouched; emission is sink-only. |
| **S3.  Operator proposal** | `propose_from_candidate()` runs real `run_replay_equivalence()` | Cognition lane runs twice; no regression → `state=pending`. |
| **S4.  Operator accept** | `accept_proposal()` against a **transient** corpus path | Active corpus byte-identical; transient gains exactly 1 line; provenance `adr-0057:discovery_promoted:2026-05-18`. |
| **S5.  Replay** | `_CORPUS_PATH` swapped to transient; fresh `ChatRuntime` runs the same prompt | Surface contains subject / humanised connective / object; `grounding_source=teaching`. |

## Sample run

```text
────────────────────────────────────────────────────────────────────────
  S1.  Cold turn — runtime cannot ground the prompt
────────────────────────────────────────────────────────────────────────
  prompt                  : Why does thought exist?
  surface                 : I don't know — insufficient grounding for that yet.
  grounding_source        : none
  discovery candidates    : 1  (emitted post-turn)

────────────────────────────────────────────────────────────────────────
  S2.  Discovery candidate — structured evidence, not a mutation
────────────────────────────────────────────────────────────────────────
  candidate_id            : 17673a2f15c8da21…
  trigger                 : would_have_grounded
  proposed_chain          : {'connective': None, 'intent': 'cause',
                             'object': None, 'subject': 'thought'}
  polarity                : undetermined
  claim_domain            : factual
  pack_consistent         : True
  boundary_clean          : True
  evidence (pack-only)    : [{'epistemic_status': 'coherent',
                              'polarity': 'affirms', 'ref': 'thought',
                              'source': 'pack'}]

────────────────────────────────────────────────────────────────────────
  S3.  Operator-authored proposal — replay-equivalence gate runs
────────────────────────────────────────────────────────────────────────
  proposal_id             : 016252428267e4f339969524988c4794
  proposed_chain          : {'subject': 'thought', 'intent': 'cause',
                             'connective': 'reveals', 'object': 'meaning'}
  evidence (corpus ref)   : cause_creation_reveals_meaning
  replay baseline         : {'intent_accuracy': 1.0, 'surface_groundedness':
                             1.0, 'term_capture_rate': 0.9167,
                             'versor_closure_rate': 1.0}
  replay candidate        : {'intent_accuracy': 1.0, 'surface_groundedness':
                             1.0, 'term_capture_rate': 0.9167,
                             'versor_closure_rate': 1.0}
  regressed_metrics       : []
  replay_equivalent       : True
  state                   : pending

────────────────────────────────────────────────────────────────────────
  S4.  Operator accept — transient corpus, active corpus untouched
────────────────────────────────────────────────────────────────────────
  appended chain_id       : cause_thought_reveals_meaning
  transient corpus path   : /tmp/learning_loop_demo_xxxxxx/cognition_chains_v1.jsonl
  transient lines  before : 10
  transient lines  after  : 11
  active corpus byte-eq   : True

────────────────────────────────────────────────────────────────────────
  S5.  Same prompt — now deterministically teaching-grounded
────────────────────────────────────────────────────────────────────────
  prompt                  : Why does thought exist?
  surface                 : thought — teaching-grounded (cognition_chains_v1):
                            cognition.thought; logos.internal.
                            thought reveals meaning (cognition.meaning).
                            No session evidence yet.
  grounding_source        : teaching

════════════════════════════════════════════════════════════════════════
  BEFORE / AFTER  (single deterministic prompt, one accept between)
════════════════════════════════════════════════════════════════════════
  prompt   : Why does thought exist?
  before   : [none]     I don't know — insufficient grounding for that yet.
  after    : [teaching] thought — teaching-grounded (cognition_chains_v1):
                        cognition.thought; logos.internal.
                        thought reveals meaning (cognition.meaning).
                        No session evidence yet.

  learning_loop_closed         : True
  active corpus byte-identical : True
```

## How to reproduce

```bash
core demo learning-loop                    # human output (preamble + scenes + before/after)
core demo learning-loop --json             # machine-readable DemoReport
python -m pytest tests/test_learning_loop_demo.py -q       # ~15s
```

## Falsifiable claims

If any of these stops holding, the headline claim no longer holds:

- `report.learning_loop_closed` is `True`.
- `report.active_corpus_byte_identical` is `True`.
- `report.before.grounding_source == "none"`; surface contains `"insufficient grounding"`.
- `report.after.grounding_source == "teaching"`; surface contains `"thought"` AND `"reveal"` AND `"meaning"` AND `"teaching-grounded"`.
- S3: `replay_evidence.replay_equivalent is True`, `regressed_metrics == []`, `state == "pending"`.
- S4: `transient_lines_after == transient_lines_before + 1` AND `active_corpus_byte_identical is True`.
- The same prompt drives both surfaces (`report.prompt == "Why does thought exist?"`).

## Why "thought" is the demo subject

The subject must satisfy three pre-conditions for the demo to fire deterministically:

1. **Pack-resident** (otherwise the discovery candidate isn't emitted) — confirmed by `'thought' in _pack_index()`.
2. **No active `(thought, cause)` chain** (otherwise the cold turn would already be teaching-grounded) — confirmed by the active corpus snapshot.
3. **Intent classifier picks `CAUSE` on a natural prompt** — `"Why does thought exist?"` classifies as `CAUSE / subject="thought"` deterministically.

The operator-authored chain (`thought reveals meaning`) cites
`cause_creation_reveals_meaning` as affirming evidence. Both endpoint
lemmas (`thought`, `meaning`) are pack-resident; the connective
`reveals` is in the canonical predicate set.

## Related

- Anti-regression demo: [`anti_regression_demo.md`](anti_regression_demo.md) — the inverse demo showing each gate refusing a bad proposal.
- Determinism benchmark: [`teaching_loop_bench.md`](teaching_loop_bench.md) — N-run byte-identical-artifact proof on this exact pipeline.
- Operator surface: see the [Inter-Session Memory section in README](../../README.md#inter-session-memory--reviewed-learning).
