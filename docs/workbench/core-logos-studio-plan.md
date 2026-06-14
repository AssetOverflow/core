# CORE-Logos Studio — UI/UX and Engineering Plan

**Status:** Proposed architecture / design plan  
**Scope:** Workbench CORE-Logos / packs / language-manifold engineering surface  
**Branch:** `docs/proposal-artifact-substrate-v1`  
**No code changes in this document.**

> **Dispatch (2026-06-14):** the first wave executes **L1–L5 as read-only** —
> holonomy is rendered only as `missing_evidence` until a pack-level
> `holonomy.jsonl` exists; Patch Forge (L6) / handlers (L7) are deferred behind
> the universal `ProposalArtifact` envelope. Brief pack:
> `docs/handoff/core-logos-studio-readonly-briefs-2026-06-14.md`.

---

## Purpose

CORE-Logos must become more than a pack manifest viewer.

The current Workbench Packs route gives operators useful identity/checksum visibility, but it does not yet provide an active engineering environment for viewing, developing, adjusting, linking, inspecting, analyzing, and safety-checking CORE-Logos pack contents.

This plan defines the next product shape: **CORE-Logos Studio**.

The Studio is the place where an operator can understand and evolve the linguistic substrate through reviewable proposal artifacts, without violating CORE's proposal-before-mutation doctrine.

---

## Product thesis

CORE-Logos is not a localization layer, dataset browser, translation table, or decorative theological page.

It is the Workbench surface for the language/manifold substrate:

```text
English operational articulation
Hebrew depth-root compression
Koine Greek depth-relation precision
cross-language alignment as resonance
holonomy as proof that meaning survived the path
```

The UI should make this role legible and usable.

---

## Governing doctrine

This plan inherits:

- ADR-0015: language packs are deterministic, checksummed, compiled linguistic manifolds.
- ADR-0160: Workbench is audit-native; proposal before mutation.
- ADR-0162: design is structural truth, not dashboard theater.
- ADR-0173: Workbench may only apply through admitted handlers.
- Proposal Artifact Substrate v1: CORE-Logos changes begin as `proposal_only` artifacts.
- `CLAUDE.md`: pack mutation is proposal-only until reviewed; filesystem/pack changes require explicit trust boundaries.

---

## Current state

Current pack UI is mostly:

```text
pack list
→ manifest detail
→ checksum metadata
→ raw JSON
→ pack evidence subject
```

That is necessary but not sufficient.

The full CORE-Logos engineering surface needs:

```text
manifest
→ lexicon
→ glosses
→ morphology
→ alignment edges
→ frames/compositions
→ holonomy cases
→ safety report
→ proposal artifact forge
→ ratification corridor only after handlers are admitted
```

---

## Route shape

Add a dedicated route:

```text
/logos
```

UI label:

```text
CORE-Logos
```

or:

```text
CORE-Logos Studio
```

The existing `/packs` route can remain the broader inventory view. `/logos` is the active engineering studio for language-manifold packs.

---

## Layout

Recommended page layout:

```text
+-----------------------------------------------------------------------+
| TopBar / Wrong=0 / Runtime / Command Palette                          |
+-------------+-------------------------------------------+-------------+
| Pack        | Studio Workspace                          | Evidence    |
| Universe    |                                           | Inspector   |
|             | Overview / Identity / Lexicon / ...       |             |
+-------------+-------------------------------------------+-------------+
| Safety + proposal status strip                                         |
+-----------------------------------------------------------------------+
```

### Left rail — Pack Universe

Shows:

- English operational/base packs
- Hebrew depth-root packs
- Koine Greek depth-relation packs
- math/cognition packs if relevant
- runtime packs if relevant
- safety verdict
- count badges for entries/edges/cases

### Center — Studio Workspace

Tabbed engineering surface for selected pack.

### Right inspector — Evidence projection

Selection publishes evidence subjects for packs, entries, morphology records, alignment edges, holonomy cases, and proposal drafts.

### Bottom strip — Safety/proposal status

Persistent summary:

```text
selected pack · checksum status · gate/OOV status · proposal mode · no mutation / proposal-only / ratification-enabled
```

---

## Tabs

### 1. Overview

Purpose: explain what role this pack plays.

Show:

