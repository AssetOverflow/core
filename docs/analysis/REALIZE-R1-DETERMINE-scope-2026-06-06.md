# REALIZE R1 + DETERMINE (Step 4) — scope, verified against the substrate

**Date:** 2026-06-06 · **Predecessor:** `REALIZE-scope-2026-06-06.md` (R0, #589/#590 merged at `16ba2771`).

This scopes the arc the goal names: R1 (relation-space recall, span-free
idempotency, the binding_graph/arithmetic realize path), the OOV-grounding
substrate question, and DETERMINE (Step 4). Every claim below was checked
against the merged `origin/main` source and, where noted, against an empirical
in-tree run (not a sandbox trace).

---

## 0. The unifying finding — the field versor is not an injective key for realized knowledge

R0 stored a realized fact as `(versor, metadata)` where
`versor = probe_ingest([subject_token]).F`. That conflates two distinct keys:

1. **Field placement** (the versor) — *associative*: "what is near this in
   concept space." Good for resonance, bad for identity.
2. **Structural identity** (`content_hash` / `structure_canonical` /
   `entity_names` / `relation_predicate`) — *exact, injective, reboot-stable by
   construction* (sha256 + canonical strings). This is what makes facts
   distinct and recallable-as-themselves.

The field versor collides on at least **three** axes (all verified):

- **Same subject, different relation.** "Truth is a concept." and "Truth is
  beautiful." both embed `probe_ingest(["truth"])` → the **same** versor. On
  recall both score `inf` (exact self-match) → indistinguishable. *(R0's
  acknowledged recall-collision.)*
- **Different OOV entities → one versor.** Empirically (in-tree, separate
  processes, `PYTHONHASHSEED` ∈ {0,1,random}): `zelophehad`,
  `photosynthesis`, `unbridgeable` — three unrelated words — all ground to the
  **byte-identical** versor (`ἀποκρίνομαι`'s root-versor). Root cause: the
  mounted morphology has **20 entries** (Greek/Hebrew cognition roots), so every
  arbitrary English token falls through `_best_decomposition`'s affinity
  fallback (`ingest/gate.py`) and collapses onto whichever root wins the tie.
- **(In-vocab is injective per-subject** but still collides per-relation, axis 1.)

**The fix that unifies R1-recall and OOV:** recall realized knowledge by its
**structural key** (exact metadata match), not solely by the field metric. The
field versor stays as deterministic associative placement. Structural recall is
**exact and deterministic** — it adds no cosine / HNSW / ANN, so it honors the
CLAUDE.md exact-recall invariant. `vault/store.py` is untouched (it stays a
forbidden-normalization site); structural recall is a read-only scan over
realized metadata, layered in `generate/realize/`.

## 1. OOV-grounding: the prior claim is refuted — it is deterministic, not non-deterministic

R0's recorded finding ("OOV grounding is NON-deterministic across reboots") is
**wrong** and is corrected here. Evidence (`/tmp/oov_proc.py`, faithful in-tree,
`no_load_state`):

- `probe_ingest([oov]).F` is **byte-identical across separate processes** and
  across `PYTHONHASHSEED` ∈ {0, 1, random}. In-vocab (`truth`) and OOV (`rhea`,
  `zelophehad`, …) are all deterministic.
- The latent hazard that *could* cause non-determinism — `_DECOMPOSITION_CACHE`
  keyed by `id(vocab)` (an `id()`-reuse-under-GC hazard) — is benign for
  identical-config runtimes (the cached value is a decomposition *string*; the
  versor is recomputed from the current vocab's roots, which are pack-identical).

So the real blocker for "accept arbitrary entities" is **non-injectivity**, not
non-determinism. And non-injectivity is **tolerable once recall is structural**:
distinct OOV facts stay distinct by `content_hash` even when they field-collide.
The honest, documented limit: *field-metric / associative recall* of OOV-named
facts is degenerate until the morphology substrate (or a content-addressed
entity identity) improves — but *structural* recall and reboot-stable storage
are exact today.

**Correction (from design-review): what actually carries reboot-stability.** The
versor placement is `probe_ingest([token])`, which `realize.py` itself documents
as composing with the *current session state* — so it is deterministic *given
the session state*, NOT a pure function of the subject, and NOT guaranteed to
re-derive identically in a fresh session at a different turn. Reboot-stability of
an already-realized fact rests on **Shape B+ snapshot** persisting the exact
versor *bytes* (`vault.to_dict`/`from_dict`, no reprojection on load), restored
bit-exactly — NOT on re-deriving the same versor. The cross-process determinism
finding above is a *bonus* (re-telling the same fact in a fresh, empty session
lands at the same place), not the load-bearing guarantee. Correctness of recall
rests on the **structural key**, not the versor, in every slice below.

## 2. The slices (dependency-ordered, each a small load-bearing PR; wrong=0 + versor_condition<1e-6 + exact recall preserved throughout)

### R1a — Structural recall (the keystone)

`generate/realize/recall.py::recall_realized(ctx, *, subject=None,
predicate=None, content_hash=None, structure_kind=None) -> tuple[RealizedRecord, ...]`.
A read-only, exact scan over `ctx.vault._metadata` entries with
`kind == "realized"`, matching the given structural predicates (subject ∈
`entity_names`, `relation_predicate ==`, `content_hash ==`, `structure_kind ==`),
returned in deterministic (vault-index) order. No metric, no vault mutation.

- **Falsifiable test:** realize two facts about "truth" with different
  predicates → `recall_realized(subject="truth")` returns **both** distinctly;
  `recall_realized(predicate=P1)` returns only the first. Assert that the raw
  `vault.recall(probe_ingest(["truth"]).F)` collides (both `inf`) — proving
  structural recall is *strictly necessary*, not decoration.

### R1b — Span-free idempotency

`content_hash = sha256_of(graph.to_canonical_string())` is **span-inclusive**
(`MeaningGraph.to_canonical_string()` emits `span={source_id}[start:end]` per
entity/relation — verified). So the same fact at a different offset does **not**
dedup. Add a span-free `structure_key` = sha256 of an ordered, span-free
projection: `(predicate, negated, tuple(argument-entity-names in arg order),
sorted other-entity-names)`. Dedup on `structure_key`; retain `content_hash`
(span-inclusive) for provenance.

- **Falsifiable test:** "Truth is a concept." at offset 0 and the same relation
  inside a longer carrier sentence (different span) → second realize returns
  `created=False`; vault length stays 1. A genuinely different fact (different
  predicate/args) is **not** collapsed.

### R1c — binding_graph / arithmetic realize

Extend `realize_comprehension` (or a sibling `realize_quantitative`) to accept a
`QuantComprehension` (`generate/quantitative_comprehension.py`):
`structure_kind = "binding_graph"`, `structure_canonical =
binding_graph.to_canonical_string()`, versor = deterministic placement
(`probe_ingest` of the asked/first entity token; OOV-safe per §1), recalled
**structurally**. Eligibility: a fact-bearing `QuantComprehension` (≥1
`BoundFact`); a pure query realizes nothing (it is recall, not intake), a
`Refusal` realizes nothing.

- **Falsifiable test:** `comprehend_quantitative("alice has 3 coins.")` →
  realize → `recall_realized(structure_kind="binding_graph", subject="alice")`
  returns the record; snapshot→reboot→recall is byte-exact; SPECULATIVE.

### OOV — lift the in-vocab gate (enabled by R1a)

Remove R0's `index_of` in-vocab gate; allow OOV subjects. Storage + structural
recall are exact and reboot-stable (§1). Add a cross-process determinism
guarantee test. Document the field-metric-collision limit in the record/docs
(honest, not papered over). Correct the refuted memory claim.

### D0 — DETERMINE (Step 4): reason over realized structure → assert / refuse

`generate/determine/determine.py::determine(question: Comprehension | Refusal,
ctx) -> Determined(answer, basis, predicate, grounds) | Undetermined(reason)`.
Take a *query-bearing* comprehension; structurally recall (R1a) the realized
facts that could ground it; run a **named entailment predicate** over the
realized structure — for R0/R1 relations, **direct structural entailment** (the
asked relation is exactly a realized relation; transitive subsumption is a later
extension). **Assert** the answer iff the asked relation is structurally
entailed by a realized fact; **refuse** (`Undetermined`) otherwise.

**Honesty correction (from design-review): as-told, never "verified".** Every
realizable record is **SPECULATIVE**, and `ADMISSIBLE_AS_EVIDENCE = {COHERENT}`
(teaching/epistemic.py) — so a realized record is admissible only as a
*candidate*, never as *evidence*. D0 therefore carries the grounding's epistemic
**basis** forward: a determination grounded in SPECULATIVE records is
`Determined(answer=…, basis="as_told", …)` — "based on what I was told
(unverified)" — and **never** a "verified" claim. COHERENT promotion is
out-of-scope, so D0 produces only `as_told` or `Undetermined` (honest and
non-vacuous). No estimation. No corpus mutation (teaching stays HITL
proposal-only). wrong=0: never assert an un-entailed claim, never upgrade
SPECULATIVE to verified.

- **Falsifiable tests (must bite):** realize "Truth is a concept."; ask "Is
  Truth a concept?" → `Determined(answer=True, basis="as_told", predicate=
  "member", grounds=[that record])`. **Present-but-non-entailing:** ask "Is
  Truth a number?" (a record about *truth* exists, but `member(truth, number)`
  is NOT realized) → `Undetermined("not_entailed")`. Ask before realizing →
  `Undetermined("ungrounded")`. A `Refusal` question → `Undetermined`. **Mutation
  check:** delete the grounding record → `Determined` flips to `Undetermined`
  (proves the verdict is entailment, not "a record about the subject exists").

## 3. Sequencing, hazards, invariants

Order: **R1a → R1b → R1c → OOV → D0** (R1a unblocks recall for R1c/OOV/D0; R1b is
independent/small). Each slice:

- preserves **wrong=0** (every ineligible/ungrounded input realizes/determines
  NOTHING — typed `NotRealized` / `Undetermined`, never a coerced write/assert);
- preserves **versor_condition < 1e-6** (no new embedder; `probe_ingest` only,
  closure stays `algebra/versor.py`'s);
- preserves **exact CGA recall** (structural recall is exact metadata match, not
  a metric approximation; `vault/store.py` untouched);
- keeps **EpistemicStatus honesty** (SPECULATIVE only; COHERENT is never a
  default — promotion stays out of scope, a later slice);
- adds no **parallel learning path** (DETERMINE asserts/refuses; it does not
  ratify or mutate corpus — teaching stays HITL proposal-only);
- holds **INV-21** (only allowlisted writers call `VaultStore.store`; R1c's
  writer is allowlisted) and does not regress the capability-index anchor
  (breadth 8, wrong 0, `50e0675b`).

## 3.5 Verified adjustments (adversarial design-review, 2026-06-06)

Six skeptic agents tried to refute each slice against the merged source +
CLAUDE.md. All six returned **adjust** (none blocked, none rubber-stamped).
Resolutions, each re-grounded in source:

- **R1a — public accessor, not `_metadata`.** `realize.py` is the *only*
  external reader of the private `vault._metadata` (the R0 "established pattern"
  comment is false). → Add a read-only `VaultStore.iter_metadata()` yielding
  `(index, metadata)` in deque order (non-mutating, not a normalization site);
  `recall_realized` and the R0 dedup loop consume it; delete the false comment.
  `vault_index` is the **live** deque position (authoritative in the unbounded
  session tier; provenance-only under bounded eviction — pinned, not left
  ambiguous). *Invariant risk: none — exact metadata equality is the opposite of
  approximate recall.*
- **R1b — entity *identity*, plus a wrong=0 refusal.** `Entity.name` is
  non-unique in the model (only `entity_id` is enforced unique; today the reader
  sets `entity_id == name`, reader.py:364, so the hazard is latent, not live).
  A name-keyed `structure_key` could collapse a converse/homonym fact →
  drops a distinct fact (wrong=0). → `structure_key` keys on the ordered
  argument **entity-ids** (`== name` today, span-free), AND realize **refuses**
  a graph with duplicate entity names: `NotRealized("ambiguous_entity_names")`
  — the defense-in-depth guard CLAUDE.md asks for *now*, before a future reader
  makes it live.
- **R1c — honest versor, real guard.** The versor rule is restated per §1
  (deterministic-given-session-state; the sumquery `"total"` is a synthesized
  OOV name with maximal collision — documented like §0, since **structural
  recall carries correctness**). The "fact-bearing" gate is vacuous at the
  realize layer (every `QuantComprehension` has ≥1 fact + one query by
  construction); the real wrong=0 filter is `isinstance(comp, Refusal) →
  NotRealized` (and `comprehend_quantitative` already refuses factless input
  upstream). *No wrong=0 admission breach: every equation passed
  `check_admissibility`; a `Refusal` short-circuits.*
- **OOV — correct the side-effect contract.** `probe_ingest` of an OOV subject
  is **not** side-effect-free: it mutates the shared vocab via
  `insert_transient` (gate.py:252). → Correct realize.py's "side-effect-free"
  comment; document the transient as session-scoped, **excluded from the
  snapshot** (snapshot serializes vault+state, *not* vocab — verified
  session/context.py:345), and re-derived on reboot. The determinism test bites
  on two axes: cross-process byte-identity AND intra-session path-independence
  (probe equals cold-reground whether or not grounded earlier). *Invariant risk:
  none — a non-versor construction raises and is caught → `NotRealized`.*
- **D0 — as-told, never verified** (see the corrected design above).
- **Cross-cutting — anchor partition proven.** The capability-index eval imports
  **no** `vault` / `ChatRuntime` / `realize` / `SessionContext` / `probe_ingest`
  (grep of `evals/capability_index/` is empty) — it scores comprehension against
  oracles and never realizes or recalls from a session vault. So realize-writes
  **cannot** regress the anchor (50e0675b) — partition by construction, not
  assertion. Runtime metric-recall pollution (OOV facts clustering at the
  root-versor) is a separate, bounded note: realized entries are SPECULATIVE +
  `kind`-tagged, so the evidence path (`min_status=COHERENT`) already excludes
  them; default (candidate) recall includes them as the session's own memory by
  design. Sequencing R1a→R1b→R1c→OOV→D0 is confirmed sound.

## 4. Explicitly out of scope (later)

COHERENT promotion (contradiction-free coherence judgment), teaching-loop
proposal generation from realized facts, trace-folding, content-addressed
entity identity / morphology-substrate expansion (the deeper OOV-injectivity
fix), LEARNED ESTIMATION (Step 6), the always-on process (L10).
