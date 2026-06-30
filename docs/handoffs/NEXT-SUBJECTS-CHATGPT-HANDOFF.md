# Handoff: Next-Subjects Readiness (ChatGPT / GitHub-connector lane)

**Audience:** ChatGPT operating with **read-only GitHub access** (mobile).
**Author:** Claude Code session, 2026-05-30.
**Status:** Active brief. Self-contained — read this file, then execute one task at a time.

---

## 0. What you (ChatGPT) can and cannot do here

You have a **GitHub connector** and nothing else. That means:

- ✅ You can **read and search** any file in `AssetOverflow/core`.
- ✅ You can **reason, synthesize, and draft** new content.
- ❌ You **cannot** run code, run tests, run the CLI, or prove anything empirically.
- ❌ You **cannot** change serving behaviour or evaluation scores.

Therefore **every deliverable in this brief is an execution-free artifact**:
a Markdown analysis, a taxonomy, a draft spec, or a draft data file. Empirical
validation (running `core test`, checking the `wrong=0` invariant, wiring code)
happens **later, in the Claude Code lane, on WiFi**. Your job is the read →
analyze → draft half. Claude's job is the execute → validate → commit half.

### How to return work
For each deliverable, output a **complete file** in a fenced code block, with the
intended repo path on the first line as a comment/heading, e.g.:

````
# FILE: docs/analysis/comprehension-primitive-inventory.md
<full contents>
````

The operator (Shay) will paste it into the repo, or hand it to Claude to land.
**If — and only if — your connector can open issues or PRs**, you may instead
file each deliverable as a GitHub issue titled `[next-subjects] <task id>`; do
**not** push commits directly.

---

## 1. What CORE is (orientation — read `CLAUDE.md` for the full version)

CORE is a **deterministic cognitive engine**: `listen → comprehend → recall →
think → articulate → learn → replay`. It is **not** an LLM wrapper. It decodes
structure that is already present in the input; it does not sample text.

Load-bearing invariants you must respect in everything you draft:

1. **`wrong = 0` is sacred.** On the real-GSM8K serving metric the engine is
   allowed to *refuse* but never to answer *wrong*. Current serving score:
   **6 correct / 44 refused / 0 wrong** on `evals/gsm8k_math/train_sample/v1`.
   Nothing you propose may create a path that could answer wrong.
2. **Serving is frozen until ratified.** The serving path is pinned by
   `scripts/verify_lane_shas.py` and `CLAIMS.md`. Do not propose edits to
   serving modules; propose **new** files only.
3. **Decoding, not generating.** Every proposal must answer: *does this teach
   the engine to find/comprehend structure better* — not *does this store another
   canned answer*. (See the project thesis: "decoding, not generating.")
4. **No synthetic-corpus overfitting.** Hand-authored corpora are
   **validation-only / held-out probes**, rich in hard negatives. They are never
   training/tuning targets. (A past lesson: a 150-case templated set moved the
   synthetic metric massively but real GSM8K barely moved — surface-cue overfit.)
5. **Proposal-only.** ADR drafts are `Status: Proposed (draft)`, never
   `Accepted`. Corpora go under a `proposed/` subfolder. Nothing is wired.
