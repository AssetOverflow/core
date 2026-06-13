# Wave M · Phase B — Calibration / Serving-Discipline Brief Pack

Date: 2026-06-13
Plan: `docs/workbench/wave-M-worthiness.md` § Phase B.
Goal: make the calibrated-learning / serving-discipline loop *visible* — the
gold-tether arena, the reliability gate, "the engine earns the right to
guess." This is the widest worthiness gap.

## Dependency DAG

```
B1 (backend readers) ──┬──→ B2 (Calibration route) ──→ B4 (leeway wiring)
                       └──→ B3 (wrong=0 global frame)
```

**B1 gates everything** — it merges first. B2/B3 are parallel-safe after B1
(disjoint files except the usual train: App.tsx / types/api.ts /
routeConformance / NOT_YET_MIRRORED → strictly sequential merges, union
rebase). B4 last (touches Proposals + Replay rails).

## Standing constraints (all briefs)

- Worktree off fresh `origin/main`; green-local (`pnpm build && pnpm test`,
  plus the Python lane for B1) before push; **STOP after checks green;
  Shay merges.**
- **NEVER re-implement engine math.** Import and call
  `core.reliability_gate` (`conservative_floor`, `license_for`, `Ceilings`,
  `Action`); never reproduce the Wilson floor or θ logic in the workbench.
- **Read-only.** No new mutation endpoints; no execution. The reader reads
  committed artifacts + computes derived numbers via the engine's own
  functions. A calibration view never changes a license.
- Token-only styling (hexScan); schema mirrored + snapshot regenerated +
  drift gate; enum coverage if a new badge enum is added; conformance rows
  (ADR-0162 §6); no invented data — absent calibration evidence renders
  honest absence.

---

## Brief B1 — Calibration readers + endpoints (Python only; GATING)

### Worktree + gates
```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-m-b1 origin/main -b feat/wb-m-calibration-readers
cd ../core-wb-m-b1
ls core/reliability_gate/ledger.py || echo "STOP: reliability_gate missing"
```

### Read first (do not wander)
- `core/reliability_gate/ledger.py` — `ClassTally(class_name, correct,
  wrong, refused, t2_verified, t2_agrees_gold)`; derived `committed`
  (=correct+wrong), `attempted`, `reliability()` (=`conservative_floor`),
  `coverage()`.
- `core/reliability_gate/{floor,gate,ceilings,propose}.py` —
  `conservative_floor(successes, committed)` (Wilson, `N_MIN=10`, 0.0 below);
  `license_for(tally, ceilings, action) -> LicenseDecision(licensed,
  measured, required)`; `Action.PROPOSE` (θ=0.85) / `Action.SERVE` (θ=0.99);
  `Ceilings.required(class_name, action)`.
- `workbench/readers.py` (list_/read_ + `_page` + `_is_allowed` patterns),
  `workbench/api.py` (route wiring), `workbench/schemas.py` + the two snapshot
  generators (`scripts/dump-schemas.py`, `scripts/dump-enums.py`).
- `evals/gsm8k_math/train_sample/v1/report.json` +
  `train_sample_coverage_report.json` — the **persisted calibration
  evidence**.

### Investigate first (decides the reader's source)
Is the live `ClassTally` ledger persisted anywhere at rest? Grep for a
written ledger jsonl/json. **If not** (likely), the reader reconstructs
per-class `ClassTally` from the committed `report.json` per-class outcomes,
then applies the *real* `conservative_floor` + `license_for`. Document which
source you used in the reader docstring + the PR.

### Deliverables
1. `workbench/calibration.py` (new): pure functions that load the committed
   report artifact(s), build `ClassTally` per class, and produce per-class
   rows via the real engine functions — no math re-implemented here.
2. Schemas (`workbench/schemas.py`): `CalibrationClass` (class_name, correct,
   wrong, refused, committed, attempted, reliability_floor, coverage,
   propose_licensed, propose_required, serve_licensed, serve_required) and
   `ServingMetrics` (lane, correct, refused, wrong, source_path,
   source_digest). Mirror in `types/api.ts`; regenerate both snapshots; the
   drift gate must pass.
3. Endpoints (`workbench/api.py`): `GET /calibration/classes` →
   `{items: CalibrationClass[]}`; `GET /serving/metrics` →
   `{items: ServingMetrics[]}` (read `train_sample` + `holdout_dev` committed
   reports; **never** run a lane). Path-validate any id; reads only inside
   allowed eval roots.
4. Trust boundary stated in the PR: read-only over committed artifacts +
   engine-owned derivation; no execution, no mutation.

