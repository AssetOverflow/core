# GSM8K XHIGH Capability Sprint 13 — Lookback (2026-06-18)

> Status: research gate complete; implementation and final validation pending.

## 1. Starting baseline

The canonical current API is `evals.gsm8k_math.train_sample.v1.runner.build_report`.
The brief's `train_sample.v1.report` import is stale and does not exist on `main`.
Using the canonical runner on the committed 50-case sample:

| Metric | Value |
|---|---:|
| correct | **26** |
| refused | **24** |
| wrong | **0** |

Correct IDs: 0001, 0002, 0003, 0004, 0005, 0006, 0007, 0008, 0009,
0010, 0013, 0014, 0015, 0017, 0018, 0021, 0024, 0025, 0029, 0030,
0035, 0037, 0038, 0042, 0045, 0046. Wrong IDs: none.

## 2. Intrinsic space and architectural directions

The refused frontier is not one arithmetic space. It is a disjoint union of
small relational manifolds. Surface categories such as
`discrete_count_statement` and `descriptive_setup_no_quantity` distort this
geometry by grouping different typed chains under one recognizer label. The
serving invariant is therefore preserved by admitting only a complete typed
relation field: named actors/objects, licensed operators, a bound question
target, source-quantity obligations, and a reconstructible final value.

Directions mapped before implementation:

1. **Two contract-backed mini-families (Path A candidate).** Pair 0016/0034 as
   bounded rate projections with explicit numerator, denominator, and target
   dimensions. Pair 0027/0039 as closed explicit-reference affine aggregates,
   implemented as two surface-specific builders rather than a generic relation
   graph. This can yield +4 without a generic equation, fraction, DCS, temporal,
   or multiplicative parser.
2. **Four unrelated strict singletons.** 0012, 0016, 0034, and 0049 each have a
   clear arithmetic graph, but this repeats binding logic and offers less
   reusable structure. It is a score bundle, not a coherent capability bundle.
3. **One mini-family plus defensive substrate (Path B/C).** Ship only the
   mini-family that clears confusers and holdout, plus a tiny quantity-obligation
   or actor-binding helper only if it is adopted without widening behavior.
4. **No serving lift (Path D).** If either selected family creates a train or
   holdout wrong answer, or cannot prove complete binding, preserve 26/24/0 and
   land only this diagnostic evidence.

## 3. Scout and Experience Flywheel summary

Commands:

```text
uv run python scripts/gsm8k_sealed_attempt_scout.py --limit 50
uv run python scripts/gsm8k_experience_flywheel.py --limit 50
uv run python scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-xhigh-sprint13.json
```

| Regime | correct | refused | wrong |
|---|---:|---:|---:|
| serving | 26 | 24 | 0 |
| sealed scout | 3 | 39 | 8 |

Scout deltas: 3 already served, 6 elimination-refused-to-wrong, 18 joint
refusals, 0 refused-to-correct lifts, 23 conservative wins. The flywheel has no
promotable family. Its broad family summaries remain diagnostic only.

| family | case IDs | refused-to-correct | sealed-wrong | blocked | top missing primitive | action |
|---|---|---:|---:|---:|---|---|
| already_served | 0003, 0021, 0037 | 0 | 0 | 0 | — | preserve |
| conservative_boundary | 23 served cases | 0 | 2 | 2 | — | preserve serving gates |
| diagnostic_hold:currency_amount | 0019, 0028, 0043 | 0 | 2 | 2 | diagnostic_hold | block wholesale currency |
| diagnostic_hold:descriptive_setup_no_quantity | 0012, 0023, 0027 | 0 | 0 | 0 | diagnostic_hold | decompose by typed relation |
| joint_sealed_no_resolution | 0048, 0050 | 0 | 0 | 0 | — | diagnostic hold |
| relation_hypothesis:discrete_count_statement | 0016, 0020, 0022, 0031, 0032, 0033, 0034, 0036, 0039, 0040, 0041, 0044, 0047, 0049 | 0 | 2 | 2 | relation_hypothesis | reject DCS; decompose exact chains |
| sealed_elimination | 0011, 0026 | 0 | 2 | 2 | — | block |

Sealed-wrong IDs are 0011, 0018, 0019, 0025, 0026, 0028, 0032, and
0047. Only 0011, 0019, 0026, 0028, 0032, and 0047 are currently refused;
0018 and 0025 are conservative serving wins and regression anchors.

## 4. Full refused-case inventory

