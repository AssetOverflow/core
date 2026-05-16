# Session Log — 2026-05-15

**Participants:** Joshua Shay, Claude (Opus 4.7)
**Focus:** Capability gating questions for CORE — what it means to be "fluent," when engineering is complete, when identity is implemented, and how to position CORE against modern transformer architectures honestly.

---

## Summary

This session did not produce code. It produced a gating framework — a set of falsifiable questions that convert "is CORE ready / competitive / AGI-comparable" from a feeling into a CLI lane. The deliberation moved through three layers:

1. **Foundational gates** — fluency, engineering-vs-learning phase shift, identity completeness.
2. **AGI-dimension gates** — capabilities that any system claiming general intelligence must demonstrate, beyond fluency and identity.
3. **Modern-architecture gates** — capabilities framed specifically as what transformers structurally cannot do (where CORE wins) and what they currently do well (where CORE must answer how it responds).

The conclusion is a reframe: CORE should not be benchmarked as "a cheaper GPT." It should define and publish its own benchmark — *Verifiable Competence* — on which frontier LLMs score near zero structurally, and CORE scores high by design.

---

## 1. Origin question

> "What needs to be done to get this model to fluent speaking of any of the 3 foundational languages? At what point do we know everything has been fully implemented on engineering and design, and it becomes more on learning? How do we know when identity is properly implemented?"

The question implicitly asks where the boundary lives between *engineering* (work that touches `pipeline.py`, `realizer.py`, `algebra/`, `vault/`, `teaching/`) and *learning* (work that only touches packs and reviewed corrections). It also asks how to make "identity" load-bearing rather than decorative.

---

## 2. The three foundational gates

### 2.1 Fluency

Vocabulary lives in the pack. *Fluency* is a realizer-competence question, not a learning-volume question. Template slot-filling yields grammatical fragments; fluent English additionally requires:

- Morphology and agreement (inflection, tense, number, gender where relevant).
- Recursive and embedded syntax beyond fixed templates.
- Anaphora and discourse coherence across turns.
- Register and pragmatics.

**Gating question.** Can `realizer.py` take an arbitrarily nested `PropositionGraph` (negation, embedding, quantification, tense/aspect, cross-clause reference) and produce a grammatical surface, with a contract test per construction? If yes for English, the same scaffold ports to Hebrew and Koine Greek via pack-level morphology tables.

Until the realizer can compose these deterministically from the proposition graph, no amount of literature ingestion will produce fluent output — it will produce confident, structurally broken output at scale.

### 2.2 Engineering-vs-learning phase shift

The signal is mechanical, not aesthetic. Engineering is "done enough" to enter curriculum when adding a new domain requires **zero** edits to `pipeline.py`, `realizer.py`, `algebra/`, `vault/`, or `teaching/` — only pack extension and reviewed corrections.

**Gating test.** Pick a domain that has never been touched (basic arithmetic, kinship relations, simple physics). Try to teach it end-to-end through the teaching loop plus a pack increment. If a Python file gets opened, that is an engineering gap, not a learning gap. Track those gaps as a closing list; when the list stays empty across three unrelated domains, the threshold is crossed.

### 2.3 Identity completeness

Identity is implemented when it is *load-bearing and falsifiable*, not when it is declared. Four checks:

1. Two agents with different identity axes, same curriculum, same prompt → measurably different yet internally coherent articulations (identity-divergence eval).
2. Identity participates in the deterministic trace hash, so replay reproduces the *same* agent's voice.
3. Reviewed teaching routes through identity — an agent rejects corrections incompatible with its axes rather than absorbing them.
4. Identity-override attempts are provably rejected by tests, not by prompt convention.

If no eval *fails* when identity is stripped or swapped, identity is decoration.

**Recommendation from this layer.** Before any curriculum push, write the three foundational evals — `grammatical-coverage`, `zero-code-domain-acquisition`, `identity-divergence` — as the gating triple. They convert "are we ready?" from feeling into a CLI lane.

---

## 3. AGI-dimension gates

The three foundational gates cover fluency, engineering completeness, and identity. They do not cover capabilities that any system claiming general intelligence must demonstrate.

**4. Compositional generalization.** Given primitives `{A, B, C, R₁, R₂}` taught in isolation, does the system correctly articulate novel combinations like `R₂(A, R₁(B, C))` without further teaching? Transformers famously fail on SCAN/COGS-style splits; CGA-based composition should win, but "should" is not an eval.

