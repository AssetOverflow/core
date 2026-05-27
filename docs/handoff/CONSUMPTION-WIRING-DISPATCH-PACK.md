# Consumption Wiring — Dispatch Pack (CW-1 + CW-2)

**Goal:** Close the consumption half of the math teaching loop. Make
ratified entries in `frames/*.jsonl` and `compositions/*.jsonl` reach
the runtime so audit refusals actually admit after operator
ratification.

**Parent brief:** `docs/handoff/COMPOSITION-FRAME-CONSUMPTION-WIRING-BRIEF.md` (PR #396)
**Parent ADRs:** ADR-0167, ADR-0168 / 0168.1, ADR-0169 / 0169.1, ADR-0172
**Type:** Implementation dispatch; not a doctrine ADR

---

## Why this pack exists

The 2026-05-27 end-to-end ratification of case 0019 wrote
`compositions/multiplicative_composition.jsonl` cleanly but the eval
didn't move (3 correct / 47 refused / 0 wrong baseline preserved).
No runtime code reads `frames/*.jsonl` or `compositions/*.jsonl`.
Lexicon's loop is closed (`generate/comprehension/lexicon.py::load_lexicon`);
Frame and Composition are half-open.

PR #396 names the work; this pack is the dispatch-ready operator form.

---

## Bundling rule

**Default: one bundled PR** (CW-1 + CW-2) on a single branch
`feat/composition-frame-consumption-wiring`. Both briefs share:

- the pack-compile mechanism
- manifest checksum extension
- the empty-registry no-op invariant
- the case 0050 hazard pin

Split into PR-α (CW-1) and PR-β (CW-2) **only if** CI cycle time
forces it. Single bundled PR is the recommendation.

---

## Dependency DAG

```
ADR-0167 / 0168 / 0169 (merged) ──┐
PR #393 (CompositionClaim handler) ─┤
                                    ▼
                              CW-1 + CW-2 (bundled)
                                    │
                                    ▼
                            Truth test: case 0019 admits
                            in train_sample eval
```

No upstream blocker. Orthogonal to workbench UI wave (#392 / #394 / #395).

---

## Operator profile (both briefs)

**Opus** (load-bearing wrong=0 surface; case 0050 mandatory pin;
same rigor as CC-2). Sonnet feasible if treated as tight-scope
mechanical wiring with `load_lexicon` explicitly referenced — but
CW-2's injector wire has enough judgment surface that Opus is the
safer default.

---

## Brief CW-1 — Frame Consumption Wiring

**Branch:** `feat/composition-frame-consumption-wiring` (shared with CW-2)
**Base:** `origin/main`
**Style:** Backend wiring; no UI; no new eval lanes.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-consume origin/main && \
  cd /tmp/wt-consume && \
  git checkout -b feat/composition-frame-consumption-wiring
```

### Reads required FIRST

- `generate/comprehension/lexicon.py::load_lexicon` (lines 90–188) — **the template**
- `teaching/math_frame_ratification.py` — write side; entry schema:
  `(surface_form, frame_category, polarity, provenance, evidence_hashes)`
- `language_packs/data/en_core_math_v1/manifest.json` — current shape + checksum semantics
- `docs/decisions/ADR-0168-frameclaim-ratification.md` §"Mutation boundary", §"Initial safe category scope"
- CLAUDE.md §"Semantic Pack Discipline" (manifest checksum rule)

### Outcome — new modules

1. **`language_packs/compile_frames.py`** (or extend the existing
   compile mechanism if one exists — read first):
   - Reads `frames/*.jsonl` sorted alphabetically
   - Produces compiled artifact `frames.jsonl` with entries sorted
     by `(frame_category, surface_form)`
   - Returns the new compiled file's sha256 for manifest update
2. **`generate/comprehension/frame_registry.py`**:
   - `FrameRegistryEntry` frozen dataclass:
     `(surface_form, frame_category, polarity, provenance)`
   - `FrameRegistry` frozen dataclass with `by_surface`,
     `by_category`, `pack_manifest_sha256`, `source_pack_id`
   - `FrameRegistryLoadError(ValueError)`
   - `load_frame_registry(pack_path: Path | None = None) -> FrameRegistry`
     — mirror `load_lexicon` byte-for-byte structurally:
     - cache key `(resolved_path_str, mtime_ns, sha256)`
     - manifest checksum verification (covers `frames.jsonl` bytes)
     - source-dir read of per-category `frames/*.jsonl`
     - empty-registry returns `FrameRegistry` with empty mappings,
       does not raise
   - `lookup(registry, surface) -> FrameRegistryEntry | None`
3. **Manifest extension.** `manifest.json` gains
   `frame_checksum: str` field (sha256 of compiled `frames.jsonl`).
   Loader verifies. Backward-compatible default: missing
   `frame_checksum` + empty `frames/` is fine; missing
   `frame_checksum` + non-empty `frames/` raises.
4. **Reader wire.** Identify the comprehension-reader frame-opener
   decision site (current refusal-emitting locations:
   `quantity_extraction` and `multi_quantity_composition` paths
   from the train_sample audit). Route through the loaded
   `FrameRegistry`. Empty registry → no behavior change.

### Hard requirements

- **No solver / parser / decomposer / arithmetic mutation** (ADR-0168 §"Mutation boundary")
- **Manifest checksum** updated per CLAUDE.md "Semantic Pack Discipline"
- **Deterministic order** — files sorted alphabetically; entries
  sorted by stable key
- **Empty-registry no-op** — eval byte-identical when `frames/` is empty
- **Case 0050 hazard pin** — synthetic FrameClaim ratification; assert case 0050 stays refused
- **No corpus-laundering at load** — read only from reviewed math pack

### Tests (`tests/`)

- `test_frame_registry_load.py`:
  - empty-registry returns valid `FrameRegistry` with empty mappings
  - non-empty round-trip: write a fixture entry, compile, load, assert lookup
  - manifest mismatch raises `FrameRegistryLoadError`
  - deterministic order across runs
- `test_pack_compile_frame_checksum.py`:
  - compile twice → same bytes
  - manifest `frame_checksum` matches `sha256(frames.jsonl)`
- `test_frame_registry_case_0050_hazard_pin.py` — mandatory
- `test_frame_registry_empty_no_op.py` — eval byte-identical
- `test_partition_frame_registry_not_visible_to_cognition.py`

### Deliverables (CW-1 portion)

- `language_packs/compile_frames.py` (or extension)
- `generate/comprehension/frame_registry.py`
- `language_packs/data/en_core_math_v1/manifest.json` schema bump
- Reader wire (one call site, typically in
  `generate/comprehension/*` or `generate/recognizer_match.py`)
- All CW-1 tests green
- `core test --suite runtime -q` green

### Forbidden (CW-1)

- Mutating solver / parser / decomposer / arithmetic operators
- Dynamic frame synthesis at load
- Nearest-frame guessing or fallback
- Silently skipping malformed frame entries (raise)
- Reading from any unsigned path

---

## Brief CW-2 — Composition Consumption Wiring

**Branch:** `feat/composition-frame-consumption-wiring` (same as CW-1; bundled)
**Base:** `origin/main`
**Style:** Backend wiring; no UI; no new eval lanes.

### Dispatch

Same worktree as CW-1 (one branch).

### Reads required FIRST

- All CW-1 reads
- `teaching/math_composition_ratification.py` — write side; entry schema:
  `(surface_pattern, composition_category, polarity, provenance, evidence_hashes)`
- `teaching/math_composition_proposal.py::SAFE_COMPOSITION_CATEGORIES`
  (the allowlist must be re-enforced at load)
- `docs/decisions/ADR-0169-compositionclaim-ratification.md`
  §"Mutation boundary", §"Initial safe category scope"
- `generate/recognizer_anchor_inject.py` — current injector entry
  points; refusal site for `recognized-but-uninjectable`
- `generate/math_candidate_graph.py` — where injector outputs feed
  the graph

### Outcome — new modules

1. **`language_packs/compile_compositions.py`** — analogous to CW-1's
   compile_frames; reads `compositions/*.jsonl`; produces
   compiled `compositions.jsonl` sorted by
   `(composition_category, surface_pattern)`; returns sha256.
2. **`generate/comprehension/composition_registry.py`**:
   - `CompositionRegistryEntry`:
     `(surface_pattern, composition_category, polarity, provenance)`
   - `CompositionRegistry`: `by_pattern`, `by_category`,
     `pack_manifest_sha256`, `source_pack_id`
   - `CompositionRegistryLoadError(ValueError)`
   - `load_composition_registry(pack_path) -> CompositionRegistry`
     mirroring `load_lexicon`
   - **Allowlist enforced at load** — any entry whose
     `composition_category` is outside
     `SAFE_COMPOSITION_CATEGORIES` raises
     `WrongCompositionCategory` (defense in depth; protects against
     pack edits that bypass the handler)
   - **Polarity respected** — `polarity: "falsifies"` entries
     produce `lookup` results that suppress injection at the
     consumer (not silently treated as `affirms`)
3. **Manifest extension** — `manifest.json` gains
   `composition_checksum: str` field. Same backward-compatibility
   rule as CW-1.
4. **Injector wire.** Identify the
   `recognized-but-uninjectable` emission site in
   `generate/recognizer_anchor_inject.py` (case 0019's refusal
   reason: *"recognizer matched but produced no injection for
   statement: ... (category=currency_amount)"*). Consult the
   `CompositionRegistry`. If a SAFE allowlist pattern matches the
   recognized structure under polarity `affirms`, emit the
   composed operand. Polarity `falsifies` continues to refuse.
   No match → continue to refuse (refusal-first preserved).

### Hard requirements

- **Allowlist enforced at load** — `WrongCompositionCategory` on
  any unsafe category (defense in depth)
- **Polarity semantics** — `falsifies` suppresses injection; not
  silently `affirms`
- **No solver / parser / decomposer / arithmetic mutation**
- **No dynamic pattern synthesis** at runtime
- **No nearest-pattern guessing**
- **No embedding-based selection**
- **Manifest checksum** updated per CLAUDE.md
- **Empty-registry no-op** — eval byte-identical when
  `compositions/` is empty (currently has 1 entry locally from my
  2026-05-27 session; remove via `git clean -fd
  language_packs/data/en_core_math_v1/compositions/` before
  starting, OR keep it as the literal canary — see Truth Test)
- **Case 0050 hazard pin** — synthetic CompositionClaim under
  every entry in `SAFE_COMPOSITION_CATEGORIES`; case 0050 must
  stay refused
- **No corpus-laundering at load**

### Tests (`tests/`)

- `test_composition_registry_load.py`:
  - empty / non-empty / manifest mismatch / deterministic order
- `test_composition_load_allowlist.py`:
  - unsafe category at load raises `WrongCompositionCategory`
- `test_composition_polarity_falsifies.py`:
  - `falsifies` entry suppresses injection that would have fired
- `test_composition_registry_case_0050_hazard_pin.py` — mandatory
- `test_composition_registry_empty_no_op.py`
- **`test_composition_case_0019_admits.py`** — **the truth test**:
  ratify case 0019 via `apply_composition_claim()` under
  `multiplicative_composition` with `surface_pattern="bound(count) × bound(unit_cost)"`,
  re-run `train_sample` reader, assert verdict transitions
  `refused → correct`
- `test_pack_compile_composition_checksum.py`
- `test_partition_composition_registry_not_visible_to_cognition.py`

### Deliverables (CW-2 portion)

- `language_packs/compile_compositions.py`
- `generate/comprehension/composition_registry.py`
- Injector wire in `generate/recognizer_anchor_inject.py`
- All CW-2 tests green including the case-0019 truth test
- `core test --suite teaching -q` green
- `core test --suite runtime -q` green
- `core test --suite packs -q` green

### Forbidden (CW-2)

- Mutating solver / parser / decomposer / arithmetic operators
- Inventing categories outside `SAFE_COMPOSITION_CATEGORIES`
- Dynamic pattern synthesis at runtime
- Nearest-pattern guessing
- Embedding-based selection
- Silently skipping unsafe categories at load (must raise)
- Treating `polarity: "falsifies"` as `affirms`
- Reading from cognition corpus or any unsigned path

---

## Truth Test (binding for the bundled PR)

[[feedback-ratify-vs-consume-loop-closure]] — artifact append is
**not** the success signal. **Eval delta is.**

The PR is "done" when **all** hold:

| # | Assertion | How to verify |
|---|---|---|
| 1 | Case 0019 admits | Ratify case 0019 under `multiplicative_composition`; run `python -m evals.gsm8k_math.train_sample.v1.runner --use-reader`; case 0019 verdict transitions `refused → correct` |
| 2 | Case 0050 stays refused | Same runner; case 0050 still `refused` |
| 3 | `train_sample` improved | `report.json` counts move from **3 correct / 47 refused** → **≥4 correct / ≤46 refused** |
| 4 | `wrong == 0` preserved | `report.json` `counts.wrong == 0` |
| 5 | `public` split unchanged | `uv run core eval gsm8k_math --split public --json` → `150/150 correct, wrong_rate=0.0` |
| 6 | Empty-registry no-op | Wipe `frames/` and `compositions/`, full eval byte-identical to pre-PR baseline |

A PR that lands the consumer code but doesn't move the eval needle
is **not done**.

---

## Anti-regression invariants (both briefs)

- `wrong == 0` on `core eval gsm8k_math` preserved
- Case 0050 stays refused after any synthetic ratification
- ADR-0166 — no new eval lanes
- ADR-0057 replay-equivalence inherited
- ADR-0167 partition (math/cognition) preserved
- Empty-registry runtime byte-identical to today
- `SAFE_COMPOSITION_CATEGORIES` enforced at write **and** load
- Polarity semantics (`affirms` vs `falsifies`) honored at consumer
- `engine_state/*` never committed
- Pinned-lane SHAs may update (intentional eval delta); call out
  the move in the PR body

---

## Memory pointers

- [[project-ratification-consumption-gap-2026-05-27]] — the finding
- [[feedback-ratify-vs-consume-loop-closure]] — the general pattern
- [[feedback-wrong-zero-hazard-case-0050]] — mandatory pin
- [[feedback-production-line-pattern]] — this dispatch pattern
- [[feedback-parallel-agent-worktrees]] — fresh worktree per brief
- [[milestone-adr-0172-tier1-2026-05-27]] — wave context
- [[adr-0167-audit-as-evidence-wave]] — parent corridor

---

## Copy-paste dispatch line

```text
# CW-1 + CW-2 bundled (Opus; load-bearing wrong=0)
Read docs/handoff/CONSUMPTION-WIRING-DISPATCH-PACK.md (entire file).
git fetch origin main && git worktree add /tmp/wt-consume origin/main && cd /tmp/wt-consume && git checkout -b feat/composition-frame-consumption-wiring
```

Operator instruction sequence:
1. Read CW-1 + CW-2 sections plus the Truth Test table.
2. Read `generate/comprehension/lexicon.py::load_lexicon` (the template).
3. Implement CW-1 modules + reader wire.
4. Implement CW-2 modules + injector wire.
5. Run the truth-test sequence end-to-end.
6. Confirm all 6 truth-test rows hold before opening PR.
7. PR title: `feat(consumption-wiring): close Frame + Composition loop halves`.

---

## What ships when this PR lands

The compounding loop's consumption half closes for Frame and
Composition. The first PR where the math teaching loop **runs in
full** beyond Lexical — 20 composition cases + any frame cases the
empty frame registry now serves become live admission events on
ratification. **The flywheel becomes operational.**

End-to-end flow (verifiable post-merge):

```
audit refusal
  → core eval math-contemplation
  → MathFrameClaimProposal / MathCompositionClaimProposal
  → HITL ratify via apply_*_claim()
  → frames/{cat}.jsonl or compositions/{cat}.jsonl append
  → pack-compile folds entries into runtime-loadable form  (NEW)
  → manifest.json checksum updated                          (NEW)
  → next runtime turn loads new entries                     (NEW)
  → reader/injector consumes ratified patterns              (NEW)
  → previously-refused cases admit (verified by train_sample eval delta)
```