### Verification
```bash
cd ../core-wb-m-b1
.venv/bin/python -m pytest tests/ -k "workbench_calibration or workbench_schemas or workbench_api" -q
.venv/bin/python scripts/dump-schemas.py | diff - workbench-ui/schema-snapshot.json
```
Add `tests/test_workbench_calibration.py`: a class that cleared SERVE shows
`serve_licensed=true`; a class below `N_MIN` shows `reliability_floor=0.0`
and `propose_licensed=false`; the reader's numbers equal a direct
`conservative_floor`/`license_for` call (proves no re-implementation).

---

## Brief B2 — Calibration / Gold-Tether route (frontend; after B1)

### Gates
```bash
git worktree add ../core-wb-m-b2 origin/main -b feat/wb-m-calibration-route
grep -q "CalibrationClass" workbench-ui/src/types/api.ts || echo "STOP: B1 not merged"
```

### Deliverables
- TS mirrors already landed in B1; add `useCalibrationClasses` /
  `useServingMetrics` query hooks.
- `app/calibration/CalibrationRoute.tsx` — per class: a coverage-vs-Wilson
  bar (reliability_floor vs the cleared θ), correct/refused/**wrong** counts
  (wrong load-bearing), and a plain verdict pill: "earned SERVE", "earned
  PROPOSE", or "not yet licensed". **Failures-first** ordering (lowest
  reliability / un-licensed at top). VirtualizedList + useListNavigation +
  SearchInput; Panel/TabBar detail (Counts / License math / Raw).
- The "License math" tab shows the honest derivation: committed N, Wilson
  floor, θ required, measured ≥ required → licensed — read from B1, not
  computed in the UI.
- Nav entry; Calibration row in `routeConformance` (loading "Loading
  calibration...", empty "No calibration evidence yet." + the practice-lane
  CLI, error). Selection publishes an evidence subject (new `calibration_class`
  kind, inspect-param) — or, if that's too much for one PR, local selection
  + flag the subject-kind as a follow-up.
- Tests: failures-first ordering, the un-licensed/below-N_MIN class renders
  "not yet licensed", the wrong count renders, j/k spine.

### Verify: `cd workbench-ui && pnpm build && pnpm test`

---

## Brief B3 — wrong=0 as a felt global presence (frontend; parallel with B2)

### Gates
```bash
git worktree add ../core-wb-m-b3 origin/main -b feat/wb-m-wrong-zero-frame
grep -q "ServingMetrics" workbench-ui/src/types/api.ts || echo "STOP: B1 not merged"
```

### Deliverables
- A small always-present invariant element in the `Shell` chrome (header
  strip): live **N correct · N refused · 0 wrong**, the zero rendered hard
  (verified token) — sourced from `/serving/metrics`, never invented; when
  unavailable, render an honest "metrics unavailable", never a fake zero.
- It links to the Calibration route (B2) and the Evals wrong=0 ledger.
- **Doctrine line:** the strip states an invariant, it does not *claim*
  correctness it can't read — if the committed report shows wrong>0 it shows
  wrong>0 in the contradicted token (the strip must be able to show a
  non-zero wrong honestly; it is a mirror, not a slogan).
- Tests: renders the triplet from a stubbed metrics fetch; renders a
  non-zero wrong honestly (no hard-coded zero); honest absence on fetch
  error.

### Verify: `cd workbench-ui && pnpm build && pnpm test`

---

## Brief B4 — The leeway story (frontend; after B1 + B2)

### Gates
```bash
git worktree add ../core-wb-m-b4 origin/main -b feat/wb-m-leeway-wiring
grep -q "CalibrationClass" workbench-ui/src/types/api.ts || echo "STOP: B1 not merged"
```

### Deliverables
- In the Replay / Proposals evidence rails, when a turn or proposal carries an
  approximate/served result, surface *why latitude was granted*: the class,
  its license (PROPOSE/SERVE), the θ it cleared, and the `[approximate]`
  disclosure — joining the existing HITL ratification to the calibration that
  grants it. Read from B1; link to the Calibration route.
- No new mutation; purely a read-only cross-link/annotation.
- Tests: a served-with-leeway fixture renders its class + θ + license; a
  fully-verified turn renders no leeway annotation (absence is honest).

### Verify: `cd workbench-ui && pnpm build && pnpm test`

---

## After this pack

Phase C brief pack (cognitive-pipeline visualizer, contemplation-as-process,
field substrate, identity continuity) is authored once Phase B lands —
C1/C3 are also backend-reader-first and Python-gated.