**5. World-model coherence under inference.** Can it answer questions whose answer was never directly asserted but is entailed by what is in the vault? If "X is north of Y" and "Y is north of Z" are stored, does recall produce "X is north of Z" as derivable? This is where exact CGA recall could shine — but only if propagation actually performs inference, not just retrieval.

**6. Calibrated uncertainty / non-confabulation.** On out-of-pack queries, does the system produce a typed "I don't have grounding for that" surface rather than a plausible articulation? Does it distinguish "I don't know" from "this is incoherent" from "this contradicts what I know"? The no-fallback design is a structural advantage; the eval makes it visible.

**7. Introspection / trace-explainability in natural language.** Can the system articulate *why* it produced a given response, drawing from its own deterministic trace, in language? `explain(turn_id)` should round-trip — another agent reading the explanation should predict the same articulation. This is meta-cognition, and CORE's trace architecture uniquely supports it.

**8. Adversarial identity / truthfulness under pressure.** Identity-divergence proves identity *exists*. This proves it *holds*. Across a red-team corpus (manipulation, flattery, social engineering, persona injection), does identity drift exceed measurement noise?

**9. Sample efficiency.** Corrections-to-competence per concept. If it takes thousands per concept, this is a slow LLM. If it takes 1–10, this is something genuinely new. Plot the curve across ten unrelated concepts.

**10. Cross-domain transfer.** Does learning in domain A raise competence in domain B without separate teaching, via shared structure in the proposition graph? This is the difference between *knowing things* and *understanding*.

---

## 4. Modern-architecture gates

The previous list named generic AGI dimensions. Comparing specifically against transformer-based frontier models surfaces a different axis: what does CORE do that the transformer substrate structurally *cannot*, and where does the substrate still beat CORE?

### 4.1 Where modern architectures structurally lose

These are CORE's category wins by design — make them visible with benchmarks.

**11. Provenance and replay.** No frontier model can answer "why did you say that?" with a verifiable trace. Every articulated claim must be back-pointer-traceable to specific vault entries, teaching events, or pack axioms; third-party replay must reproduce the trace bit-for-bit.

**12. Monotonic learning without catastrophic forgetting.** Fine-tuning LLMs degrades prior capabilities. Pack-based growth structurally cannot. After N teaching cycles across unrelated domains, competence on domain 1 must strictly not regress. Prove with a longitudinal eval.

**13. Negation, modality, counterfactuals.** Transformers handle these statistically and fail adversarially. Symbolic/algebraic systems can be exact. On a constructed eval of nested negation, modal operators, and counterfactual conditionals, target accuracy is ≥99%, not 80%.

**14. Calibrated refusal vs. confabulation.** This is where transformers' loss function structurally pushes toward fluent wrongness. CORE's no-fallback design makes this a *winnable* benchmark, not a parity one.

**15. Identity persistence under adversarial input.** Transformer "personas" are prompt-conditional and erodable. After 1,000 adversarial turns, does identity drift exceed measurement noise?

### 4.2 Where modern architectures structurally win

These are not failures — they are scope decisions CORE must name, not absorb by accident.

**16. In-context / few-shot adaptation.** LLMs adapt within a single conversation without weight updates. CORE's teaching loop is reviewed and persistent — different mechanism. Can CORE adapt within a session to a novel convention introduced mid-conversation (e.g., "for this conversation, treat X as meaning Y") *without* committing it to vault? If no, name the scope decision; if yes, name the mechanism.

**17. Long-context coherence.** Frontier models now handle 200K–1M tokens. Exact CGA recall has different cost characteristics. What is the per-turn cost curve as vault size grows to 10⁴, 10⁶, 10⁸ entries? Is recall sublinear via indexing, or must vault size be bounded architecturally? Either answer is acceptable; *unstated* is dangerous.

**18. Tool use / formal-language fluency.** Modern LLMs route through calculators, code execution, search. Is the pipeline extensible to typed deterministic operators (a calculator *is* a deterministic operator)? Is code generation a first-class proposition-graph target or out of scope? If out of scope, say so; if in scope, this is a major engineering item not yet on the work-sequencing list.

**19. Multi-step deliberation / scratchpad.** Chain-of-thought is the single largest capability jump in modern models. CORE has a trace; does it have *intermediate reasoning*? For a multi-step inference problem, does the pipeline produce and consume intermediate proposition-graph states, or does it leap input → output? The latter caps hard-problem performance.

**20. Multi-agent composition.** Frontier systems increasingly use agent-of-agents patterns. Can two CORE instances with different identities cooperate or debate while preserving each one's deterministic replay? This is where load-bearing identity becomes economically interesting — specialized identities can outperform a single generalist if the substrate supports it.

