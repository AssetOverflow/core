# ADR-0167 — Parallel Work Plan

**Date:** 2026-05-27
**Parent ADR:** [ADR-0167](../decisions/ADR-0167-audit-as-teaching-evidence.md)
**Goal:** Land the LexicalClaim-first slice of the math reader → contemplation
wire across four cooperating operators in two waves, with strict
worktree isolation and shared invariants.

---

## Shared constraints (every brief)

- Open dedicated `git worktree add` per the parallel-agent worktree rule
- `wrong == 0` non-negotiable; verify against case `gsm8k-train-sample-v1-0050`
  whenever runtime is touched
- No new canonical eval lanes (ADR-0166)
- No teaching-store / pack mutation as direct side effect of the wire — pack
  writes happen only through ratified handlers
- `uv venv` / `uv pip install` / `uv run` — never `pip --break-system-packages`,
  never `/tmp` scratch venvs
- Stage explicit files; never `git add -A`; NEVER commit `engine_state/`
- Cognition teaching-corridor tests must remain green at every layer

---

## Wave 1 — Foundation (single blocking brief)

Until Wave 1 lands, Wave 2 cannot start. Wave 1 ships one PR.

### W1-A — Schema + canonical-bytes for `MathReaderRefusalEvidence`

**Recommended operator:** **Opus 4.6/4.7**
**Why this model:** Deepest reasoning. The output is an architectural
schema that has to be right the first time (it's the type every Wave 2
brief depends on). One file of types + one file of round-trip tests.

**Deliverables:**

- `teaching/math_evidence.py` (new) — frozen dataclass
  `MathReaderRefusalEvidence` with:
  - `case_id: str`
  - `sentence_index: int`
  - `token_index: int`
  - `refusal_reason: str`
  - `missing_operator: str | None`
  - `claim_signature: str` (normalised dedup key — see W2-B)
  - `evidence_hash: str` (canonical-bytes sha256)
  - `audit_row: AuditRow` (existing type from `generate/comprehension/audit.py`)
  - `sub_type: Literal["lexical", "frame", "composition", "reference", "slot"]`
- `teaching/math_evidence.py` includes `to_canonical_bytes()` mirroring
  `state.to_canonical_bytes()` patterns (sort keys, omit None, decimal
  canonicalisation if needed)
- `tests/test_math_evidence_schema.py` (new):
  - Round-trip canonical bytes determinism (same input → byte-identical hash)
  - Frozen-dataclass immutability
  - `claim_signature` is stable across two refusals with the same surface
    semantics (placeholder; W2-B finalises the normalisation rules)
  - Cross-sub-type hash distinctness (lexical claim for `crayons` ≠ frame
    claim for `crayons`)

