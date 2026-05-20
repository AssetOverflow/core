# Writing-Chain Harvester — Specification

**Status:** Proposed (specification only — no code shipped)
**Date:** 2026-05-20
**Author:** Shay
**Companion to:** [ADR-0087](../decisions/ADR-0087-rhetorical-style-axis.md)

---

## Purpose

The writing curriculum needs *thousands* of ratified rhetorical
chains (claim → evidence → warrant; evidence → support → conclusion;
hedge → uncertainty → revision; etc.) to operate at PhD level.
Today the entire `cognition_chains_v1` corpus has ~21 active chains
for ~22 lemmas — a number chosen so each chain could be hand-authored
and reviewed by the project author. PhD-level writing operates on
orders of magnitude more.

Two paths to fill that gap:

| Path | Cost | Risk |
|---|---|---|
| Hand-author every chain | Prohibitive | None (matches existing discipline) |
| LLM-generate then accept | Cheap | Violates the no-LLM-content rule; reintroduces drift |

Neither is viable. This spec defines a **third path**: a *harvester*
that proposes candidate rhetorical chains by extracting them from
reviewed expert prose (peer-reviewed journals, ratified technical
documentation, the project author's own canonical writing) — one
proposed `(subject, predicate, object)` triple at a time, each
surfaced to a human reviewer for accept/reject via the existing
teaching/review loop.

The harvester does no LLM-style generation. It *extracts* structure
from already-reviewed text, surfaces it as a proposal, and lets the
existing `core teaching propose / review / accept` pipeline carry the
proposal to ratification. The reviewer's accept/reject is the load-
bearing trust boundary, identical in shape to the one ADR-0084
content used.

The harvester is the writing curriculum's **Layer 0**.

---

## Trust boundary

This spec touches a high-risk surface: external prose ingestion. The
input is text the author did not write. The output is candidate
content for a corpus that downstream surfaces draw from. Every step
must enforce that no input prose token ends up on a user surface
without passing through a human review gate.

| Boundary | Enforcement |
|---|---|
| Input prose | Read-only from a *manifest* of approved sources (each source pinned by checksum). No web fetch at harvest time. No automatic source admission. |
| Candidate proposals | Land in the existing teaching-proposal queue. NEVER auto-accepted. NEVER ratified without `core teaching review --accept`. |
| Tokens in proposals | Restricted to lemmas already in mounted packs (lexicon residency check) + a small "novel-token" candidate flag that requires explicit operator promotion before the proposal is ratifiable. |
| Output corpus | Existing teaching-corpus path. Harvester proposals are tagged with provenance `harvester:<source_id>:<line_no>` so any accepted chain can be traced back to the prose it came from. |

**No bypass of the review path is permitted.** The harvester
produces *proposals*, never *content*.

---

## Architecture

### Stage 0 — Source manifest

`packs/writing_sources/<corpus_id>/manifest.json` declares an
approved-source corpus:

```jsonc
{
  "corpus_id": "scientific_method_canon_v1",
  "version": 1,
  "issued_at": "2026-05-21T00:00:00Z",
  "sources": [
    {
      "source_id": "popper_logic_of_scientific_discovery_1959_ch01",
      "title": "The Logic of Scientific Discovery, Ch.1",
      "author": "Karl Popper",
      "license": "fair-use:short-quotation",
      "path": "raw/popper_1959_ch01.txt",
      "checksum": "<sha256 of raw text bytes>"
    },
    ...
  ],
  "checksum": "<sha256 of this manifest minus checksum field>",
  "provenance": "writing-harvester:reviewed:2026-05-21"
}
```

Sources are added by *human admission only*. The harvester never
auto-discovers a source. The manifest is checksum-pinned the same
way every other CORE pack is.

### Stage 1 — Sentence segmentation + clause extraction

`writing_curriculum/harvester/segment.py`:

- Tokenize raw text into sentences (deterministic, rule-based — same
  discipline as existing pack compilers; no statistical tokenizer).
- For each sentence, identify candidate clauses by punctuation +
  conjunction markers.
- Output: a typed stream of `(source_id, line_no, sentence_no,
  clause_no, raw_clause_text)` records.

This stage produces zero CORE content. It only structures the input.

### Stage 2 — Rhetorical-move classification

`writing_curriculum/harvester/classify.py`:

- For each clause, apply a *deterministic* pattern matcher (rules,
  not learned) to classify the clause's likely rhetorical move:
  - `claim`: declarative assertion without explicit warrant marker.
  - `evidence`: clause introduced by `"because"`, `"as shown by"`,
    `"the data indicate"`, etc.
  - `warrant`: clause introduced by `"therefore"`, `"hence"`,
    `"this implies"`, etc.
  - `concession`: clause introduced by `"although"`, `"while"`,
    `"granted"`, etc.
  - `hedge`: clause containing `"may"`, `"suggests"`, `"appears"`,
    `"possibly"`, etc.
  - `definitional_move`: clause matching `"X is Y"` pattern with X
    being a candidate technical term.
- Output: typed records `(source_id, ..., clause_text, move,
  confidence)`.

The classifier is deliberately conservative. Ambiguous clauses
output move `unknown` and are skipped at the proposal stage. No
classifier weight is trained — the pattern set is hand-maintained
and reviewed like any other ratified discipline.

### Stage 3 — Triple extraction

`writing_curriculum/harvester/extract.py`:

For each clause classified as a known move, attempt to extract a
`(subject, predicate, object)` triple where:

- `subject` and `object` resolve to lemmas in mounted packs (via
  `chat.pack_resolver.resolve_lemma`).
- `predicate` is one of the existing relation predicates the
  cognition / relations corpora already use (`requires`,
  `supports`, `grounds`, `precedes`, `entails`, `contrasts_with`,
  `evidences`, `causes`, `implies`).
- A new predicate is allowed ONLY if proposed as a separate
  candidate with explicit `new_predicate: true` flag — never
  silently introduced.

Extraction outputs candidate `TeachingProposal` records ready for
the existing `core teaching propose` path. Each proposal carries:

```jsonc
{
  "proposal_id": "harvester:scientific_method_canon_v1:popper_1959_ch01:L42",
  "chain_id": "<auto-generated, prefixed with `harvested_`>",
  "subject": "evidence",
  "predicate": "supports",
  "object": "claim",
  "intent_tag": "cause",
  "source_clause": "<the original prose clause, verbatim>",
  "source_id": "popper_logic_of_scientific_discovery_1959_ch01",
  "source_line": 42,
  "rhetorical_move": "evidence",
  "extractor_confidence": "high|medium|low",
  "extracted_at": "<ISO timestamp>",
  "review_state": "pending"
}
```

The `source_clause` field is REQUIRED. Every proposal carries the
exact prose it came from so a reviewer can verify the extraction.

### Stage 4 — Review queue integration

The harvester writes proposals to the existing teaching-proposal
pipeline (`teaching/store.py`). No new review mechanism. No new
ratification gate. The proposal is exactly the same shape as a
hand-authored one with two extra metadata fields (`source_id`,
`source_line`) that the existing pipeline preserves but doesn't
require.

This is the load-bearing design choice: **the harvester adds a
proposal producer, not a proposal consumer.** Reviewers see
harvested proposals in the same queue as hand-authored ones, judge
them with the same criteria, accept/reject with the same commands.

### Stage 5 — Provenance audit

`writing_curriculum/harvester/audit.py`:

A diagnostic tool that, given any chain in any teaching corpus,
reports whether it was hand-authored or harvested, and if harvested,
which source/line. Operators can run this to spot-check the
provenance of any surface the system produces.

---

## Determinism + replay

- Sentence segmentation, classification, and extraction are all
  deterministic functions of `(source_text, harvester_version)`.
- Running the harvester twice on the same input manifest produces
  byte-identical proposals.
- Harvester version is pinned in the proposal `extracted_at` metadata.
- Re-running the harvester against an updated input manifest is
  additive — it generates new proposals for new sources, never
  retroactively modifies prior proposals.

This is the same determinism discipline the rest of CORE follows.

---

## What the harvester is NOT

| Not | Why |
|---|---|
| A summarizer | It extracts triples, not summaries. No prose generation, no paraphrase. |
| A learned model | Pattern rules, hand-maintained. No statistical training. |
| An auto-ratifier | Every proposal goes through human review. The reviewer is the trust boundary. |
| A source admitter | Sources are admitted by `core writing sources add <path>` (human-initiated) only. No web crawler. |
| A revision engine | Revision (proposing edits to ratified chains) is a separate spec — possibly the next one. |
| A style detector | Source corpus selection encodes the style; the harvester doesn't classify "is this scientific?" — operators decide which corpora to harvest from. |

---

## Acceptance criteria for the spec → first implementation PR

When the first implementation PR for this spec opens, it must:

1. Ship Stage 0 (source manifest schema + loader) and Stage 1
   (segmentation) only. Not Stages 2-5.
2. Include one tiny ratified source corpus (e.g., a public-domain
   short essay) as the fixture.
3. Produce a deterministic dry-run report
   (`core writing harvest --dry-run --source <id>`) that shows the
   segmented sentences but does NOT write to the teaching-proposal
   queue.
4. Pass a "no surface emission" test: nothing the harvester produces
   reaches a user surface in this first PR.

This sequencing — substrate, then dry-run, then propose pipeline,
then accept-loop integration — mirrors ADR-0084 → 0085's
substrate-first discipline.

Stages 2-5 land in follow-up PRs, each with the same gate (no
surface emission until human review explicitly accepts the
proposals).

---

## Open questions for the implementation phase

These are deliberately left for the implementation PR to resolve,
not pre-decided here:

1. **Segmentation library choice.** Pure-Python rule-based (zero
   dependency, matches CORE's no-statistical-tokenizer discipline)
   vs `nltk`/`spacy` sentence segmenters (battle-tested but pull in
   model weights). Recommendation: pure-Python. Open for
   reconsideration only if the rule-based output is demonstrably
   worse on the fixture corpus.
2. **Source-license boundary.** What counts as an admissible
   source? Public-domain only? Fair-use short quotation? Operator-
   licensed corpora? Worth an explicit policy doc before any
   non-public-domain source is admitted.
3. **Reviewer UX.** Harvested proposals carry source-clause context
   that hand-authored ones don't. The review tool should display
   this context. Whether that's a CLI flag or a separate review
   surface is an implementation choice.
4. **Cross-corpus chain composition.** Can a harvested chain whose
   subject is in `en_core_cognition_v1` and whose object is in
   `en_core_relations_v1` be ratified into a third corpus, or must
   each pack stay in its own corpus? Likely answer: yes, via the
   existing cross-pack-chain mechanism (ADR-0064), but worth
   exercising on a real example before committing.

---

## Cross-References

- [ADR-0087](../decisions/ADR-0087-rhetorical-style-axis.md) — the
  axis this harvester ultimately feeds.
- [ADR-0084](../decisions/ADR-0084-definitional-layer.md) /
  [ADR-0085](../decisions/ADR-0085-gloss-aware-cause.md) — substrate-
  before-consumer sequencing pattern this spec adopts.
- [ADR-0064](../decisions/ADR-0064-cross-pack-teaching.md) — cross-
  pack teaching corpora mechanism the harvester will reuse.
- `teaching/store.py` — the proposal-queue integration point.
- `core teaching propose / review / supersede` — the existing review
  pipeline the harvester producer feeds.
