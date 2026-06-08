# Comprehension organ capability ledger

**As of:** `main` @ `801f0e23` (after #646–#648). A take-stock record of the
off-serving comprehension system built so far — what each organ does, where it
lives, the lane that proves it, and what is deliberately deferred.

This is a **consolidation** artifact (docs only, no capability change). It exists
so the next capability lands against a written whole rather than a stack of
per-batch ledgers.

## The shape of the work

We stopped patching one GSM8K shape with one reader rule. Each capability is now
a small **organ** built down a fixed ladder, off the sealed serving path:

```text
gold (ruler) → setup oracle → solver → answer-verifier → reader → router/contemplation → proposal ledger
```

- **gold / setup oracle** — span-free canonical *setup* signature; a fixture's
  `expect` (`solved` / `solver_refuses` / `reader_refuses`) is checked against an
  independent gold ruler, not against the reader that produced it.
- **solver** — pure typed computation over the setup; refuses (never guesses)
  outside its competence.
- **answer-verifier** — ties a solved value to a labeled answer choice
  (`generate/answer_choices/verify.py`), shared across organs.
- **reader** — text → typed setup, or a closed-set `Refusal`.
- **router / contemplation** — picks exactly one organ; on its own family a
  refusal can become a **proposal**; on foreign text it must step aside.
- **proposal ledger** — proposals are `proposal_only` / `mounted:false` /
  `requires_review:true`, content-addressed, never self-installed; they flow
  through the existing `teaching/*` HITL flywheel (ADR-0055/56/57), never a
  parallel correction path.

### The off-serving guarantee (load-bearing)

Every organ imports **no** `generate.derivation` and **no**
`core.reliability_gate`. That import-disjointness is what makes it
*structurally impossible* for this whole subsystem to regress the sealed GSM8K
serving metric or the pinned-SHA lanes. It is checked, not asserted — the
router-hygiene + off-serving greps are part of each batch's acceptance.

## Organs

### R1 — relational arithmetic

- **Capability.** "Quantity per container × containers", inverse frames, and the
  relational single-step arithmetic family. The first organ; established the
  gold→oracle→reader ladder.
- **Lives in.** `generate/` reader + `evals/setup_oracle/` (gold `r1_gold.jsonl`).
- **Lane.** setup oracle **7 / 0 / 3** (7 solved, 0 wrong, 3 refused-correct).
- **Ledger.** `docs/analysis/r1-inventory-ledger-*.md`.

### R2 — finite integer constraints

- **Capability.** Two-category integer constraint problems (a finite-integer
  constraint compiler: enumerate the bounded integer solution space, refuse if
  not uniquely determined). ADR-0217 (renumbered from 0211 — collided with the
  conformal-falsification-bench ADR; see that ADR's header).
- **Lives in.** `generate/` constraint reader + `evals/constraint_oracle/`
  (gold + reader lane).
- **Lane.** reader **10 / 0 / 0**.
- **Ledger.** `docs/analysis/r2-inventory-ledger-*.md`;
  `docs/decisions/ADR-0217-r2-finite-integer-constraint-compiler.md`.

### R3 — explicit single-rate (+ exact minute/hour conversion)

- **Capability.** A single explicit rate (`<N> <plural> per <singular>`), one
  duration or quantity unknown, compound-unit algebra
  (`mile/hour = quantity/time`). R3.2 adds **exact** time-unit conversion:
  `60 miles per hour for 30 minutes → 30 miles`. Conversion is rational
  (`fractions.Fraction`), confined to the solver, **int-or-refuse — no float
  path**. A non-convertible duration (`…per hour for 3 gallons`) refuses
  `rate_unit_mismatch` and stays a proposal surface.
- **Lives in.** `generate/rate_comprehension/`
  (`units` / `model` / `conversion` / `solver` / `reader`) +
  `evals/rate_oracle/` (gold `rate_gold.jsonl`).
- **Lane.** gold **13 / 13 valid** (7 solved / 2 solver_refuses / 4 reader_refuses);
  reader **9 setup_correct / 0 wrong / 4 refused** → answers **7 / 0 / 6**.
- **Ledger.** `docs/analysis/r3-rate-inventory-ledger-*.md`,
  `r3-2-unit-conversion-2026-06-08.md`.

## Shared machinery

### Router + contemplation + proposal loop

- **Router** (`core/comprehension_attempt/`) classifies text and routes to
  **exactly one** organ (`r1_quantitative` / `r2_constraints` / `r3_rate`),
  collecting one attempt per organ and selecting the unique `setup_correct`.
- **Contemplation** (`generate/contemplation/pass_manager.py`) drives
  read→solve→verify and lands on one of a closed set of **terminals**
  (`SOLVED_VERIFIED` / `REFUSED_KNOWN_BOUNDARY` / `PROPOSAL_EMITTED` / …).
- **Failure families** (`core/comprehension_attempt/failure_family.py`) map each
  closed-set refusal reason to a family with `must_remain_refused` /
  `proposal_allowed` / `owner`. Only *rate-like growth surfaces*
  (`unsupported_rate_duration`, the unsupported system/clause families) propose;
  boundaries that must stay refused (non-integer, temporal-state, underdetermined)
  do not.

### Proposal-review reporter (RPT)

- `core/proposal_review/` — a read-only reporter over the emitted proposal
  ledger: counts, families, owners, content addresses. Deterministic CLI
  (`python -m core.proposal_review`). It *reports*; it never mounts or ratifies.
- **Ledger.** `docs/analysis/proposal-review-reporter-*.md`.

### idle_tick read-only visibility (IT)

- `chat/runtime.py::idle_tick` gained an **opt-in, read-only** proposal-review
  sub-pass (`RuntimeConfig.review_pending_proposals`, default `False`),
  failure-isolated, that surfaces pending proposals during idle without doing
  work, setting a checkpoint, or ratifying anything.
- **Ledger.** `docs/analysis/proposal-review-idle-integration-*.md`.

## Standing invariant — router/organ hygiene

> **No organ may block another organ's legitimate proposal unless it has first
> positively recognized the input as its own family.** On foreign text an organ
> must refuse with the non-substantive `input_shape` family — never a
> substantive boundary.

Pinned by `tests/test_router_organ_hygiene.py` (#646): for each organ × every
*other* organ's gold, the refusal must map to `input_shape`. This caught the
recurring over-broad-refusal hazard three times before it was crystallized
(N6 `category_pair_not_found`, R3e `temporal_state`, R3.1 `missing_rate`). Every
new organ must clear this lane before it ships.

- **Ledger.** `docs/analysis/router-organ-hygiene-invariant-*.md`.

## Whole-system lane state (this commit)

| Lane | State |
|---|---|
| R1 setup oracle | 7 / 0 / 3 |
| R2 reader | 10 / 0 / 0 |
| R3 gold | 13 / 13 valid (7 / 2 / 4) |
| R3 reader → answers | 9 / 0 / 4 → 7 / 0 / 6 |
| router-organ-hygiene | green |
| off-serving (import grep) | clean — no `generate.derivation` / `core.reliability_gate` |
| GSM8K serving | unchanged (sealed) |

`answer_wrong == 0` across every organ. The discipline is "6/0/6 over 11/2/0" —
breadth never bought with a single wrong answer.

## Deferred (named, not forgotten)

- **R3.3** — length (`mile ↔ km`) and currency (`dollar ↔ cent`) conversion.
  Build only if an existing R3 fixture/proposal needs it; the rational-conversion
  substrate is already proven for time.
- **Combined / multi-rate** — two rates composing (work rates, closing speeds).
  Next major capability; build down the full ladder
  (gold + setup oracle → solver → reader → router/contemplation wiring), **not**
  reader-first.
- **Clock-time intervals**, compound conversions, percentage/ratio organs.

## Next capability (decision pending operator go)

Per the standing plan: after this consolidation, either **R3.3** (only if an
existing R3 fixture/proposal demands it) or, preferred, **combined-rate** down
the ladder `CMB-a` (gold + setup oracle) → `CMB-b` (solver) → `CMB-c` (reader) →
`CMB-d` (router/contemplation wiring + ledger). Do **not** start at the
combined-rate reader.
