<!-- CANONICAL | comprehension-primitive-inventory.md | updated 2026-06-03 | execution lane | supersedes prior copies -->

# Comprehension-Primitive Inventory & Cross-Subject Leverage Map

Status: draft / proposal-only
Scope: read-only analysis from `main`, **verified** in the Claude lane (see appendix)
Task: Task A from `docs/handoff/NEXT-SUBJECTS-CHATGPT-HANDOFF.md`

## Operating constraints observed

This artifact is analysis only. It proposes no serving-path edits, no eval edits, no ADR number, and no empirical claims in the inventory body. Any correctness, coverage, or `wrong=0` claim in the body is a structural reading of the code. The **Claude-lane verification appendix** at the end records what was checked against `main` with real reads of the committed report and source; it is the only section permitted to assert empirical state.

Read surfaces:

- `docs/handoff/NEXT-SUBJECTS-CHATGPT-HANDOFF.md`
- `CLAUDE.md`
- `generate/derivation/model.py`
- `generate/derivation/extract.py`
- `generate/derivation/clauses.py`
- `generate/derivation/comparatives.py`
- `generate/derivation/search.py`
- `generate/derivation/multistep.py`
- `generate/derivation/target.py`
- `generate/derivation/compose.py`
- `generate/derivation/accumulate.py`
- `generate/derivation/pool.py`
- `generate/derivation/product_bridge.py`
- `generate/derivation/state/bind.py`
- `generate/derivation/state/change.py`
- `generate/math_candidate_parser.py`
- `generate/math_candidate_graph.py`
- `generate/recognizer_anchor_inject.py`
- Skimmed referenced ADR surface in code/docstrings, especially ADR-0126, ADR-0131, ADR-0136, ADR-0163, ADR-0170, ADR-0175, ADR-0176, ADR-0178, ADR-0182, ADR-0184, ADR-0186, ADR-0189a, ADR-0191, ADR-0193, ADR-0194, ADR-0195.

## Inventory table

