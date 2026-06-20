# ProblemFrame Contract Gap Taxonomy — 2026-06-20

Status: normative diagnostic taxonomy for ADR-0223

Applies to: `KernelFacts`, `ProblemFrame`, construction bindings, and `ContractAssessment`

## Purpose

Current adequacy reports count missing role names, but a missing role can arise from several fundamentally different failures: the source fact may be absent, the fact may exist but lack a binding, the wrong construction may have been proposed, or the contract may not express an obligation at all. Treating these as one “parser gap” encourages local regex patches.

This taxonomy makes each failure actionable while preserving the rule that unknown is not false.

## Gap record

Every reported gap should be representable by the following fields, whether or not a dedicated type is introduced immediately:

| Field | Meaning |
|---|---|
| `gap_code` | stable taxonomy code |
| `construction_id` | reviewed construction family, if any |
| `organ_id` | prospective contract consumer, if any |
| `role` | missing, conflicting, or weak role |
| `state` | proposed, partial, ambiguous, closed, runnable, refused |
| `evidence_spans` | exact spans that motivated the report |
| `provenance` | lexical, construction, reviewed reconstruction, or contract source |
| `blocking` | whether the gap prevents closure |
| `hazards` | applicable corrective conditions |
| `repair_layer` | pack, lexical fact extraction, construction binding, contract, adapter, or organ |

A gap without source evidence is still useful, but it must not fabricate an evidence span.

## Primary taxonomy

### PF-LX — lexical substrate gaps

The required surface meaning is lexical and should be resolved before construction matching.

| Code | Definition | Example | Correct repair | Forbidden repair |
|---|---|---|---|---|
| `PF-LX-001 scalar_unrecognized` | a scalar surface has no exact normalized value | unsupported mixed-number spelling | reviewed scalar-equivalence entry and tests | organ-local number regex |
| `PF-LX-002 unit_unrecognized` | a unit surface cannot map to a dimension/unit identity | plural or currency alias absent from pack | reviewed unit alias | local organ unit list |
| `PF-LX-003 lexical_ambiguity` | one surface has multiple admissible lexical meanings | “half” as noun vs modifier | preserve alternatives and hazard | first-match selection |
| `PF-LX-004 span_collision` | candidate lexical facts overlap incompatibly | “one half” recognized as two scalars | deterministic overlap policy with evidence | silent deletion |
| `PF-LX-005 semantic_anchor_absent` | a construction anchor is not represented in the mounted pack | reviewed acquisition synonym absent | pack addition and checksum | broad substring trigger |

### PF-EN — entity and reference gaps

The source contains relevant participants or quantities, but their identity or continuity is unresolved.

| Code | Definition | Example | Closure obligation |
|---|---|---|---|
| `PF-EN-001 entity_missing` | no entity candidate exists for a required role | quantity present without an object surface | bind or reconstruct only through reviewed construction evidence |
| `PF-EN-002 quantity_entity_unbound` | scalar exists but is not bound to a semantic entity | `3` incorrectly followed by “more” | exact entity binding with provenance |
| `PF-EN-003 referent_unresolved` | pronoun or ellipsis has multiple/no referents | “she gave him 3 more” | deterministic reference evidence or refusal |
| `PF-EN-004 continuity_unproven` | two mentions may or may not denote the same quantity-bearing kind | apples before/after acquisition | same-entity obligation |
| `PF-EN-005 role_alias_collision` | one surface is used for incompatible roles | “ones” as several subgroups | preserve competing bindings; block closure |
| `PF-EN-006 actor_patient_ambiguous` | event participants cannot be assigned safely | passive or reversed transfer | construction-specific voice/role proof |

### PF-CN — construction proposal gaps

The system has facts but cannot identify the relational construction that could organize them.

