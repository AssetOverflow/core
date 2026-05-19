# Long-Span Fluency Baseline — 2026-05-19

Numbers-only baseline at the moment the warm-path pack-grounding
patch lands and three new eval lanes go red.  Each lane is a
deterministic, lexical-predicate measurement substrate; no LLM judge,
no embedding similarity.

## Step 1 fix — warm_grounding_stability targeted patch

`chat/runtime.py:_maybe_pack_grounded_surface` now accepts
`allow_warm=True`; warm path invokes it after articulation, overrides
`response_surface` / `articulation` / `grounding_source` when a pack
or teaching surface is available.  CAUSE / VERIFICATION without a
teaching chain emit the unknown-domain disclosure on warm just as on
cold (preserves the discovery signal — no fabricated vault content).

### warmed_session_consistency (public/v1, 8 cases / 18 turns)

| metric                       | before | after |
|---|---|---|
| no_placeholder_rate          | 1.0    | 1.0   |
| telemetry_consistency_rate   | 1.0    | 1.0   |
| grounding_match_rate         | n/a    | 1.0   |
| warm_grounding_stability     | 0.0    | 1.0   |

### Cognition lane (regression check)

| split   | intent | term capture | surface groundedness | versor closure |
|---|---|---|---|---|
| public  | 100%   | 91.7%        | 100%                 | 100%           |
| holdout | 100%   | 83.3%        | 100%                 | 100%           |

Cognition lane byte-identical to pre-patch baseline.  Full test
suite: **2294 passed, 3 skipped** in ~5 min.

## Step 2 — three new red lanes

### conversational_thread_coherence (public/v1, 6 cases / 45 turns)

| metric                  | value  |
|---|---|
| no_placeholder_rate     | 1.0    |
| not_walk_fragment_rate  | 1.0    |
| length_adequate_rate    | 1.0    |
| is_grounded_rate        | 0.9333 |
| topic_anchor_rate       | 0.5    |
| no_topic_drift_rate     | 0.8333 |

**Read:** placeholder / fragment / length predicates are clean (Step 1
fix carries through).  `topic_anchor_rate=0.5` is the next gap —
when a follow-up uses anaphora ("Why does it exist?") the system fails
to anchor on the prior subject half the time.  `no_topic_drift_rate=0.8333`
— 1 of 6 cases drops a grounded subject to `none` on later replay.

### multi_sentence_response (public/v1, 15 cases)

| metric                  | value  |
|---|---|
| multi_sentence_rate     | 0.5333 |
| non_fragment_rate       | 1.0    |
| grounded_rate           | 0.4667 |
| subject_named_rate      | 0.5333 |
| connective_present_rate | 0.1    |

**Read:** half of the elaboration prompts ("Explain X", "Describe X")
still get a single-sentence response; only 10% of cases that *should*
contain a discourse connective do.  This is the **single biggest
architectural gap** — there is no paragraph-level composer.

### self_consistency_over_time (public/v1, 7 cases)

| metric                       | value  |
|---|---|
| byte_identical_rate          | 0.8571 |
| key_terms_stable_rate        | 0.8571 |
| grounding_source_stable_rate | 0.8571 |
| no_walk_fragment_rate        | 1.0    |

**Read:** 6 of 7 probes are byte-identical across long interleaved
threads.  The one drifting case is CAUSE-no-chain (`How does memory
work?`) — vault-content accumulation across unrelated fillers changes
the disclosure.  Worth a follow-up: disclosure should also be stable.

## Architectural reading

The Step 1 patch closes the *replay* dimension.  The three new lanes
quantify what remains for *robust long-span fluency*:

1. **Multi-clause composition** (multi_sentence + connective_present) —
   no paragraph-level composer exists today; every composer in
   `chat/pack_grounding.py` and `chat/teaching_grounding.py` returns
   one terminal-`.` string.  This is the biggest gap.
2. **Anaphora resolution** (topic_anchor_rate=0.5) — the existing
   `thread_anaphora_prefix` is structural ("Recalling turn 0:") not
   in-clause.  Real coreference would lift this to ~1.0.
3. **No-drift across interleaved turns** (consistency byte_identical
   not 1.0) — drift only affects ungrounded CAUSE; disclosure
   stability is a smaller follow-up.

The natural next step is a paragraph-level composer that orchestrates
the existing single-sentence composers.  Doctrine-respecting because
deterministic.  Forward-compatible with the deferred SurfaceSelector
RFC.
