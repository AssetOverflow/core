# Logos collapse-anchor reconciliation — diagnosis + fix brief

**Date:** 2026-06-14
**Trigger:** The CORE-Logos Studio (LG-4 Alignment tab + Safety) shows
`grc_logos_cognition_v1` and `he_core_cognition_v1` as **Warning** with
**invalid alignment targets** (7 and 7 respectively). This brief records what
that means and the scoped pack-content fix.

## Diagnosis — this is a real, latent pack-data gap, not a UI/reader bug

Every invalid target is a `cross_lang.no_english_collapse` edge. That relation
is the "English collapses this distinction" negative-space marker: a Hebrew/Greek
entry points at an `en-collapse-*` anchor representing a nuance English lacks.
The edge is valid iff its `en-collapse-*` target resolves to a **declared
lexicon entry** (LG-1 removed the old relation/prefix carve-out that blindly
passed any `en-collapse-*` id, so undeclared anchors now surface honestly).

Current state on `main`:

| Pack | references (`en-collapse-*`) | declared in `en_collapse_anchors_v1`? |
|---|---|---|
| `en_collapse_anchors_v1` (the anchor pack) | declares `justice`, `love`, `peace` | — |
| `grc_logos_cognition_v1` | `time`, `heart`, `soul`, `breath`, `holy` | **none** |
| `he_core_cognition_v1` | `covenant_love`, `shalom`, `tzedek`, `heart`, `soul`, `breath`, `holy` | **none** |

Two distinct defects:

1. **Naming divergence.** The anchor pack declares *English* names
   (`en-collapse-love/peace/justice`), but the logos packs reference *source-
   concept* names (`en-collapse-covenant_love/shalom/tzedek`). So even the three
   declared anchors are never actually referenced — they are dead, and the
   concept-named references are all dangling.
2. **Missing anchors.** `time/heart/soul/breath/holy` are declared nowhere.

The Studio is doing exactly what it was built to do: a cross-pack inconsistency
that was invisible (and silently swallowed by the pre-LG-1 carve-out) is now a
visible, addressable `WARNING` with each dangling edge enumerated.

## Fix (reviewed pack-content change — NOT a workbench change)

Reconcile the collapse-anchor vocabulary so every referenced anchor resolves.
Recommended direction: **make `en_collapse_anchors_v1` declare the anchors the
logos packs actually reference** (the references encode the curated theology;
the anchor pack is the lagging inventory).

- Audit the full referenced set across all logos packs (union of the table
  above): `covenant_love, shalom, tzedek, time, heart, soul, breath, holy`
  (and decide whether `justice/love/peace` stay as aliases or are renamed).
- Add a `LexicalEntry` per anchor to `en_collapse_anchors_v1/lexicon.jsonl`
  (mirror the shape of the existing `en-collapse-love` row: `language: en`,
  `semantic_domains: ["collapse_anchor.<name>"]`, provenance to the relevant
  ADR-0073 family), in deterministic id order.
- Recompute and pin the manifest `checksum` to the bytes actually written
  (`hashlib.sha256(lexicon_path.read_bytes())`), per CLAUDE.md.
- Add/extend a pack test asserting every `cross_lang.no_english_collapse`
  target across the logos packs resolves to a declared anchor (a **non-vacuous**
  guard: it must fail today and pass after the data lands).
- Re-run the Studio: `grc_logos_cognition_v1` / `he_core_cognition_v1` Safety
  verdicts should drop their invalid-target lists (verdict can still be
  `UNKNOWN`, never `CLEAR`, while holonomy proof is absent — see W-Holonomy).

## Decision needed (Shay)

Is the source-concept naming (`shalom`/`tzedek`/`covenant_love`) the canonical
anchor vocabulary (then the declared `love/peace/justice` are renamed or
aliased), or should the logos packs be edited to reference the English names?
The reconciliation direction is a curation call, not a mechanical one — hence a
reviewed pack PR, not an auto-fix.

## Scope

Small, isolated, off-serving (no `generate.derivation` / `reliability_gate`
import; logos packs are not in the serving-frozen SHA gate). One pack-content
PR + one resolution test. Independent of W-Holonomy and W-Forge.
