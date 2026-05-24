# Parallel dispatch — 2026-05-23

Three lanes, all targeting `main`, no cross-stacking. Reconciliation seat: lead (Shay + main agent).

| Lane | Brief | Agent | Worktree | Branch |
|---|---|---|---|---|
| L1 | [B2 — teaching-corpus math eval](./L1-gemini-B2-teaching-corpus-eval.md) | Gemini | `../core-adr-0131-2-teaching-eval` | `feat/adr-0131-2-teaching-corpus-eval` |
| L2 | [Binding-graph Phase 1 (data model)](./L2-opus2-binding-graph-phase1.md) | Opus#2 | `../core-binding-graph-p1` | `feat/binding-graph-phase1` |
| L3 | [B1 sealed holdout](./L3-sealed-holdout-B1.md) | Opus#2 or Gemini (small) | `../core-adr-0131-1-sealed-holdout` | `feat/adr-0131-1-sealed-holdout` |

Sequential follow-ups (do not dispatch until prerequisites land):
- **B3 — bounded-grammar word-problems (ADR-0131.3)** — waits on L2 reaching Phase 2–3.
- **ADR-0131.4 promotion wiring** — waits on B1.B (#169) + B2 + B3 all landed.
- **ADR-0131.5 GSM8K-removal amendment** — docs-only, lands last.

## ADR-0131.G capability-axis iterations (post-#181 baseline = 0/50)

PR #181 (`ADR-0131.G`) pinned the GSM8K coverage probe as a diff-able admission number with capability-first iteration discipline. Each iteration extends **one** capability axis, ships its own curated coverage cases (axis lane), and re-runs both the axis lane and the GSM8K probe — admission rises (or a refused-reason family deliberately shrinks) as a *side effect*, not the goal. `admitted_wrong == 0` is the non-negotiable gate.

These four are **independent axes** — they can dispatch in parallel, each targeting `main`, each in its own worktree.

| Lane | Brief | Axis | Worktree | Branch |
|---|---|---|---|---|
| L9 | [G.1 verb classes for initial-state](./L9-ADR-0131-G1-verb-classes-initial-state.md) | state-introducing verbs beyond `has/is` | `../core-adr-0131-g1-verb-classes` | `feat/adr-0131-g1-verb-classes` |
| L10 | [G.2 comparatives](./L10-ADR-0131-G2-comparatives.md) | `compare_additive` + `compare_multiplicative` candidate emitters | `../core-adr-0131-g2-comparatives` | `feat/adr-0131-g2-comparatives` |
| L11 | [G.3 numeric literals](./L11-ADR-0131-G3-numerics.md) | money + fractions + compound numbers (consume `en_numerics_v1`) | `../core-adr-0131-g3-numerics` | `feat/adr-0131-g3-numerics` |
| L12 | [G.4 multi-clause composition](./L12-ADR-0131-G4-multi-clause.md) | conjoined subjects + distributive `each` + embedded quantifier phrases | `../core-adr-0131-g4-multi-clause` | `feat/adr-0131-g4-multi-clause` |

| L16 | [G.5 aggregate answer composition](./L16-ADR-0131-G5-aggregate-answer-composition.md) | `combined`/`together` cue vocab + 2/3-entity sum lane | `../core-adr-0131-g5-aggregate` | `feat/adr-0131-g5-aggregate` |
| L17 | [G.6 capacity-rate verbs](./L17-ADR-0131-G6-rate-capacity.md) | `can <verb> N <unit> in M <time>` → rate × duration; first statement-layer admission lift | `../core-adr-0131-g6-rate-capacity` | `feat/adr-0131-g6-rate-capacity` |

Lane interaction notes:
- L11/G.3 unlocks literal recognition that L9/G.1 and L12/G.4 cases rely on; if all four dispatch in parallel and L11 lands first, the others should rebase to pick up richer literal coverage. Each axis can still pass independently using inline integer/word-number literals.
- L12/G.4 is highest-risk (multi-candidate emission expands round-trip filter work); `wrong == 0` evidence in its PR body must be especially explicit.
- None depend on B1/B2/B3 (composite-gate work) — these axes target the architecture's *parser layer*, separate from the promotion gate.

## Discipline (paid-for lessons)

- Every brief opens with `git worktree add` — never share working dirs (lesson from ADR-0123 file-race).
- Target `main` only, never another agent's branch (lesson from #155→#156 force-push orphaning).
- ≤500-word brief, ≤2 reference docs (token-efficiency lesson from ADR-0051/0052).
- Each lane ships its own ratification/lane-gate test; integration is lead's job, not agents'.
