# CORE Problem-Solving Capability Roadmap v2 — 2026-06-17

**Status:** Living document (docs-only update)
**Date:** 2026-06-17
**Context:** Post PR #797 (rate injection), #798 (Grok governance), #799 (Inc3 rate connector); Inc3 evidence closure is the current hygiene step before Gate A1 comparative injection.

## Overview

This v2 roadmap refines the GSM8K Workstream A path and the broader capability sequencing after the rate injection delivered by PR #797.

As of 2026-06-17: PR #797, #798, and #799 are merged.

## GSM8K Workstream A

- Inc 1: reader/recognizer baseline lift (discrete etc.)
- Inc 2: frontier measurement + stale doctrine repair + narrow rate injection (PR #797)
- Inc 3: `"one"` connector for rate_with_currency (PR #799) — **shipped**
- **Current hygiene step:** Inc3 evidence closure (lookback + frontier test semantics; pinned `report.json` remains historical; live ephemeral frontier shows `rate_with_currency` no-injection = 0)

### Recommended Inc3 target (narrow)

Make the rate frontier evidence actionable by resolving the next narrow blocker exposed by #797.

Scope candidates (in preference order for this increment):
1. Denominator-state support for rate application (if failures surface as "actor has rate but no denom-unit quantity reachable").
2. Safe connector expansion only if frontier proves "for one cup" is a dominant blocker.
3. Measurement-only frontier report refresh if artifacts stale.

Inc3 selected #2 (connector for "for one cup"/"one" token) because live debug on the pinned report + cases showed the exact remaining rate injector deferral from Inc2 (matcher left rate_anchor_token=None for "one"; spec unresolved_notes explicitly called it out for the Alexa surface). This was the minimal change that reclassifies the rate_with_currency no-injection bucket (making evidence actionable) while preserving all guards. Denom production is larger future work (see ratification for rationale and out-of-scope).

"Complete and harden PR #797" is revised as: Complete the post-#797 rate-follow-up evidence loop: run frontier report from current main, identify the remaining rate-family blocker, and ship at most one narrow Inc3 increment before comparative injection.

Explicitly: Inc3 did not broaden to full rate language family, comparative injection, or non-rate categories.

## Gate A1 / Comparative Injection

**Next** after Inc3 evidence closure merges. Ratify-first (docs/analysis gate-a1 ratification) before any comparative injector code.

## Success Criteria (Inc3 — met on main; evidence closure completes governance)

- Inc3 ratified change merged (#799).
- Live ephemeral frontier: `rate_with_currency` no-injection = 0; aggregate proxy 6/44/0, wrong=0.
- Pinned `report.json` may remain historical; live measurement via ephemeral runner or synthetic frontier tests.
- Inc3 lookback committed (docs/analysis/gsm8k-workstream-a-increment-3-lookback-2026-06-17.md).
- No rebaseline of sealed lanes or SHA movement without separate ratification.

## Out of Scope (Inc3 — held)

- Full comparative (Gate A1) implementation.
- Denominator-state production, report.json rebaseline, broad recognizer work.
- Changes to serving sealed paths, identity, policy, or algebra invariants.

See Inc3 lookback for loop-closure criterion before Gate A1.