- pack role
- language
- script
- version
- determinism class
- gate state
- OOV policy
- entry counts
- alignment edge counts
- holonomy case counts
- safety verdict

The Overview should make the tri-language model felt:

```text
English       → operational articulation
Hebrew        → depth-root compression
Koine Greek   → depth-relation precision
```

### 2. Identity

Purpose: show the pack passport.

Show:

- manifest
- source manifest
- checksum fields
- declared files
- domain contract
- eval lanes
- reviewers
- known gaps
- source digests

Raw manifest remains available through StableJsonViewer.

### 3. Lexicon

Purpose: engineering view of lexical entries.

Show columns:

- entry ID
- surface
- lemma
- language
- POS
- semantic domains
- morphology ID
- provenance IDs
- epistemic status
- safety flags

Required interactions:

- search surface/lemma/domain
- filter by epistemic status
- filter dangling morphology links
- group by semantic domain
- select entry as evidence subject
- copy entry pointer

No direct edit/save.

### 4. Glosses

Purpose: view and analyze gloss surfaces separately from lexical identity.

Show:

- gloss ID
- entry ID / lemma link
- gloss text
- source/provenance
- status
- checksum coverage

Gloss changes are a candidate for the first low-risk handler family, but only after handler admission.

### 5. Morphology

Purpose: reveal ordered operator composition.

For Hebrew:

```text
root → stem → prefix/suffix/inflection chain
```

For Greek:

```text
lemma → case/aspect/voice/mood/clause role
```

Show:

- morphology entries
- linked lexicon entries
- root clusters
- stem/operator chain
- dangling links
- order-sensitive rendering

Selection publishes `logos_morphology` evidence subject.

### 6. Alignment

Purpose: cross-language resonance graph.

Show:

- source ID
- target ID
- relation
- weight
- evidence IDs
- target pack
- invalid target warnings

Use deterministic layout only. No force-directed movement.

Questions this tab must answer:

```text
What does this Hebrew root align with?
What Greek relation carries the same structural pressure?
What English articulation surface receives it?
What evidence supports the edge?
```

Selection publishes `logos_alignment_edge` evidence subject.

### 7. Holonomy

Purpose: proof that meaning survived the path.

Show holonomy cases as proof cards:

```text
Hebrew path
   ↘
     resonance / distinction proof
   ↗
Greek path      English path
```

Each case shows:

- source refs
- pack IDs
- expected relation
- negative refs
- tolerance
- actual proof status if computed
- missing proof evidence if absent

No success state may be rendered if proof status is absent.

Selection publishes `logos_holonomy_case` evidence subject.

### 8. Safety

Purpose: make admissibility visible before any change.

Checks:

- safe pack ID
- manifest present
- declared files present
- checksum matches
- gloss/frame/composition checksum matches when declared
- OOV policy valid for role
- gate policy valid
- no dangling morphology links
- no invalid alignment targets
- no missing holonomy refs
- epistemic status counts
- speculative entries
- contested/falsified entries
- known gaps

Safety verdicts:

```text
clear
warning
failed
unknown
```

Unknown is not clear. Warning is not clear. Failed blocks handler routing.

### 9. Patch Forge

Purpose: active engineering without unsafe mutation.

Supported proposal drafts:

```text
lexicon_add
lexicon_update
lexicon_remove
gloss_add
gloss_update
morphology_add
morphology_update
alignment_edge_add
alignment_edge_update
holonomy_case_add
holonomy_case_update
frame_add
composition_add
```

Every draft produces a `ProposalArtifact` with:

- proposed payload
- evidence pointers
- patch preview
- safety report
- checksum impact prediction
- suggested CLI/PR instructions
- `capability_level = proposal_only`

The button label must be:

```text
Draft proposal
```

Not:

```text
Save
Apply
Commit
```

### 10. Ratification Corridor

Purpose: future handler-enabled path.

Initially absent for CORE-Logos proposal-only drafts.

When a handler family is admitted, the corridor may appear only for proposals whose:

- handler is admitted,
- preconditions pass,
- safety report is clear or explicitly allowed by handler policy,
- target files/checksums are known,
- audit event sink is available,
- replay/pack verification boundary is named.

---

## Evidence subjects

Add subjects through the Workbench evidence model:

```text
logos_pack
logos_entry
logos_gloss
logos_morphology
logos_alignment_edge
logos_holonomy_case
logos_patch_proposal
```

