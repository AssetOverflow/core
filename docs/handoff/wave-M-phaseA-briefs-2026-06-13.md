# Wave M · Phase A — Structure & Polish Brief Pack

Date: 2026-06-13
Plan: `docs/workbench/wave-M-worthiness.md` § Consolidated re-sequencing.
Runs **before** resuming Phase C — A1/A2 are structural prerequisites the
Cognition cluster lands into.

## Standing constraints

- Worktree off fresh `origin/main`; green-local (`pnpm build && pnpm test`,
  Python lane where touched) before push; **STOP after checks green; Shay
  merges.** Token-only (hexScan); schema/enum/conformance gates; no new
  mutation endpoints; no invented data.
- **One workbench, one address space, one Chain Rail.** Grouping is a
  wayfinding skin, never an architectural fork. Do not split into separate
  apps; do not break the Evidence Address or cross-route co-addressability.

## Order

A1 ∥ A2 (disjoint files) → A3 trails (larger). Each is its own PR.

---

## Brief A1 — Navigation registry (one source of truth) + grouped nav + palette fix

Kills a live bug **and** delivers the grouped IA in one move: today
`LeftNav.NAV_ITEMS` and `CommandPalette.NAV_COMMANDS` + `NAV_PATHS` are two
hardcoded lists that have drifted — **Demos and Calibration are reachable
from the nav but not via `⌘K`**, and the `⌘1–0` map is stale. The fix is the
registry-driven move (same principle that made KeyboardHelp honest).

### Read first
- `src/app/LeftNav.tsx` (`NAV_ITEMS`), `src/design/components/primitives/CommandPalette.tsx`
  (`NAV_COMMANDS`, `NAV_PATHS`), `src/app/Shell.test.tsx` (the nav assertion),
  `src/app/shortcutRegistry.ts` (the registry pattern).

### Deliverables
1. `src/app/routes.ts` (new): the single source of truth —
   `export const WORKBENCH_ROUTES: RouteSpec[]` where
   `RouteSpec = { id: string; label: string; path: string; section: Section;
   shortcut?: string }` and
   `Section = "Converse" | "Cognition" | "Evidence" | "Determinism" |
   "Discipline" | "Substrate" | "Settings"`. Group the current routes:
   Chat→Converse; Trace/Runs/Audit/Vault→Evidence; Replay/Demos→Determinism;
   Evals/Calibration/Proposals→Discipline; Packs→Substrate; Settings→Settings.
   The **Cognition** section is declared now (empty) so Phase C slots in.
   Keep `shortcut` only on the routes that warrant a `⌘` (don't force 12 into
   `⌘1–0`) — primary picks get `⌘1…⌘9`; the rest are palette-only.
2. `LeftNav` renders `WORKBENCH_ROUTES` **grouped by section** (section
   label + its items, in `Section` order); empty sections render nothing.
3. `CommandPalette` derives its navigate commands and the path map from
   `WORKBENCH_ROUTES` — delete `NAV_COMMANDS`/`NAV_PATHS`. Demos + Calibration
   become reachable; shortcuts come from the registry.
4. `Shell.test` nav assertion updated to the grouped structure; add a test
   that **every** `WORKBENCH_ROUTES` path is reachable from the palette (so
   drift is caught by a test, not a human).
5. Constraint: routing, the Evidence Address, and the Chain Rail are
   untouched — this is nav presentation only.

### Verify: `pnpm build && pnpm test`

---

## Brief A2 — Calibration earned-state (the centerpiece must show its thesis)

On committed data the Calibration route shows three classes all "not yet
licensed", empty bars — it never shows a class crossing θ. The reader reads
`evals/gsm8k_math/practice/v1/report.json` `per_class`, whose committed copy
is a sub-`N_MIN` baseline (`additive` committed=0), while the *earned* state
(`additive` committed=100, measured 0.861, PROPOSE-licensed) lives in the
separately-committed `ratification_queue.json` — and the two disagree
(correct 3 vs 95, committed in different commits).

### Primary fix (preferred — coherent data, reader unchanged)
Regenerate the committed practice artifacts from **one coherent run** via the
sealed practice runner (`evals/gsm8k_math/practice/v1/runner.py` —
`build_report` / `write_report`, and the ratification-queue generation) so
`report.json` `per_class` and `ratification_queue.json` agree, and the
unchanged reader surfaces the earned class. **Trust boundary:** sealed
practice, deterministic regen, reviewed; practice regime may carry wrong>0
(attempt-and-eliminate) — that is NOT the serving wrong=0; do not conflate or
weaken either. Verify post-regen: the two artifacts agree, and
`read_calibration_classes()` shows ≥1 licensed class.

### Fallback (workbench-only, if regen is out of scope)
Extend the B1 reader to surface **both** artifacts with provenance: the
`per_class` ledger AND an "earned licenses" set parsed from
`ratification_queue.json` `proposals` (class_name, committed, measured,
required, action), each labeled by its source so the two are never silently
merged. The route gains an "Earned licenses" panel. Honest, but messier than
coherent data — prefer the primary.

### Verify
`PYTHONPATH=$PWD .venv/bin/python -m pytest tests/test_workbench_calibration.py -q`
plus, for the primary, a check that the two committed artifacts agree.

---

## Brief A3 — Doctrine station ("how this UI can't lie") — trails; larger

A read-only surface that elevates the "contracts/checks" instinct into a
first-class station: list the doctrine gates and the load-bearing invariants,
each with *what it proves* and a pointer to its executable check. Every other
AI UI asks for trust; this shows the proofs.

### Deliverables (sketch — full brief authored when A1/A2 land)
- New route under the **Cognition/meta** section: a static-but-real catalog of
  the gates — hexScan (token-only), schemaDrift (TS mirrors the engine schema,
  both snapshots), enumCoverage, route conformance (ADR-0162 §6), golden-file
  layout (DAG) — and the invariants — `wrong=0`, `versor_condition < 1e-6` —
  each row: name · what it proves · the file/command that executes it · doc
  (ADR) reference.
- Data is read from a small committed manifest of gates (so the station can't
  drift from reality silently — the manifest itself is conformance-checked
  against the test files it names). No invented "all green" badges: a gate is
  listed because its check exists, not because we assert it passes.
- Read-only; no execution from the UI.

### Verify: `pnpm build && pnpm test`

---

## After this pack

Resume **Phase C** (Cognition / core-logos cluster: pipeline visualizer,
field substrate, identity, contemplation) into the grouped structure A1
created. B4 stays parked (engine-side license stamping). Then D (tour),
E (continuous).