6. **ADR numbers collide easily.** The highest ADR is currently **0195**.
   Many operators work in parallel. **Do not hard-assign a number.** Title your
   ADR drafts `ADR-XXXX — <title>` and let Claude assign the number at land time.
   (We just spent a session fixing a real 0194 collision. Don't recreate one.)

---

## 2. Why we're doing "next subjects" now (and the honest caveat)

The math (GSM8K) frontier is currently **composition-bound**: single-capability
widenings are metric-inert; the wall is *composing* comprehension primitives and,
specifically, the **question-extraction layer**. The heavy lifting there needs
the CLI + test lanes (WiFi + Claude).

So while that waits, this lane does work that is **(a) genuinely safe** (read +
draft, reversible, touches nothing live) and **(b) opportunistically chosen to
feed back into the math** by clarifying which comprehension primitives are
subject-general vs math-specific.

**Honest caveat (do not skip):** `CLAUDE.md` explicitly warns against *"broad
docs-first churn."* This brief is scoped to avoid that. The early tasks are
**analysis that directly informs the math frontier** (high leverage, low volume).
Corpus/ADR drafting is a **gated later phase** that only proceeds if the analysis
shows it's warranted. If you find yourself generating large volumes of
speculative scaffolding, **stop and flag it** — that's the failure mode.

---

## 3. Map of what already exists (read these first; don't reinvent)

- `CLAUDE.md` — the constitution. Read it.
- `docs/decisions/` — all ADRs (0001…0195) + `README.md` narrative.
- `evals/` already contains:
  - `gsm8k_math/` — `train_sample/` (the real metric), `practice/` (sealed),
    `confusers/` (discrimination probes). **This is your structural template.**
  - `math_capability_axes/` — `G1_verb_classes`, `G2_comparatives`,
    `G3_numerics`, `G4_multi_clause`, `G5_aggregate` (+ `README.md`). The
    capability-axis pattern already exists — extend its shape, don't invent a new one.
  - `symbolic_logic/` — a logic lane **already exists**. Survey it before
    proposing any logic work.
  - `identity_divergence/`, `calibration/`, `confusers/`.
- `generate/derivation/` — the comprehension composer:
  `extract.py` (quantity/lexeme extraction), `clauses.py` (segmentation),
  `compose.py` / `accumulate.py` (referent-scoped combination),
  `multistep.py` / `search.py` (bounded search), `verify.py` (the `wrong=0`
  self-verification gate), `pool.py`, `product_bridge.py`.
- `generate/math_candidate_graph.py`, `generate/math_candidate_parser.py`,
  `generate/recognizer_anchor_inject.py` — the serving recognizer→injection→graph spine.
- `CLAIMS.md` + `scripts/verify_lane_shas.py` + `scripts/generate_claims.py` —
  the serving-frozen gate.

> Note: `binding_graph` is **in-flight in branches, not on `main`**. Do not cite
> it as an existing path; if you see it referenced, treat it as future work.

---

## 4. The tasks (do them in order; one deliverable each)

### TASK A — Comprehension-Primitive Inventory & Cross-Subject Leverage Map  *(highest priority; directly helps math)*
**Read:** `generate/derivation/*.py`, `generate/math_candidate_parser.py`,
`generate/recognizer_anchor_inject.py`, `generate/math_candidate_graph.py`,
and skim the ADRs they reference.
**Produce:** `docs/analysis/comprehension-primitive-inventory.md` — a table of
every reusable comprehension primitive the math substrate uses
(entity extraction, quantity extraction, unit grounding, clause segmentation,
referent/pronoun binding, question-frame parsing, completeness gate, round-trip
filter, branch-disagreement gate, …). For each: a one-line description, the file
it lives in, and a column **"subject-general vs math-specific?"** with a short
justification. End with a 5-bullet **"what transfers to other subjects"** summary.
**Why it helps math:** it makes the composition wall legible and tells us which
primitives a new subject could exercise for free.
**Definition of done:** every primitive maps to a real file/function you actually
read; no invented APIs.

### TASK B — Question-Layer Gap Survey  *(directly helps math)*
**Read:** the question-parsing logic in `generate/math_candidate_graph.py` and
related parsers; `evals/gsm8k_math/train_sample/v1/report.json` (the per-case
`reason` strings for the 44 refused cases).
**Produce:** `docs/analysis/question-layer-gap-survey.md` — group the 44 refused
cases by **why the question clause failed to parse/bind** (e.g. aggregate "how
many… in total", residual "how many are left", rate "how much per…", multi-step,
comparative target, …). Rank the groups by (count × estimated tractability).
This is the prioritized backlog for the math question-layer work.
**Definition of done:** every refused case id is assigned to exactly one group;
counts sum to 44; no claim that a case "would pass" — only *why it currently doesn't*.

### TASK C — Subject Readiness Survey + Recommendation  *(decides scope for D+)*
**Read:** `evals/symbolic_logic/`, `evals/math_capability_axes/`,
`docs/decisions/README.md`, and ADRs touching logic (search "0123") and
capability axes (search "0131").
**Produce:** `docs/analysis/next-subjects-readiness.md` — for each candidate
subject below, state: what substrate already exists, which primitives from
Task A it would reuse, what's missing, and a **risk-to-`wrong=0`** note. Then
recommend an ordering. Candidate subjects to assess (you may add one, with
justification):
  1. **Deductive / symbolic logic** (extend `evals/symbolic_logic/` — coherence-aligned, deterministic).
  2. **Reading comprehension / referent binding** (exercises exactly the math composition-wall primitives: coreference, clause binding, question frames).
  3. **Measurement / geometry math axis** (natural extension of `math_capability_axes`).
**Definition of done:** a clear recommended order with the cross-leverage to the
math frontier made explicit. **Stop here and wait for the operator to confirm the
subject before doing Task D.**

### TASK D — Capability-Axis Spec for the chosen subject  *(gated on C)*
**Only after the operator confirms a subject.** Mirror the
`evals/math_capability_axes/` shape: produce `docs/analysis/<subject>-capability-axes.md`
enumerating the axes (analogous to G1…G5), each with: the primitive it tests, a
refusal-first acceptance note, and 2–3 illustrative items. **No corpus files yet.**

### TASK E — Draft ADR for the chosen subject  *(gated on D)*
Produce `ADR-XXXX — <subject> comprehension lane (proposed)` as a Markdown draft
in the repo's ADR style (read 2–3 recent ADRs first for format). `Status:
Proposed (draft)`. It must state the `wrong=0` trust boundary, the eval lane it
would add (validation-only, sealed), and the invariant that proves the field
stays valid. **Leave the number as `XXXX`.**

### TASK F (optional, small) — Held-out probe corpus draft  *(gated on E)*
A **small** (≤20 item) `evals/<subject>/proposed/cases.jsonl` draft, hard-negative
rich, mirroring the `gsm8k_math` case schema (read
`evals/gsm8k_math/train_sample/v1/cases.jsonl` for the exact field shape).
Clearly marked validation-only. Keep it small — this is a shape demo, not a corpus.

---

## 5. Hard "do not" list

- ❌ Do not propose edits to anything under `generate/`, `core/`, `chat/`,
  `field/`, `vault/`, `algebra/`, or any serving/eval-scoring path.
- ❌ Do not modify `evals/gsm8k_math/**`, `CLAIMS.md`, or `report.json`.
- ❌ Do not assign a concrete ADR number.
- ❌ Do not mark anything `Accepted`/`Implemented`.
- ❌ Do not author large corpora or tune anything to surface cues.
- ❌ Do not claim empirical results ("this passes", "wrong stays 0") — you can't
  run anything. Say "expected, to be verified in the Claude lane."

## 6. Handback checklist (what Claude picks up on WiFi)

For each artifact you return, Claude will: assign ADR numbers, run
`core test --suite smoke -q` + the relevant lanes, verify `wrong=0`, and land via
PR. Make that easy: keep each deliverable a single self-contained file with its
target path on line 1, and list at the bottom of each artifact the **"open
questions for the Claude lane"** you couldn't resolve read-only.
