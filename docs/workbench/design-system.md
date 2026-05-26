# Workbench Design System v1

This document records the Branch 1 substrate for ADR-0162, cross-referenced with
[ADR-0160](../decisions/ADR-0160-core-workbench-v1.md) and
[ADR-0161](../decisions/ADR-0161-hitl-async-queue.md).

The implementation lives in `workbench-ui/`.  The preview page is `/preview`:

```bash
cd workbench-ui && pnpm install && pnpm preview
```

Branch 1 is intentionally static and read-only.  It adds no backend, no API
client, no route shell beyond `/preview`, and no runtime mutation surface.

## Token Substrate

Tokens are defined in `workbench-ui/src/design/tokens/tokens.css` and mirrored
to typed TypeScript by `workbench-ui/scripts/generate-tokens.ts`.  The build
prehook regenerates `tokens.ts`; the token test fails if CSS and TypeScript
diverge.

The theme is dark-only.  Fonts are self-hosted from `workbench-ui/public/fonts/`
and referenced through local `@font-face` rules only.

## Badge Tables

Badge components live under `workbench-ui/src/design/components/badges/`.
Each component accepts a typed enum value, never an arbitrary string.

| Badge | Values | Source |
|---|---:|---|
| `EpistemicStateBadge` | 15 | `core/epistemic_state.py` |
| `NormativeClearanceBadge` | 4 | `core/epistemic_state.py` |
| `ReviewStateBadge` | 4 | `teaching/proposals.py` |
| `GroundingSourceBadge` | 6 | ADR-0162 Branch 1 contract |
| `TraceHashBadge` | copyable digest | ADR-0153 / ADR-0160 |

`scripts/dump-enums.py` performs a read-only AST walk over the Python enum
sources.  `pnpm test:enum-coverage` regenerates `workbench-ui/enum-snapshot.json`
and asserts exact UI coverage so engine enum drift fails loudly at build/test
time.

## JSON Viewer

`StableJsonViewer` preserves raw source spans for strings and numbers, renders
object keys in deterministic lexicographic order, copies JSON Pointer paths,
renders a source-byte SHA-256 badge, supports side-by-side leaf diffs, and
refuses inline rendering above 16 MiB.

## Motion And Keyboard

All motion uses tokenized durations/easing.  `prefers-reduced-motion: reduce`
collapses tokenized durations to instant.

The preview page installs the Branch 1 keyboard baseline:

- `Cmd+K` / `Ctrl+K` opens the stub command palette.
- `Esc` closes overlays.
- Interactive primitives use `--color-focus-ring`.
- Preview tab order follows DOM order.
