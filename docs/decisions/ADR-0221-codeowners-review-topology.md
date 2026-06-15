# ADR-0221 — Branch protection for a solo-maintainer public repo (required-checks-only)

Status: accepted (applied 2026-06-15)
Date: 2026-06-15
Relates: PR #699 (original `main` branch protection), ADR-0220 / #772 (the PR that
surfaced the deadlock), `.github/CODEOWNERS`

> Repo-governance decision, not an engine-architecture one. No runtime code
> changes. It records *why* `main` is protected with required status checks only —
> no required approvals, no required code-owner review — and explicitly warns
> future agents not to "fix" this by re-adding a human-review gate.

## Context — the deadlock that prompted this

`main` was protected (PR #699) with:

```
required_approving_review_count: 1
require_code_owner_reviews:       true
.github/CODEOWNERS:               * @AssetOverflow
required status checks:           verify pinned lane SHAs, smoke, Sourcery
```

The repo is **public but has a single maintainer**, and every PR is authored by
`@AssetOverflow` (the owner/agent token). GitHub forbids a PR author from
approving their own PR, so the required approval could **never** be collected:
`reviewDecision` was permanently `REVIEW_REQUIRED`, `mergeStateStatus` `BLOCKED`,
and the only way to merge anything — even an all-green PR — was an `--admin`
override. Observed on #772 (2026-06-15), which had to be admin-merged.

## The misconception this ADR corrects

The required review was assumed to be the boundary that keeps non-maintainers
from merging. **It is not.** Merging into any branch — protected or not —
requires repository **write access**. The public are not collaborators, so they
can open PRs from forks but can **never** merge them. Public-exclusion is
provided entirely by the collaborator/write-access model.

So the `required_approving_review_count: 1` + `require_code_owner_reviews: true`
pair added **zero** exclusion. All it did was create an unsatisfiable
self-approval gate that forced `--admin` on every merge — silently normalizing
the exact bypass the protection was meant to discourage.

## Decision

Protect `main` with **required status checks only**:

```
require a pull request before merging:  true     # so CI runs on every change
required_approving_review_count:        0
require_code_owner_reviews:             false
required status checks (strict):        verify pinned lane SHAs, smoke, Sourcery
enforce_admins:                         false     # a real emergency break-glass remains
restrict who can push:                  none      # write-access already gates merge
```

`.github/CODEOWNERS` (`* @AssetOverflow`) is retained as **advisory only** — with
`require_code_owner_reviews: false` it auto-requests review / assigns ownership
but does not gate merges.

### Why this is the correct shape here

- The real quality gate is **CI** (pinned-lane SHAs + smoke + the pre-push diff),
  per the repo's pre-push-verification doctrine. That gate is fully preserved.
- A GitHub approval from the *sole* maintainer on their *own* PR is impossible
  and semantically empty; requiring it only blocks the legitimate merger.
- Result: the maintainer/agents open a PR → CI must go green → **merge normally**.
  No approval, **no `--admin`**, no second account. The public still cannot merge.

## DO NOT re-add (explicit guard for future agents)

Do **not** re-introduce `required_approving_review_count >= 1` or
`require_code_owner_reviews: true` believing it adds a security boundary. It does
**not** — write access already excludes the public — and it re-creates the
self-approval deadlock that re-normalizes `--admin`. If a genuine second-party
review is ever wanted, it requires provisioning a **real** second write-capable
reviewer (a distinct human/account) **first**; never impose a self-approval
requirement on a single-identity repo.

## Applied

2026-06-15, via:

```bash
gh api -X PATCH repos/AssetOverflow/core/branches/main/protection/required_pull_request_reviews \
  -F required_approving_review_count=0 -F require_code_owner_reviews=false
```

Before → after: `required_approvals 1 → 0`, `require_code_owner_reviews true →
false`. Required status checks unchanged. This governance PR is the first merged
through the now-working normal path — its own clean merge is the proof.

## Break-glass log (auditable, not precedent)

- **#772 — 2026-06-15** — admin-merged as a one-time exception under the old
  deadlocked config (all checks green; only unmet requirement was an
  impossible self-approval). Authorized. **Not precedent.** With this ADR's
  config, routine `--admin` is retired.

## What this does NOT change

- No engine/runtime code. Required status checks unchanged.
- PR C (the ADR-0220 identity/provenance hash split) stays blocked on ADR-0220
  ratification — independent of this governance fix.

## Consequences

- Approval-free, check-gated normal merges for the maintainer/agents.
- `--admin` retired for routine work (emergency break-glass still available via
  `enforce_admins: false`).
- If collaborators are added later and merges should be restricted to specific
  accounts, enable **"Restrict who can push"** (the `restrictions` list) — that is
  the correct lever, **not** required reviews.