| ID | Gold | Question text | Typed arithmetic graph | First missing / current refusal | Nearest evidence and candidate |
|---|---:|---|---|---|---|
| 0011 | 50 | Alexa sells lemonade for $2/cup, spent $20, and asks cups needed for $80 profit. | `(80 + 20) / 2` | graph solve; sealed elimination | 0019/0028 currency wrongs; blocked profit-cost recovery |
| 0012 | 7 | Dennis has 10 rocks; fish ate half; two were recovered; asks rocks left. | `10 × (1-1/2) + 2` | descriptive no-quantity injection | clean fraction-loss/recovery singleton; neighbor 0005 is a different fraction-decrease organ |
| 0016 | 2 | Rudolph travels 2 more than 5 miles and sees 3 less than 17 signs; asks signs per mile. | `(17-3)/(5+2)` | relation hypothesis | clean dual-offset ratio singleton; changed-target hazard |
| 0019 | 660 | Three $400 vet visits, $100 insurance after first, 80% coverage on later visits; asks total paid. | `400 + 100 + 2×400×0.2` | currency injection | sealed wrong 120000; currency family blocked |
| 0020 | 130 | Two puppies, two kittens, three parakeets; comparative prices from a $10 parakeet; asks all-pet cost. | `3×10 + 2×20 + 2×30` | relation hypothesis | multi-species price graph; currency and ambiguous “three times more” hazards |
| 0022 | 4800 | $20/kg, past four-month catch 80 kg, today twice past total; asks total earnings including today. | `(80 + 2×80)×20` | relation hypothesis | bounded historical aggregate; currency overlap |
| 0023 | 150 | Nicole has 400 cards, Cindy twice that, Rex half their combined total, then divides among himself and three siblings. | `(400 + 2×400)×1/2/(3+1)` | descriptive no-quantity injection | **blocked**: Cindy's multiplier has no explicit reference and is adjacent to permanent cv-0014/0015 guards; 0027 does not retroactively license it |
| 0026 | 6 | Two people each save $40, bill is 3/4, equal $1.5 scoops, $1 change each; asks scoops each. | `(((2×40)×1/4)-2)/2/1.5` | statement parse | sealed wrong 180; sealed-elimination/currency blocked |
| 0027 | 3840 | Instagram 240 + Facebook 500; Twitter half combined; TikTok 3× Twitter; YouTube TikTok+510; asks all followers. | `S=240+500; T=S/2; K=3T; Y=K+510; total=240+500+T+K+Y` | descriptive no-quantity injection | positive anchor for selected combined-half family; 0023 sibling |
| 0028 | 200 | $100,000 opening cost, daily cost 1%, 150 tickets/day at $10; asks days to recover investment. | `100000 / (150×10 - 100000×0.01)` | currency injection | sealed wrong 0; currency/profit recovery blocked |
| 0031 | 92 | Jeremie plus three friends buy $18 tickets and $5 snacks each; asks total. | `(3+1)×(18+5)` | relation hypothesis | bounded group-cost aggregate but currency family adjacency |
| 0032 | 34 | Ten pictures, 2 hours drawing each, coloring takes 30% less; asks total hours. | `10×(2 + 2×0.7)` | relation hypothesis | sealed wrong 20; DCS/percent-time blocked |
| 0033 | 60 | Rachel is 12; grandfather 7×; mother half grandfather; father 5 older; asks father age when Rachel is 25. | `father_now=(12×7)/2+5; answer=father_now+(25-12)` | relation hypothesis | selected named-actor affine chain; 0039 sibling; 0032 negative |
| 0034 | 112 | 40 yards in 5 seconds, speed improves 40%; asks yards in 10 seconds. | `(40/5)×1.4×10` | relation hypothesis | clean percent-rate projection singleton; 0032 percent-time negative |
| 0036 | 22 | Study 2 hours Wednesday, 3× Thursday, half Thursday Friday, weekend equals weekday total; asks five-day total. | `W=2; T=3W; F=T/2; total=2×(W+T+F)` | relation hypothesis | bounded schedule aggregate; temporal ambiguity on “during weekend” |
| 0039 | 20 | Orlando gains 5; Jose gains two more than twice Orlando; Fernando gains 3 less than half Jose; asks all three total. | `J=2×5+2; F=J/2-3; total=5+J+F` | relation hypothesis | selected named-actor affine chain; 0033 sibling; 0032 negative |
| 0040 | 72 | Counts of horses, dogs, cats, turtles, goat; asks total legs. | `(2+5+7+3+1)×4` | relation hypothesis | requires animal-leg external grounding; implementation blocked |
| 0041 | 6 | Two 16-piece brownie pans; guests eat one plus 75% of second; all but four use two scoops; eight scoops/tub. | `guests=16+0.75×16; tubs=(guests-4)×2/8` | relation hypothesis | multi-stage implicit guest binding; fraction/container hazards |
| 0043 | 11 | Sandra has $10+$4+twice $4; buys 14×$0.5 and 20×$0.2; asks money left. | `10+4+2×4-14×0.5-20×0.2` | currency injection | no sealed wrong itself, but 0019/0028 family blockers |
| 0044 | 1300 | $1000 earns 10% simple interest for three years; asks final money. | `1000×(1+0.1×3)` | relation hypothesis | explicit simple-interest singleton; currency adjacency |
| 0047 | 45 | 12 five-ounce macaroons split over four bags; one bag eaten; asks remaining weight. | `(12-12/4)×5` | relation hypothesis | sealed wrong 240; DCS/divisive blocked |
| 0048 | 4 | Start 20 cards; +6 weekly; -2 every two weeks; asks weeks to reach 40. | `20 + 6w - 2×(w/2)=40`, with even-period obligation | statement parse | bounded periodic recurrence; generic temporal parser prohibited |
| 0049 | 18 | Two walking routes with twice/third segment relations; asks how much longer route two is. | `R1=6+12+(6+12)/3; R2=14+28; R2-R1` | relation hypothesis | clean route-duration comparator; nearest duration organs are narrower |
| 0050 | 280 (artifact inconsistent) | Gig every other day for two weeks; two five-minute songs and one twice as long; asks minutes. | Source rationale computes `7×2=14` gigs and `14×20=140`, while stored gold is 280. | statement parse | **implementation forbidden**: dataset's rationale and gold contradict; do not hardcode the final answer |

