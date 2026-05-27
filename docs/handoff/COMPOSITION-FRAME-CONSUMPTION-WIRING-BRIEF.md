# Composition + Frame Consumption Wiring — Follow-Up Brief

**Date:** 2026-05-27
**Author:** Shay
**Parent:** ADR-0167, ADR-0168 / 0168.1, ADR-0169 / 0169.1, ADR-0172
**Related:** [[project-ratification-consumption-gap-2026-05-27]], [[feedback-ratify-vs-consume-loop-closure]]
**Type:** Implementation brief (one or two PRs); not a doctrine ADR

---

## Why this brief exists

The end-to-end CompositionClaim ratification ran cleanly on 2026-05-27
post-#393 merge. The handler appended one entry to
`language_packs/data/en_core_math_v1/compositions/multiplicative_composition.jsonl`
with provenance `adr_0169_composition_ratified_shay_2026-05-27`.

**The eval did not change.** `train_sample` re-ran with the reader on
returned the same baseline: **3 correct / 47 refused / 0 wrong**. Case
0019 (the one I ratified) still refused with `recognized-but-uninjectable`.
`wrong=0` held — no regression — but also no admission.

Why: **no runtime code reads `compositions/*.jsonl` or `frames/*.jsonl`**.

| Directory | Has handler (writes) | Has consumer (reads) |
|---|---|---|
| `language_packs/data/en_core_math_v1/lexicon/` | ✓ LexicalClaim (W2-D) | ✓ `generate/comprehension/lexicon.py::load_lexicon` |
| `language_packs/data/en_core_math_v1/frames/` | ✓ FrameClaim (#389 / ADR-0168) | ✗ none |
| `language_packs/data/en_core_math_v1/compositions/` | ✓ CompositionClaim (#393 / ADR-0169) | ✗ none |

Two of three sub-types ship the **ratification half** of the loop
but not the **consumption half**. The handler-side compounding loop
is closed; the runtime-effect compounding loop is not.

This brief names the work to close the consumption half.

---

## Scope

Two parallel-safe wirings:

- **CW-1 — Frame consumption.** Make ratified entries in
  `frames/{category}.jsonl` reach the runtime frame-opener
  registry consumed by the comprehension reader.
- **CW-2 — Composition consumption.** Make ratified entries in
  `compositions/{category}.jsonl` reach the runtime injector path
  (`generate/recognizer_anchor_inject.py` and adjacent) that
  composes bound quantities into a single operand.

Recommendation: ship as **one PR** because (a) they share the
pack-compile + manifest-checksum mechanism, and (b) the eval-delta
truth-test only registers if both halves are wired (the audit
refusals span both frame and composition gaps).

Optionally split into PR-α (compile + frame consumption) and PR-β
(composition consumption) if CI cycle time argues for it, but
prefer bundled.

---

## Out of scope

- ReferenceClaim and SlotClaim ratification handlers (ADR-0167
  FOLLOWUPS §1) — those need their own sub-type ADRs first.
- Workbench UI wave (W1..W4) — orthogonal; can run in parallel.
- New eval lanes (ADR-0166).
- Pack-mutation autonomy — runtime still reads packs only at load
  time; no live-running registry edits.

---

## Proven pattern (template)

The lexicon consumer in `generate/comprehension/lexicon.py::load_lexicon`
is the working reference:

```python
# pseudocode of the proven pattern
def load_lexicon(pack_path):
    compiled = pack_path / "lexicon.jsonl"
    manifest = json.loads((pack_path / "manifest.json").read_text())
    actual_sha = sha256(compiled.read_bytes())
    if manifest["checksum"] != actual_sha:
        raise LexiconLoadError(...)
    entries = []
    for src in sorted((pack_path / "lexicon").glob("*.jsonl")):
        for line in src.read_text().splitlines():
            entries.append(parse_entry(line))
    return Lexicon(entries, ...)
```

Key invariants from CLAUDE.md ("Semantic Pack Discipline"):

- Manifest checksum hashes the bytes actually written to disk
  (`hashlib.sha256(Path(lexicon_path).read_bytes()).hexdigest()`).
- Deterministic ordering: per-category files sorted alphabetically,
  entries within each file sorted by key.
- Cache by (resolved_path, mtime, sha256) to avoid re-reading on
  every turn.

Both CW-1 and CW-2 mirror this pattern.

---

## CW-1 — Frame consumption wiring

**Branch:** `feat/composition-frame-consumption-wiring`
(bundled with CW-2; same branch)
**Reads required FIRST:**

- `generate/comprehension/lexicon.py::load_lexicon` (the template)
- `teaching/math_frame_ratification.py` (write side — entry schema)
- `docs/decisions/ADR-0168-frameclaim-ratification.md` §"Mutation boundary"
- `language_packs/data/en_core_math_v1/manifest.json` (current shape)
- The empty `language_packs/data/en_core_math_v1/frames/` directory

**Outcome.**

1. **Compile step.** Extend the pack-compile mechanism (or add a
   new sibling) that:
   - reads `frames/*.jsonl` (sorted)
   - produces a deterministic compiled artifact `frames.jsonl`
     (or folds entries into a runtime-friendly index — choose one
     and pin it)
   - regenerates `manifest.json` checksum to include the new
     compiled bytes per CLAUDE.md "Semantic Pack Discipline"
2. **Runtime consumer.** New function (or extension of an existing
   loader) — `load_frame_registry(pack_path)` — analogous to
   `load_lexicon`, with the same caching + checksum-verification
   discipline.
3. **Reader wire.** Plumb the loaded frame registry into the
   comprehension reader's frame-opener decision path. The current
   refusal `frame closed with no quantity` (`quantity_extraction`)
   and `multi-quantity operations are Phase-2.1 scope`
   (`multi_quantity_composition`) are the relevant refusal sites —
   identify where the reader decides those and route through the
   ratified registry.
4. **Empty-registry safe behavior.** When `frames/` is empty
   (current state), the runtime behaves exactly as today — no
   regression. Verified by an empty-frames test.

**Hard requirements.**

- **No solver / parser / decomposer mutation.** ADR-0168 §"Mutation
  boundary" forbids it. The consumer reads only; it must not
  rewrite arithmetic semantics.
- **Manifest checksum.** New compiled bytes participate in
  `manifest.json::checksum`; loader rejects mismatch (see lexicon
  template).
- **Deterministic order.** Per-category files sorted; entries
  sorted within file.
- **Empty-registry no-op.** Eval is byte-identical when `frames/`
  has zero entries.
- **Case 0050 hazard pin.** A new test ratifies a synthetic
  FrameClaim, runs `train_sample` eval, asserts case 0050 stays
  refused.

---

## CW-2 — Composition consumption wiring

**Branch:** same as CW-1 (`feat/composition-frame-consumption-wiring`)
**Reads required FIRST:**

- All CW-1 reads
- `teaching/math_composition_ratification.py` (write side — entry schema)
- `docs/decisions/ADR-0169-compositionclaim-ratification.md` §"Mutation boundary", §"Initial safe category scope"
- `generate/recognizer_anchor_inject.py` — current injector entry points (`inject_from_match`, `inject_discrete_count_statement`)
- `generate/math_candidate_graph.py` — where injector outputs feed the graph

**Outcome.**

1. **Compile step.** Same shape as CW-1 but for
   `compositions/*.jsonl` → `compositions.jsonl` (or runtime index).
   Manifest checksum extended again.
2. **Runtime consumer.** `load_composition_registry(pack_path)` —
   analog of `load_lexicon` for composition patterns.
3. **Injector wire.** Wire the composition registry into the
   injector path. Specifically: when the recognizer matches a
   structure that the existing injector currently emits as
   `recognized-but-uninjectable`, the injector consults the
   composition registry to determine if a SAFE_COMPOSITION_CATEGORIES
   pattern applies, and if so emits the composed operand.
4. **Empty-registry safe behavior.** Same as CW-1.

**Hard requirements.**

- **Allowlist enforced at consumption.** Even though the handler
  enforces `SAFE_COMPOSITION_CATEGORIES` at write time, the
  consumer must also enforce: any entry with a category outside
  the allowlist is **rejected at load** with `WrongCompositionCategory`
  — not silently skipped. (Defense in depth; protects against a
  pack edit that bypasses the handler.)
- **Polarity respected.** `polarity: "falsifies"` entries must
  suppress an injection that would otherwise have fired — not be
  silently treated as `affirms`. Pinned by a parametrized test.
- **No corpus-laundering at load.** The consumer reads from the
  reviewed math pack only; it must never read cognition corpus or
  any other unsigned path.
- **Case 0050 hazard pin.** Synthetic CompositionClaim under
  every entry in `SAFE_COMPOSITION_CATEGORIES`; assert case 0050
  remains refused after each one.
- **`wrong=0` preserved.** Full `train_sample` eval green; full
  `core eval gsm8k_math` green.

---

## Eval-delta truth test (the real success criterion)

[[feedback-ratify-vs-consume-loop-closure]] — the artifact append
is **not** the success signal. The eval delta is.

The PR is "done" when:

1. `apply_composition_claim()` on case 0019 (the canary I ratified
   2026-05-27) under `multiplicative_composition` with the same
   `surface_pattern` causes **case 0019 to admit** in
   `train_sample` eval (verdict transitions from `refused` to
   `correct`).
2. Case 0050 still refuses (mandatory hazard pin).
3. `train_sample` eval count moves from **3 correct / 47 refused**
   to at least **4 correct / 46 refused** (admitting at least case
   0019; better if more of the 12 `quantity_extraction` cases
   also admit under the same multiplicative pattern).
4. `wrong == 0` invariant unchanged.
5. `core eval gsm8k_math` (`public` split) unchanged: **150/150**.

A PR that lands the consumer code but doesn't move the eval needle
is **not done** — it has the same shape as the bug this brief is
fixing (handler writes, runtime ignores).

---

## Tests

- `tests/test_frame_registry_load.py` — empty-registry no-op;
  deterministic order; manifest mismatch raises
- `tests/test_composition_registry_load.py` — same
- `tests/test_composition_load_allowlist.py` — unsafe category at
  load raises `WrongCompositionCategory`
- `tests/test_composition_polarity_falsifies.py` — falsifying
  entries suppress injection
- `tests/test_composition_case_0019_admits.py` — the truth test:
  ratify case 0019, re-run train_sample reader, assert verdict
  flips from `refused` to `correct`
- `tests/test_composition_case_0050_hazard_pin.py` — mandatory
- `tests/test_consumption_empty_registry_no_op.py` — eval
  byte-identical when both `frames/` and `compositions/` empty
- `tests/test_pack_manifest_checksum_includes_compiled_frames.py`
- `tests/test_pack_manifest_checksum_includes_compiled_compositions.py`
- end-to-end: `core eval math-contemplation` → `apply_composition_claim()`
  → `train_sample` re-run → assert verdict delta

---

## Anti-regression invariants

- `wrong == 0` on `core eval gsm8k_math` preserved
- Case 0050 stays refused after any synthetic ratification
- ADR-0166 — no new eval lanes
- ADR-0057 replay-equivalence inherited
- ADR-0167 partition (math/cognition) preserved
- Empty-registry runtime byte-identical to today
- `SAFE_COMPOSITION_CATEGORIES` allowlist enforced at both write
  and load (defense in depth)
- Polarity semantics (`affirms` vs `falsifies`) honored at consumer
- `engine_state/*` never committed
- Pinned-lane SHAs may update (intentional eval delta); call out
  the move in the PR body

---

## Deliverables

- pack-compile mechanism extended (or new sibling) for `frames/`
  and `compositions/`
- `generate/comprehension/frame_registry.py` (or analogous) —
  loader + cache + checksum verification
- `generate/comprehension/composition_registry.py` (or analogous) —
  same
- reader wire (CW-1) and injector wire (CW-2)
- manifest schema updated to carry the new compiled-bytes checksums
- tests above, all green
- `core test --suite teaching -q` green
- `core test --suite runtime -q` green
- `core test --suite packs -q` green
- `core eval gsm8k_math` green
- `train_sample` eval count improved (truth test)

---

## Forbidden

- Mutating solver, parser, decomposer, or arithmetic operators
  (ADR-0168 / 0169 mutation boundary)
- Dynamic category synthesis at load time
- Nearest-pattern guessing
- Embedding-based composition selection
- Silently skipping unsafe categories at load (must raise)
- Treating `polarity: "falsifies"` as `affirms`
- Reading from cognition corpus or any unsigned path
- New eval lanes (ADR-0166)
- New corpus families

---

## Sequencing

1. **Dispatch:** after the workbench UI W0 (ADR-0173, PR #394) does
   **not** need to land first — this brief is orthogonal to the UI
   wave and can ship anytime.
2. **Operator profile:** Opus (load-bearing wrong=0 surface;
   case 0050 pin; same rigor as CC-2). Sonnet is feasible for
   CW-1/CW-2 if treated as tight-scope mechanical wiring with the
   lexicon template explicitly referenced — but the injector wire
   in CW-2 has enough judgment surface that Opus is the safer
   default.
3. **Bundle vs split.** Default: one PR bundling both CW-1 and
   CW-2. Split only if CI cycle time forces it.

---

## Memory pointers

- [[project-ratification-consumption-gap-2026-05-27]] — the
  finding that motivated this brief
- [[feedback-ratify-vs-consume-loop-closure]] — the general pattern
- [[feedback-wrong-zero-hazard-case-0050]] — mandatory pin
- [[milestone-adr-0172-tier1-2026-05-27]] — wave context
- [[adr-0167-audit-as-evidence-wave]] — parent corridor
- [[feedback-batch-during-research]] — bundling rule

---

## What ships when this PR lands

The compounding loop's **consumption half** closes for Frame and
Composition. End-to-end:

```
audit refusal
  → core eval math-contemplation (8 proposals; CC-3 dispatch)
  → MathFrameClaimProposal / MathCompositionClaimProposal
  → HITL ratify via apply_*_claim()
  → frames/{cat}.jsonl or compositions/{cat}.jsonl append
  → pack-compile (NEW) folds entries into runtime-loadable form
  → manifest.json checksum updated
  → next runtime turn loads new entries
  → reader/injector consumes ratified patterns
  → previously-refused cases admit (verified by train_sample eval delta)
```

This is the first PR where the loop **runs in full** for math
sub-types beyond Lexical.

The 20 composition cases + however-many frame cases the empty
frame registry now serves become live admission events on
ratification. The compounding flywheel is operational.