| # | Primitive | File / function(s) actually read | One-line description | Subject-general vs math-specific? |
|---:|---|---|---|---|
| 1 | Grounded quantity object | `generate/derivation/model.py::Quantity` | Represents a text-sourced numeric value with unit and source token provenance. | **Subject-general core, math-shaped payload.** Provenance-bearing "observed fact" objects transfer broadly; the `value/unit` fields are math-specific. |
| 2 | Grounded derivation step | `generate/derivation/model.py::Step` | Represents one operation, its operand, and the licensing cue that must ground in text. | **Subject-general.** The pattern "claim/action must carry its own evidence cue" transfers to logic, reading comprehension, measurement, and any rule-bound subject. |
| 3 | Deterministic left-fold derivation | `generate/derivation/model.py::GroundedDerivation.answer` | Computes a candidate result by left-folding validated steps over a start quantity. | **Mostly math-specific.** The arithmetic fold is math-specific; the generalizable primitive is ordered, evidence-carrying state transition. |
| 4 | Primary-unit answer tracking | `generate/derivation/model.py::GroundedDerivation.answer_unit` | Carries the start quantity's unit as the answer unit under current derivation assumptions. | **Math-specific.** It is specifically dimensional arithmetic; the cross-subject analogue is "result type/class propagation." |
| 5 | Digit quantity extraction | `generate/derivation/extract.py::extract_quantities`, `_QTY_RE`, `_quantity` | Extracts digit values followed by single unit tokens into `Quantity` records. | **Subject-general extraction pattern, math-specific symbols.** Literal-span extraction with provenance transfers; numeric parsing/unit attachment is math-specific. |
| 6 | Word-number extraction | `generate/derivation/extract.py::_WORD_QTY_RE`, `_resolve_word_number`, `extract_quantities` | Resolves closed-set word numerals and conservative hyphen compounds into quantities. | **Broadly reusable.** Any subject with controlled lexical facts can use the same closed-vocabulary grounding discipline. |
| 7 | Function-word unit hygiene | `generate/derivation/extract.py::_NON_UNIT_WORDS`, `_clean_unit` | Blanks function words that would otherwise be misread as units. | **Subject-general.** This is a lexical false-positive suppression primitive; math uses it for units, but other subjects need equivalent stop-token guards. |
| 8 | List-unit inheritance | `generate/derivation/extract.py::_LIST_WITH_TRAILING_UNIT_RE`, `extract_quantities` | Assigns a trailing unit to every number in a same-list numeric sequence. | **Mixed.** The list inheritance pattern transfers to reading/measurement; the inherited object is math-specific. |
| 9 | Sentence-final bare number extraction | `generate/derivation/extract.py::_FINAL_NUMBER_RE`, `extract_quantities` | Keeps terminal numbers available with unknown/empty unit rather than inventing a unit. | **Subject-general refusal-first grounding.** It preserves observed evidence without hallucinating missing attributes. |
| 10 | Hyphen-bonded quantity extraction | `generate/derivation/extract.py::_HYPHEN_QTY_RE`, `extract_quantities` | Extracts tight `number-unit` surfaces such as `25-foot` without admitting open-ended multi-word units. | **Mixed.** Hyphenated modifier handling transfers; the payload is measurement/math-specific. |
| 11 | Clause segmentation | `generate/derivation/clauses.py::segment_clauses` | Splits problem text into sentence-level clauses using terminal punctuation. | **Subject-general.** Clause segmentation is a foundational reading primitive; the implementation is intentionally orthographic and conservative. |
| 12 | Clause-local sub-derivation | `generate/derivation/clauses.py::clause_local_results` | Derives each clause's local contribution or holds unresolved on ambiguity. | **Subject-general.** "Resolve locally before composing globally" transfers directly to reading comprehension, logic proof steps, and multi-sentence science/measurement tasks. |
| 13 | Comparative scalar extraction | `generate/derivation/comparatives.py::extract_comparative_scalars`, `_load_comparatives`, `_N_TIMES_RE` | Maps closed comparative lexemes and `<N> times` phrases into scalar operations. | **Mixed.** Closed lexical relation extraction is subject-general; scalar multiplication is math-specific. |
| 14 | Comparative-to-step bridge | `generate/derivation/comparatives.py::comparative_step` | Converts a comparative scalar into a derivation step whose grounding comes from the cue, not necessarily a literal numeric token. | **Subject-general.** The idea that an irreducible lexical fact licenses a typed transformation transfers strongly; the concrete operation is math-specific. |
| 15 | Multiplicative cue hypothesis | `generate/derivation/search.py::MULTIPLICATIVE_CUES`, `_sentence_candidates` | Uses a closed cue set to propose in-clause product candidates only when a multiplicative cue is present. | **Mixed.** Cue-licensed candidate generation is general; multiplication/product semantics are math-specific. |
| 16 | Bounded candidate generation | `generate/derivation/search.py::MAX_QUANTITIES`, `multiplicative_candidates`, `search_multiplicative`; `generate/derivation/multistep.py::MAX_QUANTITIES`, `candidate_chains` | Refuses rather than enumerating unbounded candidate spaces. | **Subject-general.** This is a core safety/performance primitive for any new subject. |
| 17 | Target extraction from question clause | `generate/derivation/target.py::_question_clause`, `extract_target` | Extracts question quantities, aggregation cues, and units named in the question. | **Strongly subject-general.** Every subject lane needs "what is being asked?" extraction; current fields are math-specific. |
| 18 | Prior-state question guard | `generate/derivation/target.py::asks_prior_state`, `_PRIOR_STATE_RE` | Detects questions asking for an earlier temporal state that forward derivation does not compute. | **Subject-general.** Temporal target mismatch is common across reading comprehension, science word problems, and procedural reasoning. |
| 19 | Aggregation hint extraction | `generate/derivation/target.py::_AGG_WORDS`, `_AGG_PHRASES`, `extract_target` | Detects aggregation words/phrases such as `total`, `combined`, and `in all`. | **Mixed.** Aggregation-cue extraction transfers; summation semantics are math-specific. |
| 20 | Question unit intersection | `generate/derivation/target.py::extract_target` | Treats asked units as body-known units that appear in the question. | **Mixed.** Target-slot/body-slot intersection transfers; unit semantics are math-specific. |
| 21 | Shape-based multi-step chain enumeration | `generate/derivation/multistep.py::_candidate_chains`, `_chain`, `candidate_chains` | Builds a small deterministic set of product/sum chains, optionally followed by comparative tail steps. | **Mixed.** Shape-pruned candidate enumeration is general; product/sum chain templates are math-specific. |
| 22 | Same-unit list-sum composition | `generate/derivation/compose.py::compose_sequential`, `_same_unit`, `_ADDITIVE_CUES` | Composes same-unit quantities within one clause using additive cues, with comparative tail application. | **Mixed.** Same-scope list composition transfers to reading/logic lists; same-unit arithmetic is math-specific. |
| 23 | Clause-scoped referent guard | `generate/derivation/compose.py::compose_sequential` | Refuses when a list-sum structure spans multiple quantity-bearing clauses or has out-of-clause comparatives. | **Subject-general.** Scope containment is a central comprehension primitive and directly transfers to reading comprehension. |
| 24 | Single-referent accumulation chaining | `generate/derivation/accumulate.py::_build_accumulation`, `compose_accumulation` | Chains gain/loss changes across clauses only when a later clause safely continues the anchor referent. | **Strongly subject-general.** This is state tracking over discourse; math uses numeric state, but the primitive is broadly useful. |
| 25 | Foreign-distractor candidate handling | `generate/derivation/accumulate.py::_build_accumulation`, `accumulation_candidates`; `generate/derivation/verify.py::classify_derivation` | Allows isolated foreign quantities to enter as disagreement-only/exempt readings rather than commit candidates. | **Subject-general safety primitive.** Distractor evidence handling transfers to all comprehension lanes with irrelevant details. |
| 26 | Sub-clause splitting | `generate/derivation/accumulate.py::_sub_clauses`, `_CONJUNCTION_SPLIT`, `_build_accumulation_anchor_skip` | Locally splits clauses on conjunctions for anchor/change discovery without changing the global segmenter. | **Subject-general.** Local structural refinement under a narrow caller-owned scope transfers well. |
| 27 | Leading-subject extraction | `generate/derivation/state/bind.py::leading_subject_token` | Extracts a clause's leading word token as a loose subject signal. | **Subject-general.** It is a minimal discourse entity cue. |
| 28 | Conservative same-referent continuation | `generate/derivation/state/bind.py::continues_anchor_referent`, `PRONOUNS` | Allows pronouns/same subjects/lowercase continuations and refuses new capitalized actor hazards. | **Subject-general.** This is directly reusable for reading comprehension and logic story-state tracking. |
| 29 | Change polarity classification | `generate/derivation/state/change.py::classify_change_polarity`, `GAIN_VERBS`, `LOSS_VERBS` | Maps closed gain/loss cue sets to `+1`, `-1`, or refusal on ambiguity. | **Mixed.** Polarity classification is subject-general; gain/loss inventory is math-story specific. |
| 30 | Grounded change cue selection | `generate/derivation/state/change.py::select_change_cue` | Chooses the actual cue lexeme that will be checked by the verifier. | **Subject-general.** Separating classification from evidence-cue selection is broadly valuable. |
| 31 | Operand grounding gate | `generate/derivation/verify.py::self_verifies`, `_base_reasons` | Requires every non-comparative operand value token to ground in the problem text. | **Subject-general.** No invented evidence is a cross-domain invariant. |
| 32 | Operation-cue grounding gate | `generate/derivation/verify.py::_base_reasons` | Requires every operation's licensing cue to appear in the text. | **Subject-general.** Every subject lane should require transformation rules to be evidence-licensed. |
| 33 | Unit consistency gate | `generate/derivation/verify.py::_base_reasons`, `_SAME_UNIT_REQUIRED` | Requires same units for add/subtract while allowing multiply/divide composition. | **Math-specific with transferable type discipline.** The gate's type-checking role transfers; the unit rules are math-specific. |
| 34 | Completeness gate | `generate/derivation/verify.py::_unused_quantities`, `self_verifies` | Refuses derivations that leave problem quantities unused. | **Subject-general.** "Account for all salient evidence" is central to reading, logic, measurement, and science tasks. |
| 35 | Branch disagreement / uniqueness gate | `generate/derivation/verify.py::select_self_verified`; `generate/derivation/pool.py::resolve_pooled`; `generate/math_candidate_graph.py::parse_and_solve` | Commits only when verified candidates collapse to one distinct answer; otherwise refuses. | **Strongly subject-general.** This is one of the most transferable wrong=0-preserving primitives. |
| 36 | Commit-eligible vs exempt classification | `generate/derivation/verify.py::classify_derivation` | Classifies readings as complete, exempt, or invalid; exempt readings can force disagreement but cannot commit alone. | **Subject-general.** "Counter-reading can block commitment without becoming an answer" is broadly useful. |
| 37 | Repeated-unit product hazard detector | `generate/derivation/verify.py::_is_repeated_unit_product` | Marks pure products that repeat non-empty dimensions as commit-ineligible. | **Math-specific.** The general form is domain-type impossibility detection. |
| 38 | Cross-composer pooling | `generate/derivation/pool.py::pooled_candidates`, `resolve_pooled` | Pools accumulation, multiplicative, and target-guided chain readings before applying disagreement/commit rules. | **Subject-general architecture.** Multiple independent readers should meet at a common disagreement gate. |
| 39 | Serving promotion bridge | `generate/derivation/product_bridge.py::resolve_promotable_product`, `_has_hazard_surface`, `_has_product_target` | Promotes only complete pure-product readings whose question target and blocker checks make them safe for serving exposure. | **Mixed.** Promotion-boundary pattern is subject-general; current target/hazard surfaces are math-specific. |
| 40 | Candidate initial-state extraction | `generate/math_candidate_parser.py::extract_initial_candidates`, `CandidateInitial` | Emits initial possession/state candidates with source-span provenance. | **Subject-general.** Initial state extraction is foundational for any story/world model; possession quantity is math-specific. |
| 41 | Value-slot resolution | `generate/math_candidate_parser.py::_resolve_value`, `_resolve_currency`, `_is_indefinite_quantifier` | Resolves digits, money, fractions, word numbers, and hyphenated cardinals; refuses indefinite/unparseable values. | **Mixed.** Refusal-first lexical resolution transfers; supported value types are math-specific. |
| 42 | Unit canonicalization | `generate/math_candidate_parser.py::_canonicalize_unit`, `_money_unit_normalization` | Maps surface unit tokens to canonical/plural units, including money normalization. | **Math/measurement-specific with transferable normalization boundary.** Other subjects need similar canonicalization for entities, predicates, or labels. |
| 43 | Operation candidate extraction | `generate/math_candidate_parser.py::extract_operation_candidates`, `_op_pattern`, `_build_op_candidate` | Emits add/subtract/transfer operation candidates from canonical subject-verb-value-unit shapes. | **Mixed.** Typed event extraction transfers; arithmetic operation kinds are math-specific. |
| 44 | Comparative operation extraction | `generate/math_candidate_parser.py::_compare_additive_candidates`, `_compare_multiplicative_candidates`, `_compare_nested_candidates`, `_resolve_reference_token` | Emits comparison candidates using closed comparison anchors and reference grounding. | **Mixed.** Comparative relation extraction transfers strongly; numeric delta/factor semantics are math-specific. |
| 45 | Question candidate extraction | `generate/math_candidate_parser.py::extract_question_candidates`, `CandidateUnknown` | Emits unknown target candidates from closed question shapes. | **Subject-general.** Question-frame parsing is a primary cross-subject bottleneck. |
| 46 | Aggregate question frames | `generate/math_candidate_parser.py::_Q_TOTAL_RE`, `_Q_THERE_RE`, `extract_question_candidates` | Maps total-across question surfaces to `Unknown(entity=None, unit=...)`. | **Mixed.** Aggregate target framing transfers; "unit total" is math-specific. |
| 47 | Activity question frame | `generate/math_candidate_parser.py::_Q_DID_RE`, `extract_question_candidates` | Handles `How many <unit> did <Entity> <verb>?` activity-count questions. | **Mixed.** Activity target extraction transfers; counted activity quantity is math-specific. |
| 48 | Conditional-prefix stripping | `generate/math_candidate_graph.py::_strip_conditional_prefix`, `_filtered_question_choices` | Retries question parsing after removing an `If X,` prefix. | **Subject-general.** Conditional-wrapper removal is broadly useful across logic and reading comprehension. |
| 49 | Comparative-question refusal detector | `generate/math_candidate_parser.py::_pattern_b_comparative_candidates`, `_pattern_b_detects` | Recognizes "how many more" questions but emits no candidate until solver semantics exist. | **Subject-general safety primitive.** Detection-only recognizers can force clean refusal without pretending capability. |
| 50 | Pronoun question resolution | `generate/math_candidate_parser.py::_resolve_pronoun_entity`, `_resolve_question_entity`, `_pattern_c_pronoun_verb_candidates` | Resolves gendered pronoun question entities only when exactly one whitelisted antecedent is present. | **Subject-general, implementation narrow.** The refuse-on-ambiguity pattern transfers; current name lists are GSM8K-specific. |
| 51 | Statement context classifier | `generate/math_candidate_parser.py::has_numeric_token`, `classify_sentence` | Skips non-numeric context statements while preserving numeric-state-bearing statements as required parse/refuse inputs. | **Mixed.** Context filtering transfers; numeric-token criterion is math-specific. |
| 52 | Capacity/rate extraction | `generate/math_candidate_parser.py::extract_capacity_candidates`, `extract_capacity_question_candidates`, `_to_seconds`; `generate/math_candidate_graph.py::parse_and_solve` | Extracts capacity per time and matching time-target questions, then computes scaled rate answers in a guarded short-circuit. | **Math/measurement-specific.** The broader primitive is matched statement/question rate-frame binding. |
| 53 | Earnings-rate extraction | `generate/math_candidate_parser.py::extract_earnings_candidates`, `extract_earnings_question_candidates`; `generate/math_candidate_graph.py::parse_and_solve` | Extracts currency-per-time statements and matching money-over-time questions. | **Math/measurement-specific.** Transfers mainly to measurement/finance-like lanes. |
| 54 | Conditional operation question | `generate/math_candidate_parser.py::extract_conditional_op_question_candidates`; `generate/math_candidate_graph.py::parse_and_solve` | Handles `If entity changes by N, how many ... left/now?` by matching one existing initial state and applying polarity. | **Mixed.** Conditional hypothetical target binding transfers strongly; arithmetic update is math-specific. |
| 55 | Sentence splitting / one-question invariant | `generate/math_candidate_graph.py::_split_sentences`, `parse_and_solve` | Splits text, requires exactly one question sentence, and refuses otherwise. | **Subject-general.** Most subject lanes need explicit problem/question segmentation and clean refusal on malformed tasks. |
| 56 | Per-sentence round-trip filtering | `generate/math_candidate_graph.py::_filtered_statement_choices`, `_filtered_question_choices`, `_initial_admissible`, `_question_admissible` | Filters emitted candidates by structural grounding before graph assembly. | **Subject-general.** Candidate emission and admissibility must remain separate in every subject. |
| 57 | Most-grounded-slots tiebreaker | `generate/math_candidate_graph.py::_slot_count`, `_collapse_per_sentence_ties` | Collapses same-sentence candidates to the most grounded candidate when appropriate. | **Subject-general but hazardous if overused.** It transfers as a deterministic tiebreaker, but each subject must prove it cannot mask ambiguity. |
| 58 | Graph construction with referential integrity | `generate/math_candidate_graph.py::_build_graph` | Builds a `MathProblemGraph`, rejecting branches whose question references unknown entities or violate graph invariants. | **Subject-general architecture, math-specific graph type.** Every subject needs typed graph construction with integrity checks. |
| 59 | Cartesian branch enumeration cap | `generate/math_candidate_graph.py::MAX_TOTAL_BRANCHES`, `parse_and_solve` | Bounds branch enumeration and refuses when the space would exceed the cap. | **Subject-general.** Essential for deterministic safety and performance. |
| 60 | Recognizer registry fallback | `generate/math_candidate_graph.py::_load_ratified_registry_or_empty`, `parse_and_solve` | Consults ratified recognizers only when parser choices are empty, and treats registry failures as empty. | **Subject-general.** Reviewed recognizer fallback with fail-closed behavior transfers directly. |
| 61 | Anchor injection dispatch | `generate/recognizer_anchor_inject.py::inject_from_match` | Converts recognized anchors into typed solver primitives or returns empty on unsupported/unsafe categories. | **Subject-general.** This is a reusable boundary between recognizers and solver primitives. |
| 62 | Composition registry consultation | `generate/recognizer_anchor_inject.py::_consult_composition_registry` | Admits pre-composed payloads only when the composition registry affirms their surface shape. | **Subject-general.** Reviewed structural-shape admission is reusable for logic, reading, and geometry. |
| 63 | Discrete-count anchor injection | `generate/recognizer_anchor_inject.py::inject_discrete_count_statement`, `_build_initial_from_discrete_count`, `_build_operation_from_discrete_count_acquisition` | Builds initial-state or add-operation candidates from discrete-count recognizer anchors. | **Mixed.** Anchor-to-typed-fact injection is general; discrete count semantics are math-specific. |
| 64 | Sealed injector lane | `generate/recognizer_anchor_inject.py::_SEALED_INJECTORS`, `inject_from_match`; `generate/math_candidate_graph.py::parse_and_solve(sealed=...)` | Keeps in-development injectors out of default serving until reviewed promotion. | **Subject-general.** This is a major reusable safety boundary for new subject lanes. |
| 65 | Lookback pronoun resolution / ambiguity defense | `generate/math_candidate_graph.py::parse_and_solve` recognizer-injection section | Holds pronoun-requiring injected candidates until a discourse antecedent or pack-backed disambiguation is available; otherwise drops them. | **Strongly subject-general.** This is directly relevant to reading-comprehension and story-state subjects. |
| 66 | Reader trace events | `generate/math_candidate_graph.py::CandidateGraphResult.reader_trace`, pronoun/lookback trace appends in `parse_and_solve` | Carries JSON-encoded trace events for reader phases and elimination/refusal causes. | **Subject-general.** Traceability/replay evidence is central to every future lane. |