## 5. Candidate ranking and research gate

| Rank | Candidate / cases | Expected lift | Typed-chain clarity | Sealed-wrong / blocked overlap | Decision |
|---:|---|---:|---|---|---|
| 1 | `bounded_rate_projection` / 0016, 0034 | +2 | high; two explicit affine/rate graphs with dimension-bound questions | 0018/0032 nearest rate/percent sealed wrong; 0019/0028 currency and 0047 packing confusers | implement as two narrow modes under one ClusterContract |
| 2 | `closed_explicit_reference_affine_aggregate` / 0027, 0039 | +2 | high; every comparative names its source and target aggregate is closed | DCS surface includes 0032/0047 and aggregate 0025; permanent no-reference guards must remain refused | implement as two surface-specific modes under one ClusterContract |
| 3 | `fraction_loss_recovery` / 0012 | +1 | high | fraction surface; 0026 is structurally different but dangerous | fallback only |
| 4 | `route_duration_difference` / 0049 | +1 | high | temporal organs and unrelated-clause completeness | fallback only |
| 5 | `periodic_net_target_horizon` / 0048 | +1 | high only at integral two-week boundaries | 0050 calendar ambiguity and 0028 recovery surface | fallback only |
| 6 | `intergenerational_age_projection` / 0033 | +1 | high but timeline-specific | broad DCS family and changed-time target hazards | defer behind selected contracts |
| 7 | `bounded_schedule_aggregate` / 0036 | +1 | medium | “during weekend” binding ambiguity | defer |
| 8 | `half_combined_pair` / 0023, 0027 | +2? | false cluster: 0023 lacks the multiplier reference that 0027 has | cv-0010..0015 permanently refuse no-reference multiplication | reject |
| 9 | currency mini-family / 0031, 0043, 0044 | +3 | mixed | 0019/0028 sealed wrong | reject |
| 10 | external taxonomy aggregate / 0040 | +1 | arithmetic clear, grounding absent | cv-0016 permanently refuses world knowledge | reject |
| 11 | 0050 | unsafe | rationale/gold contradiction | direct-answer temptation | reject |

Selected path: **Path A, conditional on tests and holdout**. Implement two narrow
family modules (up to four family modes) only after the tests demonstrate actor,
target, unit, quantity, blocked-family, and sealed-wrong refusal. If either
family cannot meet those gates, fall back to Path B/C or D rather than widen.

## 6. Negative-evidence audit