Each subject must have:

- stable ID
- route/address grammar
- right-inspector projection
- raw JSON access
- copyable pointer

Suggested addresses:

```text
logos:<pack_id>
logos:<pack_id>:entry:<entry_id>
logos:<pack_id>:gloss:<gloss_id>
logos:<pack_id>:morphology:<morphology_id>
logos:<pack_id>:alignment:<edge_id>
logos:<pack_id>:holonomy:<case_id>
logos-proposal:<proposal_id>
```

---

## Backend readers

Initial read-only endpoints:

```text
GET /logos/packs
GET /logos/packs/{pack_id}
GET /logos/packs/{pack_id}/contents
GET /logos/packs/{pack_id}/safety
GET /logos/packs/{pack_id}/alignment
GET /logos/packs/{pack_id}/holonomy
```

Proposal-only endpoint:

```text
POST /logos/packs/{pack_id}/proposals/draft
```

The draft endpoint must not write to language-pack source files. It may return a proposal artifact and patch preview.

---

## Data shapes

### `LogosPackOverview`

```text
pack_id
language
role
script
version
determinism_class
gate_engaged
oov_policy
lexicon_count
gloss_count
morphology_count
frame_count
composition_count
alignment_edge_count
holonomy_case_count
safety_status
manifest_digest
```

### `LogosPackContents`

```text
pack_id
manifest
lexicon
glosses
morphology
frames
compositions
alignment_edges
holonomy_cases
```

### `LogosSafetyReport`

```text
pack_id
checksum_status
oov_policy_ok
gate_policy_ok
path_safety_ok
dangling_morphology_links
invalid_alignment_targets
missing_holonomy_refs
epistemic_status_counts
speculative_entries
contested_entries
falsified_entries
known_gaps
verdict
```

### `LogosPatchProposal`

Should be represented through the universal `ProposalArtifact` envelope with `subject.kind = logos_pack`.

---

## Handler family order

Handler admission should be incremental.

Suggested sequence:

1. `gloss_add` / `gloss_update`
2. `lexicon_add` with speculative status only
3. morphology attach/update
4. alignment edge add/update
5. holonomy case add/update
6. coherent/admissible promotion only after stricter review path

Each handler family requires its own proof pack.

Required proof obligations:

- no direct UI file write
- safe pack ID enforcement
- deterministic ordering
- checksum update correctness
- pack compile/verify pass
- no OOV policy regression
- no depth-language fallback collapse
- no silent epistemic promotion
- audit event emission
- replay reconstruction

---

## Design language

CORE-Logos Studio should feel like an instrument, not an illustration.

Allowed motifs:

- ordered morphology chains
- deterministic alignment diagrams
- holonomy proof cards
- checksum seals
- evidence rails
- status badges with text labels
- patch previews

Forbidden motifs:

- glowing brains
- mystical particles
- generic neural-network webs
- force-directed graph animation
- decorative theological imagery that is not structurally meaningful
- save/apply buttons before handler admission

---

## Implementation sequence

### L0 — This plan

Documentation only.

### L1 — Logos read models

Add backend schemas/readers for overview, contents, and safety.

### L2 — Logos route shell

Add route, pack universe rail, overview, identity, safety status.

### L3 — Contents tabs

Lexicon, glosses, morphology, selection evidence subjects.

### L4 — Alignment / holonomy tabs

Deterministic diagrams and proof cards.

### L5 — Safety report

Full pack safety panel.

### L6 — Patch Forge

Proposal-only drafting through universal `ProposalArtifact` envelope.

### L7 — Handler family 1

Admit the first minimal CORE-Logos handler family only after ADR/tests.

---

## Acceptance standard

CORE-Logos Studio is real when an operator can:

```text
open /logos
select he_logos_micro_v1
inspect identity, lexicon, morphology, alignment, holonomy, and safety
select a speculative or linked entry
see its evidence chain and safety status
draft a proposed alignment/gloss/morphology correction
preview JSONL patch and checksum impact
see that no pack file has been mutated
copy the ratification/PR instructions
```

The operator should leave knowing exactly what can be trusted, what is only proposed, and what cannot yet be applied.

---

## Final design sentence

CORE-Logos Studio is where the language substrate stops being hidden infrastructure and becomes a lawful engineering instrument.
