# Scope: REALIZE — comprehended/told structure → the held self (Step 3)

**Status:** scoped 2026-06-06 (reconnaissance + design + adversarial verification).
Ready to build slice **R0**. One focused PR.

REALIZE is roadmap **Step 3** (`MEASURE ✓ → COMPREHEND → REALIZE → DETERMINE →
LOOP`). COMPREHEND now reads five reasoning domains from prose, but every read is an
**eval artifact** — the comprehended structure is scored and thrown away. REALIZE is
the boundary that turns reading into **accumulating living knowledge**: integrate a
comprehended/told structure into the held self with an `EpistemicStatus`, persisted
across reboot, recalled exactly. Intake ("being told") lands here.

This scope is grounded in a reconnaissance of the actual substrate (vault,
`EpistemicStatus`, Shape B+ persistence, teaching/intake, comprehension output,
determinism/replay) and **adversarially verified** against that substrate on three
lenses (API-reality / invariants+wrong=0 / determinism+boundary). Findings below
fold in the confirmed refinements.

## The central recon finding: REALIZE is a vault entry, not a new store

A realized record is **a structured vault entry `(versor, metadata)`** — so it
inherits, for free:

- **exact recall** via `cga_inner` (no ANN/cosine — the only metric in CORE),
- **`EpistemicStatus` stamping + admission filtering** (`teaching/epistemic.py`
  *already exists*: `COHERENT | CONTESTED | SPECULATIVE | FALSIFIED`),
- **bit-exact Shape B+ persistence** (`VaultStore.to_dict/from_dict` inside
  `SessionContext.snapshot/restore`, no reprojection on load).

A *new* `RealizedKnowledgeStore` was rejected: it would duplicate persistence and
risk a parallel recall path drifting toward forbidden approximate search. Writing
into the teaching corpus directly was rejected: that is a parallel learning path
into ratified-adjacent state (forbidden). **Reuse the vault.**

## The realized-knowledge record

A vault entry whose metadata is all JSON-primitive (so `to_dict` stays JSON-safe):

| field | value |
|---|---|
| `versor` | 32-dim Cl(4,1) null vector — the **subject field point**, derived only via the existing `session/context.py` embedding path (no new embedder) |
| `kind` | `'realized'` (new, non-colliding; existing namespace is `role ∈ {user,assistant}`, `kind ∈ {proposition}`) |
| `meaning_graph_canonical` | `MeaningGraph.to_canonical_string()` — the deterministic, reconstructable **source of truth** |
| `relation_predicate`, `entity_names` | denormalized recall keys |
| `epistemic_status` | `str`, default **`speculative`**; `epistemic_state` derived. `COHERENT` only via the explicit contradiction-free coherence judgment — **never** a default |
| `source_span` | provenance: `MeaningSpan.to_canonical_string()` → `'source_id[start:end]'` (the audit chain to the NL origin). *Note: `MeaningSpan`, not `SourceSpanLink` — the latter is the binding-graph's span type* |
| `content_hash` | `sha256` over `meaning_graph.to_canonical_string()` via existing canonical-JSON hashing (floats forbidden) |
| `replay_hash` | `sha256` over canonical(`content_hash` + `source_span` + `epistemic_status`) — the determinism anchor |
| `tier` | `'session'` (episodic, vault-resident, immediate). `reviewed`/`ratified` tiers are **not** written by REALIZE — they go through `teaching/*` proposals |
| `proposition` | optional `Proposition` (tagged `__core_proposition__`) when the graph maps to the existing frame — round-trips via its verified `to_dict/from_dict` |

`meaning_graph_canonical` (a plain string) is the **durable** source-of-truth so a
record stays reconstructable even if the typed `Proposition`/`MeaningGraph` schema
evolves (the `proposition` tag is optional enrichment).

## Contract: TOLD → REALIZE → RECALL → SURVIVES-REBOOT