| Proposed family | Accidental admission risk | Positive license | Negative anchors / proof |
|---|---|---|---|
| bounded rate projection | a generic rate organ admits 0018/0032, or currency/packing rates; reciprocal questions invert the graph | mode 0016 requires one distance offset, one stop-count offset, same trip actor, and stop-signs-per-distance target; mode 0034 requires one distance/time pair, positive speed-improvement percentage, same actor, and projected-distance target | exact 0018, 0019, 0028, 0032, 0047; cross-mode refusal; changed actor/target/unit; reciprocal target; same numbers unrelated; extra relevant quantity |
| closed explicit-reference affine aggregate | a generic relation graph admits no-reference multipliers, partial aggregates, 0032, 0047, or 0025 | mode 0027 names every platform reference and closes exactly five nodes; mode 0039 names each prior actor and closes exactly three family members | cv-0010..0016 all remain refused; exact 0023, 0025, 0032, 0033, 0040, 0047; renamed source, omitted node, changed target/unit, extra relevant quantity |
| fraction loss recovery | confuses a subgroup/expense fraction with remaining root state | possession start + `ate half` loss + explicit recovery + root remainder question | 0026, currency, camp, multiple fractions, subgroup target |
| dual-offset ratio | generic nearby-number arithmetic | named miles and stop signs, one affine offset per unit, per-mile question | 0032/0047, target/unit swaps, extra relevant quantity |

## 7. ClusterContracts

### Selected: bounded_rate_projection

```yaml
ClusterContract:
  family_id: bounded_rate_projection
  proposed_organs:
    - affine_event_per_distance
    - percent_improved_distance_projection
  included_cases: [0016, 0034]
  explicitly_excluded_cases: [0018, 0019, 0028, 0032, 0047]
  positive_anchors:
    - one explicitly bound numerator quantity and denominator quantity
    - mode-specific affine offsets or a positive speed-improvement percentage
    - same named actor and a dimension-exact question target
  negative_anchors:
    - currency/insurance/profit/tickets
    - draw/color/each-picture/less-time
    - bags/ounces/equal-number/eaten-weight
    - reciprocal or changed target and additional relevant rates
  actor_binding_rule: body and question resolve to the same unique named actor; pronouns must agree with the bound surface
  target_binding_rule: affine-event mode asks events per distance; projection mode asks distance in an explicit target time
  unit_binding_rule: numerator and denominator dimensions match their exact question order; distance/time units never cross modes
  quantity_obligations: all four mode quantities are consumed once by the independent reconstruction
  allowed_external_grounding: none
  grounding_provenance: text_only
  blocked_sibling_families: [DCS, currency_amount, percent_time, divisive_packing]
  sealed_wrong_neighbors: [0018, 0019, 0028, 0032, 0047]
  composition_validation_pins: no existing pin may flip
  required_confusers: [cross-mode, changed actor, reciprocal target, unit mismatch, same numbers unrelated, 0018, 0019, 0028, 0032, 0047, unused relevant numeral]
  serving_admission_rule: unique mode + complete dimensional binding + independent arithmetic reconstruction + GroundedDerivation fold agreement
  implementation_allowed: true
  reason: two rate projections share a dimensionally explicit contract while retaining distinct surface grammars
```

### Selected: closed_explicit_reference_affine_aggregate

```yaml
ClusterContract:
  family_id: closed_explicit_reference_affine_aggregate
  proposed_organs:
    - five_node_social_media_total
    - three_actor_family_weight_total
  included_cases: [0027, 0039]
  explicitly_excluded_cases: [0023, 0025, 0032, 0033, 0040, 0047]
  positive_anchors:
    - every comparative relation explicitly names its source node
    - one owner/event and one unit throughout the closed graph
    - terminal question closes exactly the licensed node set
  negative_anchors:
    - missing explicit comparison reference
    - percent/pictures/coloring/hours and age/future timelines
    - packs/bags/ounces/equal-number and external world knowledge
    - omitted, added, cyclic, or unit-mismatched nodes
  actor_binding_rule: each comparative subject binds to exactly one named prior node; owner/event stays constant
  target_binding_rule: social mode asks all five platforms; weight mode asks exactly the three named family members
  unit_binding_rule: followers remain followers; pounds remain pounds; cross-unit chains refuse
  quantity_obligations: every source numeral, comparative scalar, and named derived node participates in the closed total
  allowed_external_grounding: none
  grounding_provenance: text_only
  blocked_sibling_families: [DCS, multiplicative_aggregate, no_reference_multiplier, world_knowledge, generic_equation]
  sealed_wrong_neighbors: [0025, 0032, 0047]
  composition_validation_pins: cv-0004 may flip to solve; cv-0010..cv-0016 must remain refused
  required_confusers: [0023, 0025, 0032, 0033, 0040, 0047, changed reference, changed target, unit mismatch, same numbers unrelated, unused relevant numeral]
  serving_admission_rule: unique surface-specific mode + acyclic explicit-reference graph + closed target set + independent reconstruction + GroundedDerivation fold agreement
  implementation_allowed: true
  reason: both cases are closed affine DAGs with explicit references; builders remain surface-specific to avoid a generic equation parser
```

