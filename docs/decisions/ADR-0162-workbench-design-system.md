# ADR-0162 — Workbench Design System (v1)

**Status:** Proposed
**Date:** 2026-05-26
**Author:** Shay
**Parent:** [ADR-0160 — CORE Workbench v1](./ADR-0160-core-workbench-v1.md)
**Companions:** [ADR-0161 — HITL async queue](./ADR-0161-hitl-async-queue.md), [ADR-0153 — TurnEvent.trace_hash back-stamp](./ADR-0153-turn-event-trace-hash-backstamp.md), [ADR-0159 — Contemplation-quality eval](./ADR-0159-contemplation-quality-eval.md)

---

## Context

ADR-0160 named the Workbench's product doctrine — read-only first, calm
by default, infinite depth, replay before persuasion, no accept/reject in
v1.  W-026 landed the read-only API with typed schemas and closed-set
error codes.

What the cascade still lacks is a **ratified design substrate**.  Without
one, every downstream branch (W-027 frontend shell, W-028 chat + trace
drawer, W-029 proposal queue, W-030 eval center, W-031 replay theater)
will hand-roll its own tokens, badge mappings, motion rules, JSON-viewer
behavior, and empty/error/loading states.  Five branches' worth of
silent drift is exactly the failure mode ADR-0160 forbids ("no dashboard
soup").

This ADR pins the design substrate **before** any frontend code exists.
Tokens, typography, motion, semantic state mapping, the
`StableJsonViewer` invariants, empty/error/loading contracts, keyboard
behavior, and the explicit no-go list are doctrine, not styling.  They
are the trust surface the visual layer sits on.

The principle behind every call below is the same as ADR-0161's: select
the **narrowest commitment** that still names testable invariants.  This
ADR ships zero implementation; it commits the contract that W-027 will
honor and that every later branch will inherit.

---

## Product north star (one paragraph)

The Workbench should feel like Linear's calm + Raycast's speed +
GitHub PR review's auditability + Xcode Instruments' precision —
operating a deterministic cognition engine with full traceability.  Not
a chat clone.  Not a SaaS dashboard.  Not animated AI theater.  The
beauty comes from structural truth, hierarchy, responsiveness, and
precision; from operational sovereignty, not decoration.

Every meaningful surface must be able to answer six questions: *What
happened?  Why was it allowed?  What evidence supports it?  Can it be
replayed?  Did it mutate anything?  Who/what has authority to ratify the
next step?*  A panel that cannot answer one of those questions does not
ship in v1.

---

## Decision summary

| Concern | Decision |
|---|---|
| Token namespace | Semantic, not literal.  `--color-surface-base`, not `--color-zinc-900`.  Tokens are CSS custom properties + a typed TS export. |
| Theme | Dark default.  Light theme deferred to v2.  No system-theme auto-switch in v1. |
| Typography | Inter (UI), JetBrains Mono (hash/JSON/trace).  System fallback chain pinned. |
| Color semantics | Bound to ratified `EpistemicState` (15) and `NormativeClearance` (4) enums in `core/epistemic_state.py`.  No badge color without an enum binding. |
| Motion | Allowed: drawer/palette/expand/diff/route transitions.  Forbidden: "thinking" animations, particle effects, glowing networks, avatar pulses, shimmer-everywhere. |
| `StableJsonViewer` | Deterministic, lossless, copyable, diffable.  Trust surface, not a code block.  Six tested invariants. |
| Empty / error / loading | Every route ships all three.  Empty includes a next action.  Error includes reproducer + mutation status.  Loading uses specific labels. |
| Keyboard | Keyboard-first.  `⌘K` palette, `Esc` closes overlays, `Enter` opens selection, focus-visible everywhere, no color-only encoding. |
| Layout shell | Five-region grid: TopBar / LeftNav / MainSurface / RightInspector / StatusFooter.  Routes may collapse the rail but not the bar/nav/footer. |

---

## Decision detail

### 1. Token namespace and theme

Tokens live in `workbench-ui/src/design/tokens/` as CSS custom
properties (`tokens.css`) plus a typed TypeScript mirror
(`tokens.ts`).  The TS export is generated from the CSS to keep one
source of truth.

**Naming rule.**  Token names are **semantic**, not literal.  A consumer
reads what the value *means*, not what shade it is:

```text
--color-surface-base
--color-surface-raised
--color-surface-overlay
--color-border-subtle
--color-border-strong
--color-text-primary
--color-text-secondary
--color-text-mono
--radius-sm  --radius-md  --radius-lg
--space-1 .. --space-12
--shadow-panel  --shadow-floating
--motion-fast  --motion-base  --motion-slow
--motion-ease-out  --motion-ease-spring
```

Forbidden: `--color-blue-500`, `--color-zinc-900`.  Literal-named tokens
leak palette decisions into consumers and prevent palette evolution.

**Theme.**  Dark by default.  Light theme is deferred to a follow-up
ADR.  No system-theme auto-switching in v1 (avoids first-render flash
and keeps screenshots stable for the audit trail).

### 2. Typography

UI: **Inter** with the system stack as fallback (`-apple-system,
"Segoe UI", Roboto, "Helvetica Neue", sans-serif`).

Mono: **JetBrains Mono** with fallback (`"SF Mono", "Menlo",
"Consolas", monospace`).  Used for every surface that carries
audit-significant text: `trace_hash`, `proposal_id`, JSON, file paths,
CLI commands, digests.

Hierarchy is pinned by token, not by class proliferation:

```text
--font-size-display  --font-size-h1  --font-size-h2
--font-size-body  --font-size-meta  --font-size-mono
--line-height-tight  --line-height-base
--font-weight-regular  --font-weight-medium  --font-weight-semibold
```

No more than two weight steps per surface.  Density without clutter.

### 3. Color semantics — bound to ratified enums

This is the load-bearing call.  Every status badge color **must** be
bound to an enum value that the engine already emits.  No "aspirational"
badge colors.  No two badges may share a color.  This keeps the badge
layer honest and audit-grade.

#### 3a. EpistemicState (15 values from `core/epistemic_state.py`)

| State | Badge label | Token | Felt meaning |
|---|---|---|---|
| `decoded` | Decoded | `--color-state-decoded` (cool blue-green) | Engine reconstructed the answer in canonical form |
| `decoded_unarticulated` | Decoded (silent) | `--color-state-decoded` (muted) | Reconstructed but no surface emitted |
| `verified` | Verified | `--color-state-verified` (cool green) | Cross-checked against reviewed evidence |
| `evidenced` | Evidenced | `--color-state-evidenced` (teal) | Direct evidence supports the surface |
| `evidenced_incomplete` | Evidenced (partial) | `--color-state-evidenced` (muted) | Evidence partial; surface qualified |
| `inferred` | Inferred | `--color-state-inferred` (indigo) | Composed from existing chains, not directly evidenced |
| `unverified_possible` | Unverified | `--color-state-unverified` (blue-gray) | Plausible but unverified |
| `unverified_novel` | Unverified (novel) | `--color-state-unverified` (warm) | New territory, no prior evidence |
| `perceived` | Perceived | `--color-state-perceived` (cyan) | Input registered, not yet grounded |
| `contradicted` | Contradicted | `--color-state-contradicted` (red) | Evidence falsifies the surface |
| `ambiguous` | Ambiguous | `--color-state-ambiguous` (violet) | Multiple coherent readings |
| `undetermined` | Undetermined | `--color-state-undetermined` (muted gray) | Insufficient evidence to choose |
| `scope_boundary` | Out of scope | `--color-state-scope` (slate) | Outside the engine's accepted domain |
| `computationally_bounded` | Bounded | `--color-state-bounded` (orange) | Computation hit a deliberate ceiling |
| `epistemic_state_needed` | Needs review | `--color-state-needed` (amber) | Engine declined to self-classify |

Clicking any badge opens a popover explaining the state, citing the
ADR that pinned it, and listing the evidence that produced the
classification.

#### 3b. NormativeClearance (4 values from `core/epistemic_state.py`)

| State | Badge label | Token |
|---|---|---|
| `cleared` | Cleared | `--color-clearance-cleared` (cool green) |
| `violated` | Violated | `--color-clearance-violated` (red) |
| `unassessable` | Unassessable | `--color-clearance-unassessable` (muted gray) |
| `suppressed` | Suppressed | `--color-clearance-suppressed` (muted red) |

#### 3c. ReviewState (4 values from `teaching/proposals.py`, per ADR-0057 / ADR-0161)

| State | Badge label | Token |
|---|---|---|
| `pending` | Pending | `--color-review-pending` (amber) |
| `accepted` | Accepted | `--color-review-accepted` (cool green) |
| `rejected` | Rejected | `--color-review-rejected` (muted red) |
| `withdrawn` | Withdrawn | `--color-review-withdrawn` (muted gray) |

#### 3d. Grounding source (6 values from cold-start-grounding lane)

| State | Badge label | Token |
|---|---|---|
| `teaching` | Teaching | `--color-grounding-teaching` (cool green) |
| `pack` | Pack | `--color-grounding-pack` (teal) |
| `vault` | Vault | `--color-grounding-vault` (indigo) |
| `partial` | Partial | `--color-grounding-partial` (muted teal) |
| `oov` | Out of vocab | `--color-grounding-oov` (orange) |
| `none` | Not grounded | `--color-grounding-none` (slate) |

**Color-only encoding is forbidden.**  Every badge carries its label;
the color is reinforcement.  Accessibility and screenshot-audit fidelity
both depend on this.

### 4. Motion

The motion rule is one line: **motion reveals structure, not cognition.**

Allowed motion (each with a single token, no per-surface bespoke easing):

| Motion | Duration | Easing |
|---|---|---|
| Drawer open/close | `--motion-base` (180ms) | `--motion-ease-out` |
| Command palette enter/exit | `--motion-fast` (120ms) | `--motion-ease-out` |
| Trace row expand | `--motion-base` (180ms) | `--motion-ease-out` |
| Diff highlight pulse | `--motion-fast` (120ms) | `linear` (one cycle, no loop) |
| Route transition | `--motion-base` (180ms) | `--motion-ease-out` |
| Skeleton loading shimmer | `--motion-slow` (1200ms) | `linear`, ≤2 cycles before falling back to static "Loading…" label |

Forbidden:

- "thinking…" pulses, dots, or orbs
- particle effects
- glowing neural-network animations
- avatar movement
- glassmorphism / frosted-glass surfaces
- shimmer applied to anything that is not a loading skeleton
- animated graph or chain construction "theater"
- background gradients that move
- any animation that loops indefinitely

Reduced-motion (`prefers-reduced-motion: reduce`) must collapse every
allowed motion to instant.  No exceptions.

### 5. `StableJsonViewer` — trust surface invariants

This is the component that, if done casually, silently erodes the audit
invariant.  It is **doctrine, not styling**.  Six invariants, each
testable:

1. **Deterministic key ordering.**  Keys render in the order the source
   serialized them.  When the source is a dict, sort lexicographically.
   When the source is an already-serialized JSON string, preserve
   appearance order.  Never silently re-sort.
2. **Lossless string preservation.**  No smart quotes.  No whitespace
   stripping.  No unicode normalization.  No HTML entity coercion.
   What you see is what is on disk.
3. **No semantic auto-format.**  Numbers display as the source typed
   them (`1e-6` ≠ `0.000001`).  Booleans, null, and integer/float
   distinctions are preserved.
4. **Copy paths.**  Right-click (and a keyboard shortcut) yields the
   JSON Pointer path to the selection (e.g., `/scenes/3/detail/proposed_chain/object`).
   This is the audit-trail handle.
5. **Diff mode.**  Given two values, render side-by-side with
   structural alignment.  Highlight only the leaf fields that changed.
   Color-only encoding forbidden — changed leaves carry a glyph
   (`≠ added`, `≠ removed`, `≠ changed`).
6. **Large-document safety.**  Virtualize rendering above 1,000 leaf
   nodes.  Above 16 MiB raw bytes, refuse to inline-render and surface a
   "Open in external viewer" affordance with a copy-path button — same
   ceiling as the W-026 read API.

The viewer must also display the SHA-256 digest of the rendered source
as a `--font-mono` badge.  Clicking the digest copies it.

### 6. Empty / error / loading state contract

Every route ships **all three** states from day one.  This is acceptance
criterion #9 from the vision doc, lifted into doctrine here.

#### Empty

Every empty state must contain:

- A one-line statement of what is absent.
- A **next action** — either a CLI command to copy, a route to navigate
  to, or a runtime config to inspect.

Example:

```text
No pending proposals.
Run: core demo learning-arc
```

Never empty-empty.  Never just a "—".

#### Error

Every error state must surface:

- **What failed** (one sentence)
- **Whether state was mutated** (`No corpus mutation occurred.` is a
  load-bearing line per CLAUDE.md doctrine)
- **A reproducer** — the CLI command or curl that triggers it
- **Whether retry is safe**

Example:

```text
Replay failed before comparison.
No corpus mutation occurred.
Reproduce:
  uv run core demo learning-arc --json
Retry: safe
```

#### Loading

Loading labels are specific, never "Thinking…":

```text
Loading trace…
Computing replay…
Reading proposal log…
Running eval lane…
Comparing artifacts…
```

The skeleton shimmer caps at two cycles (per §4) and then collapses to
the static label.  Indefinite shimmering is forbidden.

### 7. Keyboard contract

The Workbench is keyboard-first.  Baseline:

- `⌘K` / `Ctrl+K` opens the command palette from any route
- `Esc` closes any overlay (drawer, palette, popover)
- `Enter` activates the focused item (open, expand)
- `↑` / `↓` traverse lists; `←` / `→` traverse adjacent panels
- `?` opens the keyboard-shortcut cheat sheet
- Every interactive element has `focus-visible` styles drawn from
  `--color-focus-ring`
- `Tab` order matches visual order; explicit `tabIndex` only where the
  visual order conflicts with the semantic order
- Every drawer/dialog announces a `role` and an `aria-label`
- No interactive surface is reachable only by mouse

The command palette must support, at minimum, fuzzy search across:

```text
Run eval lane
Open proposal
Replay trace
Compare run
Inspect pack
Search trace hash
Copy ratification command
Open latest contemplation report
```

### 8. Layout shell

The shell is a five-region grid, named consistently across routes:

```text
+---------------------------------------------------------------+
| TopBar             (command palette / context / status)       |
+---------+-------------------------------------------+---------+
|         |                                           |         |
| LeftNav | MainSurface                               | Right   |
|         |                                           | Inspect |
|         |                                           |         |
+---------+-------------------------------------------+---------+
| StatusFooter       (runtime / replay / mutation mode)         |
+---------------------------------------------------------------+
```

Routes may **collapse** the RightInspector but not hide the TopBar,
LeftNav, or StatusFooter.  Removing the persistent surfaces breaks the
"always know what runtime you're talking to" affordance that ADR-0160
required.

LeftNav contents are pinned and ordered:

```text
Chat
Trace
Replay
Proposals
Evals
Runs
Packs
Vault / Recall
Audit Log
Settings / Runtime
```

No giant sidebar.  No collapsible sub-trees in v1.

StatusFooter surfaces three signals at all times:

- `mutation_mode` from `GET /runtime/status` (`read_only` or
  `runtime_turn`) — color-encoded **and** labeled
- `git_revision` (short SHA, mono)
- `checkpoint_revision` (short SHA, mono) — turns amber when
  `revision_warning: true` per ADR-0157

### 9. Component map — v1 must-ship vs follow-up

The vision doc lists ~30 components.  The honest v1 scope is narrower.
This ADR commits to **must-ship** for W-027..W-031; everything else is
named here so the design system anticipates it, but ships in a follow-up.

**Must ship in v1 (W-027..W-031):**

```text
WorkbenchShell
TopBar              LeftNav             StatusFooter
CommandPalette

ChatTurnList        ChatTurnCard
ResponseEvidenceStrip
TraceDrawer
EpistemicStateBadge GroundingSourceBadge NormativeClearanceBadge ReviewStateBadge
TraceHashBadge      CopyableHash

ReplayTheater       ReplayComparisonPanel ReplayDiffViewer

ProposalQueue       ProposalCard          ProposalDetailPanel
RatificationCommandPanel

EvalCenter          EvalLaneList          EvalFailureViewer

StableJsonViewer    StableJsonDiffViewer  ArtifactLink
```

**Follow-up after v1 milestone:**

```text
TraceStepList         (inline trace step navigator)
ProposalChainViewer   (chain visualization)
SourceProvenancePanel (deep provenance graph)
PackInspector         CorpusInspector      VaultRecallInspector
MetricGateTable       RegressionDiffPanel
```

Pinning the v1 component set keeps the implementation branches honest.

### 10. The no-go list

Explicit, because doctrine drift is what produces "AI dashboard" UIs:

- No chat-clone styling.  No avatar bubbles.  No "AI is thinking…"
  affordances.
- No animated cognition theater (particles, glowing networks, pulsing
  orbs).
- No glassmorphism / frosted glass.
- No purple gradients, no neon accents, no cyberpunk styling.
- No live "hallucinated" chain or graph construction animations.
- No node-graph builder in v1.
- No workflow automation canvas in v1.
- No "accept proposal" button anywhere in v1 (per ADR-0160 + ADR-0161 §2).
- No dashboard-soup pages.
- No vanity green-dashboard eval views.
- No "active session count" / "total turns" splash metrics on a landing
  page.
- No system-tray notifications, no toasts that auto-dismiss audit
  events.
- No icon-only buttons without accessible labels.
- No color-only state encoding.

---

## Implementation plan — Branch 1

Pre-W-027 deliverable.  Single PR titled `feat(workbench-ui): design
system v1 (ADR-0162)`:

1. `workbench-ui/` directory created at repo root with `package.json`,
   `vite.config.ts`, `tsconfig.json`.  Pin React 18, Vite 5, TS 5.x,
   Tailwind 3.x, shadcn primitives.  No app routes yet.
2. `workbench-ui/src/design/tokens/tokens.css` — every token from §1–§4.
3. `workbench-ui/src/design/tokens/tokens.ts` — typed TS mirror, generated
   from `tokens.css` at build time (a `scripts/generate-tokens.ts` reader).
4. `workbench-ui/src/design/components/StableJsonViewer/` — full
   implementation honoring all six invariants in §5, with tests.
5. `workbench-ui/src/design/components/EpistemicStateBadge/` and the
   four other badge primitives — each generated from the enum tables in
   §3 so the badge set is provably exhaustive.
6. `workbench-ui/src/design/components/EmptyState/`, `ErrorState/`,
   `LoadingState/` — primitives the route screens compose.
7. `workbench-ui/preview/` — a Vite route exposing every primitive on
   one page so the design baseline is reviewable in a browser.  Not
   shipped to end users; it is the operator's "Storybook lite".
8. Frontend tests: token presence, badge-set exhaustiveness against the
   Python enums (parsed from `core/epistemic_state.py` and
   `teaching/proposals.py` at build time), `StableJsonViewer` invariants
   1–6, reduced-motion collapse, keyboard contract for the palette and
   drawers.
9. Docs update: `docs/workbench/design-system.md` linking the ADR,
   `docs/workbench/README.md` runbook addition (`cd workbench-ui &&
   pnpm preview`).

**Crucially: no app shell, no routes, no API client yet.** Branch 1 is
*only* the substrate.  W-027 (frontend shell) is the first branch that
consumes it.

---

## Acceptance criteria

This ADR is ratifiable when:

1. Every token in §1–§4 is a CSS custom property with a matching typed
   TS export, and a test fails if either drifts.
2. Every enum value in §3a–§3d has exactly one badge component, and a
   test parses the Python enums and asserts 1:1 coverage.  Adding an
   enum value to the engine without adding a badge fails the test.
3. `StableJsonViewer`'s six invariants each have a test:
   - byte-identical round-trip on a synthetic source,
   - copy-path returns a valid JSON Pointer,
   - diff highlights only changed leaves and adds the glyph,
   - large-document virtualization triggers above 1,000 leaves,
   - oversize-document refusal triggers above 16 MiB,
   - SHA-256 digest matches the source bytes.
4. Every primitive component renders an `EmptyState` / `ErrorState` /
   `LoadingState` snapshot test from a fixture and asserts the
   "next action" / "reproducer" / "specific label" rules in §6.
5. `prefers-reduced-motion: reduce` collapses all motion to instant in a
   Playwright test.
6. The command palette is reachable via keyboard from every primitive's
   preview page (Playwright).
7. The preview page (`pnpm preview`) renders every primitive without
   network access (offline-safe, deterministic).

---

## Out of scope

This ADR is the design substrate.  It does not commit to:

- the app shell or routes (W-027)
- chat or trace UI (W-028)
- proposal queue UI (W-029)
- eval center UI (W-030)
- replay theater UI (W-031)
- a backend API beyond what W-026 already exposes
- light theme / system-theme switching
- internationalization
- multi-tenant or remote operation
- mobile layouts (Workbench is a desktop tool; the mobile path for
  ratification stays the GitHub mobile app + workflow_dispatch per
  ADR-0161 §2)
- a frontend authentication layer (deferred to a separate ADR; v1 is
  local-only, unauthenticated, per ADR-0160)
- Storybook / Chromatic — the `/preview` route is the substitute
- Figma component mirroring — design tokens are the source of truth, not
  a Figma file

---

## Consequences

### Positive

- Five downstream branches inherit one substrate.  No silent drift
  between W-027 and W-031.
- The badge layer is provably exhaustive against the engine's ratified
  enums — adding a new `EpistemicState` value cannot ship without a
  badge.
- `StableJsonViewer` becomes a tested trust surface, not a code-styling
  choice.  Replay-equivalence claims gain a UI-side audit handle.
- The no-go list closes the "AI dashboard drift" failure mode by name,
  not by hope.
- Empty / error / loading contracts ship from day one.  The "we'll add
  empty states later" failure mode is forbidden.

### Negative

- Branch 1 is overhead before any user-visible UI exists.  ~1 day's
  work that shows nothing in the chat surface.  Worth it.
- Tying badges to enums means engine refactors that rename or remove
  enum values cascade into the UI.  This is the intended behavior, not
  a cost — the UI cannot diverge from the engine's self-classification.
- The 16 MiB `StableJsonViewer` ceiling matches the W-026 API ceiling.
  If either ceiling moves, the other must move with it.

### Risks

- Token bikeshedding.  Mitigation: tokens are semantic-only.  The
  conversation is about *what the surface means*, not what shade it is.
- Inter / JetBrains Mono licensing.  Both are OFL-licensed; bundling is
  permitted.  Self-hosted, not fetched at runtime.
- Component scope creep.  The §9 component map names what ships in v1
  vs follow-up; deviation requires a separate ADR.

---

## Cross-references

- [ADR-0160 — CORE Workbench v1](./ADR-0160-core-workbench-v1.md) — product doctrine; this ADR is its design substrate.
- [ADR-0161 — HITL async queue](./ADR-0161-hitl-async-queue.md) — the proposal-queue UI's semantic contract (admits ≠ ratifies).
- [ADR-0153 — TurnEvent.trace_hash back-stamp](./ADR-0153-turn-event-trace-hash-backstamp.md) — `TraceHashBadge` consumes this.
- [ADR-0157 — Revision-mismatch warning](./ADR-0157-revision-mismatch-warning.md) — `StatusFooter` consumes this.
- [ADR-0159 — Contemplation-quality eval](./ADR-0159-contemplation-quality-eval.md) — `EvalCenter` reads against this lane shape.
- [`core/epistemic_state.py`](../../core/epistemic_state.py) — the enum tables in §3a–§3b are bound to this file.
- [`teaching/proposals.py`](../../teaching/proposals.py) — `ReviewState` for §3c.
- [`workbench/schemas.py`](../../workbench/schemas.py) — typed dataclasses the UI mirrors as TS discriminated unions.
- [CLAUDE.md](../../CLAUDE.md) — deterministic replay, exact recall, proposal-only learning; this ADR encodes those into the UI substrate.

### Memory cross-references

- [[thesis-decoding-not-generating]] — the UI must reveal the engine
  *decoding* (badges, replay, trace hashes), not staging a *generating*
  performance (animation theater).  Every motion / animation choice is
  measured against this.
- [[feedback-address-critiques-dont-waive]] — the vision-doc gaps
  (StableJsonViewer underdefined, empty-states absent, badge taxonomy
  outrunning the engine) are addressed here, not deferred.
- [[feedback-adr-cross-reference-discipline]] — every badge color is
  bound to a ratified enum.  No badges without a Python source of
  truth.
- [[user-circumstances]] — the operator works from a tent / library, on
  intermittent connectivity.  Local-only, offline-safe, no fonts or
  assets fetched at runtime.  The `/preview` page must render with the
  network disabled.
