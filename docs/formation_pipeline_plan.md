# Formation Pipeline — Implementation Plan

Status: **DRAFT — awaiting confirmation**
Author: planner pass, 2026-05-16
Companion doc: `docs/decisions/ADR-0021-epistemic-grade-policy.md`,
`docs/runtime_contracts.md`

## 0. Purpose

A content-addressed, trust-bounded data foundry that turns raw subject material
into Ratified, replay-proof versor relations through
**Mine → Smelt → Forge → Compose → Compile → Run → Ratify → Promote**, on top
of CORE's existing `CognitiveTurnPipeline`. LLMs propose, the Forge disposes,
CORE composes.

The pipeline reduces to one promise: **untrusted text becomes
content-addressed, identity-vetted, replay-proof versor relations — or it does
not enter the manifold at all.**

---

## 1. Tweaks and corrections to the proposed design

These are adjustments I am applying to the design before phase planning. Each
is a small change; none alters the architecture. Confirm or push back per item.

1. **Module name `compile.py` → `compiler.py`.** `compile` shadows a Python
   builtin and breaks `from formation import compile` in subtle ways. Rename
   the file and class to `Compiler` / `compiler.py`. The CLI verb stays
   `core formation compile`.
2. **Top-level package, not nested under `core/`.** Sibling to `teaching/`,
   `generate/`, `ingest/`, `vault/` — i.e. `/Users/kaizenpro/Projects/core/formation/`.
   Matches the existing layout and keeps import paths short.
3. **`EpistemicStatus` reuse, not parallel enum.** The design says "SPECULATIVE
   → COHERENT". `teaching/epistemic.EpistemicStatus` already defines both. Use
   it directly. Do not introduce a separate `FormationStatus`.
4. **`UNVERIFIED` is not in `EpistemicStatus`.** The design references
   `UNVERIFIED → SPECULATIVE` graduation. Map this onto a Forge-local
   `CandidateState` enum (`PROPOSED`, `QUARANTINED`, `VALIDATED`) that exists
   **before** entering `EpistemicStatus`. Only `VALIDATED` candidates emerge
   with `epistemic_status = SPECULATIVE`. This keeps ADR-0021's enum closed.
5. **Cache directory `.formation/` → `.formation_cache/`.** Avoid collision
   with potential future runtime state dir; the `_cache` suffix signals
   deletability. Add to `.gitignore`.
6. **Deterministic JSON, not pickle.** Every artifact (`OreBundle`,
   `ValidatedTripleSet`, `CourseYAML`, `FormationPlan`, `MasteryReport`)
   serializes via `json.dumps(obj, sort_keys=True, separators=(",", ":"))`
   then SHA-256. No pickle anywhere — pickle defeats replay determinism and is
   a code-execution attack surface (per CLAUDE.md trust doctrine).
7. **YAML for the Course only; JSON for everything else.** Humans read the
   Course; machines read the rest. Drop YAML from the cache to remove a
   parsing-divergence vector.
8. **MasteryReport self-seal: SHA omits its own field.** Compute SHA over the
   report with `report_sha256 = ""`, then write the SHA in. Standard
   self-sealing convention; document it explicitly in the schema so verifiers
   know how to re-check.
9. **CLI: `compile` is internal.** Drop `core formation compile` from the
   public surface — it runs inside `core formation run`. Keeps the seven-verb
   shape from leaking to eight. Internal: `formation/compiler.py` still
   exists.
10. **Versor invariant: `< 1e-6`, not `≤ 1e-6`.** Match CLAUDE.md's
    non-negotiable threshold exactly. Hard halt on `>=`.
11. **No `formation/miner.py` LLM adapter in the MVP.** The LLM adapter is
    the highest-risk component (network, prompt injection, attribution). Build
    it last, behind a `--enable-llm-source` flag that is off by default.
12. **`MasteredCoursesIndex` lives under `vault/` or `packs/`?** Neither —
    put it at `formation/index.py` with a JSON file at
    `packs/mastered_courses.json`. Vault is exact-recall runtime; this is
    governance metadata.
13. **Promotion path goes through `teaching/review.py`.** Do not add a new
    pack-mutation path. The promote stage constructs a
    `ReviewedTeachingExample` per validated triple, stamped with the Mastery
    Report SHA, and submits it through the existing reviewed apply path.
    This preserves ADR-0021's "one mutation path" invariant.
14. **Trust boundary table belongs in `docs/runtime_contracts.md`.** Add a
    new "§Formation trust boundaries" section listing the six boundaries from
    the design. Update the contracts doc in the same PR as Phase 1.
15. **CLI subparser: `core formation` as new top-level verb.** Mirrors `core
    pack`, `core test`, `core eval` style.

