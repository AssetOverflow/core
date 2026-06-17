# CORE Problem-Solving Capability Roadmap v2 — 2026-06-17

**Status:** Living document (docs-only update)  
**Date:** 2026-06-17  
**Context:** Post PR #797 (rate injection) + #798; preparing Inc3 rate follow-up before Gate A1 comparative injection.

## Overview

This v2 roadmap refines the GSM8K Workstream A path and the broader capability sequencing after the rate injection delivered by PR #797.

As of 2026-06-17, PR #797 is merged and #798 is merged.

## GSM8K Workstream A

- Inc 1: reader/recognizer baseline lift (discrete etc.)
- Inc 2: frontier measurement + stale doctrine repair + narrow rate injection (PR #797)
- **Inc 3 (current seam):** Complete the post-#797 rate-follow-up evidence loop: run frontier report from current main, identify the remaining rate-family blocker, and ship at most one narrow Inc3 increment before comparative injection.

### Recommended Inc3 target (narrow)

Make the rate frontier evidence actionable by resolving the next narrow blocker exposed by #797.

Scope candidates (in preference order for this increment):
1. Denominator-state support for rate application (if failures surface as "actor has rate but no denom-unit quantity reachable").
2. Safe connector expansion only if frontier proves "for one cup" is a dominant blocker.
3. Measurement-only frontier report refresh if artifacts stale.

Inc3 selected #2 (connector for "for one cup"/"one" token) because live debug on the pinned report + cases showed the exact remaining rate injector deferral from Inc2 (matcher left rate_anchor_token=None for "one"; spec unresolved_notes explicitly called it out for the Alexa surface). This was the minimal change that reclassifies the rate_with_currency no-injection bucket (making evidence actionable) while preserving all guards. Denom production is larger future work (see ratification for rationale and out-of-scope).

"Complete and harden PR #797" is revised as: Complete the post-#797 rate-follow-up evidence loop: run frontier report from current main, identify the remaining rate-family blocker, and ship at most one narrow Inc3 increment before comparative injection.

As of 2026-06-17, PR #797 is merged and #798 is merged.

Explicitly: do not broaden to full rate language family, comparative injection, or non-rate categories in this increment.

## Gate A1 / Comparative Injection

Deferred until after the post-#797 rate follow-up loop is closed with Inc3 measurement.

## Success Criteria for This Phase

- Frontier report run on current main (train-sample proxy).
- One narrow ratified Inc3 change.
- Wrong=0 preserved on train_sample, practice, and relevant confusers.
- Rate-family "recognized_no_injection" bucket reduced or its refusal mode made actionable (e.g. surfaces the true next blocker like denom reachability).
- No rebaseline of sealed lanes or SHA movement without separate ratification.
- Documentation (this roadmap + Inc3 ratification) committed as docs-first.

## Out of Scope (for Inc3)

- Full comparative (Gate A1) implementation.
- Broad recognizer anchor work or other shape categories.
- Changes to serving sealed paths.
- Any mutation of identity, policy, or algebra invariants.

Follow the ratified Inc3 doc for the exact bounded change.
