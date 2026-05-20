# ADR-0085 Content Style Pass v2 — Brief

**Audience:** Same cheaper dev agent that did PR #73 (v1 fluency pass). You can re-read [ADR-0085-content-style-pass-brief.md](./ADR-0085-content-style-pass-brief.md) for context but most of it still applies — this v2 narrows scope to the two patterns v1 deferred or missed.

**Mission:** Apply targeted 3sg-agreement and plural-after-quantifier fixes to the existing gloss entries. ~18 candidate entries identified up front. No other patterns in scope.

**Estimated effort:** very small — ~18 one-character edits.

---

## What v1 covered (already on main as PR #73)

- Article insertion (`Light is a visible medium...` ← `Light is visible medium...`)
- Infinitive insertion (`To recall means to get memory...` ← `To recall means get memory...`)
- Copula insertion (`Something is bad when it is different...` ← `... when it different`)

All shipped. Closure verifier exits 0, cognition eval byte-identical. The composer surfaces now read well except for two remaining patterns.

## What v2 covers

### Pattern A — 3sg present-tense agreement after relative pronouns

Glosses with `what {VERB}`, `who {VERB}`, `that {VERB}`, or `which {VERB}` where `{VERB}` is in bare form and the implied subject is singular. The verb needs an `s`.

| pack | lemma | before | after |
|---|---|---|---|
| en_core_causation_v1 | effect | `"what cause make"` | `"what causes make"` (and `make` → `makes` too — see note) |
| en_core_cognition_v1 | beginning | `"start before what follow"` | `"start before what follows"` |
| en_core_cognition_v1 | creation | `"start of what make"` | `"start of what makes"` |
| en_core_cognition_v1 | definition | `"word that explain meaning"` | `"word that explains meaning"` |
| en_core_cognition_v1 | evidence | `"what support truth"` | `"what supports truth"` |
| en_core_cognition_v1 | light | `"a visible medium that reveal truth"` | `"a visible medium that reveals truth"` |
| en_core_cognition_v1 | reason | `"what explain why"` | `"what explains why"` |
| en_core_cognition_v1 | symbol | `"image that mean more"` | `"image that means more"` |
| en_core_meta_v1 | example | `"one case that make a point visible"` | `"one case that makes a point visible"` |
| en_core_meta_v1 | mind | `"part that think and know"` | `"part that thinks and knows"` |

**Note on `effect`** — both verbs need the `s`: `"what causes makes"` reads wrong (looks like two finite verbs). The actual fix is `"what a cause makes"` (insert article) — that converts the second verb to make the gloss grammatical. Worth your judgment: either rewrite OR accept the slight awkwardness OR leave `effect` for a future pass.

**Modal verbs are NOT 3sg.** Glosses like `"who can know and do"` (en_core_cognition_v1/person) are CORRECT — `can` is a modal, the bare verbs after it (`know`, `do`) take no `s`. Do NOT change those.

### Pattern B — Plural agreement after quantifier / preposition

Glosses with `between {N}`, `among {N}`, `of {N}`, `two {N}`, `three {N}`, `many {N}`, etc., where `{N}` is a count noun in singular form. The noun needs an `s`.

| pack | lemma | before | after |
|---|---|---|---|
| en_core_attitude_v1 | broad | `"is general in many part"` | `"is general in many parts"` |
| en_core_cognition_v1 | context | `"relation between word"` | `"relation between words"` |
| en_core_cognition_v1 | order | `"relation of part to part"` | `"relation of parts to parts"` |
| en_core_cognition_v1 | style | `"way of voice and word"` | `"way of voice and words"` (note: `voice` is mass, leave it) |
| en_core_spatial_v1 | between | `"in relation to two place"` | `"in relation to two places"` |

**Three borderline cases** — apply your judgment, default to leave-alone if uncertain:

| pack | lemma | gloss | judgment |
|---|---|---|---|
| en_core_attitude_v1 | factual | `"is of fact and truth"` | Both `fact` and `truth` are mass-noun-ish in this context. **Probably leave.** |
| en_core_cognition_v1 | therefore | `"then because of reason"` | `reason` here is mass-noun-ish ("reasoning"). **Probably leave.** |
| en_core_meta_v1 | argument | `"group of reason for a point"` | `reason` here is count ("group of reasons"). **Apply fix → `"group of reasons for a point"`.** |

---

## What v2 does NOT do

- No edits beyond the patterns above. Other awkward surfaces (if any) are out of scope.
- No edits to `definitional_atoms`, `predicates_invited`, `pos`, `lemma`, `definition_version` — same rules as v1.
- No edits to Greek/Hebrew packs.
- No edits to the primitives pack.
- No new fluency patterns invented in this pass.

## Phase 0 — Baseline (mandatory)

```bash
PYTHONPATH=. python3 -m core.cli eval cognition > baseline.json
```

## Phase 1 — Apply Pattern A edits (10 entries)

For each row in the Pattern A table above, edit the gloss in place. Append `"adr-0085-style-v2:reviewed:2026-05-22"` to `provenance_ids`.

## Phase 2 — Apply Pattern B edits (5 confident + 1 borderline-accepted entry = 6 total)

For each row in the Pattern B table where the column says "→ ...", edit the gloss in place. Append the same provenance tag.

## Phase 3 — Refresh checksums

Same per-pack checksum-refresh shell snippet as v1 (in [ADR-0085-content-style-pass-brief.md](./ADR-0085-content-style-pass-brief.md) Phase 3).

## Phase 4 — Verify

All four must pass:

```bash
PYTHONPATH=. python3 scripts/verify_definitional_closure.py
# Expected: 0 unresolved / 0 mismatches

PYTHONPATH=. python3 -m pytest tests/test_adr_0084_integration_closure.py -q
# Expected: 30 passed

PYTHONPATH=. python3 -m core.cli eval cognition > /tmp/eval_post.json
diff /tmp/eval_post.json baseline.json
# Expected: empty diff

PYTHONPATH=. python3 -m core.cli test --suite smoke -q
PYTHONPATH=. python3 -m core.cli test --suite packs -q
```

If `core eval cognition` drifts byte-from-byte from baseline.json, **STOP** and roll back the edit that caused it.

---

## Why this v2 exists separately from a single bigger v1

v1 covered the patterns that could be reliably detected via simple substring search (missing articles, missing infinitives, missing copulas). 3sg-agreement and plural-after-quantifier need a small POS-aware classifier that wasn't worth building for the v1 scope. v2 ships the *concrete row-by-row edit list* up front so no classifier is required — you just apply the table.

---

## Deliverables

1. Edits on branch `feat/adr-0085-content-style-pass-v2`.
2. Draft PR titled `feat(packs): ADR-0085 content style pass v2 (3sg + plural agreement)` with this report:

```
## v2 fluency summary

- pattern A (3sg): N of 10 applied, M skipped (list which + why)
- pattern B (plural): N of 5+1 applied, M skipped
- closure verifier: exit 0
- integration test: 30/30
- cognition eval: byte-identical to baseline
- packs lane: pass

## sample 10 surfaces post-v2

(framed via the composer's POS table — same format as v1's report)
```

3. Mark **Draft**. Human reviews before merge.

## Hard rules

Same as v1. Do not touch code. Do not change atoms / predicates / pos / lemma / definition_version. Cognition eval must stay byte-identical. Closure verifier must exit 0.
