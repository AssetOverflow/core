# CHATGPT REMOTE BRIEF — work to do while Shay is away from the library

**Audience:** ChatGPT, acting through its GitHub connector (read repo + open PRs).
**Reviewer:** Claude Code (Opus), at the library. Claude ratifies and fixes minor issues.
**Date scoped:** 2026-05-28. **Status:** active.

> **You (ChatGPT) read this file directly from the repo.** Shay will send a short
> dispatch line from a phone (see §8). Each line points you back here. Do **only**
> the task named, open **one PR**, and **stop**. Do not merge. Claude verifies with
> the CLI (which you cannot run) and merges.

---

## 1. The one rule that overrides everything: `wrong=0`

CORE is a deterministic engine that **refuses rather than guesses**. The serving
math lane is frozen at exactly **3 solved / 47 refused / 0 wrong** (`3/47/0`). A
single wrong answer is a worse outcome than a thousand refusals. Your job never
makes the engine answer *more confidently*; it makes the engine *read more of the
text* so the existing gate has better inputs to either verify or refuse.

You **cannot run the test suite or the `core` CLI** from the connector. That is
fine, because every task in this brief is scoped to a lane where **the worst case
of a mistake is "more refusals," never "a wrong answer."** Claude runs the
invariant gate before anything merges.

---

## 2. The safety boundary (why these tasks are safe to hand you)

There are two lanes in this codebase:

- **Sealed practice lane** — `generate/derivation/*`. Experimental composition.
  `chat/` (serving) does **not** import it. Changes here **cannot** move the
  `3/47/0` serving number. **All your build work lives here.**
- **Serving lane** — `chat/`, and the shared grounding helper
  `generate/math_roundtrip.py::_value_grounds`. wrong=0-sensitive. **Off-limits
  to you** (see §6).

`generate/derivation/extract.py` is in the sealed lane (confirmed: `extract_quantities`
is imported only within `generate/derivation/*`). Over-extraction there is caught
downstream by the self-verification gate, which is **refuse-preferring**. That is
the property that makes this delegable.

---

## 3. State of play (what just shipped — context for your audit)

- **ADR-0176** (merged): multi-step chain model, question-targeting, comparatives
  pack, self-verification gate (`generate/derivation/verify.py`).
- **ADR-0178 / Gap B** (active, multi-phase): comprehension-guided sequential
  composer. **GB-1** = `generate/derivation/clauses.py` (clause segmentation).
  **GB-2** = `generate/derivation/compose.py` (sequential combination). Both
  **just merged as a 2-PR stack**. GB-3 (lookback), GB-4 (held hypotheses), GB-5
  (DAG), GB-6 (measurement) are **not yet built**.