---

## 2. Architectural restatement (post-tweaks)

```
formation/
├── __init__.py
├── course.py          # Frozen dataclasses for every artifact
├── hashing.py         # canonical JSON + SHA-256 helpers
├── cache.py           # .formation_cache/{subject}/{stage}/{input_sha}.json
├── candidate.py       # CandidateState enum, ConceptCandidate, RelationCandidate, CounterCandidate
├── forge.py           # TRUST BOUNDARY — produces ValidatedTripleSet
├── compose.py         # ValidatedTripleSet → CourseYAML (deterministic)
├── templates/
│   ├── __init__.py
│   ├── definition.py
│   ├── procedure.py
│   ├── system.py
│   ├── adversarial.py
│   └── identity_safe.py
├── compiler.py        # CourseYAML → FormationPlan
├── runner.py          # FormationPlan → list[CognitiveTurnResult]  (thin shim)
├── mastery.py         # MasteryReport dataclass + self-seal
├── ratify.py          # gate checks + emit MasteryReport
├── index.py           # MasteredCoursesIndex
├── promote.py         # MasteryReport → reviewed teaching apply
├── miner.py           # Stage 1, async (built LAST)
├── smelter.py         # Stage 2 (built LAST)
└── adapters/          # source adapters (built LAST)
    ├── arxiv.py
    ├── wikipedia.py
    ├── user_documents.py
    └── llm_ideation.py   # behind --enable-llm-source
```

CLI:
```
core formation new      <subject_id>
core formation mine     <subject_id>     # Stage 1
core formation smelt    <subject_id>     # Stage 2
core formation forge    <subject_id>     # Stage 3
core formation compose  <subject_id>     # Stage 4
core formation run      <subject_id>     # Stages 5–7
core formation promote  <report_sha>     # Stages 8–9
core formation autorun  <subject_id>     # 1→7, halts before promote
core formation status   <subject_id>     # show cache state per stage
```

Test suite alias: `core test --suite formation`.

---

## 3. Phase plan

Each phase ends with a CLI lane and tests green. **Build the gates first, the
velocity second.** Stages execute back-to-front: Forge → Ratify is hardened
before Mine → Smelt is even attempted.

### Phase 1 — Substrate and contracts (1 day)

**Goal:** dataclasses, hashing, cache, and the trust-boundary docs.

Deliverables:
- `formation/course.py` — frozen, slot-based dataclasses for every artifact
  (`SubjectSpec`, `OreBundle`, `ConceptCandidate`, `RelationCandidate`,
  `CounterCandidate`, `ValidatedTripleSet`, `CourseYAML`, `FormationPlan`,
  `MasteryReport`). Pure data, no behavior. Each carries a `schema_version`.
- `formation/hashing.py` — `canonical_json()`, `sha256_of()`, `self_seal()`.
- `formation/cache.py` — `.formation_cache/` read/write with
  `(subject_id, stage, input_sha)` keys. Path-traversal-safe.
- `formation/candidate.py` — `CandidateState` enum
  (`PROPOSED`/`QUARANTINED`/`VALIDATED`).
- `docs/runtime_contracts.md` — append "§Formation trust boundaries" with the
  six-boundary table.
- Tests: round-trip serialization, canonical-form stability, SHA stability
  across runs, cache-key sanitization.

Invariant proof: any two byte-identical inputs produce byte-identical SHAs;
any path-traversal pattern in `subject_id` is rejected at cache write.

CLI lane added: `core test --suite formation` (initially: just Phase 1
tests).

### Phase 2 — Forge: the trust boundary (2 days)

**Goal:** the only validator in the system. Accepts hand-curated triples;
emits a `ValidatedTripleSet`.

Deliverables:
- `formation/forge.py` with `Forge.validate(candidates) -> ValidatedTripleSet`.
- Validation rules in order:
  1. `teaching.relation_parse.parse_triple` must succeed (well-typed triple).
  2. Identity-axis collision screen — reject any triple whose head/tail
     matches identity-axis terms; cite `core/physics/identity.py`.
  3. Source allow-list check — `OreBundle.source_sha` must appear in
     `formation/allowlist.json` (initially: hand-curated short list).
  4. Pack collision check — reject duplicates against current language pack
     and `TeachingStore`.
  5. Cross-reference rule: a candidate graduates `PROPOSED → VALIDATED` iff
     it has ≥2 independent source SHAs OR exactly one source whose
     `authority_tier == "primary"` in the allowlist.
  6. LLM-sourced candidates require ≥2 corroborating non-LLM sources.