## Cross-subject leverage map

### Strong transfer primitives

These are the highest-leverage primitives for new subjects because they are not inherently arithmetic:

1. **Evidence-carrying candidate objects** — anchors: `Quantity`, `Step`, `CandidateInitial`, `CandidateOperation`, `CandidateUnknown`. Cross-subject use: claims, propositions, logical premises, reading-comprehension facts, geometry givens.
2. **Candidate emission separated from admissibility** — anchors: `extract_*_candidates`, `_initial_admissible`, `_question_admissible`, `roundtrip_admissible`, `self_verifies`. Cross-subject use: emit possible readings, then require grounding/type/consistency before commitment.
3. **Refusal-first ambiguity handling** — anchors: `select_self_verified`, `resolve_pooled`, `parse_and_solve` decision rule. Cross-subject use: when multiple interpretations remain, refuse instead of choosing.
4. **Scope/referent guards** — anchors: `segment_clauses`, `compose_sequential` clause-local guard, `continues_anchor_referent`, `_resolve_pronoun_entity`, lookback ambiguity defense. Cross-subject use: reading comprehension, narrative state tracking, logic variable binding.
5. **Question/target extraction** — anchors: `extract_target`, `extract_question_candidates`, conditional prefix stripping, capacity/earnings/conditional question extractors. Cross-subject use: target-frame parsing is the obvious shared bottleneck across math, logic, reading, and measurement.
6. **Completeness and distractor classification** — anchors: `_unused_quantities`, `classify_derivation`, exempt readings, context classifier. Cross-subject use: all subjects need "account for all relevant evidence" without forcing irrelevant distractors into the committed answer.
7. **Promotion boundaries** — anchors: `resolve_promotable_product`, sealed injectors, ratified registry fallback. Cross-subject use: experimental readers can exist without becoming served behavior.