| Code | Definition | Example | Correct repair |
|---|---|---|---|
| `PF-CN-001 no_candidate` | no reviewed construction is proposed | proportional decrease case `0005` | construction catalog and exact candidate anchors |
| `PF-CN-002 overbroad_candidate` | surface trigger proposes a family lacking structural support | “left” creates percent-partition candidate | tighter declaration/proposal evidence; proposal remains non-runnable |
| `PF-CN-003 competing_candidates` | multiple constructions plausibly explain the same spans | consumption vs partition | retain candidates until obligations disambiguate |
| `PF-CN-004 construction_variant_missing` | family exists but a legitimate voice/order/topology variant is absent | transfer phrased passively | reviewed variant under same role contract |
| `PF-CN-005 negative_licensing_missing` | a construction lacks its disqualifying conditions | inverse question accepted as forward partition | add target/hazard obligations |
| `PF-CN-006 neighborhood_evidence_missing` | proposed family has no replayable retrieval evidence | hard-coded family activation | exact source/span/manifold evidence |

### PF-BD — role-binding gaps

A plausible construction exists, but required roles are not closed from facts.

| Code | Definition | Example | Closure obligation |
|---|---|---|---|
| `PF-BD-001 required_role_unbound` | declared role has no binding | labor `worker`, `rate`, or `duration` | exact role-to-fact binding |
| `PF-BD-002 relation_unanchored` | relation lacks an event/source anchor | percent linked to generic “ones” | event/entity anchored relation |
| `PF-BD-003 wrong_role_kind` | bound value has the wrong semantic type | object label used where numeric whole is required | typed role constraint |
| `PF-BD-004 positional_binding` | binding depends on first/nearest textual occurrence rather than structure | final 28 selected as original whole | construction topology proof |
| `PF-BD-005 cardinality_mismatch` | too few or too many role bindings exist | partition needs two distinct subgroups | role cardinality constraint |
| `PF-BD-006 incompatible_units` | quantities cannot participate dimensionally | hours treated as money | dimensional compatibility |
| `PF-BD-007 relation_direction_unknown` | operands exist but orientation is not proven | who has 3 more than whom | directional relation obligation |
| `PF-BD-008 event_order_unknown` | state transitions exist but temporal order is unresolved | acquisition then loss vs loss then acquisition | ordered event binding |
| `PF-BD-009 aggregate_membership_unknown` | members of a sum/partition are not proven co-members | percentages from unrelated groups | shared whole/topology obligation |
| `PF-BD-010 binding_conflict` | two closed-looking bindings assert incompatible roles | same scalar as initial and remaining value | ambiguous state; refuse |

### PF-TG — target gaps

The question target is a semantic operator over the frame, not merely a nearby noun.

| Code | Definition | Example | Closure obligation |
|---|---|---|---|
| `PF-TG-001 target_surface_missing` | no question/goal span is identified | declarative prompt or nonstandard question | explicit target evidence |
| `PF-TG-002 target_entity_unbound` | target operator is known but its entity is not | “How many are left?” | reference-resolved target entity |
| `PF-TG-003 target_operator_unknown` | count/difference/total/remaining/rate is unresolved | current generic `unknown` | typed target operator |
| `PF-TG-004 target_direction_unknown` | forward vs inverse or initial vs final state is unresolved | `0393` asks original from remainder | direction/state obligation |
| `PF-TG-005 target_scope_ambiguous` | target may apply to several subgroups/events | “How many did they have?” | exact scope binding |
| `PF-TG-006 target_unit_unproven` | expected answer dimension is not known | “How much money” classified as generic count | target dimension constraint |
| `PF-TG-007 target_incompatible_with_construction` | target is grounded but the candidate construction cannot produce it | remaining target for forward aggregate contract | block candidate contract |

### PF-TP — relational topology gaps

Individual bindings exist but do not prove the shape required by the construction.