- `ValidatedTripleCache` — content-addressed by `(head, relation, tail)`,
  append-only JSON file at `.formation_cache/triple_cache.json`.
- Tests (TDD, per project rules):
  - Malformed triple → `RejectedCandidate("malformed")`.
  - Identity override → `RejectedCandidate("identity_axis_collision")`.
  - Path-traversal in source SHA → `RejectedCandidate("invalid_source")`.
  - Single LLM source → `PROPOSED`, never `VALIDATED`.
  - Two independent non-LLM sources → `VALIDATED`, status = SPECULATIVE.
  - Cache hit on identical triple → no re-validation cost.

Risk: HIGH. This is the only thing standing between untrusted text and the
manifold. Every rejection path needs a test.

### Phase 3 — Compose: deterministic Course YAML (1 day)

**Goal:** `ValidatedTripleSet + Template → CourseYAML`, byte-stable.

Deliverables:
- `formation/compose.py` with `compose(validated, template, spec) -> CourseYAML`.
- `formation/templates/definition.py` as the only initial template
  (simplest case). Topo-sort relations; deterministic concept ordering by
  `(canonical_term, source_sha)` lexicographic.
- Tests:
  - Same input → identical YAML bytes across two runs.
  - Reorder input list → identical YAML bytes (deterministic ordering).
  - YAML round-trips through `yaml.safe_load` → identical structure.
  - Course SHA stable across Python sessions.

### Phase 4 — Compiler + Runner: drive the existing pipeline (2 days)

**Goal:** thin shim, zero new operators. Drive `CognitiveTurnPipeline` from a
`FormationPlan`.

Deliverables:
- `formation/compiler.py` — `compile_course(course_yaml) -> FormationPlan`.
  Plan is a list of typed steps: `SeedConcept`, `IntroduceRelation`,
  `WalkStep`, `AdversarialProbe`, `ReplayAssertion`. Plan has its own SHA.
- `formation/runner.py` — `run_plan(plan, pipeline) -> list[CognitiveTurnResult]`.
  Hard-halts on `versor_condition >= 1e-6`. Streams telemetry events to
  stdout in JSON-lines when `--json` is passed.
- Tests:
  - Plan SHA stable for same course YAML.
  - Runner produces exactly N results for an N-step plan.
  - Synthetic plan that injects a high-versor state → runner halts; no
    silent continuation.
  - Runner does not call any pack-mutation API (introspection / mock
    assertion).

### Phase 5 — Ratify + Mastery (2 days)

**Goal:** gate checks → self-sealed `MasteryReport`.

Deliverables:
- `formation/mastery.py` — `MasteryReport` dataclass, self-seal helpers.
- `formation/ratify.py` — `ratify(results, prior_index) -> MasteryReport |
  RatificationFailure`. Gates:
  1. `replay_determinism == 1.0` (re-run produces identical trace_hash
     tuple).
  2. No regression vs any prior `Ratified` course (run their replay
     assertions; all must still pass).
  3. Adversarial rejection rate == 1.0.
  4. Legitimate acceptance rate == 1.0.
  5. Provenance non-empty rate == 1.0.
  6. Every Phase II relation exercised in ≥1 Phase III walk.
- Tests:
  - All gates green → `MasteryReport` with valid self-seal.
  - Tamper any field of the report → SHA recomputes differently (test the
    seal contract).
  - Single failing gate → `RatificationFailure` carrying the failed metric.

### Phase 6 — CLI + end-to-end micro-course (1 day)

**Goal:** prove the back half works end-to-end on a tiny hand-curated input.

Deliverables:
- `core formation` subparser wired in `core/cli.py`.
- `tests/formation/test_micro_course.py` — 5 concepts, 10 relations, 3
  walks, 2 adversarial probes. Asserts a `Ratified` `MasteryReport`.
- `_TEST_SUITES["formation"]` registered in `core/cli.py`.
- Update `docs/runtime_contracts.md` with the micro-course as a worked
  example.

**Milestone:** hand-curated triples now flow Forge → Ratify with a Mastery
Report. Pipeline back half is hardened and replay-proof. No mining yet.

### Phase 7 — Promote (1 day)

**Goal:** the **only** SPECULATIVE → COHERENT bridge.

Deliverables:
- `formation/index.py` — `MasteredCoursesIndex` reader/writer at
  `packs/mastered_courses.json`.
- `formation/promote.py` — `promote(report_sha)`:
  1. Load and verify report self-seal.
  2. Verify all `requires_courses` are in the index.
  3. For each validated triple, construct a `ReviewedTeachingExample`
     stamped with `report_sha`.
  4. Submit through `teaching/review.py` (the existing reviewed apply path —
     **no new mutation path**).
  5. Append entry to `MasteredCoursesIndex`.