### Math-specific primitives with reusable analogues

| Math-specific primitive | Why math-specific | Reusable analogue |
|---|---|---|
| Unit consistency | Depends on dimensional arithmetic rules. | Type consistency / sort checking. |
| Product/sum chain enumeration | Depends on arithmetic operator semantics. | Bounded proof/action sequence enumeration. |
| Comparative scalar multiplication | Numeric scalar operation. | Relation-strength or predicate-transform facts from closed packs. |
| Capacity/earnings rate short-circuits | Rate arithmetic over time/currency. | Matched statement-target frame with deterministic transformation. |
| Repeated-unit product hazard | Dimensional impossibility. | Domain-type impossibility detector. |
| Money/currency normalization | Numeric unit system. | Canonical symbol/entity normalization. |

## Observed composition wall

The current substrate already has many individually strong primitives. The bottleneck is not lack of primitives; it is safe composition among them:

- Clause-local reasoning exists, but cross-clause reasoning remains guarded and narrow.
- Question target extraction exists, but many target frames still require closed shape support.
- Referent continuation exists, but pronoun/coreference resolution is intentionally conservative.
- Candidate pooling exists, but promotion to serving requires narrow target/hazard gates.
- Completeness is strong, but it can over-force distractors unless exempt/disagreement paths are present.

