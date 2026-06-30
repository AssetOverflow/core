# Wave R3 Briefs — Theater (the wow, honest)

Date: 2026-06-13
Plan: `docs/workbench/wave-R-mastery-revamp.md` § Wave R3.
Predecessor: Wave R2 complete (#714–#721; all six routes real). Replay
backend already merged (#716, `GET /replay/{turn_id}` → `TurnReplayComparison`).

Four pieces. The Replay Moment is first (its backend exists and the old
artifact-keyed `ReplayRoute` is now stale against it). The others are
independent and can be authored after.

## Standing constraints (all briefs)

Same as Wave R2: worktree off fresh `origin/main`; green-local before push
(`pnpm build && pnpm test`); **STOP after checks green, Shay merges**;
token-only styling (hexScan); shrink-only `NOT_YET_MIRRORED`; conformance
rows (ADR-0162 §6); no new mutation endpoints; no invented data; no
force-directed / nondeterministic layout — ever.

---

## Brief R3-Replay — The Replay Moment (first; reworks + retires)

The hero flow. Turn-keyed sealed replay made *felt*: same prompt, same
genesis substrate → bit-identical envelope, rendered as hash≡hash with an
honest leaf diff. Consumes the merged #716 backend.

**This PR also retires the dead W-026 artifact-keyed replay machinery**
(confirmed zero serving uses) on both sides — the `NOT_YET_MIRRORED` comment
already anticipates it.

### Retirement surface (verified)

- **Python** (`workbench/schemas.py`): delete `ReplayDivergenceSeverity`,
  `ReplayStatus`, `ReplayDivergence`, `ReplayComparison` (the artifact-keyed
  block). Keep the `TurnReplay*` block. Zero word-boundary uses elsewhere.
- **Snapshots**: regenerate both — `pnpm schema:snapshot` (drops
  `ReplayComparison`/`ReplayDivergence`) and `pnpm enum:snapshot` (drops
  `ReplayStatus`/`ReplayDivergenceSeverity`).
- **TS** (`types/api.ts`): remove `ReplayComparison`/`ReplayDivergence`/
  `ReplayDivergenceSeverity`; add `TurnReplayComparison`/`TurnReplayDivergence`
  (+ the `TurnReplayDivergenceSeverity`/`TurnReplayBasis`/`TurnReplayOriginState`
  unions). Remove both `TurnReplay*` entries from `NOT_YET_MIRRORED`.
- **Badges** (`design/components/badges/{types,mappings,index}.ts*`): remove
  `ReplayStatusBadge` + `ReplayDivergenceSeverityBadge` + their meta/types;
  drop their two cases from `enumCoverage.test.ts`. The hero renders the new
  severity (`critical`/`informational`) inline with a `≠` glyph — no new
  enum-tracked badge.
- **API** (`client.ts`/`queries.ts`): remove `fetchReplayComparison`/
  `useReplayComparison`; add `fetchTurnReplay(turnId)` → `/replay/<turnId>` and
  `useTurnReplay(turnId)`.
- **Route dir** (`app/replay/`): delete `ArtifactList`, `ReplayComparisonPanel`,
  `ReplayDiffViewer`, `ReplayMetadataTable`, and the old `replay.test.tsx`.

### New ReplayRoute (turn-keyed hero)

- List journaled turns (reuse `useTraceTurns`) in the left pane (VirtualizedList
  + useListNavigation + SearchInput), same as Trace.
- Select → navigate `/replay/<turnId>` (replace) → `useTurnReplay(turnId)`.
- Hero: `original_trace_hash` vs `replay_trace_hash` rendered big; a clear
  `≡ equivalent` (when `equivalent`) or `≠ diverged` verdict. **Honesty card**
  states `comparison_basis` (`sealed_fresh_runtime_single_turn`) and
  `origin_state` (`unrecorded`) — a divergence means nondeterminism OR
  origin-state influence, never disambiguated; never render divergence as a
  determinism-failure verdict.
- Leaf diff: each `divergence` as a row with `path`, original vs replay, and a
  `≠` glyph; `critical` weighted above `informational`; informational
  divergences (timestamp/cost/digest) explicitly labeled as expected.
- Publishes the `turn` subject for the inspector (identity → detail), like Trace.
- App route `path="replay/:turnId?"`; conformance row turn-keyed
  (loading "Loading turns...", empty "No turns recorded yet. Use Chat to
  create evidence." + `core chat`).
- Tests: hero equivalence (hash≡hash), a tampered-leaf divergence renders `≠` at
  the right path, informational-only divergence still reads equivalent, the
  honesty fields render, j/k spine, replace-mode URL selection.

### Verification

```bash
cd workbench-ui && pnpm build && pnpm test
# plus the Python lane the snapshots feed:
uv run python scripts/dump-schemas.py | diff - workbench-ui/schema-snapshot.json
uv run python scripts/dump-enums.py | diff - workbench-ui/enum-snapshot.json
```

---

## Brief R3-DAG — Deterministic DAG viewer

One hand-rolled component (`design/components/Dag/`): longest-path layering,
lexicographic tie-break, ~150 lines, **golden-file layout tests**, no graph
dependency (force-directed = doctrine violation). Pan/zoom/click-node →
inspector. Consumers: proposal chains, the 8 PCCP proof-promotion scenarios
(`demos/proof_carrying_promotion`), entailment traces. Pure layout function;
golden tests pin node coordinates.

---

## Brief R3-Demo — Demo Theater route

`GET /demos`, `POST /demos/{id}/run` (new read + a scoped run endpoint).
Scenario results with evidence-class badges and "what this proves / what this
does not prove" honesty cards; proposer-was-wrong scenarios visually
highlighted. Backend brief first (Python), then the route.

---

## Brief R3-Ledger — wrong=0 ledger view

Evals renders the correct/refused/wrong triplet as the PRIMARY visualization;
refusal reasons inspectable; failures-first ordering. Additive to the existing
EvalsRoute — no retirement, lowest risk of the four.