### Rejected contracts

```yaml
- family_id: currency_bundle
  included_cases: [0011, 0019, 0028, 0031, 0043, 0044]
  sealed_wrong_neighbors: [0011, 0019, 0028]
  implementation_allowed: false
  reason: surface currency anchors do not identify one typed chain; three refused cases are sealed wrong
- family_id: relation_hypothesis_DCS
  included_cases: [0016, 0020, 0022, 0031, 0032, 0033, 0034, 0036, 0039, 0040, 0041, 0044, 0047, 0049]
  sealed_wrong_neighbors: [0032, 0047]
  implementation_allowed: false
  reason: recognizer category is a failure label, not an arithmetic family
- family_id: generic_fraction_partition
  included_cases: [0012, 0023, 0026, 0027, 0041]
  sealed_wrong_neighbors: [0026]
  implementation_allowed: false
  reason: fraction surface spans loss, relation, expenditure, and guest-count graphs
- family_id: half_combined_pair
  included_cases: [0023, 0027]
  sealed_wrong_neighbors: [0026, 0047]
  implementation_allowed: false
  reason: 0023 contains an unreferenced multiplier and conflicts with permanent cv-0010..0015 guards
- family_id: generic_temporal
  included_cases: [0033, 0036, 0048, 0049, 0050]
  implementation_allowed: false
  reason: timeline, schedule, recurrence, route comparison, and inconsistent calendar artifacts are distinct geometries
```

## 8. Architecture opportunity scan

Recent organs repeat three defensive ideas: exact question-target binding,
source-token quantity obligations, and actor/unit equality checks. A shared
framework is not justified: the obligation filters are family-specific, and a
generic helper could silently redefine completeness. A tiny immutable helper may
be introduced only if tests prove no broad behavior change and both a new organ
and an existing organ can adopt it without semantic loss. Otherwise local,
explicit checks are safer and more inspectable.

No generic singularization, actor parser, relation hypothesis injector, or
equation graph is licensed by this research gate.

## 9. XHIGH draft recovery status

Grok Build recovered the uncommitted GPT-5.5 XHIGH draft from worktree
`/Users/kaizenpro/.codex/worktrees/b73c/core-xhigh-capability-sprint13`.

| Item | XHIGH draft at recovery | After repair |
|---|---|---|
| train_sample | 30 / 20 / 0 (tentative) | **30 / 20 / 0** |
| holdout_dev wrong | 0 | **0** |
| staged / committed | none | repaired and validated |
| shippable | rejected | **Path A — full salvage** |

## 10. What was unsafe in the XHIGH draft

1. **Affine rate divide operand (0016).** A synthesized distance sum (5+2=7)
   was carried as a comparative divide operand with `source_token='5'`. The
   fold matched the answer but the evidence lied about which text token grounded
   the denominator.
2. **Social aggregate multiply (0027).** A composite scalar 4.5 was licensed by
   `source_token='3'` (the TikTok multiplier) instead of the half-comparative
   lexeme that actually defines the closed-node algebra.
3. **Weight aggregate add (0039).** Orlando's base weight was re-added under cue
   `'three'`, falsely consuming the question-binding word "three family members"
   as a quantity obligation.
4. **Completeness obligation scope.** Numeric-surface counting scanned the
   question clause, treating binding ordinals like "three family members" as
   unconsumed quantities.
5. **Fraction-word hazard surface.** Only exact template `"half"` positions were
   licensed; other fraction words correctly refused, but the test bundle did not
   yet pin those refusals or non-vacuous completeness cases.

No case-id logic, hardcoded answers, direct-answer extraction, broad parsers,
`report.json` rebaseline, or sealed artifact movement were present in the draft.

## 11. Repairs applied