This confirms the brief's framing: the next-subject work should exercise the same composition primitives without creating live serving risk.

## What transfers to other subjects

- **Reading comprehension should reuse the most math-relevant primitives immediately:** clause segmentation, referent guards, pronoun ambiguity refusal, target-frame parsing, completeness, and branch disagreement are already the exact pain points behind the math composition wall.
- **Symbolic/deductive logic can reuse the candidate/admissibility/disagreement architecture:** premises become evidence-bearing candidates, inference rules become cue- or schema-licensed steps, and ambiguous proof branches refuse rather than commit.
- **Measurement/geometry can reuse the most math-specific substrate with low conceptual impedance:** quantity extraction, unit canonicalization, unit/type consistency, target-unit matching, rate/measurement frames, and dimensional impossibility checks are already close to that domain.
- **All future subjects should preserve the sealed/promotion boundary pattern:** draft readers and recognizers can be explored only as proposal-only or sealed lanes until the Claude lane verifies the relevant invariants.
- **The highest cross-subject ROI is not a new corpus first; it is a small capability-axis spec that stresses target extraction, referent binding, completeness, and disagreement without weakening `wrong=0`.**

## Open questions for the Claude lane

1. Verify whether any functions above are currently serving-active vs sealed/practice-only on `main`; this read-only pass did not run lane-sha checks or tests.
2. Confirm the exact current serving count and wrong/refusal distribution through the pinned eval lane before using this document as planning evidence.
3. Decide whether Task B should treat `product_bridge.resolve_promotable_product` as part of the active question layer or as a promotion boundary around the derivation reader.
4. Inspect coverage for the "most-grounded-slots-wins" tiebreaker before reusing that pattern in any new subject; it is powerful but could mask ambiguity if applied too broadly.
5. For Task C, compare candidate subject ordering against the actual contents of `evals/symbolic_logic/` and `evals/math_capability_axes/` before drafting any subject-specific axes.