1. **TOLD.** Text arrives. `comprehend(text, source_id)` → `Comprehension(meaning_graph, queries)` or `Refusal`. **A `Refusal` realizes nothing** (wrong=0: refuse, never fabricate). Only a declarative `MeaningGraph` with ≥1 non-query `Relation` is eligible; queries are recall, not intake.
2. **REALIZE.** For the declarative structure: (a) derive the subject field point via the existing session embedding path; (b) compute `content_hash`/`replay_hash` via existing canonical-JSON SHA-256 primitives; (c) assemble the metadata above; (d) `vault.store(F, metadata, epistemic_status=SPECULATIVE)`. This is the eval-artifact → living-knowledge boundary.
3. **RECALL.** A later query versor (embedded via the **same** path) scores against the vault by exact `cga_inner` (`recall(query, top_k, min_status=)`). Exact self-match promotes via `_exact_index`. `min_status=COHERENT` admits only coherence-judged records; default recall surfaces SPECULATIVE as candidate-only. No ANN, no cosine.
4. **SURVIVES-REBOOT.** Under `persist_session_state=True`, the vault is captured by `SessionContext.snapshot() → save_session_state()` (before `save_manifest`, atomic) and restored bit-exactly by `from_dict()` with **no reprojection**. The same query recalls the identical record at the identical score.

## Composition (verified seams)

