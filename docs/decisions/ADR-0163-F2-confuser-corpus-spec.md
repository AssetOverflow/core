# ADR-0163-F2 — Confuser Corpus: a discrimination probe, not a coverage target

**Status:** Proposed (spec only — no code). Follow-on to ADR-0163 §F (the Track-B
additive practice scale). Corrects the *metric*, not just the data.

> **One line.** A small, curated set of **hard negatives and near-miss confusers**
> whose purpose is to measure whether the reader **refuses what it cannot yet read**
> — success is `wrong = 0` on the confusers, *not* a higher solved count.

---

## 1. Why this exists (the failure it fixes)

ADR-0163 §F added 150 templated additive practice cases. GB-3b flipped 55–96 of
them — but on **real GSM8K (`train_sample`) accumulation fired on only 2/50, 1
correct / 1 wrong**. The synthetic flips did not generalise. The canonical misfire:

> `train_sample-0002`: *"Jan buys 1000 feet of cable. She splits it into 25-foot
> sections. She gives 1/4 to a friend. She puts half in storage. How much does she
> keep?"* (gold 15) — read as `buys 1000 … gives … to` → **996**.

The templated corpus has two defects that *cause* overfitting (memory:
`feedback-synthetic-corpus-overfitting-trap`):

1. **Redundancy** — the 46 gain cases are one template × 46 noun/number swaps, so a
   surface-cue matcher "passes" without comprehension and the CP ledger fills with
   tautological confirmations.
2. **No hard negatives** — there is no problem that *looks* like accumulation but
   isn't (a fraction problem, a disguised-polarity verb, a second actor). The
   confusers are exactly what teach a reader **where to refuse**, and a corpus of
   clean templates contains none.

This spec builds the missing half: the cases that make being wrong *informative*.

## 2. The reframe — what "success" means here

This corpus is a **discrimination probe**, scored the opposite way from a coverage
lane:

| metric | meaning | bar |
|---|---|---|
| **`wrong` on confusers** | the reader committed an answer a confuser was built to trip | **must be 0** |
| **`refused` on confusers** | the reader declined (the correct response to a not-yet-readable shape) | expected-high, honest frontier |
| **`solved` on the paired positives** | the reader genuinely read the near-identical solvable case | real-capability signal |

The headline number is **wrong=0**, never "how many solved." A change that solves
more confusers is only progress if it does so by a **general mechanism** that also
keeps `wrong=0` — and is validated on the held-out real lane, not by passing these
specific rows.

## 3. Anti-overfitting design rules (the load-bearing part)

1. **Minimal pairs.** Every confuser ships with a near-identical *solvable* twin
   that shares its surface cues but has a different correct reading. A reader that
   passes by surface cue alone gets the pair wrong; only a reader that reads the
   *structure* separates them. Example pair:
   - solvable: *"Anna has 25 stickers. She gives 10 **more** to her collection…"* → +10
   - confuser: *"Anna has 25 stickers. She gives 10 **to a friend**…"* → −10
2. **Real-sourced, not invented templates.** Each case is a paraphrase of (or
   structurally drawn from) a real GSM8K problem; record the source id. No new
   generative template that a matcher could learn.
3. **Held-out by contract.** The corpus is a **probe, never a training-to-fit
   target.** If the reader is changed so a confuser stops misfiring, that change
   MUST be a general mechanism (e.g. completeness counting the fractions it
   currently misses), proven not to regress `train_sample`, and the confuser MUST be
   one of *many* of its category so the fix can't be memorisation.
4. **Diversity quota per category.** ≥ ~8 distinct cases per confuser category
   (below), with varied surface forms, so "passing the category" can't be one rule.
