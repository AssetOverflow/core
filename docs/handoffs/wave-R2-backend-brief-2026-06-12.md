# Brief R2-B — Workbench Backend Read Substrate (/runs, /audit, /packs, /vault)

Date: 2026-06-12
Plan: `docs/workbench/wave-R-mastery-revamp.md` § Wave R2 (the route specs);
this brief front-loads their BACKEND halves so R2 route briefs become
frontend-only.

**Agent:** GPT5.5-Thinking (XHIGH)
**Scope:** Python ONLY — `workbench/` + its tests. **Do not touch
`workbench-ui/` at all** (R0d is concurrently changing it; zero-overlap is
the parallel-safety guarantee). TS types land with each R2 route later.
**Parallel-safe with:** R0d, R1. Merges independently of both.

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-backend origin/main -b feat/wb-r2-backend-reads
cd ../core-wb-r2-backend
```

### Read first

- `workbench/api.py`, `workbench/readers.py`, `workbench/schemas.py`,
  `workbench/journal.py` — the existing read-only patterns (envelope,
  pagination, error codes, size ceilings)
- `docs/workbench/api-contract-v1.md`, `docs/workbench/data-shapes-v1.md`
- `docs/workbench/wave-R-mastery-revamp.md` § Wave R2
- CLAUDE.md "Security and Trust Boundaries" (path traversal, pack IDs)

### Deliverables — read-only endpoints, `{ ok, generated_at, data/error }` envelope

For each endpoint: deterministic ordering, `?limit=&offset=` pagination on
lists, 404 (not synthetic data) for unknown ids, no mutation anywhere, and
the W-026 16 MiB read ceiling.

1. **`GET /packs`, `GET /packs/{pack_id}`** — sources: `language_packs/data/*`
   manifests (and identity packs if cleanly readable). Surface manifest
   checksums VERBATIM (the UI's DigestBadge verify affordance depends on
   byte-honesty). **Trust boundary (mandatory):** validate `pack_id` against
   a safe pattern BEFORE any filesystem access; reject path traversal with a
   test proving it.

2. **`GET /audit/events`** — merged read-only view over the deterministic
   audit sources that already exist on disk (reboot-event audit trail per
   ADR-0158, teaching review/ratification records, workbench operator
   telemetry). Stable total ordering (timestamp + tiebreak), each event
   tagged with `source` and `mutation_boundary: bool`. Do NOT invent an
   event store — this is a reader over existing artifacts.

3. **`GET /runs`, `GET /runs/{session_id}`** — **investigate first**: derive
   "run/session" only from artifacts that already exist (engine_state
   manifests/checkpoints, turn journal grouping). If no deterministic
   on-disk session boundary exists, ship what IS derivable and document the
   gap in the PR body — never synthesize.

4. **`GET /vault/summary`, `GET /vault/entries`** — **investigate first,
   optional**: only if Shape B+ persisted engine_state provides a
   deterministic on-disk vault source (persistence is OPT-IN, often absent).
   If absent: return a typed `evidence_unavailable` error (the 501/unsupported
   pattern already used for `/replay/`), document the gap, and stop. Do NOT
   reach into live runtime memory; do NOT fake entries.

5. **Schemas** in `workbench/schemas.py` for every new shape (dataclasses,
   same style as existing) — these become the source for the R1
   schema-drift gate.

### Tests (pytest, alongside the existing workbench API tests)

Per endpoint: list + get + 404 + pagination + deterministic ordering;
path-traversal rejection for packs; a read-only proof (no writes outside
nothing — assert no dirty tree after requests); envelope conformance.

### Verification before push

```bash
uv run python -m pytest tests/ -k "workbench" -q     # adjust to the real test path
core test --suite smoke -q
git diff --stat origin/main                          # workbench/ + tests + docs ONLY — no workbench-ui/
```

PR title: `feat(workbench): R2 backend read substrate — packs, audit, runs (+vault investigate)`

PR body must state, per CLAUDE.md: the trust boundary enforced (pack_id
validation, path confinement), and that no mutation path was added.