---

## Claude-lane verification (landed)

Verified against `main` at commit `3e29559` by reading the committed serving report and source. Method note: the inventory above was authored read-only; the checks below resolve its five open questions. The full `core test`/MLX/Rust suite was **not** re-run in this lane (Apple-Silicon/MLX substrate unavailable here); the serving metric cited is the committed, pinned report — the authoritative source of truth for the frozen serving path — not a fresh run.

**Definition-of-done check (Task A):** all 66 primitives resolve to real files on `main`. Every referenced module exists (`generate/derivation/{model,extract,clauses,comparatives,search,multistep,target,compose,accumulate,pool,product_bridge,verify}.py`, `generate/derivation/state/{bind,change}.py`, `generate/{math_candidate_parser,math_candidate_graph,recognizer_anchor_inject}.py`). No invented APIs found.

### Q1 — serving-active vs sealed
- `_SEALED_INJECTORS = {}` is **empty** on `main`. Nothing is currently sealed. Inventory row #64 describes a real mechanism, but it is presently inert — so "sealed lane" is not what is suppressing any current behavior.
- `discrete_count_statement` is **serving-active**: it is wired directly into the live dispatch map (`ShapeCategory.DISCRETE_COUNT_STATEMENT: inject_discrete_count_statement`). Its empty injections (see Q2) are genuine conservatism in the active injector, not sealing.
- The frozen-serving gate (`scripts/verify_lane_shas.py`) pins the **SHA-256 of report outputs** for 8 eval lanes (reviewer_registry, miner_loop_closure, curriculum_loop_closure, domain_contract_validation, fabrication_control, demo_composition, public_demo, math_teaching_corpus). It freezes serving by making any drift in those outputs detectable; it does not pin a static list of serving source files.