- **ADR-0179** (proposed, doc-only, open PR #446): diagnoses that the structure
  machinery is **built but starved** — `extract.py`'s `digit + single word` regex
  loses word-numbers, multi-word units, currency/decimals, sentence-final numbers,
  and mis-attributes units. Sub-phases EX-1…EX-6. **This is your build work.**

Read these before starting:
- `docs/decisions/ADR-0178-compositional-structure.md` (esp. §"wrong=0 obligations", §"Sub-phases")
- `docs/decisions/ADR-0179-extraction-richness.md` (the full extraction plan)
- `generate/derivation/extract.py` (~40 lines — the file you mostly edit)
- `generate/derivation/clauses.py`, `generate/derivation/compose.py` (GB-1/GB-2)
- `tests/test_adr_0178_gb1_clauses.py`, `tests/test_adr_0178_gb2_compose.py` (test style to mirror)
- Gold cases: `evals/gsm8k_math/train_sample/v1/cases.jsonl` (grep ids `0003 0019 0021 0024 0033 0041`)

---

## 4. STREAM A — the double-check (do this FIRST, it's read-only)

CLAUDE.md mandates a **lookback review** before the next phase of a multi-phase
ADR. GB-1 and GB-2 are a 2-PR stack on `generate/derivation/` and GB-3 is next, so
this is owed. You are well-suited to the **read-only** half: you read, you report,
you cannot break anything.

**Task:** audit GB-1 (`clauses.py`) + GB-2 (`compose.py`) against the ADR-0178
claims and produce a findings report. **Do not change any code in this stream.**

Check, and write down findings for, each of:

1. **Doc-vs-impl drift.** Does `clauses.py` / `compose.py` actually do what
   ADR-0178 §"Sub-phases" GB-1/GB-2 says? Note any signature/scope differences,
   anything the ADR promised that isn't there, anything present that the ADR
   didn't scope.
2. **wrong=0 obligation coverage** (ADR-0178 §"wrong=0 obligations", items 1–5).
   For each obligation, find the test in `tests/test_adr_0178_gb*` that would
   **fail if the obligation were violated**. If you can construct an input where a
   *spurious / unlicensed structure* (obligation #4) or an *irreducible hold*
   (#2) might be admitted/resolved, write it down as a candidate hazard — **do not
   fix it**, just flag it with the exact input string and why.
3. **Refuse-preferring on ambiguity.** Trace: when a clause's local op is
   ambiguous, does `clause_local_results` (GB-1) and `compose_sequential` (GB-2)
   resolve to a hold (`None` / refuse) rather than guess? Cite the line.
4. **Determinism.** Any iteration over a `set`/`dict` without ordering, any
   reliance on insertion order that isn't guaranteed, any nondeterministic tie-break?
5. **Cross-PR consistency.** GB-2 builds on GB-1's `ClauseResult`. Do the dataclass
   shapes, `None`/hold conventions, and unit handling compose cleanly?

**Output:** create a branch `audit/adr-0178-gb1-gb2-lookback`, add **one** markdown
file `docs/handoff/AUDIT-ADR-0178-GB1-GB2.md`, and open a PR titled
`audit: ADR-0178 GB-1/GB-2 lookback (findings only — no code change)`. Categorise
findings as **solid / gaps (no risk) / drift (need amendment) / hazards (live
wrong=0 risk)**. Every hazard must quote the exact triggering input. **No code edits
in this PR.**

---

## 5. STREAM B — the build (ADR-0179 extraction, sealed lane only)

The composer is starved by `extract.py`. Enrich it. **One sub-phase = one PR.**
Each sub-phase only touches `generate/derivation/extract.py` and its test file
`tests/test_adr_0179_extract.py` (create it; mirror the style of
`tests/test_adr_0178_gb2_compose.py` — plain input-string → `assert`). Stay
**lexeme-level / orthographic** (ADR-0165): patterns for "what a number-piece looks
like," **never** grammar templates for "how words combine to mean X" (combining is
the search's job, not the extractor's).

Do these four, in this order. Each is independent; each can ship alone:

- **EX-1 — word-numbers.** `"three"`, `"twelve"`, `"twenty-four"` should extract as
  values. Reuse the existing `WORD_NUMBERS` mapping / `en_numerics_v1` if present
  (grep for `WORD_NUMBERS`); do **not** hand-roll a new number table if one exists.
  Tests: `"three apples"` → value `3.0`; a sentence mixing digit and word numbers
  extracts both, left-to-right.
- **EX-3 — multi-word units.** `"12 jumping jacks"` should attach unit
  `"jumping jacks"`, not just `"jumping"`. Lexeme-level: a number followed by one
  or more lowercase word tokens. Be conservative — over-greedy units cause
  *refusals* (safe) not wrong answers, but keep it tight. Tests: `"12 jumping jacks"`
  → unit `"jumping jacks"`; single-word units still work (don't regress GB-1/GB-2 tests).
- **EX-4 — list-unit inheritance** *(highest payoff — unblocks gold case 0024).*
  In a same-unit list like `"20, 36, 40 and 50 push-ups"`, the trailing unit
  attaches to **every** number in the list, so GB-2's same-unit list-sum can fire.
  Tests: that list extracts four quantities all with unit `"push-ups"`. Verify
  against case `0024` in `cases.jsonl`.
- **EX-5 — sentence-final numbers.** A number with no following unit word (end of
  sentence, or followed by punctuation) should still extract, with an empty/None
  unit. Tests: `"She had 5."` extracts value `5.0`.

For each PR: branch `feat/adr-0179-exN-<slug>`, title
`ADR-0179 EX-N: <what> (sealed lane, do-not-merge until Claude verifies)`. In the
PR body, state: which gold case(s) it targets, that it touches only `extract.py` +
its test, and that **serving is untouched** (you did not edit `chat/` or
`math_roundtrip.py`).

---

## 6. HARD RULES — forbidden, non-negotiable

- **Never merge a PR.** Leave every PR open. Claude merges after CLI verification.
- **Never touch** any of: `chat/**`, `generate/math_roundtrip.py` (esp.
  `_value_grounds`), `algebra/**`, `field/**`, `vault/**`, `generate/stream.py`,
  `ingest/gate.py`, `language_packs/compiler.py`, identity/safety/ethics packs, CI
  workflow files, or any test that currently passes (don't "fix" green tests).
- **Do EX-1, EX-3, EX-4, EX-5 only.** **Do NOT do EX-2** (currency/decimal) — it is
  entangled with a wrong=0-sensitive grounding change in `_value_grounds` that
  **only Claude does**. **Do NOT do EX-6** (measurement — needs the CLI). If you
  think EX-2 is needed, write a note in the PR body; don't touch the grounding.
- **No new dependencies, no network calls, no config/threshold changes.** Do not
  weaken any numeric threshold (e.g. `1e-6`) to make something pass.
- **No grammar templates, no ML, no fuzzy/approximate matching.** Lexeme/orthographic
  patterns only.
- **Determinism:** left-to-right order, no unordered-set iteration affecting output,
  no randomness, no timestamps in output.
- **One sub-phase per PR. Small diffs.** If a change grows beyond `extract.py` + its
  test, stop and leave a note instead.
- **If unsure, refuse the change and write a note** in the PR body. A note Claude
  reads is worth more than a guess Claude has to revert.

---

## 7. What Claude does when back at the library (so you know the handoff)

For each open PR, Claude will: read the diff → run `core test --suite full -q`
and the relevant `tests/test_adr_0179_extract.py` → run the **lane-SHA gate** to
prove serving stays `3/47/0` byte-identical → run `core eval` on the gold cases to
see if any extraction-blocked case (0003/0024) now flips under self-verification →
fix minor issues (naming, a missed edge token, a test assertion) → merge or leave
review comments. Your audit report (Stream A) feeds Claude's GB-3 lookback.

---

## 8. MOBILE DISPATCH LINES (copy-paste one at a time from the phone)

Send these to ChatGPT one at a time. Each is self-contained; ChatGPT pulls the full
brief from the repo itself.

```
Read docs/handoff/CHATGPT-REMOTE-BRIEF.md in the AssetOverflow/core repo, then do STREAM A exactly as written. Read-only audit, one findings PR, do not change code, do not merge.
```
```
Read docs/handoff/CHATGPT-REMOTE-BRIEF.md, then do STREAM B EX-4 (list-unit inheritance) exactly as written. Only edit generate/derivation/extract.py and its test. One PR. Do not merge.
```
```
Read docs/handoff/CHATGPT-REMOTE-BRIEF.md, then do STREAM B EX-1 (word-numbers). Reuse WORD_NUMBERS if it exists. Only extract.py + its test. One PR. Do not merge.
```
```
Read docs/handoff/CHATGPT-REMOTE-BRIEF.md, then do STREAM B EX-3 (multi-word units). Only extract.py + its test. Keep units tight. One PR. Do not merge.
```
```
Read docs/handoff/CHATGPT-REMOTE-BRIEF.md, then do STREAM B EX-5 (sentence-final numbers). Only extract.py + its test. One PR. Do not merge.
```

**Suggested order:** Stream A first (it's owed and risk-free), then EX-4 (best
payoff), then EX-1 / EX-3 / EX-5 in any order. They don't depend on each other.

---

## 9. If ChatGPT gets confused or asks to do more

Tell it: *"Stop. Do only the one task. Leave a note in the PR body for anything
else. Do not merge, do not touch serving, do not touch `_value_grounds`."* Then
move to the next dispatch line, or save it for Claude.
