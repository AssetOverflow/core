# Teaching Order — How to Curriculum CORE

**Status:** Reference doctrine. Update only when the formation pipeline's gate semantics change.
**Last updated:** 2026-05-17
**Companion docs:** [`formation_pipeline_plan.md`](formation_pipeline_plan.md), [`capability_roadmap.md`](capability_roadmap.md), [`sessions/SESSION-2026-05-15-capability-gates.md`](sessions/SESSION-2026-05-15-capability-gates.md)

---

## TL;DR

Teach in **prerequisite-topological order**, not in pedagogical grade order. The "elementary → college" intuition is correct at the macro level (simple before composed, anchored before novel) and wrong at the literal level (do not start with a 3rd-grade language-arts corpus). Start with the smallest set of CORE-grade primitives the formation pipeline can ratify, then expand the prerequisite DAG outward.

---

## Why order matters in CORE specifically

CORE is not a transformer absorbing a corpus. Three structural reasons force a strict ordering:

1. **`formation/ratify.py` G3** checks that every relation's `head` and `tail` concepts already exist as mastered or in-scope predecessors. Teach a triple whose endpoints aren't anchored and the gate hard-fails.
2. **`formation/index.py::MasteredCoursesIndex`** is built specifically so the next course's P3 (prerequisites) can read prior mastery. The system is curriculum-DAG-aware by construction; there is nowhere to hide an out-of-order triple.
3. **CGA recall is exact algebraic distance**, not a fuzzy embedding. A concept's position in the manifold is determined by the relations it participates in. Teaching `gravity ENTAILS mass` before `mass` and `gravity` are seeded produces an under-constrained point — the equivalent of writing equations with undefined variables.

A sampling architecture absorbs corpora regardless of order because the loss surface averages everything out. CORE has no loss surface. Order is part of the construction.

---

## The Five-Layer Ordering Rule

Always teach in this order, both globally and re-applied within every new domain:

1. **Identity axes and refusal probes.** Seeded first so identity is load-bearing before any content lands. As of [ADR-0027](decisions/ADR-0027-identity-packs.md) the runtime identity manifold is loaded from a swappable pack at `packs/identity/<pack_id>.json`; the ship default is `default_general_v1`. The `formation/templates/identity_anchor.py` template ratifies new identity packs through the standard formation gates. Canned override probes live in `formation/templates/_common.py::IDENTITY_OVERRIDE_PROBES`. Reference: [`identity_packs.md`](identity_packs.md). Adversarial probes must be defined before the concepts they protect.

2. **Atomic definitions.** Concepts with no internal structure — `is_a`, `kind_of`, `instance_of` only. These are the leaf nodes of the prerequisite DAG. No relation in a step-2 course references a concept defined later in the same course.

3. **Binary relations between defined concepts.** `entails`, `composes`, `contrasts`, `causes`, `precedes`, etc. — exactly the 17 predicates currently in the `en_core_cognition_v1` pack, applied only to concepts ratified in step 2.

4. **Composed relations.** Chains that reuse step-3 predicates (`A causes B AND B entails C ⇒ A licenses C`). These exercise `compose_relations` and the realizer's chain-handling — the work that lifted the discourse_paragraph lane from 68.8% → 100%.

5. **Domain expansion.** Pick *one* commercial domain and run the full 1→4 progression *inside* that domain before opening a second domain. Cross-domain triples come last and only after both domains have ratified their own internal DAG.

The failure mode this rule prevents: a triple lands whose `tail` concept is "scheduled for next week" — `ratify.py` G3 fails, the course is rejected, and you've wasted the LLM mining cost on a course that can't be promoted.

---

## What "elementary → college" gets right and wrong

**Right:** Build simple before composed. Anchor before extend. Teach `parent_of` before `grandparent_of`, then `ancestor_of`. Teach `red` and `crimson` before `red is_a color and crimson is_a red`.

**Wrong:** Don't import a K–12 ELA corpus. Most of that material is *generated content* (essays, stories, vocabulary lists) — the proposition graphs are mostly implicit, the relations are mostly stylistic, and the ratification gates will reject the bulk of it. CORE doesn't need stories; it needs ratified relations. A 200-triple curated kinship lane gets you further than 200,000 lines of children's literature.

The right "elementary" for CORE is the smallest closed set of primitives that exercises every gate end-to-end. That's the kinship + color + spatial + uncertainty + modal mix already prototyped in `evals/identity_divergence/curriculum/teaching.jsonl`.

---

## Where the curriculum platform lives today

| Artifact | Path | Role |
|---|---|---|
| Shared 93-event teaching corpus | `evals/identity_divergence/curriculum/teaching.jsonl` | Reference curriculum for identity-divergence lane |
| Curriculum generator | `scripts/generate_identity_curriculum.py` | Produces teaching events across kinship / color / spatial / logical / uncertainty / modal domains |
| Axis profiles | `evals/identity_divergence/axes/{axis_a,axis_b}.yaml` | Precision-first vs Generosity-first identity profiles |
| Lane contract | `evals/identity_divergence/contract.md` | What the lane measures, scoring rubric, pass thresholds |
| Lane runner | `evals/identity_divergence/runner.py` | Deterministic scorer |
| First course template | `formation/templates/definition.py` | "Every relation = definitional edge" Course YAML template |
| Pack-template artifact | `packs/common/anchors/trilingual-anchor-template.json` | Trilingual anchor template (separate concern from formation/templates/) |

**Known gap (as of 2026-05-17):** the identity-divergence curriculum predates the formation pipeline. Its triples currently flow through `runner.py`, not through `Forge → Compose → Ratify → Promote`. Routing existing curriculum events through the formation gates is a closing item — see [`formation_pipeline_plan.md`](formation_pipeline_plan.md).

---

## Decision rule for "what to teach next"

Before adding any course to the queue, answer:

1. Are all `head` and `tail` concepts in this course already in `MasteredCoursesIndex` or earlier in this batch?
2. Does the course's template type exist? (Today: only `definition`. Composed-relation, procedural, falsification, and identity-anchor templates are not yet implemented.)
3. Is at least one identity-override probe present?
4. Would `ratify.py`'s six gates (G1–G6) succeed against this material?

If any answer is no, the course is out of order. Move it later in the queue, or add the missing prerequisite course first.
