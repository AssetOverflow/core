# ADR-0084 Pack-Content Build Brief

**Audience:** A fresh dev agent (cheaper/faster tier). You have NO prior context — read this file and `docs/decisions/ADR-0084-definitional-layer.md` and act from there. Do not invent design decisions; if something is unclear, surface a question rather than guessing.

**Mission:** Produce the *content* required by ADR-0084 (Definitional Layer for Lexicon Packs). You are not implementing the schema parser, the composer integration, or any runtime code. You are only producing JSONL pack files and verifying they cohere.

---

## What already exists (do not duplicate)

```
language_packs/data/
├── en_core_cognition_v1/      ← HAS glosses.jsonl (78 entries)
├── en_core_meta_v1/           ← HAS glosses.jsonl (72)
├── en_core_attitude_v1/       ← HAS glosses.jsonl (40)
├── en_core_polarity_v1/       ← HAS glosses.jsonl (16)
├── en_core_action_v1/         ← HAS glosses.jsonl (26)
├── en_core_temporal_v1/       ← HAS glosses.jsonl (28)
├── en_core_spatial_v1/        ← HAS glosses.jsonl (24)
├── en_core_causation_v1/      ← HAS glosses.jsonl (15)
├── en_core_quantitative_v1/   ← HAS glosses.jsonl (24)
├── en_core_relations_v1/      ← lexicon only, no glosses
├── en_core_relations_v2/      ← lexicon only, no glosses
├── en_core_relations_v3/      ← lexicon only, no glosses
├── en_collapse_anchors_v1/    ← lexicon only, no glosses
├── he_core_cognition_v1/      ← lexicon only, no glosses
├── grc_logos_cognition_v1/    ← lexicon only, no glosses
├── grc_logos_micro_v1/        ← lexicon only, no glosses
├── he_logos_micro_v1/         ← lexicon only, no glosses
└── en_minimal_v1/             ← lexicon only, no glosses (skip — staging)
```

Existing `glosses.jsonl` entries have the flat shape:

```jsonc
{"lemma":"analogy","gloss":"a mapping of relations shared between distinct domains","pos":"NOUN","provenance_ids":["seed:glosses_v1"]}
```

They DO NOT yet carry `definitional_atoms` or `predicates_invited` — those fields are what ADR-0084 introduces. You will extend each existing entry with those two fields, in place, preserving every other field byte-identically.

---

## Phase 1 — Primitives pack (highest priority, blocks everything else)

Create `packs/primitives/en_semantic_primitives_v1/`. This is a new top-level directory; create it if it does not exist.

### Files to create

1. `packs/primitives/en_semantic_primitives_v1/manifest.json`
2. `packs/primitives/en_semantic_primitives_v1/primitives.jsonl`
3. `packs/primitives/en_semantic_primitives_v1/README.md` (one paragraph)

### Primitives discipline

A *primitive* is a word whose meaning is taken as terminal at the system level — it does not require a gloss because every other definition can bottom out on it. Pick ~40–60 primitives across these tight categories:

| Category | Examples |
|---|---|
| Existence | `exist`, `be`, `not_be` |
| Identity | `same`, `different`, `this`, `that` |
| Relation | `relation`, `cause`, `part`, `whole`, `connected_to` |
| Mode | `way`, `means`, `medium` |
| Disclosure | `visible`, `hidden`, `seen`, `known` |
| Quantity (basic) | `one`, `many`, `none`, `some` |
| State | `change`, `still`, `start`, `end` |
| Reference | `who`, `what`, `where`, `when`, `why`, `how` |
| Communication | `say`, `mean`, `ask`, `answer` |
| Logic | `if`, `then`, `and`, `or`, `because` |

Avoid overlap with the existing 9 core packs — primitives must be the *floor*, not duplicates of vocabulary already glossed elsewhere. If you see a word in any existing `glosses.jsonl`, prefer to leave it out of primitives.

### Primitive entry schema

```jsonc
{
  "lemma": "exist",
  "category": "existence",
  "pos": "VERB",
  "primitive_version": 1,
  "provenance_ids": ["adr-0084:reviewed:2026-05-20"]
}
```

No `gloss`. No `definitional_atoms`. Primitives are terminal.

### Manifest

```jsonc
{
  "pack_id": "en_semantic_primitives_v1",
  "language": "en",
  "kind": "primitives",
  "definitional_layer": true,
  "version": 1,
  "issued_at": "2026-05-20T00:00:00Z",
  "checksum": "<sha256 of primitives.jsonl as written>",
  "primitive_count": <N>,
  "never_auto_mutable": true,
  "provenance": "adr-0084:reviewed:2026-05-20"
}
```

