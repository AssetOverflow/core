# contemplation pipeline (ADR-0080)

## What it measures

The contemplation pipeline does not produce a single score — it
produces **typed SPECULATIVE findings** sourced from explicit evidence
artifacts, with three load-bearing invariants:

1. **Read-only**: never mutates packs, vault, teaching corpus, or
   runtime state.  Only emits.
2. **SPECULATIVE-only**: every emitted `ContemplationFinding` is
   stamped `EpistemicStatus.SPECULATIVE`; the schema's `__post_init__`
   raises on any other status.  No autonomous ratification.
3. **Deterministic replay**: same input files + same flags →
   identical `run_id`, identical `finding_id` per finding, identical
   sink output.

Two evidence miners ship today:

- **`frontier_compare`** — failed benchmark cases from
  `evals/frontier_compare/results/*.json` become
  `FindingKind.BENCHMARK_CASE` findings.  Subject is
  `"<suite>/<case_id>"`; predicate is `failed_case`; evidence
  summary lists the case's `failures` array.

- **`contradiction_detection`** — failed cases from
  `evals/contradiction_detection/results/*.json` become
  `FindingKind.CONTRADICTION` findings with a **predicate split**:
  - `missed_contradiction` — `paired_contradiction` case the
    detector failed to flag.
  - `false_contradiction_flag` — `paired_consistent` case the
    detector wrongly flagged.
  The split is load-bearing: each calls for a different repair
  (tighten vs loosen the threshold).

Both miners flow through the **same `DiscoveryCandidateSink`
protocol** that `teaching/discovery_sink.py` uses for in-session
`DiscoveryCandidate`s (ADR-0055 Phase B).  When invoked with
`--sink-root`, findings land at `<root>/<YYYY>/<YYYY-MM>.jsonl` —
the same monthly layout discovery candidates use, so operators
can grep one stream.

## Why it matters (structural win)

LLM evaluation harnesses produce reports.  Those reports are read
by humans, filed away, and rarely flow back into the system's
sense of "what is unfinished."  The gap-aggregation step usually
happens in a spreadsheet, if at all.

CORE's contemplation pipeline treats every failed benchmark case
as **a SPECULATIVE finding that flows into the same evidence
stream as session-time discovery candidates**.  Operators see one
unified backlog of "things the system has noticed are wrong" with
typed evidence pointers, deterministic IDs, and a clear repair
path.  No silent ratification — every promotion goes through the
existing reviewed-teaching gate.

The deeper architectural claim: contemplation **never** ratifies
its own conclusions.  It can mine evidence, propose actions, and
file SPECULATIVE findings — but the actual `EpistemicStatus.COHERENT`
transition happens only through the human-reviewed proposal flow
in `teaching/review.py`.  This is the load-bearing boundary
documented in ADR-0080.

## How to run

```bash
# CORE-only path — emits to stdout, optionally writes report blob
core contemplation evals/frontier_compare/results/<file>.json

# With shared sink — findings persist to monthly JSONL
core contemplation evals/contradiction_detection/results/<file>.json \
    --lane contradiction_detection \
    --sink-root teaching/discovery_log

# With provenance metadata
core contemplation evals/frontier_compare/results/<file>.json \
    --pack-id en_core_cognition_v1 \
    --note "Wave 1 first cross-provider audit pass" \
    --report run.json
```

Equivalent `python -m core.contemplation ...` works identically —
the `core contemplation` CLI delegates to the module's `main()`.

## How to read the output

Each `ContemplationRun` carries:

```json
{
  "run_id": "c8b27698189c3a9f",
  "config_hash": "...",
  "substrate_hash": "b43e53...",
  "finding_count": 4,
  "findings": [
    {
      "finding_id": "...",
      "kind": "contradiction",
      "subject": "contradiction_detection/CON-PUB-002",
      "predicate": "missed_contradiction",
      "object": null,
      "evidence_refs": [
        { "source_type": "contradiction_detection_report",
          "source_id": "evals/.../v1_public_*.json",
          "pointer": "lane=contradiction_detection;case=CON-PUB-002",
          "summary": "kind=paired_contradiction;flagged=False;versor_delta=0.0" }
      ],
      "proposed_action": "Inspect the paired-contradiction probe...",
      "substrate_hash": "...",
      "epistemic_status": "speculative"
    }
  ]
}
```