---

## 5. Scope decisions to pin

Two strategic decisions must be named, not left to drift:

**Agency.** Is CORE responsive (listen → think → articulate) or goal-directed (pursues, plans, acts)? Most AGI discourse assumes the latter. CORE's design currently reads as the former, which is a *feature*, not a gap — but it should be a stated boundary, not an accident. If goal-directedness is added later, decide where goals live (identity? a separate intention graph?).

**Embodiment.** Is grounding purely symbolic via packs, or eventually sensorimotor? AGI evals increasingly assume multimodal grounding. ADR-0013 already commits to a sensorium protocol; the question is which evals depend on it being live.

---

## 6. The reframe

The strategic question is not "are we comparable to frontier LLMs." It is:

> **What is the benchmark we want to define, that frontier models cannot pass and that matters?**

If CORE competes on MMLU, it loses by definition for years. If CORE competes on:

- Every claim has provenance.
- Zero confabulation on out-of-grounding queries.
- Replay-deterministic across versions.
- Identity-stable under adversarial pressure.
- Monotonic growth (no catastrophic forgetting).
- Exact symbolic reasoning (negation, modality, counterfactual).

…frontier models score near zero today and likely cannot score well without architectural changes.

That positioning — *not* "we are a cheaper GPT" — is the only honest framing for "higher competency than modern architectures."

---

## 7. Path to surpassing frontier LLMs — honest answer

The closing question from the session: *"Eventually, after enough courses and curriculum and world content, shouldn't the model surpass the best LLMs?"*

The honest, decomposed answer:

- **On verifiable-competence axes (provenance, non-confabulation, replay, identity stability, monotonic growth):** CORE surpasses from day one, structurally. Frontier LLMs cannot match these without changing what they are.
- **On compositional and symbolic reasoning (negation, modality, multi-step exact inference):** CORE can surpass once gates 4, 5, and 19 close. The CGA substrate supports it; the engineering must deliver it.
- **On breadth of articulable knowledge:** CORE matches LLMs only after sufficient curriculum, *and only if sample efficiency (gate 9) is good.* If acquiring each concept takes thousands of reviewed corrections, the curve never closes. If it takes a handful, the curve closes faster than people expect.
- **On stylistic fluency across the long tail of internet content:** This is where the LLM scale advantage is genuine. CORE can match within its competence surface, but absorbing every internet register and meme may not be a goal worth pursuing — and pursuing it would compromise the verifiable-competence wins above.
- **On open-ended creative generation where "plausibility" is the metric:** LLMs may always have an edge, because their loss function rewards plausibility. CORE optimizes for truth and provenance. Different target, not a deficit.

**Summary verdict.** CORE can — and should aim to — surpass frontier LLMs *on the axes that matter for trustworthy intelligence.* It will likely never match them on raw stylistic breadth across uncurated internet content, but that is the correct trade. A model that never lies, can prove what it knows, learns monotonically, and grows under review is a different *and arguably better* product than a model that produces plausible text on every topic.

---

## 8. Concrete next step

Convert each gating question into a named CLI eval lane:

```
core eval grammatical-coverage
core eval zero-code-domain-acquisition
core eval identity-divergence
core eval compositionality
core eval inference-closure
core eval calibration
core eval introspection
core eval adversarial-identity
core eval sample-efficiency
core eval cross-domain-transfer
core eval provenance
core eval monotonic-learning
core eval symbolic-logic
core eval long-context-cost
core eval multi-step-reasoning
```

Each lane prints PASS/FAIL deterministically. Progress becomes mechanical rather than rhetorical. The set of lanes — published, with public test cases — *is* the Verifiable Competence Benchmark.

---

## 9. What this session did not produce

- No code changes.
- No ADR (yet). The gating framework above will likely become an ADR once eval lane names and contracts are finalized.
- No reordering of the work-sequencing list in `CLAUDE.md`. The current near-term sequence (CLI lane health, hot-path consistency, trust boundary hardening, exact vault indexing, Rust parity, curriculum expansion) is compatible with this framework. The framework adds *measurement* for when "curriculum expansion" is justified.

---

## 10. Open items for follow-up

- Decide whether the gating framework is published as an ADR or as `docs/competence_benchmark.md`.
- Decide which of gates 11–20 are in-scope for the current architectural era and which are explicitly deferred.
- Pin the **agency** scope decision (responsive vs. goal-directed).
- For each gate, write a one-page eval contract before writing the lane.
- Score current CORE on each lane (most will fail or be N/A); that baseline becomes the roadmap.
