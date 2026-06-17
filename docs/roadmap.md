# CORE Problem-Solving Capability Roadmap

**Ultimate Revision – Capability-Gated (v2.1)**

## North Star

CORE becomes a trustworthy, inspectable, edge-native problem-solving engine by systematically expanding typed, grounded reasoning coverage while preserving its core invariants.

Progress is measured by the ability to reliably solve increasingly deep, structured problems with `wrong_total == 0`, while making the reasoning process itself inspectable and improvable through explicit representation and audit artifacts.

## Core Metrics (Paired)

- `wrong_total == 0` (non-negotiable safety and truth invariant)
- `coverage_at_wrong0` (primary progress metric)

Supporting operational metrics:
- Reduction in `recognized_no_injection` refusals
- Depth curve improvement (1-hop → 3-hop → 5-hop reliability)
- Proposal acceptance yield + review cost efficiency
- Replay hash stability and corpus byte-identity
- Structural completeness of representation and audit artifacts

## Four Capability Ladders

### Ladder A — Problem-Solving Substrate (Highest Near-Term Priority)

**Focus**: Turn recognition into well-represented, typed, solvable state with strong initial analysis.

**Key principle**: Experts spend significantly more time analyzing and representing the problem before acting. A first-class `ProblemRepresentation` artifact creates a stable audit point before operator injection.

**Gates**:
- **A1**: Comparative injection complete with grounded actor/reference rules and strong confuser suite.
- **A2**: Typed `ProblemRepresentation` artifact emitted before operator injection for selected high-refusal GSM8K frontier classes.
- **A3**: Narrow affine equation frame operational with explicit problem representation phase.
- **A4**: `graph_planner.py` + new typed operations support reliable 3–5 hop problems in ratified domains with high-quality explain() output and reflection artifacts.

**Success signal**: Measurable reduction in `recognized_no_injection` while `wrong_total` remains 0 and depth curve improves.

### Ladder B — Reasoning Truth Substrate

**Focus**: Maintain clear, non-collapsing truth distinctions with explicit separation of reasoning modes.

**Key principle**: Open-world unknown ≠ finite-frame false ≠ refused. Reasoning mode must be monitored but must not collapse into claim status.

**Gates**:
- **B1**: Finite-frame closed-world verdicts (`FrameVerdict`) are usable inside explicitly closed scopes without leaking into open-world paths.
- **B2**: Relational and negative inference only occurs under declared, grounded, non-vacuous rules with independent verification.
- **B3**: The system can cleanly distinguish and surface True / Unknown / Refused / False within finite frames, with explicit recording of reasoning mode.

### Ladder C — Self-Building Flywheel (Deliberate Practice Engine)

**Focus**: Turn contemplation into a frontier-targeted proposal engine that functions as deliberate practice for the system.

**Refined mechanics**:
- Contemplation analyzes refusal patterns, frontier reports, and reasoning traces.
- It generates targeted proposals (including negative proposals) focused on specific weakness classes.
- Proposals are evaluated on both coverage gain and improvement in structural verification / review yield.
- The loop actively targets current frontiers rather than generating generic improvements.

**Gate C1**: Proposal cycles produce measurable `coverage_at_wrong0` gain per ratified artifact with stable or declining review cost and demonstrable improvement on previously weak problem classes.

### Ladder D — Operator & Workbench Mastery

**Focus**: Make every capability claim and reasoning process deeply inspectable end-to-end.

**Gates**:
- **D1**: `ProblemRepresentation`, `ReasoningAuditArtifact`, `ProposalArtifact`, `FrameVerdict`, eval evidence, replay hash, and lookback artifacts are first-class inspectable surfaces in CORE-Logos and the Workbench.
- **D2**: CORE-Logos becomes an active inspection and development surface for lexicon, morphology, semantic claims, and pack status.
- **D3**: Trace / explain / replay / eval / representation / audit views converge into a coherent evidence chain.
- **D4**: An independent evaluator can verify a capability claim (including the quality of the reasoning process) without trusting developer narrative.

## Governance

- Every major increment requires a ratification artifact in `docs/analysis/`.
- Lookbacks must accurately reflect actual diff, test results, and structural completeness of representation/audit artifacts.
- Regular frontier reports remain the primary monitoring mechanism.
- Any regression in `wrong_total`, replay stability, or unexpected increase in `recognized_no_injection` triggers immediate review and scope adjustment.

## Strategic Shape

CORE grows trustworthy structured problem-solving capability by closing typed operation gaps, strengthening multi-hop graph planning, maintaining clear open/closed-world separation with explicit reasoning-mode recording, and turning contemplation into an increasingly effective deliberate-practice proposal engine — advancing only when evidence bundles (coverage at wrong=0, depth curves, replay stability, proposal yield, and structural verification quality) justify the next step.

This version is deliberately sharper, more faithful to the current codebase, and structured for disciplined, high-probability execution while incorporating research-backed principles of expert problem solving (strong problem representation, explicit reasoning monitoring, and targeted improvement on weaknesses).