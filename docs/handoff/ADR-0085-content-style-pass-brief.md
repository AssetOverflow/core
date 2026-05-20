# ADR-0085 Content Style Pass — Brief

**Audience:** A fresh dev agent (cheaper/faster tier). You have NO prior context — read this file plus `docs/decisions/ADR-0085-gloss-aware-cause.md` and act from there.

**Mission:** Apply a fluency pass to the ratified gloss entries so the surfaces produced by the composer read as natural English. You are only editing JSONL gloss content. You are NOT implementing composer changes, NOT touching algebra, NOT changing pack schemas.

**Estimated effort:** small — about 30–60 lines of JSONL edits across 13 packs. The closure rule already holds (`scripts/verify_definitional_closure.py` exits 0 today); your edits must keep it holding.

---

## Why this exists

ADR-0084 ratified per-lemma `gloss` text. ADR-0085 made the composer use those glosses for CAUSE intent. Today the runtime emits:

```
Light exists as visible medium that reveal truth. pack-grounded (...).
```

The shape is right, but `"reveal"` should be `"reveals"` (3sg present after `"medium that"`). Same lemma in DEFINITION shape:

```
Light is visible medium that reveal truth. pack-grounded (...).
```

Same fix needed. The gloss content is the locus — fixing the gloss text fixes both intents at once.

The agent who wrote the initial glosses used bare lemma forms (uninflected dictionary forms) because the closure rule wants `definitional_atoms` to list LEMMAS. They conflated *atoms must be lemma form* with *gloss should use lemma form*. Those are different fields for different purposes — let them diverge correctly.

---

## What you ARE changing

For each gloss entry in `language_packs/data/<pack>/glosses.jsonl` where the gloss reads ungrammatically when slotted into the composer's POS frame:

| POS | Composer frame | Example before | Example after |
|---|---|---|---|
| NOUN | `{Lemma} is {gloss}.` | `Light is visible medium that reveal truth.` | `Light is a visible medium that reveals truth.` |
| VERB | `To {lemma} means {gloss}.` | `To recall means get memory from before.` | `To recall means to get memory from before.` |
| ADJ  | `Something is {lemma} when it {gloss}.` | `Something is bad when it different from good.` | `Something is bad when it is different from good.` |

The CAUSE frame (ADR-0085) uses the same gloss, so a single fix lifts both shapes:

```
CAUSE   "Light exists as a visible medium that reveals truth."
DEFN    "Light is a visible medium that reveals truth."
```

## What you are NOT changing

| Field | Rule |
|---|---|
| `definitional_atoms` | NEVER change. Stays in lemma form. (`"reveal"` stays in atoms even when gloss becomes `"reveals"`.) |
| `predicates_invited` | NEVER change. |
| `pos` | NEVER change. |
| `lemma` | NEVER change. |
| `definition_version` | NEVER bump. Style edits aren't version-worthy. |
| `provenance_ids` | Append `"adr-0085-style:reviewed:2026-05-21"` to indicate the pass. |

Any code, any pack schema, any composer, any algebra: **do not touch**.

---

## Phase 1 — Inventory the issues

Run this from the repo root to get an honest list:

```bash
PYTHONPATH=. python3 - <<'EOF'
import json, re
from pathlib import Path
ROOT = Path('language_packs/data')

# Patterns flagging fluency issues likely visible in the composer surface.
# These are heuristics — manually verify each hit.
SUSPECT_BARE_VERBS = {
    'support','reveal','know','show','cause','give','make','mean','follow',
    'happen','become','belong','depend','imply','verify','check','find',
    'explain','lack','do','see','feel','hold','work','serve','help','tell',
    'come','go','use','get','put','keep','have','leave','matter','live','die',
}
patterns = [
    ('3sg-agreement-after-relative',
     re.compile(r'\b(what|who|that|which) (' + '|'.join(SUSPECT_BARE_VERBS) + r')\b')),
    ('plural-after-quantifier',
     re.compile(r'\b(two|three|many|several|some|few|all)\s+([a-z]+ing\b|[a-z]+(?<![s])\b)')),
    ('missing-article-after-copula',
     re.compile(r'^(visible|broad|small|good|bad|right|true|clear|new)\s+[a-z]+\b')),
]
hits = []
for pack_dir in sorted(ROOT.iterdir()):
    g = pack_dir / 'glosses.jsonl'
    if not g.exists(): continue
    for line in g.read_text().splitlines():
        if not line.strip(): continue
        e = json.loads(line)
        for name, pat in patterns:
            m = pat.search(e['gloss'])
            if m:
                hits.append((pack_dir.name, e['lemma'], name, e['gloss']))
                break
for pack, lemma, kind, gloss in hits:
    print(f'{pack:32}{lemma:18}{kind:32}{gloss!r}')
print(f'\\nTOTAL: {len(hits)}')
EOF
```

This gives you a starting list. Some hits will be false positives (the pattern is approximate). You decide per entry.

You should expect on the order of **20–40 entries** that genuinely need a one-line edit. Larger than the integration-test PR found because the integration test only checks resolution, not fluency.

## Phase 2 — Per-entry edits

For each entry flagged in Phase 1 that genuinely needs a fix:

1. **Read the gloss aloud** in the composer frame for its POS (table above). If it reads awkwardly, fix it.
2. **Keep changes minimal.** A typical fix is adding `"s"`, `"a "`, `"the "`, `"to "`, or inflecting one verb.
3. **Verify `definitional_atoms` still lists the LEMMA form** of every content word. (`"reveals"` in gloss → `"reveal"` in atoms; `"meanings"` in gloss → `"meaning"` in atoms.)
4. **Append the style-pass provenance:** add `"adr-0085-style:reviewed:2026-05-21"` to `provenance_ids`.
5. **Do NOT bump `definition_version`** — that's reserved for definitional changes, not fluency.

### Fluency rules-of-thumb

| Pattern | Fix |
|---|---|
| `what X` (bare verb) | `what Xs` (3sg agreement) — `what support` → `what supports` |
| `that X` (bare verb in relative clause) | `that Xs` — `that reveal` → `that reveals` |
| `two X` (singular noun) | `two Xs` — `two meaning` → `two meanings` |
| `group of X` (singular noun, group context) | `group of Xs` — `group of reason` → `group of reasons` |
| starts with adjective directly (no article) | prepend `a ` or `the ` as appropriate to make NOUN frame fluent — `visible medium` → `a visible medium` |
| VERB gloss missing `to` infinitive | prepend `to ` if VERB frame's "means" needs it — `means get memory` → `means to get memory` |
| ADJ gloss missing copula | prepend `is ` when ADJ frame ends with `when it` — `when it different` → `when it is different` |

When in doubt, **leave it.** A slightly stilted gloss that reads OK is better than an over-corrected one that drifts from primitive vocabulary.

## Phase 3 — Re-checksum

For each pack you touched, recompute `glosses_checksum`:

```bash
for pack in $(ls language_packs/data); do
  gloss_path=language_packs/data/$pack/glosses.jsonl
  manifest_path=language_packs/data/$pack/manifest.json
  if [ ! -f "$gloss_path" ]; then continue; fi
  new_sha=$(python3 -c "import hashlib; print(hashlib.sha256(open('$gloss_path','rb').read()).hexdigest())")
  old_sha=$(python3 -c "import json; print(json.load(open('$manifest_path')).get('glosses_checksum',''))")
  if [ "$new_sha" != "$old_sha" ]; then
    python3 -c "
import json, pathlib
p = pathlib.Path('$manifest_path')
m = json.loads(p.read_text())
m['glosses_checksum'] = '$new_sha'
p.write_text(json.dumps(m, indent=2) + '\\n')
print(f'updated $pack: $old_sha[:8].. → $new_sha[:8]..')
"
  fi
done
```

## Phase 4 — Verify everything still works

All of these must pass:

```bash
# Closure rule still holds — your edits did not break the gate.
PYTHONPATH=. python3 scripts/verify_definitional_closure.py
# Expected: total entries / total atoms / 0 unresolved / 0 mismatches

# Substrate parser still accepts every gloss.
PYTHONPATH=. python3 -m pytest tests/test_adr_0084_integration_closure.py -q
# Expected: 30 passed

# Cognition eval byte-identical.
PYTHONPATH=. python3 -m core.cli eval cognition > /tmp/eval_post.json
diff /tmp/eval_post.json baseline.json
# Expected: empty diff
#   (capture baseline.json with `core eval cognition > baseline.json` BEFORE
#    starting any edits)

# Smoke + packs lanes.
PYTHONPATH=. python3 -m core.cli test --suite smoke -q
PYTHONPATH=. python3 -m core.cli test --suite packs -q
# Expected: all green
```

If `core eval cognition` drifts byte-from-byte, **STOP**. That means a metric moved unexpectedly. Either:
- (a) Your fix changed term-capture by inflecting a word the cognition eval expects in lemma form. Roll the edit back.
- (b) You accidentally changed a `pos` or `definition_version`. Roll that back.

The cognition eval staying byte-identical is the load-bearing invariant of this entire pass.

---

## Deliverables

1. The edited `glosses.jsonl` and updated `manifest.json` files on branch `feat/adr-0085-content-style-pass`.
2. A draft PR titled `feat(packs): ADR-0085 content style pass (fluency in glosses)`. Mark **Draft** — a human reviews before merge.
3. A report in the PR body with this shape:

```
## Style pass summary

- packs touched:     <N>
- entries edited:    <N>
- total atoms:       <unchanged from 847>
- closure verifier:  exit 0
- cognition eval:    byte-identical to baseline
- packs lane:        pass

## Sample edits (10 representative)

| pack | lemma | before | after |
|---|---|---|---|
| en_core_cognition_v1 | light | `"visible medium that reveal truth"` | `"a visible medium that reveals truth"` |
| en_core_cognition_v1 | evidence | `"what support truth"` | `"what supports truth"` |
| ...

## Open questions

(anything unclear or that needed judgment — list here)
```

---

## Hard rules

| Rule | Consequence if broken |
|---|---|
| Do NOT touch any code (`*.py`, `chat/`, `core/`, `algebra/`, `generate/`) | PR rejected |
| Do NOT touch Greek/Hebrew packs (`grc_*`, `he_*`) — they're not in the definitional layer | PR rejected |
| Do NOT touch the primitives pack (`packs/primitives/`) | PR rejected |
| Do NOT change `definitional_atoms`, `predicates_invited`, `pos`, `lemma`, `definition_version` | PR rejected |
| Do NOT bypass closure verification | PR rejected |
| Cognition eval must stay byte-identical | PR rejected, edits rolled back |
| Closure verifier must exit 0 | PR rejected, edits rolled back |

If anything is unclear, **surface the question rather than guessing.**