Compute `checksum` as `hashlib.sha256(Path("primitives.jsonl").read_bytes()).hexdigest()` AFTER writing the file (the manifest hashes the bytes actually on disk).

### Acceptance for Phase 1

- File exists at the path above.
- 40 ≤ `primitive_count` ≤ 60.
- Every line of `primitives.jsonl` is valid JSON with the schema above.
- No primitive lemma appears in any existing `glosses.jsonl` (run a quick `grep -l "\"lemma\":\"<word>\"" language_packs/data/*/glosses.jsonl` for each — should return empty).
- Manifest `checksum` matches `sha256` of `primitives.jsonl` bytes.

---

## Phase 2 — Extend existing 9 core glosses to ADR-0084 schema

For each pack in `language_packs/data/` that already has a `glosses.jsonl`, extend each entry to:

```jsonc
{
  "lemma": "analogy",
  "gloss": "a mapping of relations shared between distinct domains",
  "pos": "NOUN",
  "definitional_atoms": ["mapping", "relation", "shared", "distinct", "domain"],
  "predicates_invited": ["reveals", "illustrates", "maps"],
  "definition_version": 1,
  "provenance_ids": ["seed:glosses_v1", "adr-0084:reviewed:2026-05-20"]
}
```

### `definitional_atoms` rule

Every content word in `gloss` (skip articles, prepositions, "is", "of", "to", "by", "the", "a", "an", "that", "which") must be in `definitional_atoms`. Each entry in `definitional_atoms` must resolve to EXACTLY ONE of:

1. Another lemma in the SAME pack's `lexicon.jsonl` or `glosses.jsonl`.
2. A lemma in another pack's `lexicon.jsonl` or `glosses.jsonl` under `language_packs/data/`.
3. A primitive in `packs/primitives/en_semantic_primitives_v1/primitives.jsonl`.

If a word in the gloss does not resolve, do ONE of:

- Rephrase the gloss using a word that does resolve (preferred).
- Add the unresolved word to the primitives pack (only if it is genuinely terminal — surface a note in your final report listing every word you promoted to primitive).
- Add a new gloss to the most appropriate existing core pack (e.g. if "mapping" belongs in `en_core_action_v1`, add it there with its own closure).

NEVER invent a new pack just to hold one stray word.

### `predicates_invited` rule

List 2–6 predicates that this lemma legitimately appears with **as the subject**. Examples:

- `light` → `["reveals", "illuminates", "shines", "exposes"]`
- `knowledge` → `["requires", "grounds", "supports", "informs"]`
- `parent` → `["raises", "begets", "guides", "shelters"]`

If you are unsure for a given lemma, set `predicates_invited: []` (the v1 spec accepts empty during migration). Prefer empty over guessing.

### Acceptance for Phase 2

- Every pre-existing `glosses.jsonl` entry gains `definitional_atoms`, `predicates_invited`, `definition_version`, and an additional `adr-0084:reviewed:2026-05-20` provenance entry.
- Run the closure check (Phase 4) and fix any unresolved references before moving on.
- Each pack's `manifest.json` is updated:
  - Add `"definitional_layer": true`.
  - Refresh `checksum` against the new `glosses.jsonl` bytes.
  - Append `adr-0084` to provenance.

---

## Phase 3 — New glosses for packs that lack them

Add `glosses.jsonl` to each of these packs, one entry per lemma in the pack's `lexicon.jsonl`:

- `en_core_relations_v1`, `v2`, `v3` (kinship — `parent`, `child`, `sibling`, `family`, `ancestor`, `descendant`, `spouse`, `offspring`, and the v2/v3 additions)
- `en_collapse_anchors_v1` (only 3 lemmas — small)

Use the same schema as Phase 2. Same closure rule. Same `predicates_invited` discipline.

DO NOT touch these in this brief:

- `he_core_cognition_v1`, `grc_logos_cognition_v1`, `grc_logos_micro_v1`, `he_logos_micro_v1` — Greek/Hebrew per-lens glosses are a separate ADR (anchor-lens substrate, deferred per ADR-0084 scope limits).
- `en_minimal_v1` — staging pack, not production.

### Acceptance for Phase 3

- Each named pack has a `glosses.jsonl` with one entry per `lexicon.jsonl` entry.
- All Phase 2 acceptance items apply.