| Code | Definition | Example | Closure obligation |
|---|---|---|---|
| `PF-TP-001 whole_missing` | no numeric base/whole is proven | percent without base quantity | numeric whole binding |
| `PF-TP-002 subgroup_missing` | a required subgroup lacks identity | percentage linked only to generic noun | subgroup entity binding |
| `PF-TP-003 subgroup_not_distinct` | multiple subgroup roles may denote the same group | repeated “ones” surfaces | distinctness proof |
| `PF-TP-004 partition_coverage_unknown` | subgroups are not proven to cover the whole | two mentioned groups may omit others | coverage obligation or explicit partial-partition construction |
| `PF-TP-005 scale_base_unlinked` | fraction/percent is not linked to the correct base | 80% attached to consumed group, not original whole | scoped base relation |
| `PF-TP-006 state_transition_open` | initial, changed, and final states do not form a closed transition | proportional decrease without final-state relation | state equation topology |
| `PF-TP-007 rate_axes_unbound` | rate numerator/denominator dimensions are not assigned | dollars per hour | dimensional axes and participant binding |
| `PF-TP-008 container_axes_unbound` | container/content/count-per roles are not connected | boxes with items each | container cardinality topology |
| `PF-TP-009 comparison_axis_unbound` | comparator/reference/difference are not connected | “3 more” | comparison topology |
| `PF-TP-010 inverse_topology_unlicensed` | facts support an inverse reconstruction not implemented by the candidate organ | `0393` original-from-remainder | refuse or route to a distinct reviewed contract |

### PF-HZ — hazard and correction gaps

Positive evidence exists, but the system lacks or ignores the conjugate corrective condition.

| Code | Definition | Example | Required behavior |
|---|---|---|---|
| `PF-HZ-001 hazard_unregistered` | known ambiguity has no centralized representation | overloaded comparative surface | add reviewed hazard |
| `PF-HZ-002 hazard_unattached` | hazard exists but is not linked to the relevant span/binding | percent-base ambiguity | attach with provenance |
| `PF-HZ-003 hazard_ignored_by_contract` | blocking hazard is visible but runnable remains true | unbound base tolerated | contract must block |
| `PF-HZ-004 confuser_missing` | positive test exists without a minimally different negative case | forward partition only | add adversarial pair |
| `PF-HZ-005 conflict_auto_resolved` | system silently picks one of competing interpretations | repeated entity aliases | preserve ambiguity/refuse |
| `PF-HZ-006 negation_scope_unknown` | negation may reverse or suppress an event/relation | “did not give” | scoped negation obligation |

### PF-CT — contract-definition gaps

The frame may contain adequate evidence, but the assessment does not express or enforce the organ's true preconditions.

| Code | Definition | Example | Correct repair |
|---|---|---|---|
| `PF-CT-001 contract_absent` | no assessment exists for a supported diagnostic family | proportional decrease | explicit contract over frame facts |
| `PF-CT-002 obligation_omitted` | assessment ignores a necessary precondition | percent contract omits numeric whole | add typed obligation |
| `PF-CT-003 obligation_too_weak` | surface equality substitutes for semantic proof | subgroup/percent both equal “ones” | topology-aware obligation |
| `PF-CT-004 candidate_gate_too_broad` | unrelated process candidate emits an organ assessment | consumption implies percent partition | construction-specific candidate gate |
| `PF-CT-005 runnable_false_positive` | assessment declares runnable but organ geometry is not closed | holdout `0393` | block and add regression |
| `PF-CT-006 runnable_false_negative` | all facts are present but assessment cannot recognize closure | future fully bound variant | strengthen contract without relaxing proof |
| `PF-CT-007 hazard_policy_incomplete` | assessment does not define blocking vs advisory hazards | ambiguity present but unused | explicit hazard disposition |
| `PF-CT-008 organ_capability_mismatch` | contract promises a target/topology the organ cannot execute | inverse target sent to forward organ | narrow contract or add distinct organ |

### PF-AD — adapter and graph-boundary gaps

The comprehension result is closed, but no safe projection exists or a projection crosses architectural boundaries.

| Code | Definition | Example | Correct repair |
|---|---|---|---|
| `PF-AD-001 organ_adapter_absent` | no typed adapter converts a closed contract to organ input | all current ProblemFrame diagnostics | narrow immutable adapter |
| `PF-AD-002 raw_text_reparse` | consumer ignores closed facts and reparses source | current derivation organs | consume typed projection and delete parser |
| `PF-AD-003 mega_ir_leak` | consumer-specific fields are added to a general graph | solver operands in `EpistemicGraph` | separate graph plus adapter |
| `PF-AD-004 provenance_dropped` | projected input loses source/reconstruction evidence | scalar passed without span/source | provenance-preserving projection |
| `PF-AD-005 target_semantics_dropped` | adapter passes quantities but not target operator/direction | forward/inverse confusion | include typed target contract |
| `PF-AD-006 fallback_divergence` | failed structured path silently falls back to a different parser | contract refusal followed by legacy solve | explicit lane policy; no hidden fallback |