- Tests:
  - Tampered report SHA → promote refused.
  - Missing prerequisite → promote refused.
  - Two consecutive `promote` calls on same report → idempotent.
  - Promotion adds to index; entries are append-only.

### Phase 8 — Smelter and basic source adapters (3 days)

**Goal:** front half begins. Non-LLM sources first.

Deliverables:
- `formation/smelter.py` — extract `ConceptCandidate`,
  `RelationCandidate`, `CounterCandidate`, `OrderingHint` from text spans.
  Initial strategy: deterministic pattern-based extraction only. No LLM.
- `formation/adapters/user_documents.py` — accept local PDF/Markdown/TXT.
- `formation/adapters/wikipedia.py` — read-only, with cached snapshots
  pinned by URL + SHA. No live fetch from the test suite.
- Async adapter pool with per-source rate limits.

### Phase 9 — Mining: async fan-out (2 days)

**Goal:** `core formation mine` runs adapters in parallel, caches by SHA.

Deliverables:
- `formation/miner.py` — async coordinator. Retry budgets. Source caching.
- Tests with a mock adapter pool (no network).

### Phase 10 — LLM ideation adapter (gated; 2 days)

**Goal:** the highest-risk surface, built last, off by default.

Deliverables:
- `formation/adapters/llm_ideation.py` — prompt SHA + model name baked into
  every candidate's provenance.
- `--enable-llm-source` flag on `core formation mine`. Default: off.
- Forge treats LLM candidates with elevated scrutiny (rule already in
  Phase 2).
- Tests with a stubbed LLM that returns canned outputs.

### Phase 11 — Autorun + status + polish (1 day)

- `core formation autorun` chains Stages 1–7, halts before promote.
- `core formation status` shows cache state per stage.
- Performance pass: parallel adapter pool tuning, triple cache benchmarks.
- Final `docs/runtime_contracts.md` update; new ADR-0022 if the trust
  boundaries deserve a standalone decision record.

---

## 4. Total estimate

~18 working days end-to-end. The two-week claim in the original design is
plausible **only** if Phases 8–10 (front half) reuse heavily from existing
ingest adapters; otherwise budget ~3 weeks. Back half (Phases 1–7) — the part
that protects the manifold — is achievable in ~10 days.

---

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Forge has a bypass path | CRITICAL | Phase 2 TDD: every rejection rule has ≥1 negative test; introspection test asserts no other module mutates packs |
| Non-deterministic Course YAML | HIGH | Canonical JSON, sorted keys, stable topo-sort, Phase 3 byte-equality test |
| Identity axis contamination | HIGH | Forge rule 2, plus an end-to-end "identity-override course" test that must be wholly rejected |
| LLM-sourced hallucinated triples slip through | HIGH | LLM adapter behind a flag; Forge requires ≥2 non-LLM corroborators |
| Cache poisoning via path traversal | HIGH | Phase 1 cache-key sanitization with explicit allow-pattern |
| Versor invariant violation mid-run | MEDIUM | Runner hard-halts on `versor_condition >= 1e-6`; no repair logic |
| Replay non-determinism | MEDIUM | Ratify gate 1; if it ever fails, fix the source of non-determinism, never relax the gate |
| Promotion mutates pack outside reviewed path | CRITICAL | Phase 7 routes exclusively through `teaching/review.py`; runner introspection test asserts no other write path |
| Course YAML schema drift | LOW | `schema_version` on every dataclass; ratify checks schema match |

---

## 6. Out of scope (explicitly NOT building)

- UI / dashboard / web app
- "Course author" natural-language-to-YAML magic tool
- General-purpose ontology editor
- A parallel "fast training mode" that bypasses the Forge
- Approximate recall (cosine / HNSW / ANN) anywhere
- Pickle-based caching
- Live network fetches during tests
- Identity-axis mutation through any path
- Auto-promotion (promotion is always a separate, deliberate command)

---

## 7. PR checklist (per CLAUDE.md)

Each PR in this plan must answer:

- What capability, performance property, or security boundary did this
  add/protect?
- Which invariant proves the field remains valid?
- Which CLI suite/eval proves the lane? (Default: `core test --suite formation`.)
- Did this avoid hidden normalization, stochastic fallback, approximate
  recall, and unreviewed mutation?
- If it touches user input, files, dynamic imports, or logs, what trust
  boundary was enforced?

---

## 8. Confirmation gate

**This is a planning document. No code is written until the user confirms.**

Reply with:
- `proceed` — start Phase 1
- `modify: …` — change specific phase scope
- `skip phase N` — skip a phase
- `different approach: …` — rework the plan