### Q2 — exact serving distribution (CONFIRMED)
Pinned report `evals/gsm8k_math/train_sample/v1/report.json` (ADR-0126, sample_count=50):

- **6 correct / 44 refused / 0 wrong.** `wrong=0` holds. `exit_criterion.correct_min=10` → `passed: false`.

The 44 non-correct cases decompose as:

| Failure mode | Count |
|---|---:|
| Recognizer matched but produced **no injection** | 32 |
| **No admissible candidate** (parser emitted nothing usable) | 12 |

Locus of the 44: statement (recognizer) 32 · statement (parser) 7 · question (parser) 5.

Recognizer-fired-but-empty-injection (32) by category:

| Category | Count |
|---|---:|
| `discrete_count_statement` | 18 |
| `descriptive_setup_no_quantity` | 4 |
| `rate_with_currency` | 3 |
| `multiplicative_aggregation` | 3 |
| `currency_amount` | 3 |
| `temporal_aggregation` | 1 |

**Headline:** the single largest refusal bucket is `discrete_count_statement` — **18 of 44 (41%)** — where the serving-active recognizer fires on a count-like token but the injector returns empty. **This marks *where* the composition wall surfaces; it is not a lever to widen.** As the corrected Net-read below establishes, all 18 are 2–4 capability compositions the injector *correctly* declines (emitting an initial-state there is metric-inert). The concentration is diagnostic — the most common surface form of the wall — not a backlog item, and it touches the entity/initial-state primitives (#40, #63) only as evidence that the wall sits *downstream* of extraction, in composition.

### Q3 — `product_bridge.resolve_promotable_product` classification (RESOLVED)
It is part of the **active serving question layer, behaving as a promotion boundary around the derivation reader** — both, not either/or. Its module docstring places it on "the serving candidate-graph path," and it returns a "serving-safe product resolution" only after passing `_has_hazard_surface` and `_has_product_target`. Recommendation for Task B: treat it as the guarded gate by which derivation-reader products reach serving, i.e. a promotion boundary that is itself live — not a sealed/practice-only reader.

### Q4 — "most-grounded-slots-wins" tiebreaker coverage (CAUTION CONFIRMED, scope corrected)
`_collapse_per_sentence_ties` / `_slot_count` are invoked at two serving sites in `parse_and_solve` (lines 958, 999). No test references those functions **by name** (no white-box test). However — correcting an earlier overstatement in this appendix — the collapse **is** behaviorally covered on the happy path: `tests/test_math_candidate_graph.py::TestAmbiguityResolution::test_gives_with_target_resolves_to_transfer` exercises the slot-count collapse ("Sam gives 3 apples to Tom" → transfer reading wins on more grounded slots) and would fail if the collapse broke. The accurate, narrower gap is therefore: happy-path collapse is covered; what is **missing** is (a) a white-box test naming the functions and (b) an **adversarial "high-slot-but-wrong vs low-slot-but-right"** case — the scenario where "more slots = better" selects the wrong reading. Recommendation: add both before reusing this pattern in any new subject.

### Q5 — Task C input (DEFERRED to Task C execution)
Not resolved here; Task C explicitly requires comparing candidate subject ordering against the live contents of `evals/symbolic_logic/` and `evals/math_capability_axes/`. Flagged for the Task C pass so it is not double-counted as Task A scope.

### Net read for planning (corrected)
An earlier version of this section recommended widening the serving-active `discrete_count_statement` injector as "the highest-count, lowest-risk math lever (18/44)." **That conclusion was wrong and is retracted.** Reading all 18 of those cases in full shows they are **2–4 capability compositions** (ratio chains 0020/0029/0033, multi-step rate/percent 0032/0034/0044, accumulate-against-target 0037/0039, and 0040 which needs per-entity attribute lookup before any arithmetic). The recognizer fires on the first count token ("2 horses"); the injector **correctly declines** because the surrounding problem is not a bare count. Emitting an initial-state there is **metric-inert** — the graph still cannot compose to the answer. The 18/44 concentration is the **composition wall surfacing at the most common recognizer category**, not an injector to widen. This is reinforced by **ADR-0174 (Proposed)**, which deprecates the per-category injector dispatch table as the runtime admission path (injectors become hypothesis-emitters in a held-hypothesis reader), and by the wrong=0 hazard of that surface (case-0050 canary on the same serving path).

Corrected steer: primitives are not the bottleneck; **safe composition is.** The honest next lever is a **composition capability** over the existing grounded primitives — multi-quantity chains (ratio, multi-step rate/percent, accumulate-against-target). The direct GSM8K-metric lever is **ADR-0174's held-hypothesis reader (Proposed)**; the adjacent proof-DAG substrate — binding-graph acyclicity, proof-graph builder, modus-ponens disagreement — is already **Accepted** (ADR-0203/0204/0205, proof_chain phase 2.1–2.3). So the work is composition through the held-hypothesis reader on an accepted proof substrate, **not** category-dispatch widening. For Task B: group all 44 and rank by **composition-arity** (1-capability gaps = tractable; 2–4-capability compositions = the wall), not by raw recognizer-category count.