### PF-EV — evidence and evaluation gaps

The feature cannot be judged safely because evidence is insufficient or non-replayable.

| Code | Definition | Example | Required evidence |
|---|---|---|---|
| `PF-EV-001 positive_case_missing` | no representative successful construction case | new family without fixture | exact expected frame/assessment |
| `PF-EV-002 confuser_case_missing` | no close negative case | no inverse variant | minimally different refusal fixture |
| `PF-EV-003 morphology_coverage_missing` | supported relation has no lexical/syntactic variation | fixed transfer sentence only | reviewed variants preserving geometry |
| `PF-EV-004 deterministic_replay_missing` | repeated extraction/assessment is not compared | unstable candidate order | identical serialized evidence/hash |
| `PF-EV-005 serving_safety_unmeasured` | diagnostic change lacks train/holdout serving comparison | new runnable cases only | correct/refused/wrong and wrong IDs |
| `PF-EV-006 false_runnable_unaudited` | runnable diagnostic cases are not manually/structurally audited | current holdout `0393` | per-case obligation proof |
| `PF-EV-007 parser_retirement_unmeasured` | substrate path added without demonstrating legacy deletion | duplicate paths remain | allowlist and call-site reduction |

### PF-TR — trust-boundary gaps

The proposed substrate change can execute, mutate, disclose, or ingest beyond its reviewed authority.

| Code | Definition | Example | Required control |
|---|---|---|---|
| `PF-TR-001 unreviewed_construction_mutation` | runtime/user correction changes construction catalog | learned trigger immediately active | reviewed proposal lifecycle |
| `PF-TR-002 unsafe_pack_path` | pack ID/path can escape approved roots | traversal in dynamic load | validation before access |
| `PF-TR-003 dynamic_execution` | construction data can execute arbitrary code | validator/import hook | explicit opt-in trust boundary |
| `PF-TR-004 sensitive_surface_leak` | reports log raw user tokens unnecessarily | full prompt in shared report | centralized safe display policy |
| `PF-TR-005 answer_evidence_contamination` | answers/labels enter recognition or construction retrieval | benchmark answer mining | source isolation and tests |
| `PF-TR-006 approximate_or_stochastic_retrieval` | proposal cannot replay exactly | ANN or randomized ranking | exact deterministic CGA scan |

## Severity and ownership

| Severity | Meaning | Examples | Merge policy |
|---|---|---|---|
| `S0 invariant` | can corrupt field, truth, replay, or trust boundary | approximate recall, hidden mutation, false answer | hard stop |
| `S1 readiness` | can declare an unclosed case runnable | `PF-CT-005`, ignored ambiguity | fix before any promotion |
| `S2 capability` | blocks a legitimate case safely | missing construction or binding | may merge as documented refusal; prioritize by roadmap |
| `S3 evidence` | weakens confidence or maintainability | missing morphology/confuser fixture | required before claiming capability |

Repair ownership follows the first layer able to resolve the gap without guessing:

```text
lexical fact -> construction proposal -> construction binding
  -> contract -> adapter -> organ -> evaluation/trust boundary
```

Downstream layers must not compensate for an upstream gap by reparsing raw text.

## Applying the taxonomy to current evidence

### Train case `0005` — proportional decrease

Observed facts: exact `3/4`, `84`, a unit binding, but no process construction, no proportional relation, and an unresolved target.

Primary gaps:

- `PF-CN-001 no_candidate` — no proportional-decrease construction;
- `PF-TP-006 state_transition_open` — base/final/delta geometry is not formed;
- `PF-TG-003 target_operator_unknown` and `PF-TG-004 target_direction_unknown`;
- `PF-CT-001 contract_absent`;
- `PF-AD-001 organ_adapter_absent`.

It is not primarily `scalar_unrecognized`; adding another number regex would not close it.

### Train case `0046` — percent partition

Observed facts are adequate enough for the current forward aggregation, but proof is incomplete.

