# L17 brief — ADR-0131.G.6 — Capability axis: capacity-rate verbs

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g6-rate-capacity -b feat/adr-0131-g6-rate-capacity origin/main
cd ../core-adr-0131-g6-rate-capacity
```

**Scope.** Admit capacity-rate problems — "Bob can shuck 10 oysters in 5
minutes. How many oysters can he shuck in 2 hours?" is the shortest
unambiguous GSM8K sample case (81 chars, case `gsm8k-0014`). No part of
the current parser or candidate graph handles `"<Actor> can <verb> N
<unit> in M <time-unit>."` or `"How many <unit> can <actor> <verb> in T
<time-unit>?"`. Both are missing.

**Pre-flight check (run before coding):**

```python
from generate.math_candidate_graph import parse_and_solve
r = parse_and_solve(
    "Bob can shuck 10 oysters in 5 minutes. How many oysters can he shuck in 2 hours?"
)
assert r.refusal_reason is not None  # currently refuses — this is the gap
```

**Architecture constraint.** `math_solver.py` and `math_problem_graph.py`
are **off-limits** — do not modify them. The capacity-rate path must be
self-contained in the parser + candidate graph. Implement as a
**short-circuit path in `parse_and_solve`**: when both a capacity-rate
statement candidate and a capacity-rate question candidate are found,
compute `(N / M) × T` (with time-unit conversion) and return the answer
directly, bypassing `_build_graph` and `solve`. This is structurally
identical to the aggregate path (`entity=None` → solver sums), which also
short-circuits at the question layer.

**Reference docs (read these, only these):**

1. `generate/math_candidate_parser.py` lines 424–763 — the initial-state
   extractor and question extractor patterns; model new extractors on
   these shapes (`@dataclass(frozen=True, slots=True)`, return
   `list[Candidate...]`, compile regex as module-level `Final` constants).
2. `generate/math_candidate_graph.py` lines 277–400 — `parse_and_solve`
   structure; see how the aggregate path branches before `_build_graph`.

**What to ship:**

- **Parser additions** in `generate/math_candidate_parser.py`:

  - `CandidateCapacityRate` frozen dataclass: `actor`, `count`
    (float), `unit`, `per_count` (float), `per_unit`, `source_span`.
    Computed rate `= count / per_count`.
  - `_CAPACITY_RE`: matches `"<Actor> can <verb> N <unit> in M
    <time-unit>."` — closed `<verb>` set: `shuck`, `pick`, `read`,
    `write`, `run`, `make`, `produce`, `pack`, `paint`, `type`; closed
    `<time-unit>` set: `second`, `minute`, `hour`, `day`.
  - `extract_capacity_candidates(sentence) -> list[CandidateCapacityRate]`.
  - `CandidateCapacityQuestion` frozen dataclass: `actor` (str | None),
    `unit`, `per_count` (float), `per_unit`, `source_span`.
  - `_CAPACITY_Q_RE`: matches `"How many <unit> can <actor> <verb> in T
    <time-unit>?"` — same closed verb + time-unit sets; `<actor>` may be
    a pronoun (`he`, `she`, `they`, `it`).
  - `extract_capacity_question_candidates(sentence) -> list[CandidateCapacityQuestion]`.
  - Time-unit conversion helper: `_to_seconds(count, unit) -> float` —
    second=1, minute=60, hour=3600, day=86400. Division gives
    rate-per-second; multiplication gives total count.

- **Candidate graph branch** in `generate/math_candidate_graph.py`:
  Add a short-circuit check in `parse_and_solve` before the Cartesian
  product: if `len(statement_sentences) == 1` and the statement yields
  exactly one `CandidateCapacityRate` and the question yields exactly one
  `CandidateCapacityQuestion`, compute `rate_per_sec × T_seconds` and
  return. Actor pronoun resolution: if `question.actor` is a pronoun,
  accept any capacity candidate; if it is a named entity, require it to
  match `capacity.actor` (case-insensitive). `wrong == 0` must hold; if
  the actor doesn't match or the rate is zero, return refusal.

- **Curated axis lane** at
  `evals/math_capability_axes/G6_rate_capacity/v1/cases.jsonl` —
  **≥16 cases**:

  | Shape | Count | Notes |
  |---|---|---|
  | Same time-unit in statement and question | ≥4 | minutes → minutes |
  | Cross time-unit (statement minutes, question hours) | ≥4 | requires conversion |
  | Pronoun actor in question | ≥4 | "how many can he …" |
  | Refusal: mismatched unit (oysters vs books) | ≥4 | wrong==0 probe |

  Include `gsm8k-0014` verbatim as one case (source-labeled, not a
  special branch — the general path must admit it).

- **Runner + report** at `evals/math_capability_axes/G6_rate_capacity/v1/`.
  Same shape as G5 runner. `wrong == 0` gate.

- **Tests** at `tests/test_adr_0131_G6_rate_capacity.py` (**≥15**):
  - `_CAPACITY_RE` matches canonical forms.
  - `_CAPACITY_Q_RE` matches pronoun and named-actor forms.
  - Same-unit and cross-unit round-trips produce correct counts.
  - `gsm8k-0014` verbatim admits with answer `240.0`.
  - Mismatched-unit refusals hold.
  - `wrong == 0` on full axis lane.
  - Byte-equal report across two runs.
  - B3 lane regression guard.
  - GSM8K safety rail: `admitted_wrong == 0` preserved.

- **ADR** `docs/decisions/ADR-0131.G.6-rate-capacity.md`. Parent:
  ADR-0131.G. Document closed verb set, closed time-unit set, conversion
  table, short-circuit path rationale. State explicitly that
  `math_solver.py` and `math_problem_graph.py` are unchanged. Call out
  deferred: multi-statement rate (duration asserted separately from
  capacity), money/earnings rates (`makes $18/hour`), rate operations
  on pre-existing state.

**Hard constraints:**

- `wrong == 0` on every axis case and the GSM8K safety rail.
- No changes to `math_solver.py`, `math_problem_graph.py`, or
  `math_verifier.py`.
- Closed verb set and closed time-unit set — no wildcard matching.
- `gsm8k-0014` must admit verbatim.
- `report.json` byte-equal across runs.

**Out of scope:**

- Multi-statement rate (duration in a separate sentence from capacity).
- Money/earnings rates ("makes $18.00 an hour" — needs money parsing).
- Rate applied to pre-existing denominator state (existing `apply_rate`).
- Any GSM8K admission beyond gsm8k-0014 and gsm8k-0018 (Xavier goals).

**Target branch.** PR against `main`. Title:
`feat(ADR-0131.G.6): capacity-rate verbs — can-verb-N-in-M shape, axis lane N/N, wrong==0`.

**Exit criterion.** CI green; axis runner exits 0 with `wrong == 0`;
`gsm8k-0014` admits with answer `240.0`; B3 unchanged; GSM8K
`admitted_wrong == 0` preserved; ADR committed.