5. **Expected-behavior labelling.** Each case is labelled `expected: refuse | solve`.
   Most confusers are `refuse` (the reader can't yet read them and must not guess) —
   so the corpus is primarily a *refusal-correctness* test.

## 4. Confuser categories (grounded in observed real misfires)

| category | what it trips | example (confuser) | correct | expected |
|---|---|---|---|---|
| **disguised-polarity verb** | gain verb that is actually a spend | "He buys a gift **for** 60" (coins) | −60 | refuse |
| **pseudo-accumulation / fractions** | has/gives surface over a fraction-division problem | the 0002 cable problem | (multi-step) | refuse |
| **multi-referent (H1)** | two actors, same unit | "Alice has 6. **Tom** has 2. How many does Alice have?" | 6 | refuse |
| **multi-actor pronoun (ADR-0174)** | ambiguous "he/she" antecedent | "Sam and Tom shopped. **He** bought 5 more." | (ambiguous) | refuse |
| **distractor quantity** | a number not in the computation | "for **3** days", "**25**-foot sections" | (varies) | refuse-unless-consumed |
| **temporal/question-scope (H3)** | question asks *before* a stated change | "…gave 3 away. How many **before** giving any?" | pre-change | refuse |
| **comparative-referent (H2)** | comparative binds to the non-asked actor | "**Tom** picked twice as many. How many did **Alice** pick?" | Alice's | refuse |
| **unit confuser** | different-unit quantities that look summable | "6 **boxes** and 50 **apples**" | (not a sum) | refuse |
| **genuine positive (paired twin)** | the solvable near-identical case | "She gives 10 **more**…" | +10 | solve |

Categories are derived from the actual hazards already proven live (GB-3a H1/H2/H3,
the 0002 misfire, the `buys-a-gift-for` polarity flip) — not invented.

## 5. Schema (`evals/gsm8k_math/confusers/v1/cases.jsonl`)

```json
{
  "case_id": "confuser-v1-0001",
  "question": "…",
  "answer_numeric": 15,
  "category": "pseudo-accumulation",
  "surface_trap": "buys/gives-to over a fraction-division problem",
  "expected": "refuse",
  "pair_id": "confuser-v1-0002",
  "source": "gsm8k-train-sample-v1-0002 (paraphrase)",
  "notes": "fractions 1/4, half and 25-foot sections are unconsumed -> must refuse"
}
```

Deterministic ordering; `pair_id` links minimal pairs; `source` records provenance.

## 6. The runner / how it scores (`confusers/v1/runner.py`)

For each composer under test (accumulation, multiplicative, chain), report **per
category**: `solved-correct / refused / wrong`, plus the **pair-consistency** check
(did the reader separate each minimal pair, or pass both by surface cue?). The gate:

- **`wrong == 0` across all confusers** — the hard bar (a confuser answered is a
  defect, regardless of value).
- **pair-consistency** — a pair where the reader solves the twin but *also* answers
  the confuser (same surface, wrong) is a surface-matching tell → fail.
- `refused` count is reported as the honest frontier, never optimised down by patches.

## 7. How the CP ledger uses it (the real learning value)

Run the general composers over the confusers and `record_case` by gold. The
**wrong attempts on confusers become the negative samples** the templated corpus
lacked — they push the offending `(cue, op, unit_shape)` reliabilities *down*,
which is exactly the discrimination signal CP-2b needs. Positive twins push the
genuine cues up. This is "compare and contrast" with hard negatives, not redundant
template confirmations.

## 8. Construction process (and its guardrails)

1. Start from the proven hazards + real `train_sample` misfires; paraphrase real
   problems into confuser/twin pairs.
2. Curate by hand (small, ≤ ~80 cases); no generative template.
3. Each row carries category + surface_trap + expected + source + pair_id.
4. **Guardrail:** building this corpus is *not* an invitation to grow reader vocab
   to pass it. The corpus is frozen as a probe; reader changes are judged on
   `train_sample` + pair-consistency, never on raw confuser solved-count.

## 9. Acceptance (Proposed → Accepted)

1. The corpus lands (~8/ category, all paired where applicable) with the schema +
   a runner reporting per-category `solved/refused/wrong` + pair-consistency.
2. The current composers score **`wrong = 0`** on it (they should *refuse* nearly
   all — that is the correct, honest result today).
3. A documented baseline (mostly-refuse) is recorded; future reader work is measured
   against it as a **regression gate** (`wrong` may never rise) and a generalisation
   signal (`solved` may rise only via general mechanisms that hold on `train_sample`).

## 10. Non-goals / explicit guardrails

- **Not** a coverage lane; **not** scored by solved-count.
- **Not** to be expanded with templates or used to tune cue vocab reactively.
- **Not** a replacement for `train_sample` as the real-capability measure — it is the
  *refusal-correctness* complement to it.

See [[thesis-decoding-not-generating]],
`feedback-synthetic-corpus-overfitting-trap`, ADR-0178 (GB-3a hazards),
ADR-0177 (CP ledger consumes the hard negatives).