Residual gaps/risk:

- `PF-CT-002 obligation_omitted` — numeric whole and full topology are not explicitly required;
- `PF-TP-003 subgroup_not_distinct` / `PF-TP-004 partition_coverage_unknown` are not generally proven;
- `PF-EV-004 deterministic_replay_missing` if serialized assessment identity is not asserted across runs.

The case may remain runnable only after its positive obligations are made explicit.

### Holdout case `0393` — false runnable

Observed defects:

- `PF-BD-004 positional_binding` — final 28 is selected as original whole;
- `PF-BD-002 relation_unanchored` and `PF-EN-005 role_alias_collision` — “ones” links unrelated/local roles;
- `PF-TG-004 target_direction_unknown` or incorrectly tolerated;
- `PF-TP-010 inverse_topology_unlicensed`;
- `PF-CT-003 obligation_too_weak` and `PF-CT-005 runnable_false_positive`;
- `PF-EV-006 false_runnable_unaudited` before this audit.

Required disposition: not runnable for `percent_partition`. It may remain a proposal/partial frame until a distinct inverse-reconstruction construction is reviewed.

### Acquisition probe — “Lena has 5 apples. She buys 3 more apples.”

- `PF-EN-002 quantity_entity_unbound` because `3` can bind to “more”;
- `PF-CN-002 overbroad_candidate` for incidental comparison;
- `PF-TP-006 state_transition_open`;
- `PF-BD-008 event_order_unknown` if acquisition ordering is not bound;
- `PF-TG-004 target_direction_unknown` until final-state total is proven.

### Labor/rate probe

- `PF-BD-001 required_role_unbound` for worker/rate/duration;
- `PF-TP-007 rate_axes_unbound`;
- `PF-TG-006 target_unit_unproven` when money is classified as count;
- `PF-CT-008 organ_capability_mismatch` if a generic target is accepted.

## Report aggregation rules

Adequacy and morphology reports should aggregate without losing case-level evidence:

1. count each stable `gap_code` by split, construction, organ, and blocking status;
2. list every runnable case with its closed obligations and hazards;
3. list every false-runnable regression explicitly;
4. distinguish `no_candidate`, `candidate_partial`, `candidate_ambiguous`, and `contract_absent`;
5. never infer a missing relation from a missing answer;
6. keep answer labels out of construction extraction and gap classification;
7. preserve exact source spans when present, but do not require fabricated spans for absent roles;
8. produce deterministic sorted output.

Recommended headline metrics:

| Metric | Meaning |
|---|---|
| candidate precision | proposed cases that have at least one structurally supported role |
| binding closure rate | candidates whose required construction roles close |
| contract soundness | runnable cases whose organ preconditions are manually/test-proven |
| target soundness | runnable cases with explicit operator, scope, direction, and dimension |
| hazard effectiveness | blocking hazards that prevent a documented confuser |
| parser retirement | legacy parser/call-site/allowlist reduction after migration |
| serving safety | correct/refused/wrong with `wrong_ids` |

Coverage alone is not a success metric.

## Acceptance taxonomy for the immediate PR

The proportional-decrease/readiness PR is complete only if:

- `0005` eliminates `PF-CN-001`, `PF-TP-006`, `PF-TG-003/004`, and `PF-CT-001` through a closed diagnostic construction;
- `0393` eliminates `PF-CT-005` by becoming non-runnable for percent partition;
- `0046` remains runnable with explicit numeric-whole, topology, target, and hazard obligations;
- new confusers cover inverse target, remainder target, entity discontinuity, unit mismatch, and ambiguous base;
- no `PF-AD-002 raw_text_reparse` is added to a new layer;
- serving results retain `wrong_ids == []`;
- all new frame/assessment output is deterministic and provenance-bearing.

`PF-AD-001 organ_adapter_absent` is intentionally allowed to remain in that PR because serving migration is a later, separately reviewed step.

## Conclusion

The central distinction is between missing words, missing relations, and missing proof. CORE already recognizes many scalars and entities; most present gaps are constructional bindings, target semantics, topology, and contract obligations. This taxonomy directs repairs to those layers and blocks the default failure mode of compensating with another local prose parser.
