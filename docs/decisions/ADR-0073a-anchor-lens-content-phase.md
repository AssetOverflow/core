# ADR-0073a — Anchor lens content phase (Plan Phase L1.1)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase L1.1 (content prerequisites — pack enrichment, no code)
**Parent:** [ADR-0073](./ADR-0073-anchor-lens-substrate.md) (umbrella anchor-lens architecture)

---

## Context

ADR-0073 identifies three honest gaps blocking anchor-lens
implementation, the first being **distinction-bearing breadth absent
from cognition-tier packs**.  Greek's interesting move is splitting
one English concept into multiple lemmas; the cognition packs carry
one lemma per concept.  Without those distinctions on disk, no later
phase (L1.2–L1.4) can render `"knowing-as-experience"` vs
`"knowing-as-system"` deterministically — the substrate atoms simply
do not exist to pivot on.

L1.1 fixes this with **pure content enrichment**.  No runtime code,
no composer, no realizer, no test of behaviour — only:

* lexicon.jsonl additions
* matching morphology.jsonl additions
* alignment.jsonl creation on the cognition-tier packs (currently
  only the micro packs carry alignment)
* manifest.json checksum refresh + re-verification

This is the highest-leverage step in the L1 sequence because it
unblocks every later phase without code risk.

---

## Decision

### Greek additions (`grc_logos_cognition_v1`)

Nine new lemmas covering three distinction-bearing families that
English collapses:

**Knowledge family** (English collapses to `knowledge`):

| entry_id | lemma | distinguishing atom |
|---|---|---|
| `grc-core-cog-021` | ἐπιστήμη | `logos.episteme.systematic_knowledge` |
| `grc-core-cog-022` | σύνεσις | `logos.synesis.insight` |

(γνῶσις at `grc-core-cog-007` retains `logos.epignosis.knowledge` —
the L1.3 lens reads it as the experiential variant.)

**Love family** (English collapses to `love`):

| entry_id | lemma | distinguishing atom |
|---|---|---|
| `grc-core-cog-023` | ἀγάπη | `logos.agape.covenant_love` |
| `grc-core-cog-024` | φιλία | `logos.philia.companion_love` |
| `grc-core-cog-025` | ἔρως | `logos.eros.passionate_love` |
| `grc-core-cog-026` | στοργή | `logos.storge.familial_love` |

**Time family** (English collapses to `time`):

| entry_id | lemma | distinguishing atom |
|---|---|---|
| `grc-core-cog-027` | αἰών | `logos.aion.age_era` |
| `grc-core-cog-028` | χρόνος | `logos.chronos.clock_time` |
| `grc-core-cog-029` | καιρός | `logos.kairos.opportune_moment` |

### Hebrew additions (`he_core_cognition_v1`)

Three new lemmas from Hebrew's load-bearing covenant / wholeness /
righteousness distinctions:

| entry_id | lemma | distinguishing atom |
|---|---|---|
| `he-core-cog-021` | חסד | `logos.chesed.covenant_loyalty` |
| `he-core-cog-022` | שלום | `logos.shalom.wholeness_peace` |
| `he-core-cog-023` | צדק | `logos.tzedek.right_order` |

### Alignment.jsonl on both cognition-tier packs

The cognition-tier packs (`grc_logos_cognition_v1`,
`he_core_cognition_v1`) gain a companion `alignment.jsonl` mirroring
the micro packs' format.  Edges fall in three categories:

* **`cross_lang.<atom>`** — three-way alignment on the shared
  `logos.*` atoms where all three substrates have the lemma (word /
  truth / light / life / beginning / pneuma / sophia).
* **`cross_lang.<family>`** — within-family alignment where two
  substrates have distinguishing lemmas but the third collapses or
  lacks the family (e.g. ἀγάπη ↔ חסד on the covenant-love axis;
  English has no covenant-love lemma).
* **`cross_lang.no_english_collapse`** — annotation edges marking
  families English does not split (love, time).  These are
  metadata: target_id is `en-collapse-<family>`, a sentinel pointing
  at no real lexicon entry, with `weight=0.0` and an
  `evidence_ids` list naming the collapsed English term.

### Manifest checksum refresh

Per CLAUDE.md doctrine:

```python
checksum = hashlib.sha256(Path(lexicon_path).read_bytes()).hexdigest()
```

`grc_logos_cognition_v1/manifest.json` and
`he_core_cognition_v1/manifest.json` are updated with the new
checksums of their post-enrichment lexicon.jsonl files.
`python -m language_packs verify <pack_id>` is the canonical gate.

---

## What L1.1 deliberately does NOT do

* **No new `AnchorLens` class.**  That's L1.2.
* **No composer wiring.**  Composers continue to render English
  by default.
* **No `--anchor-lens` CLI flag.**  That's L1.4.
* **No teaching corpus in non-English.**  Teaching chains in grc/he
  are a later phase (L2+).
* **No modification of existing lemma atoms.**  The 20 grc + 20 he
  existing entries are untouched so downstream tests / composers /
  teaching chains keep referencing the same atoms they always have.
  Only new lemmas carry the distinguishing atoms.

These deferrals are deliberate: L1.1 keeps the diff to pure
JSONL/JSON, so the substrate is ratified independently of any
runtime change.

---

## Trust boundary

L1.1 touches user-influenceable content (pack files) but the gate
remains the same as for every other language pack: manifest
checksum + `python -m language_packs verify`.  The new entries are
authored by hand here, not ingested from an external source.

No dynamic imports, no filesystem traversal, no shell passthrough.

---

## Verification

```
python -m language_packs verify grc_logos_cognition_v1   → OK
python -m language_packs verify he_core_cognition_v1     → OK
python -m language_packs list                            → both packs listed,
                                                            entry counts 29 / 23
python -m core.cli test --suite packs -q                 → green
python -m core.cli eval cognition                        → public 100/100/91.7/100
                                                            (byte-identical;
                                                             new lemmas not yet
                                                             consumed by any
                                                             composer)
```

The cognition eval byte-identity holds because the new lemmas sit on
disk but no composer references them yet — composers will start
consuming them in L1.3.

---

## What this unlocks

L1.2 (AnchorLens class + loader + `default_unanchored_v1` sentinel)
can now start.  Without L1.1's substrate, L1.2 would have nothing
to lens onto: the unanchored-vs-anchored distinction would be
academic because both branches would render the same single lemma.
L1.1 makes anchor lens *possible*; the later phases make it
*operator-visible*.