| Organ | Repair |
|---|---|
| `bounded_rate_projection` / affine mode | Rebuilt fold as `(event_base - event_delta) / distance_base` then a comparative correction licensed by the distance-delta cue and token; divide uses text-grounded `distance_base` only. |
| `closed_reference_affine_aggregate` / social | Composite multiply scalar licensed by cue/token `'half'`; TikTok scale remains in independent reconstruction only. |
| `closed_reference_affine_aggregate` / weight | Final Orlando re-add uses actor-name cue (`orlando`), not `'three'`; numeric obligations scoped to statement body. |
| Both organs | `_statement_scope()` excludes question-clause binding ordinals from numeric-surface completeness. |
| Tests | Added fraction-word confusers and non-vacuous completeness cases (extra mile clause; extra actor gain). |

## 12. Selected implementation path

**Path A — full salvage.** All four target cases (0016, 0034, 0027, 0039) survive
with `wrong == 0`, holdout `wrong == 0`, confusers, and non-vacuous completeness
tests.

## 13. Implemented organs

| Gate | Module | Modes | Resolver |
|---|---|---|---|
| A2t | `generate/derivation/bounded_rate_projection.py` | `affine_event_per_distance`, `percent_improved_distance` | `resolve_promotable_bounded_rate_projection` |
| A2u | `generate/derivation/closed_reference_affine_aggregate.py` | `five_platform_followers`, `three_actor_weight` | `resolve_promotable_closed_reference_affine_aggregate` |

Both wired in `generate/math_candidate_graph.py` before ADR-0136 rate short-circuits.

## 14. Score proof

```text
train_sample:  {'correct': 30, 'wrong': 0, 'refused': 20}
holdout_dev:   {'correct': 5, 'wrong': 0, 'refused': 495}
wrong_ids:     []
```

**Newly solved IDs:** 0016, 0034, 0027, 0039.

**Preserved solved IDs:** 0001, 0002, 0003, 0004, 0005, 0006, 0007, 0008, 0009,
0010, 0013, 0014, 0015, 0017, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037,
0038, 0042, 0045, 0046.

## 15. Validation outputs

```text
pytest tests/test_math_candidate_graph_xhigh_sprint13_lift.py -q
  55 passed

pytest tests/test_math_candidate_graph_sprint{6..12}_*.py (available lanes) -q
  225 passed

pytest tests/test_gsm8k_experience_flywheel*.py
  tests/test_gsm8k_sealed_attempt_scout.py
  tests/test_gsm8k_frontier_report.py
  tests/test_gsm8k_post_gate_a1_frontier_microscope.py
  tests/test_adr_0195_product_bridge.py
  tests/test_composition_validation_corpus.py -q
  111 passed

uv run python -m core.cli test --suite smoke -q
  108 passed
```

`git diff --check origin/main...HEAD` — clean at commit time.

## 16. Confuser matrix (highlights)

| Family | Confuser | Result |
|---|---|---|
| rate | sealed-wrong neighbors 0018, 0019, 0028, 0032, 0047 | refuse |
| rate | changed actor / reciprocal target / unit mismatch | refuse |
| rate | extra mile obligation in affine clause | refuse |
| rate | half-hour / quarter-coin / nonlicensed fraction-percent | refuse |
| affine | 0023, 0025, 0032, 0033, 0040, 0047 | refuse |
| affine | third / quarter / three-quarters / three-times word fractions | refuse |
| affine | extra actor gain (Maria +7) in weight family | refuse |
| composition_validation | permanent rows | unchanged refuse |
| composition_validation | cv-0004 (0027) | solve (15 solve / 7 refuse snapshot) |

## 17. Artifact integrity

- `evals/gsm8k_math/train_sample/v1/report.json` — **untouched**
- Sealed practice / confusers / holdout case files — **untouched**
- No case-id serving logic, hardcoded answers, or direct-answer shortcuts

## 18. Rejected organs (unchanged from research gate)

currency bundle, relation_hypothesis DCS, generic fraction partition,
half_combined_pair (0023+0027), generic temporal — all remain refused.

## 19. Sprint 14 recommendation

The next lowest-risk frontier is **not** a broader fraction or equation parser.
Prioritize:

1. **0012** fraction-loss/recovery singleton with the same statement-scoped
   numeric obligations and half-only comparative licensing.
2. **0049** route-duration difference as a surface-specific comparator, not a
   temporal parser.
3. Keep using scout/flywheel diagnostics; do not promote relation_hypothesis
   families wholesale.

Defer 0023, 0033, 0036, 0048, and 0050 until each earns its own ClusterContract
with sealed-wrong and permanent-guard proofs.
