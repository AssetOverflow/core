"""The L10 continuity soak runner — drives the REAL turn loop over N turns.

It runs the deterministic corpus through ``CognitiveTurnPipeline`` over a fresh
``ChatRuntime`` whose engine-state checkpoint lives in a caller-supplied
directory. Optionally it injects *reboot legs*: at a chosen turn boundary it
drops the live runtime and reconstructs a new one from the on-disk checkpoint —
exactly the lifecycle the L10 telos asks about ("resume as the same life") — and
optionally simulates a kill mid-checkpoint-write by leaving an orphan temp file
the reconstruct must ignore (ADR-0156 atomicity).

The runner is pure instrumentation: it records per-turn evidence
(``versor_condition``, canonical ``trace_hash``, vault size, peak RSS, anchor
distance, turn-to-turn field movement, and which boot segment produced the turn)
and returns it. It makes NO pass/fail judgement — that is ``predicates.py`` — and
it never repairs, normalizes, or mutates field state (it only reads what the real
pipeline produced).

What a reboot restores (Shape B+ / engine_state schema v2): recognizers,
discovery candidates, ``turn_count``, AND the full lived session state — field,
vault, session graph, referents, session anchor, and dialogue — via
``SessionContext.snapshot/restore``. So a reboot now resumes the SAME life and
P2b is transparent. (Under the original Shape B / ADR-0146 only the first three
survived and the lived field/vault were discarded — "many lives sharing a
checkpoint".) The ``booted_segment`` tag on each record lets the
reboot-transparency predicate (P2b) confirm a rebooted run is byte-identical to
an uninterrupted one.
"""

from __future__ import annotations

import resource
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig

from evals.l10_continuity.corpus import prompt_at


@dataclass(frozen=True, slots=True)
class TurnRecord:
    """Per-turn evidence captured from the real pipeline (no judgement)."""

    turn_index: int
    input_text: str
    trace_hash: str
    versor_condition: float
    surface: str
    vault_size: int
    peak_rss_raw: int
    booted_segment: int
    # P5 signals (NaN when undefined — e.g. movement on a segment's first turn,
    # or distance before an anchor exists).
    dist_to_anchor: float
    turn_movement: float


@dataclass(frozen=True, slots=True)
class ProbeRecord:
    """One P5a vault-recall probe: a field state registered at one turn, then
    queried against the vault at a later turn.

    The probe field bytes are stored as float32 (matching the vault's internal
    dtype so the recall can exercise the ``_exact_index`` path).  ``rank`` is the
    1-based position of the probe entry in the top-k recall results, or ``None``
    if the entry was not found within top-k.  ``across_reboot`` is True when the
    query turn falls after at least one reboot — the cross-reboot case is the
    primary claim P5a checks.
    """

    registered_at: int    # turn whose field state was captured as the probe
    verified_at: int      # turn when vault.recall was issued with that field
    rank: int | None      # 1-based rank in recall results (None = not found)
    top_k: int
    across_reboot: bool   # a reboot occurred between registered_at and verified_at


@dataclass(frozen=True, slots=True)
class SoakResult:
    """The full ordered evidence of one soak run."""

    n_turns: int
    reboot_at: tuple[int, ...]
    records: tuple[TurnRecord, ...]
    probe_records: tuple[ProbeRecord, ...] = ()  # P5a vault-recall probes

    def trace_hashes(self) -> tuple[str, ...]:
        return tuple(r.trace_hash for r in self.records)

    def versor_conditions(self) -> tuple[float, ...]:
        return tuple(r.versor_condition for r in self.records)

    def post_reboot_records(self) -> tuple[TurnRecord, ...]:
        """Records produced at/after the first reboot (the recovered tail)."""
        if not self.reboot_at:
            return ()
        first = self.reboot_at[0]
        return tuple(r for r in self.records if r.turn_index >= first)


def _peak_rss_raw() -> int:
    """Process peak RSS as the OS reports it (bytes on macOS, KiB on Linux).

    The unit differs by platform, so callers must use this only for
    *ratio*/monotonic checks (P3), never as an absolute byte ceiling.
    """
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _new_runtime(config: RuntimeConfig, engine_state_dir: Path) -> ChatRuntime:
    """Construct a ChatRuntime bound to the checkpoint dir.

    Reconstruction is the reboot: ``ChatRuntime.__init__`` loads the on-disk
    engine-state checkpoint when one exists, so a second instance over the same
    directory resumes from the last durable checkpoint. The continuity lane is
    the resume-mode lane by definition, so it forces ``persist_session_state`` on
    (the full lived field/vault/anchor/graph survive reboot — what P2b measures).
    """
    if not config.persist_session_state:
        config = replace(config, persist_session_state=True)
    return ChatRuntime(config=config, engine_state_path=engine_state_dir)


def _inject_orphan_tmp(engine_state_dir: Path) -> None:
    """Simulate a kill mid-checkpoint-write: leave an orphan temp file.

    ADR-0156 writes ``content`` to a ``.<name>.<rand>.tmp`` file, fsyncs, then
    ``os.replace``s it into place. A SIGKILL between fsync and replace leaves
    exactly such an orphan with the *real* target fully intact. The loader reads
    only the canonical filenames, so the orphan must be ignored. We write a
    deliberately-corrupt orphan to prove the loader never reads it.
    """
    engine_state_dir.mkdir(parents=True, exist_ok=True)
    orphan = engine_state_dir / ".manifest.json.deadbeef.tmp"
    orphan.write_text("{ this is a torn, half-written checkpoint <<<", encoding="utf-8")