---

## Phase 4 — Closure verification

Write a stand-alone Python script at `scripts/verify_definitional_closure.py` that:

1. Loads every `glosses.jsonl` under `language_packs/data/` whose pack manifest has `"definitional_layer": true`.
2. Loads `packs/primitives/en_semantic_primitives_v1/primitives.jsonl`.
3. For each gloss entry, for each token in `definitional_atoms`, checks it resolves to ONE of (a) same-pack lemma, (b) other-pack lemma, (c) primitive.
4. Prints a report:
   - total entries checked
   - total `definitional_atoms` tokens checked
   - unresolved tokens grouped by pack
   - exit code 0 iff zero unresolved
5. Optional `--json` flag for machine-readable output.

This script is the ratification gate proxy until the real one ships in the schema parser ADR. Run it after every batch of edits.

### Acceptance for Phase 4

- Script exists, is runnable as `python -m scripts.verify_definitional_closure`.
- Exit code 0 on the final pack state.
- A `--json` invocation produces a parseable report.

---

## Phase 5 — Run the safety lanes

After every phase, run these and confirm green:

```bash
PYTHONPATH=. python3 -m core.cli test --suite smoke -q
PYTHONPATH=. python3 -m core.cli test --suite packs -q
PYTHONPATH=. python3 -m core.cli test --suite cognition -q
PYTHONPATH=. python3 -m core.cli eval cognition
```

If any of these breaks, STOP and surface the failure. Do not patch around it — the composer was not changed by this ADR, so any cognition/teaching regression means a pack content drift broke an existing invariant. The fix is to the pack content, not to the runtime.

### Acceptance for Phase 5

- All four green.
- `core eval cognition` metrics byte-identical to pre-brief baseline (capture the baseline FIRST — run the eval before starting Phase 1 and save the output for diff).

---

## Things you must NOT do

- DO NOT modify any file under `chat/`, `core/`, `generate/`, `vault/`, `field/`, `algebra/`, `teaching/`, `evals/` (except for reading them).
- DO NOT modify `language_packs/compiler.py` or `language_packs/data/<pack>/manifest.json` fields other than `checksum`, `provenance`, and the new `definitional_layer` flag.
- DO NOT introduce any LLM-generated glosses by routing through an external API. Every gloss is hand-written, drawn from primitives + co-pack vocabulary. If a lemma is genuinely outside your domain knowledge, surface it as a question instead of guessing.
- DO NOT touch Greek / Hebrew packs (per ADR scope limit).
- DO NOT add `predicates_invited` you cannot defend — empty is the correct default for uncertainty.
- DO NOT skip checksum refresh — packs are content-addressed; stale checksums fail ratification.

---

## Reporting

When you are done (or blocked), produce a single markdown report:

```markdown
# ADR-0084 Pack-Content Build — Final Report

## Phase 1 — primitives pack
- created: <path>
- primitive_count: <N>
- categories covered: <list>
- words promoted to primitive (during Phase 2 closure): <list>

## Phase 2 — existing glosses extended
- packs touched: <list>
- entries extended: <total>
- entries left with predicates_invited=[]: <count>
- closure status: <verified | issues>

## Phase 3 — new glosses created
- packs touched: <list>
- entries added: <total>

## Phase 4 — closure verifier
- script path: <path>
- final exit code: <0 | nonzero>

## Phase 5 — safety lanes
- smoke: <pass | fail>
- packs: <pass | fail>
- cognition: <pass | fail>
- eval cognition metrics diff: <byte-identical | drift details>

## Open questions / handoff items
- <list anything you couldn't answer without guessing>
```

Surface this report at the end. Do not commit. The human reviews the report before any merge.

---

## Sanity primitives (a starter list — extend, don't blindly copy)

You may use these as a starting point for the primitives pack. Confirm each is NOT already in an existing `glosses.jsonl` before including:

```
exist, be, not_be, same, different, this, that, relation, cause, part,
whole, connected_to, way, means, medium, visible, hidden, seen, known,
one, many, none, some, change, still, start, end, who, what, where,
when, why, how, say, mean, ask, answer, if, then, and, or, because,
through, from, into, between, before, after
```

That's 49. Decide which deserve to be in the primitives pack and which are better placed inside an existing core pack (e.g. `through`, `from`, `into`, `between`, `before`, `after` are likely already in `en_core_spatial_v1` or `en_core_temporal_v1`).

End of brief.