The **sink JSONL stream** (when `--sink-root` is set) is one
canonical JSON line per finding — same shape, no run wrapper, so
`jq` over `<root>/<YYYY>/<YYYY-MM>.jsonl` answers questions like
"every SPECULATIVE finding this month" across both contemplation
runs and ADR-0055 discovery candidates.

## Pass criteria

| Property | Definition | Threshold | Current |
|----------|------------|-----------|---------|
| SPECULATIVE-only invariant | `ContemplationFinding.__post_init__` raises on any non-SPECULATIVE status | always | ✅ pinned by test |
| Deterministic replay | two `contemplate_*` calls on the same inputs → identical `run_id` and `as_dict()` | byte-identical | ✅ pinned by test |
| Sink path is additive | the `ContemplationRun` blob is byte-identical whether or not a sink is supplied | byte-identical | ✅ pinned by test |
| No pack mutation | `language_packs/` tree mtimes unchanged across a `contemplate_*` invocation | true | ✅ pinned by test |
| Predicate split | `missed_contradiction` and `false_contradiction_flag` produce distinct `proposed_action` text | distinct | ✅ pinned by test |
| Lane config_hash separation | `contemplate_frontier_reports` and `contemplate_contradiction_reports` produce distinct `config_hash` on identical input paths | distinct | ✅ pinned by test |

## When it has failed and why

- **2026-05-20** — ADR-0080 first shipped (`#55`) with one miner
  (`frontier_compare`) and no consumer.  SPECULATIVE invariant
  protected a write path that didn't exist.
- **2026-05-20** — `#56` fast-follow miner was **closed** to avoid
  entrenching the parallel `core/contemplation/` lane.  Replaced
  by `#58` which connected the boundary doctrine to existing
  `teaching/discovery_sink.py` plumbing.
- **2026-05-20** — `#58` documented the BOUNDARY between
  `EvidencePointer` (teaching: reviewed memory only) and
  `ContemplationEvidenceRef` (core: external report files).
  Forcing them to merge would have either widened the
  reviewed-memory enum (losing the guarantee) or made benchmark
  reports masquerade as `vault_coherent`.  Both worse than
  documented separation.
- **2026-05-20** — `#60` discovered the CLI was invisible — the
  contemplation module was reachable only via `python -m
  core.contemplation`, not via `core --help`.  Subcommand added.

## Runner / module layout

- `core/contemplation/schema.py` — `ContemplationFinding`,
  `ContemplationRun`, `ContemplationEvidenceRef`, `FindingKind`,
  the BOUNDARY doc.
- `core/contemplation/runner.py` —
  `contemplate_frontier_reports(...)`,
  `contemplate_contradiction_reports(...)`,
  `_emit_findings(...)` (shared sink emission helper).
- `core/contemplation/miners/frontier_compare.py` —
  `mine_frontier_compare_report(report_path, *, substrate_hash)`.
- `core/contemplation/miners/contradiction_detection.py` —
  `mine_contradiction_detection_report(report_path, *, substrate_hash)`.
- `core/contemplation/snapshot.py` — `ContemplationSubstrate`
  (pack ids + report file digests).
- `core/contemplation/__main__.py` — module-level CLI.
- `core/cli.py:cmd_contemplation` — delegating subcommand wrapper.

## Tests

- `tests/test_contemplation_loop.py` — schema invariants, frontier
  miner, runner replay determinism, CLI write path.
- `tests/test_contemplation_pipeline_convergence.py` — shared sink
  protocol, contradiction miner, BOUNDARY doc regression guard,
  per-finding canonical JSONL, config_hash separation.
- `tests/test_architectural_invariants.py` — pack-tree
  non-mutation guard (cross-lane).

Total: 18 tests pinning the contract.
