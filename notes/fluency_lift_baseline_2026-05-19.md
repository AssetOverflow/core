# Fluency Lift Baseline — 2026-05-19

Numbers-only record of the 2026-05-19 fluency push.  Captures what
changed, where, and by how much, so subsequent work has a fixed
substrate to measure against.

## Eval lanes — before / after

All three lanes are run from a fresh `ChatRuntime()` per case
(cold-start invariant) except where noted.

### `cold_start_grounding` (44 conversational prompts)

|                       | Before intent fix (b52e04a) | After intent fix | After gloss landing (07da601) |
|---|---|---|---|
| `intent_accuracy`     | 0.4773                      | 1.0000           | 1.0000 |
| `grounding_accuracy`  | 0.4773                      | 1.0000           | 1.0000 |
| `subject_accuracy`    | 0.4318                      | 1.0000           | 1.0000 |
| `none` count          | 21 / 44                     | 0 / 44           | 0 / 44 |
| `pack` count          | 19 / 44                     | 39 / 44          | 39 / 44 |

Five intent-classification patterns recovered 21 prompts that
previously fell to `"I don't know — insufficient grounding"`:
`Define X`, `What does X mean?`, `What is to V?`, `How does X work?`,
`What causes X?`.

### `warmed_session_consistency` (8 cases / 18 turns)

|                              | Before pipeline gate (Phase B1) | After pipeline gate (c3e2a22) |
|---|---|---|
| `no_placeholder_rate`        | 0.4444                          | 1.0000 |
| `telemetry_consistency_rate` | 0.4444                          | 1.0000 |
| `warm_grounding_stability`   | 0.0000                          | 0.0000 |
| `grounding_match_rate`       | 0.4444                          | 0.4444 |

The pipeline-override usefulness gate cured the placeholder-prose
bug + the telemetry/result mismatch.  `warm_grounding_stability`
remains 0 because of a separate architectural bug: a pack-grounded
turn 1 reverts to vault-walk on turn 2 of the same prompt.  Fix
deferred to the SurfaceSelector RFC (`notes/surface_selector_design_2026-05-19.md`).

### `deterministic_fluency` (15 cases × 6 predicates)

|                              | Before gloss landing | After gloss landing (07da601) |
|---|---|---|
| `no_placeholder_rate`        | 1.0000               | 1.0000 |
| `complete_punctuation_rate`  | 1.0000               | 1.0000 |
| `finite_predicate_shape_rate`| 1.0000               | 1.0000 |
| `no_provenance_only_rate`    | 1.0000               | 1.0000 |
| `surface_provenance_match_rate` | 1.0000            | 1.0000 |
| `no_dotted_inventory_rate`   | **0.3333**           | **1.0000** |

The gloss feature delivered the no_dotted_inventory metric from
33% to 100%.  Every gloss-backed surface now reads as a fluent
sentence instead of structured-disclosure dotted paths.

### `cognition` (CORE's authoritative cognitive eval)

|                       | Public (13 cases) | Holdout (19 cases) |
|---|---|---|
| `intent_accuracy`     | 1.0000            | 1.0000             |
| `term_capture_rate`   | 0.9167            | 0.8333             |
| `surface_groundedness`| 1.0000            | 1.0000             |
| `versor_closure_rate` | 1.0000            | 1.0000             |

**Byte-identical** across every change in this push.  Substring
assertions in the eval continue to find every expected term in the
new fluent surfaces.

## Sample probe — fluent vs. before

Fresh `ChatRuntime()` per prompt:

```text
input:  What is truth?
before: truth — pack-grounded (en_core_cognition_v1):
        cognition.truth; logos.core; epistemic.ground.
        No session evidence yet.
after:  Truth is a claim or state grounded by evidence and coherent
        judgment.  pack-grounded (en_core_cognition_v1).

input:  Define moment.
before: I don't know — insufficient grounding for that yet.
after:  Moment is a brief or pointlike interval of time.
        pack-grounded (en_core_temporal_v1).

input:  What does important mean?
before: I don't know — insufficient grounding for that yet.
after:  Something is important when it carries weight or priority in
        some judgment context.  pack-grounded (en_core_attitude_v1).

input:  What is to create?
before: I haven't learned 'to create' yet (intent: definition).
        Mounted lexicon packs: en_core_cognition_v1, ...
after:  To create means to bring something into existence through
        deliberate action.  pack-grounded (en_core_action_v1).

input:  What is quasar?              (genuinely OOV — control)
both:   I haven't learned 'quasar' yet (intent: definition).
        Mounted lexicon packs: ...

input:  How does memory work?        (CAUSE w/o teaching chain — control)
both:   I don't know — insufficient grounding for that yet.
        (deliberately preserved as the discovery-gap signal)
```

## Lexicon + gloss inventory

After this push:

|                      | Lexicon entries | Glosses | Coverage |
|---|---|---|---|
| en_core_cognition_v1 | 85              | 78      | 91.8% |
| en_core_meta_v1      | 73              | 72      | 98.6% |
| en_core_attitude_v1  | 40              | 40      | 100.0% |
| en_core_temporal_v1  | 28              | 28      | 100.0% |
| en_core_action_v1    | 26              | 26      | 100.0% |
| en_core_quantitative_v1 | 24           | 24      | 100.0% |
| en_core_spatial_v1   | 24              | 24      | 100.0% |
| en_core_polarity_v1  | 16              | 16      | 100.0% |
| en_core_causation_v1 | 15              | 15      | 100.0% |
| **Total**            | **331**         | **323** | **97.6%** |

The 8 unglossed entries in cognition are dual-POS lemmas (e.g.
`cause` exists as NOUN and VERB; only the more salient POS got a
gloss in the first dispatch).  Adding the duals is a follow-up
authoring pass.

## Commits in this push

```
07da601 feat(packs): seed 323 reviewed glosses across 9 English content packs
46ac737 feat(pack-grounding): selector-ready gloss wiring via PackSurfaceCandidate
24daebf feat(pack-resolver): gloss resolver with lexicon-residency + dual-checksum hardening
c3e2a22 fix(pipeline): usefulness gate on realized-plan override
a67a3cc feat(evals): deterministic_fluency lane — six structural predicates
0cf1a8f feat(evals): warmed_session_consistency lane — pipeline override regression substrate
c6b4f1d fix(runtime): config-replace + thin API wrappers + stale docstring
a084f1d feat(evals): cold_start_grounding lane — 44-prompt routing probe
b52e04a fix(intent): five conversational definition patterns + polarity-stopword
```

Earlier in the session (now ancestors of the above):

```
8 commits seeding 9 new English content packs (230 lemmas, 5x prior coverage)
```

## What's deferred (with rationale)

- **SurfaceSelector refactor** — `notes/surface_selector_design_2026-05-19.md`
  Cures `warm_grounding_stability`.  Crosses runtime + pipeline +
  telemetry + hash.  Solo-landing carries too much blast radius;
  reviewer is best positioned to land it.

- **Spine unification** — `notes/spine_unification_design_2026-05-19.md`
  Cures `core chat` ≠ pipeline-eval drift.  Depends on the
  SurfaceSelector landing first.

- **Cognition dual-POS gloss completion** — 8 cognition lemmas have
  dual entries (NOUN+VERB) where only one got a gloss.  Mechanical
  follow-up; one subagent dispatch can close it.

- **Gloss-formed sentences for AUX/PRON/SCONJ** — three lemmas in
  cognition (`be`, `why`, `because`) have glosses authored to a
  specific frame.  Manual QA pass on the resulting surface is
  pending.

## Reproducing the numbers

```bash
core eval cold_start_grounding
core eval warmed_session_consistency
core eval deterministic_fluency
core eval cognition
core eval cognition --split holdout

# Live probe:
python3 -c "
from chat.runtime import ChatRuntime
for p in ['What is truth?', 'Define moment.', 'What does important mean?',
          'What is to create?', 'How does memory work?']:
    r = ChatRuntime().chat(p)
    print(f'[{r.grounding_source}] {p}\n  -> {r.surface}\n')
"
```