**Out of scope for W1-A:**
- Audit-to-evidence adapter (that's W2-A)
- Dedup policy implementation (W2-B specifies; W1-A only places the field)
- Ratification handlers (W2-D)

**Exit:** PR merged to main; the type is importable; tests are green;
no runtime change outside `teaching/`.

---

## Wave 2 — Parallel build (four briefs, dispatched in one message)

All four branch off `main` (post-W1-A merge). Each in its own worktree.
Each opens its own PR.

### W2-A — Audit → candidate adapter

**Recommended operator:** **GPT-5.3-Codex** (or Sonnet 4.6 as second choice)
**Why this model:** Mechanical wiring with a defined contract. Codex
excels at "take type A, produce type B, write tests." Short cycle time.

**Deliverables:**

- `teaching/math_contemplation.py` (new) — function
  `audit_to_evidence(audit_rows: list[AuditRow]) -> list[MathReaderRefusalEvidence]`
- Maps `missing_operator` → `sub_type` per the table in ADR-0167
- Computes `evidence_hash` from `MathReaderRefusalEvidence.to_canonical_bytes()`
- Leaves `claim_signature` as the empty string for non-lexical sub-types
  (W2-B fills it for lexical)
- `tests/test_math_contemplation_adapter.py` — 8+ tests:
  - Round-trip from `audit_brief_11.json` produces N evidence records
    (one per refused case)
  - Determinism: same audit input → byte-identical evidence list
  - Mapping table is exhaustive (no `missing_operator` falls through to
    `None` sub_type)
  - Empty audit → empty evidence list

**Dependencies:** Wave 1 (`MathReaderRefusalEvidence` type)
**Exit:** Adapter callable from a test; cognition tests untouched.

### W2-B — Dedup policy + claim signature normalisation (LexicalClaim only)

**Recommended operator:** **Sonnet 4.6**
**Why this model:** Pure-Python text-normalisation work with clear
invariants. Sonnet is fast and reliable on this shape. Output is
tightly scoped and testable.

**Deliverables:**

- `teaching/math_claim_signature.py` (new) — function
  `lexical_claim_signature(surface: str, refusal_detail: str) -> str`
- Normalisation rules (deterministic; documented in module docstring):
  - Lowercase the surface
  - Strip leading/trailing punctuation
  - Encode the unknown-token from `refusal_detail` literally
  - Hash with sha256, return hex
- Update `teaching/math_contemplation.py` (W2-A's file) so that lexical
  sub_type evidence carries the computed signature; non-lexical pass
  empty string (deferred to follow-up ADR)
- `tests/test_math_claim_signature.py` — 10+ tests:
  - Identical surface → identical signature
  - Different surface → different signature
  - Punctuation strip leaves the same signature
  - Two GSM8K cases both refusing on `crayons` produce one signature
  - Real-data sanity: run over `audit_brief_11.json`, assert no false
    collisions among the actual `lexicon_entry` cases

**Dependencies:** Wave 1; coordinates with W2-A on which file owns the
signature call.
**Exit:** Lexical evidence rows carry a stable signature; dedup test
proves identical claims collapse.

### W2-C — Cross-domain partition audit + discriminator

**Recommended operator:** **Gemini** (long-context, mechanical audit)
**Why this model:** This is a scan-many-files survey: find every
contemplation/teaching code path that touches `DiscoveryCandidate`,
identify where `domain` discrimination must be added, list every test
that touches the candidate type, propose minimal surgical patches.
Gemini's long-context window suits the scan; the architecture call
remains the operator's.

**Deliverables (docs + minimal-impl PR):**

- `docs/handoff/ADR-0167-W2C-cross-domain-audit.md` (new) — survey of
  every code path that constructs or consumes `DiscoveryCandidate`,
  with explicit yes/no on whether each path needs to read a `domain`
  field
- Minimal `domain: Literal["cognition", "math"]` field added to
  `DiscoveryCandidate` (default `"cognition"` to keep existing cognition
  tests passing without changes)
- `tests/test_candidate_domain_partition.py` — assert:
  - Existing cognition candidates default to `domain="cognition"`
  - A math candidate can be constructed with `domain="math"`
  - Round-trip serialisation preserves the field

**Hard constraint:** all existing cognition teaching-corridor tests must
remain green with zero modification.
**Dependencies:** Wave 1 (so the audit can reference the math evidence
type accurately).
**Exit:** Domain field present; cognition tests green; survey doc
identifies any remaining partition risk for Wave 3.

### W2-D — `LexicalClaim` ratification handler

**Recommended operator:** **GPT-5.5 / 5.4** (highest-stakes implementation;
needs GitHub connector access for cross-PR coordination)
**Why this model:** Touches the highest-risk surface: pack files. Needs
the most careful handling of wrong=0, manifest checksum, and
ratification provenance. GPT-5.5's longer-step coding plus GitHub
connector keeps it coordinated with #348's lexicon work.

**Deliverables:**

- `teaching/math_lexical_ratification.py` (new) — function
  `apply_lexical_claim(claim: MathReaderRefusalEvidence, category: str,
  reviewer: str) -> RatificationReceipt`
- Writes to `language_packs/data/en_core_math_v1/lexicon/<category>.jsonl`
  with the rules established by #348 (alphabetical sort, provenance tag,
  alias-vs-lemma decision)
- Provenance tag: `phase_2_reader_ratified_<reviewer>_<YYYY-MM-DD>`
- Manifest checksum recompute decision: source-file edits do NOT
  regenerate `lexicon.jsonl` (matches #348's pattern); document this in
  the function's docstring
- `RatificationReceipt` includes: target_file, lemma, category,
  provenance, file_sha256_before, file_sha256_after, evidence_hash
- `tests/test_math_lexical_ratification.py` — 10+ tests, including:
  - Round-trip: write a lemma, verify it loads through `load_lexicon`
  - Idempotency: applying the same claim twice raises a deterministic
    `AlreadyRatified` error (no silent dup)
  - Manifest checksum invariant: source-file write does not change
    `manifest.json`'s declared checksum
  - Hazard pin: ratifying `does` as `accumulation_verb` (mis-category)
    raises `WrongZeroViolationCandidate` (because case 0050's `does`
    is currently `modal_aux` and reclassifying would risk wrong>0)
- Workbench integration is **out of scope** (ADR-0167 §"Open Questions
  Q4"); the function returns a receipt, the workbench wiring is a
  follow-up PR.

**Dependencies:** Wave 1; coordinates with #348's pack patterns.
**Exit:** Operator can call `apply_lexical_claim()` from a Python
session to ratify a single lexical evidence row; all tests green.

---

## Wave 3 — Integration + regression (after Wave 2 fully lands)

Single brief; sequential after all Wave 2 PRs merge.

### W3-A — End-to-end determinism + cognition regression

**Recommended operator:** **Opus 4.6/4.7** (or Sonnet 4.6 if Opus is
busy)
**Why this model:** Verification work; the test suite is the contract.
Deep reasoning helps spot subtle invariant breaks across the wire.

**Deliverables:**

- `tests/test_math_evidence_e2e.py` — end-to-end test:
  - Load audit_brief_11.json
  - Adapter produces evidence list
  - Two reruns produce byte-identical evidence list (replay equivalence)
  - Ratify one lexical claim
  - Re-run audit; the previously-refused case now passes through that
    lemma (advances `unknown_word` row by one)
  - Cognition teaching-corridor regression: existing
    `evals/identity_divergence/` lanes still green
- Update `evals/gsm8k_math/train_sample/v1/audit_brief_11.md` with a
  "post-W2 baseline" row in the taxonomy table

**Hard constraint:** if any cognition test breaks, the wire is not
ready to merge.
**Exit:** Full LexicalClaim slice operational; ready for first
operator-driven math ratification.

---

## Dispatch protocol

When ready to launch Wave 2:

```text
Single message → three Agent tool calls in parallel:
  1. subagent_type=general-purpose → W2-A brief (Codex-style ops)
  2. subagent_type=general-purpose → W2-B brief (Sonnet-style ops)
  3. subagent_type=general-purpose → W2-C brief (Gemini-style ops)
+ separate dispatch to GPT-5.5 via GitHub connector → W2-D brief
```

W2-D goes to GPT-5.5 separately because the ratification handler
touches the highest-risk surface and benefits from human-paced review
coordination via the connector.

Wave 3 is single-operator, dispatched after Wave 2 fully merges.

---

## Operator workload (rough estimate)

| Wave | Brief | Operator | Effort |
|------|-------|----------|-------:|
| 1    | W1-A  | Opus     | small  |
| 2    | W2-A  | Codex    | small  |
| 2    | W2-B  | Sonnet   | small  |
| 2    | W2-C  | Gemini   | medium |
| 2    | W2-D  | GPT-5.5  | medium |
| 3    | W3-A  | Opus     | small  |

Six PRs total. Two waves of true parallelism. One serial foundation,
one serial integration. Every wave gate is `wrong == 0` + cognition
tests green.

---

## What this plan does NOT do

- Does **not** add new eval lanes (ADR-0166)
- Does **not** wire workbench v1 (ADR-0167 §Q4 — out of scope)
- Does **not** ship the four non-lexical sub-types (deferred to ADR-0168+)
- Does **not** mutate cognition packs (math wire only)
- Does **not** auto-ratify anything (HITL always)
