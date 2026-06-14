# W-Forge — universal ProposalArtifact envelope + CORE-Logos Patch Forge

**Date:** 2026-06-14
**Status:** forward brief (post read-only Studio, L1–L5 merged). Dispatch when
prioritized. **Substrate-first**: this wave grants *no new mutation power* — it
makes proposed pack changes flow through the existing review/audit/replay spine.
**Predecessors:** `docs/workbench/proposal-artifact-substrate-v1.md` (the
envelope design, no code yet) + `core-logos-studio-plan.md` L6 (Patch Forge) /
L7 (handler families).

## Mandatory first step — reconnaissance, not reinvention (ADR discipline)

Before any code, grep **all** ADRs + existing proposal machinery and write a
one-page inventory. Known existing surfaces to reuse (confirm against source):
- `teaching/proposals/` (`proposals.jsonl`, `ReviewState`) — cognition teaching
  proposals + HITL review path.
- math proposal corridor (`teaching/math_proposals/`) + ADR-0173 (narrowly
  admitted ratification handlers).
- PCCP / ADR-0218 (proof-carrying promotion) + `demos/proof_carrying_promotion`.
- the workbench Proposals route + ratify/reject/defer + audit log (already shipped).

The substrate doc's thesis: **one** `ProposalArtifact` envelope with
subject-specific adapters + validators, **preserving every existing trust
boundary**. Do NOT create a parallel logos-only proposal pipeline (that is the
architectural drift the doc exists to prevent). If the inventory shows an
existing envelope can be extended, extend it.

## Sequenced PRs

### WF-1 (ADR + substrate) — ratify the universal envelope
- Promote `proposal-artifact-substrate-v1.md` to a numbered ADR (the design must
  survive review before code). Define the `ProposalArtifact` envelope:
  `subject` (kind + id), proposed payload, evidence pointers, patch preview,
  safety report, checksum-impact prediction, suggested CLI/PR instructions,
  `capability_level` (starts `proposal_only`).
- Subject adapters/validators for the existing corridors (cognition, math) +
  a `logos_pack` adapter. Migrate existing pipelines onto the envelope **without
  changing their trust boundaries** (parity tests: same inputs → same review
  outcomes, including failure modes). This is the gating dependency for WF-2+.

### WF-2 (backend) — logos proposal draft endpoint (proposal-only)
- `POST /logos/packs/{id}/proposals/draft` — returns a `ProposalArtifact` +
  JSONL patch preview + checksum-impact prediction. **Hard boundary: it MUST
  NOT write to language-pack source files.** State the trust boundary in the PR
  (user-controlled text → pack mutation proposal; reject path traversal / unsafe
  pack ids before any fs access).
- Supported draft kinds, proposal-only: start with `gloss_add` / `gloss_update`
  (the plan's lowest-risk family); the envelope carries the rest as future kinds.
- Read-only doctrine still holds for everything else; this is the *first*
  allowlisted non-read endpoint and it is proposal-only (no apply).

### WF-3 (UI) — Patch Forge tab (L6)
- A **Patch Forge** tab on `/logos`. Button label is **`Draft proposal`** —
  never `Save` / `Apply` / `Commit`. Renders the returned `ProposalArtifact`:
  payload, patch preview, safety report, checksum impact, copyable
  ratification/PR instructions.
- `logos_patch_proposal` evidence subject (mirror the LG-3/LG-4 subject pattern)
  + inspector + chain-rail (the `authority` stage = `capability_level` /
  handler admission state).
- Bottom status strip flips to `proposal mode: proposal-only` on this tab.
  No ratification corridor yet (L7).

### WF-4 (handler family 1) — admit `gloss_add` / `gloss_update` (L7)
- Only after WF-1's ADR + tests. Admit the first minimal CORE-Logos handler with
  its full proof-obligation pack (from the plan): no direct UI file write; safe
  pack-id enforcement; deterministic ordering; correct checksum update; pack
  compile/verify passes; no OOV-policy regression; no depth-language fallback
  collapse; no silent epistemic promotion; audit-event emission; replay
  reconstruction. The Ratification Corridor appears in the UI **only** for
  proposals whose handler is admitted, preconditions pass, and safety is clear.

## Non-negotiables
- Pack mutation is **proposal-only until a reviewed handler applies it**
  (CLAUDE.md). The draft endpoint never writes.
- Every proposed change passes the **same** evidence/validation/safety/replay/
  handler/audit spine — no parallel pipeline.
- Any path that could write pack files / execute validators states its trust
  boundary and rejects unsafe ids/paths before fs access.
- Deterministic replay evidence preserved for every proposal decision.

## Out of scope
- Holonomy proof cards (W-Holonomy).
- Applying proposals for any family beyond an explicitly admitted handler.