| subsystem | how REALIZE composes it |
|---|---|
| `generate/meaning_graph/reader.py::comprehend` | INPUT. `Comprehension` ingested; `Refusal` is a no-op. MeaningGraph is field-neutral pure data (INV-26/INV-28), carries `MeaningSpan` provenance + `to_canonical_string`. The arithmetic `binding_graph` reader is a **later slice** (see forks). |
| `session/context.py::_field_from_tokens` | EMBEDDING BRIDGE. The sanctioned, closure-preserving path already used by `commit_ingest` to store a SPECULATIVE user point. **Signature: `field_state, _ = ctx._field_from_tokens(tokens, resolve_referents=…)`; take `field_state.F`.** No new embedder (keeps `versor_condition<1e-6` by construction; closure stays `algebra/versor.py`'s job). |
| `vault/store.py::store/recall` | STORAGE + RECALL. Adds metadata keys only — **stays a forbidden normalization site** (no repair/projection/reprojection). |
| `teaching/epistemic.py` | HONESTY GATE. Default SPECULATIVE; `ADMISSIBLE_AS_EVIDENCE={COHERENT}` and `_status_admits` unchanged. REALIZE writes status, never weakens admission. |
| `teaching/* + chat/runtime.py::idle_tick` | TOLD/PROPOSAL path. Anything that would mutate a ratified pack/corpus is a **proposal** through the existing reviewed loop (proposal-only, HITL). REALIZE adds **no parallel learning path**. |
| `session/context.py::snapshot/restore` + `core/array_codec.py` | SURVIVES-REBOOT. Realized records ride the existing bit-exact vault snapshot — no new persistence file. |
| `core/cognition/trace.py` + `formation/hashing.py` | REPLAY. Hashes via existing canonical-JSON SHA-256. Folding a realize event into `compute_trace_hash` **would be a new parameter** (mirroring how `teaching_epistemic_status` is folded) — **out of scope for R0**, deferred to the in-turn-vs-out-of-turn open question. |

## Obligations (non-negotiable)

- **wrong=0 (structural):** a `Refusal` realizes nothing; only a MeaningGraph with ≥1 non-query Relation is eligible. Never coerce un-comprehended input into a record.
- **provenance:** every record carries `source_span` (`MeaningSpan` canonical) **and** `meaning_graph_canonical`. No record without a pointer back to the NL origin.
- **EpistemicStatus honesty:** default SPECULATIVE on every realize. `COHERENT` only via explicit contradiction-free coherence judgment — never from source authority (ADR-0021), recency, or a designed-in confidence default.
- **no forbidden normalization:** metadata keys only; no drift repair / grade projection / reprojection in `vault/store.py`, `generate/stream.py`, `field/propagate.py`, or logging. `to_dict/from_dict` stay pure serialization.
- **no parallel learning path:** session-tier vault records are immediate/local (allowed). Pack/corpus changes are proposals through `teaching/*` + `idle_tick` (proposal-only). No second writer, no embedding store, no opaque ratifier.
- **determinism/replay:** see honest framing below.

## Determinism — the honest framing (adversarially corrected)

The naïve claim "identical input → identical vault placement and recall score" is
**too strong** and was corrected in review:

- **`content_hash` / `replay_hash` are input-pure** (a function of the canonical
  string only) — these are byte-identical across reboots and re-tells.
- **The versor and the recall score are session-state-dependent**:
  `_field_from_tokens` composes against `self.state`, so the *same fact realized at a
  different turn is not vault-identical*. Recall-score equality across reboot holds
  because `restore()` rebuilds `self.state` bit-exactly — it is a consequence of
  **bit-exact state restore**, not of input identity.

The contract is therefore: *realize a fact, snapshot, restore, embed the query at
the restored state → byte-identical `content_hash` and byte-identical recall score.*
The gate (below) embeds the query at the same restored state and additionally guards
the history-dependence.

## Slice R0 (the first build)

One thin module — `generate/realize/realize.py` — with one function:

```
realize_comprehension(comprehension: Comprehension, ctx: SessionContext) -> RealizedRecord | None
```

It: (1) returns `None` on `Refusal` or a graph with no realizable declarative
Relation; (2) for the first declarative Relation, derives the subject field point via
`ctx._field_from_tokens(entity_tokens, resolve_referents=…)` taking `field_state.F`
— **wrapping it so a `KeyError`/empty-decomposition (OOV grounding failure) becomes a
clean `None` no-op, never a crashed turn** (adversarial WRONG-finding fix);
(3) computes `content_hash` + `replay_hash` via existing hashing primitives over
`meaning_graph.to_canonical_string()` + `source_span`; (4) `ctx.vault.store(F,
metadata{kind:'realized', meaning_graph_canonical, relation_predicate, entity_names,
source_span, content_hash, replay_hash, tier:'session'},
epistemic_status=SPECULATIVE)`.

No COHERENT promotion, no teaching-loop wiring, no binding-graph path, no recall API
change. Net new surface: one module + its tests. Persistence/recall/determinism are
inherited from substrate already present.

**Scope R0 to in-vocab entities** (or add the OOV arm to the gate) until OOV-entity
grounding determinism is verified across fresh runtime+vocab instances.

## Exit gate (falsifiable — fails if REALIZE is decoration)

With `persist_session_state=True`:
1. comprehend a declarative statement S; `realize_comprehension` it into a fresh `SessionContext`; `snapshot() → save_session_state()`.
2. construct a **new** `SessionContext`; `restore()` from that state (simulated reboot).
3. comprehend a query Q over the same entity/relation; embed via the same path **against the restored state**; `recall()`.

**ASSERT:** the realized record is in `top_k`; its `metadata['content_hash']` equals
the pre-reboot value byte-for-byte; the recall score equals the pre-reboot score
byte-for-byte (exact f32); `metadata['epistemic_status']=='speculative'`; and the
restored versor satisfies `versor_condition<1e-6`.

The gate **fails** (proving it is not vacuous) under each of:
- a `Refusal` input silently producing a record;
- a `COHERENT` default;
- a missing `source_span`;
- any reprojection/normalization on load mutating the versor;
- *(adversarial-sharpened, replacing the vacuous "decimal-float" arm)*
  **(a)** embedding the recall query under a **different** session state and the score
  being silently treated as a match (guards `_field_from_tokens` history-dependence);
  **(b)** a determinism re-run: realizing the **same** fact twice **in the same
  state** must yield identical `content_hash` **and** identical versor bytes (guards
  idempotency + placement determinism).

Run via a dedicated CLI lane (`core test` pattern) plus the determinism re-run.

## Design forks (recommendations)

1. **Ingest in slice 1?** → **MeaningGraph only.** `comprehend_quantitative`/binding-graph has no runtime entry point yet; a unified adapter is premature.
2. **New store or vault entry?** → **Vault entry** (inherits exact recall + Shape B+; a new store risks a parallel/approximate recall path).
3. **Field point for a MeaningGraph (it carries no versor)?** → **Reuse `_field_from_tokens`** (sanctioned, closure-preserving; a hash-pseudo-versor breaks exact CGA recall; a new embedder is a new closure surface).
4. **When does a record become COHERENT?** → **Always SPECULATIVE in slice 1.** Promotion only via the contradiction-free coherence judgment later — never source-trust (ADR-0021) or recall-count (a confidence default).
5. **"Told something that should change a ratified pack"?** → **Vault record + a `teaching/*` proposal** (proposal-only, HITL). REALIZE never writes packs; `idle_tick` proposes, never ratifies.

## Risks (carry into the build)

- **Subject-versor recall collision:** storing the subject point means two facts about one entity collide on recall ordering (the existing Proposition-storage gotcha — storage is subject-keyed, recall finds subject-space neighbors). Mitigation: keep `meaning_graph_canonical` in metadata and disambiguate post-recall by `content_hash`; relation-space recall is a later slice. Document, don't silently rely on it.
- **Vault growth / cost:** each fact is a vault entry; snapshot is O(N + V·32·4) per turn, eviction rebuilds `_exact_index` O(N). Mitigation: `max_entries` bound + accept the documented O(turns) cost (incremental persistence is deferred substrate).
- **Honesty drift toward a confidence default:** the strongest temptation is COHERENT-when-source-reliable or COHERENT-after-N-recalls — both forbidden. The gate asserts `'speculative'` and must fail on any COHERENT default.
- **Comprehension coverage is the real wall:** the template reader refuses most real told-statements, so REALIZE realizes little at first. This is honest (wrong=0); do **not** "fix" thin coverage by loosening refusal.
- **Schema-evolution on reboot:** keep `meaning_graph_canonical` (plain string) as the durable source-of-truth so records reconstruct even if typed objects evolve.

## Open questions (resolve before/within the build)

- **Eligibility predicate:** exactly which MeaningGraph shapes are durable declarative facts vs queries vs refuse (negated relations? multi-arg? cyclic general relations, which MeaningGraph permits)? Needs a precise, testable rule before R0 to avoid realizing junk.
- **Relation-space recall:** does REALIZE need relation/object field points too (Proposition already carries them)? Slice-2 decision: multiple points per fact vs post-filter by `content_hash`.
- **SPECULATIVE→COHERENT wiring:** is the trigger the existing `teaching/store.py::_detect_contradiction` or a new geometric metric (`cga_inner ≥ τ_admit ∧ no reviewed R with cga_inner ≤ τ_reject`) flagged as an ADR-0021 v2 candidate?
- **Idempotency / re-told facts:** same fact twice → same `content_hash`. No-op dedup (via `_exact_index`/`content_hash`) or a second entry? Affects recall ordering + vault growth.
- **Energy-class on realize:** does a record need an initial `EnergyProfile`, or is omitting energy metadata (`policy.decide(None) → 'missing_energy_profile'`) the honest session-tier default?
- **Trace-fold scope:** fold every realize `replay_hash` into the turn's `compute_trace_hash` (like `teaching_epistemic_status`), or only when realize occurs inside `CognitiveTurnPipeline.run()`? Out-of-turn (bulk) intake needs its own determinism anchor.

## Adversarial verification summary

Three critics checked this scope against the real substrate. The design was confirmed
**invariant-faithful and grounded** (every load-bearing API exists with the claimed
behavior; wrong=0, exact recall, no forbidden normalization, proposal-only learning,
provenance all preserved). Folded-in corrections: (1) **R0 must catch embedding
`KeyError`/empty-decomposition → no-op** and verify/scope OOV-entity grounding
determinism *(the one WRONG finding)*; (2) the determinism contract is **state-restore
based, not input-pure** (versor/score are session-state-dependent); (3) corrected API
details (`_field_from_tokens` returns `(field_state, _)`; provenance is `MeaningSpan`
not `SourceSpanLink`; namespace is `role∈{user,assistant}`/`kind∈{proposition}`;
trace-fold is new work, not "today"); (4) **sharpened gate arms** (history-dependence
+ idempotency/placement re-run replace the vacuous decimal-float arm).