def read_recovered_turn_count(engine_state_dir: Path) -> int | None:
    """Read ``turn_count`` from the on-disk manifest, or None if absent."""
    from engine_state import EngineStateStore

    manifest = EngineStateStore(engine_state_dir).load_manifest()
    return None if manifest is None else int(manifest.get("turn_count", 0))


def _anchor_distance(runtime: ChatRuntime) -> float:
    ctx = runtime._context
    if ctx.state is None or ctx._anchor_field is None:
        return float("nan")
    f = np.asarray(ctx.state.F, dtype=np.float64)
    anchor = np.asarray(ctx._anchor_field, dtype=np.float64)
    return float(np.linalg.norm(f - anchor))


def _current_field(runtime: ChatRuntime) -> np.ndarray | None:
    ctx = runtime._context
    return None if ctx.state is None else np.asarray(ctx.state.F, dtype=np.float64)


def run_soak(
    n_turns: int,
    *,
    engine_state_dir: Path,
    reboot_at: tuple[int, ...] = (),
    config: RuntimeConfig | None = None,
    inject_orphan_tmp_at_reboot: bool = False,
    probe_at: tuple[int, ...] = (),
    verify_probes_at: tuple[int, ...] = (),
    probe_top_k: int = 5,
) -> SoakResult:
    """Run ``n_turns`` of the deterministic corpus, optionally rebooting.

    ``reboot_at`` is a set of turn indices at which, *before* running that turn,
    the live runtime is dropped and reconstructed from the checkpoint. A reboot
    at turn 0 is meaningless (nothing checkpointed yet) and is ignored. When
    ``inject_orphan_tmp_at_reboot`` is set, a torn-write orphan temp file is left
    in the checkpoint dir immediately before each reconstruct, so the reboot
    exercises ADR-0156 crash recovery rather than a clean restart.

    P5a vault-recall probes: ``probe_at`` names turns at which the current field
    state is captured as a probe query (float32 bytes, matching the vault's
    storage dtype).  ``verify_probes_at`` names turns at which every registered
    probe is recalled against the vault and its rank recorded.  A probe
    registered before the reboot and verified after is the cross-reboot case.
    """
    if n_turns < 0:
        raise ValueError(f"n_turns must be non-negative, got {n_turns}")
    config = config or RuntimeConfig()
    reboot_set = {i for i in reboot_at if i > 0}
    probe_set = set(probe_at)
    verify_set = set(verify_probes_at)

    runtime = _new_runtime(config, engine_state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    segment = 0
    prev_field: np.ndarray | None = None
    records: list[TurnRecord] = []
    probe_registry: dict[int, bytes] = {}  # registered_at → float32 field bytes
    probe_records: list[ProbeRecord] = []

    for i in range(n_turns):
        if i in reboot_set:
            if inject_orphan_tmp_at_reboot:
                _inject_orphan_tmp(engine_state_dir)
            runtime = _new_runtime(config, engine_state_dir)
            pipe = CognitiveTurnPipeline(runtime=runtime)
            segment += 1
            prev_field = None  # movement is undefined across a reboot boundary

        text = prompt_at(i)
        result = pipe.run(text)
        field = _current_field(runtime)
        movement = (
            float(np.linalg.norm(field - prev_field))
            if field is not None and prev_field is not None
            else float("nan")
        )
        records.append(
            TurnRecord(
                turn_index=i,
                input_text=text,
                trace_hash=result.trace_hash,
                versor_condition=float(result.versor_condition),
                surface=result.surface,
                vault_size=len(runtime._context.vault),
                peak_rss_raw=_peak_rss_raw(),
                booted_segment=segment,
                dist_to_anchor=_anchor_distance(runtime),
                turn_movement=movement,
            )
        )
        prev_field = field

        # P5a: register probe after this turn's vault entries are committed.
        if i in probe_set and field is not None:
            probe_registry[i] = field.astype(np.float32).tobytes()

        # P5a: verify all registered probes against the live vault.
        if i in verify_set and probe_registry:
            vault = runtime._context.vault
            for reg_turn, probe_bytes in probe_registry.items():
                across_reboot = any(reg_turn < r <= i for r in reboot_set)
                probe_arr = np.frombuffer(probe_bytes, dtype=np.float32).copy()
                hits = vault.recall(probe_arr, top_k=probe_top_k)
                rank: int | None = None
                for j, hit in enumerate(hits, start=1):
                    stored = np.asarray(hit["versor"], dtype=np.float32)
                    if stored.tobytes() == probe_bytes:
                        rank = j
                        break
                probe_records.append(
                    ProbeRecord(
                        registered_at=reg_turn,
                        verified_at=i,
                        rank=rank,
                        top_k=probe_top_k,
                        across_reboot=across_reboot,
                    )
                )

    return SoakResult(
        n_turns=n_turns,
        reboot_at=tuple(sorted(reboot_set)),
        records=tuple(records),
        probe_records=tuple(probe_records),
    )
