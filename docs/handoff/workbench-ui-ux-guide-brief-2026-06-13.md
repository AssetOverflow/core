# Brief — CORE Workbench UI/UX Guide (indexed, teach-everything doc)

Date: 2026-06-13
**Dispatch target: Sonnet (or any mid-tier model)** — this is a documentation
task over already-shipped code, not architecture. No code changes.

## Goal

Produce a single comprehensive, **indexed** guide that explains, defines,
guides, and *teaches* the entire Workbench UI/UX — so an external evaluator
(Anthropic, xAI) or a new operator can understand every surface and *why* it
works the way it does, and a returning contributor can navigate by the index.

Deliverable: `docs/workbench/UI-UX-GUIDE.md` (one file, top-anchored table of
contents linking to every section). Markdown only — no standalone HTML, no
sidecar assets (CLAUDE.md § Documentation Discipline). Mermaid fenced blocks
are allowed where a flow genuinely helps; `<details>` for long tables.

## Audience & voice

Two readers: an impressed-but-skeptical evaluator, and a new operator. Voice:
humble + precise, ADR-0160's pillars (audit-native, calm/infinite-depth,
replay-before-persuasion). **Never oversell** — every capability claim must
match what the code actually does; prefer "shows / refuses / replays" over
"understands / knows". If a surface is read-only, say so.

## Required sections (this is the index)

1. **What the Workbench is** — the thesis ("determinism made felt, not
   animated cognition"), the three pillars, and the evidence model (one
   evidence manifold per route).
2. **Run it** — point to `scripts/workbench` (doctor/setup/up), ports, the
   pure-Python guarantee. Mirror the README; don't duplicate the launcher's
   internals.
3. **The evidence model** — Evidence Address (URL = subject, the `?inspect=`
   param, `Cmd+Shift+C` copy), the Evidence Chain Rail (intent → subject →
   provenance → admissibility → replay → authority → action; lit/hollow/dim),
   the EvidenceSubject kinds.
4. **The eleven routes** — one subsection each: Chat, Trace, Replay (the
   Moment), Demos (Demo Theater), Proposals (+ HITL ratification), Evals
   (+ wrong=0 ledger), Runs, Packs, Vault (fail-closed), Audit, Settings.
   For each: *purpose · what evidence it projects · how to use it · key
   interactions · its three states (loading/error/empty)*.
5. **The design system & primitives** — tokens (semantic color roles, no
   palette literals), and each primitive: Panel, TabBar, SplitPane,
   VirtualizedList, SearchInput, TreeView, DAG viewer, Timeline, DigestBadge,
   Timestamp, MetadataTable, StableJsonViewer, the state components, badges.
6. **Keyboard & command** — the full keyboard map (Cmd+K palette, Cmd+I
   inspector, Cmd+1..0 nav, Cmd+Shift+C, j/k list nav, `/` search, Enter,
   Esc, `?` help) and the registry-driven help contract.
7. **Why the UI can't lie** — the doctrine gates as a feature: hexScan
   (token-only), schemaDrift (TS mirrors the engine schema), enumCoverage,
   route conformance, golden-file layouts. Explain that these *prove* the
   honesty, they aren't decoration.
8. **Determinism & replay** — the Replay Moment in depth (sealed single-turn,
   `trace_integrity`, the honesty card), and what replay does/doesn't prove.
9. **Glossary** — trace hash, versor, epistemic state, grounding source,
   wrong=0, gold-tether, θ, evidence subject, etc.

## Read first (ground every claim in the real code)

- `docs/workbench/` — `core-workbench-v1-blueprint.md`, `design-system.md`,
  `ui-component-map.md`, `api-contract-v1.md`, `acceptance-gates.md`,
  `wave-R-mastery-revamp.md`, `wave-M-worthiness.md`, `README.md`.
- `workbench-ui/src/app/` — read each route component for accurate behavior
  (don't infer); `evidenceAddress.ts`, `evidenceContext.tsx`,
  `EvidenceChainRail.tsx`, `shortcutRegistry.ts`, `KeyboardHelp.tsx`.
- `workbench-ui/src/design/` — tokens, components, `doctrine/` gates.
- `README.md` § CORE Workbench (the launcher).
- ADR-0160, ADR-0162 (the UI doctrine + acceptance gates).

## Constraints

- **Accuracy over completeness** — if unsure what a control does, read the
  component; never guess. A wrong instruction is worse than an omission.
- Cross-link every section to the source file(s) so it stays maintainable.
- Keep it one navigable file with a working top-of-doc index; if it grows
  past ~800 lines, split by section into `docs/workbench/guide/` with an
  index page — but prefer one file.
- Add a one-line pointer from `docs/workbench/README.md` to the guide.

## Verification

- Every route/primitive named in the guide exists in the code (grep-check).
- The keyboard map matches `shortcutRegistry` / `KeyboardHelp`.
- No standalone HTML; `git diff --check` clean.
