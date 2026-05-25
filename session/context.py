"""
SessionContext — binds field, vault, vocab, persona, referents, and graph.

The ingest path is split into a non-mutating probe and a committing ingest so
runtime gates can inspect the candidate field before durable vault writes.  All
response paths finalize through one graph/vault/session-state method.
"""

from __future__ import annotations

import numpy as np

from algebra.backend import cga_inner, versor_apply
from algebra.rotor import rotor_power, word_transition_rotor
from algebra.versor import versor_condition as _versor_condition
from field.state import FieldState
from generate.dialogue import DialogueTurn
from generate.proposition import Proposition
from generate.result import GenerationResult
from generate.stream import generate
from ingest.gate import inject
from persona.motor import PersonaMotor
from session.graph import SessionGraph
from session.referents import ReferentRegistry
from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore

# Dialogue blade EMA decay — how much the running blade "remembers" prior turns.
# α=0.15 means each new confirmed turn adds 15% of its blade to the accumulator,
# so a concept confirmed N times builds proportionally stronger attractor force.
_BLADE_EMA_ALPHA: float = 0.15

# Anchor pull strength — how hard each finalized turn is pulled back toward the
# session anchor field. 0.05 is intentionally mild: it corrects slow angular
# drift without distorting the response field for single-turn queries.
_ANCHOR_PULL_ALPHA: float = 0.05


class SessionContext:
    def __init__(self, vocab, persona=None, vault=None, vault_reproject_interval: int = 100):
        self.vocab = vocab
        self.persona = persona or PersonaMotor.identity()
        self.vault = vault or VaultStore(reproject_interval=vault_reproject_interval)
        self.state: FieldState | None = None
        self.turn: int = 0
        self.graph: SessionGraph = SessionGraph()
        self.referents: ReferentRegistry = ReferentRegistry()
        self.running_dialogue_blade: np.ndarray | None = None
        self._last_response_tokens: tuple[str, ...] | None = None
        self._anchor_field: np.ndarray | None = None
        self._dialogue_history_compat: list[DialogueTurn] = []
        self._last_input_tokens: tuple[str, ...] = ()
        self._last_resolved_input_tokens: tuple[str, ...] = ()
        self._last_input_versor: np.ndarray | None = None

    @property
    def dialogue_history(self) -> list[DialogueTurn]:
        return self._dialogue_history_compat

    @property
    def last_input_tokens(self) -> tuple[str, ...]:
        return self._last_input_tokens

    @property
    def last_resolved_input_tokens(self) -> tuple[str, ...]:
        return self._last_resolved_input_tokens

    def _field_from_tokens(self, tokens: list[str], *, resolve_referents: bool) -> tuple[FieldState, list[str]]:
        resolved_tokens = self.referents.resolve(tokens) if resolve_referents else list(tokens)
        injected = inject(resolved_tokens, self.vocab)
        anchor_token = resolved_tokens[0] if resolved_tokens else (tokens[0] if tokens else "")
        try:
            node_idx = self.vocab.index_of(anchor_token)
        except (KeyError, IndexError):
            node_idx = self.vocab.index_of(tokens[0]) if tokens else 0

        if self.state is None:
            candidate = FieldState(
                F=injected.F,
                node=node_idx,
                step=injected.step,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
        else:
            composed_F = versor_apply(injected.F, self.state.F)
            condition = _versor_condition(composed_F)
            if condition > 1e-2:
                raise RuntimeError(
                    f"Cross-turn field composition violated versor condition: {condition:.3e}"
                )
            candidate = FieldState(
                F=composed_F,
                node=node_idx,
                step=self.state.step + 1,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
        return candidate, resolved_tokens

    def probe_ingest(self, tokens: list[str]) -> FieldState:
        """Build the candidate ingest field without mutating state or vault."""
        snapshot_sources = self.referents.consumed_turns()
        snapshot_slots = self.referents.consumed_slots()
        candidate, _ = self._field_from_tokens(tokens, resolve_referents=True)
        self.referents._last_resolved_sources = snapshot_sources
        self.referents._last_resolved_slots = snapshot_slots
        return candidate

    def commit_ingest(self, tokens: list[str]) -> FieldState:
        """Resolve, inject, mutate live state, and store the user field."""
        field_state, resolved_tokens = self._field_from_tokens(tokens, resolve_referents=True)
        self.state = field_state
        if self._anchor_field is None:
            self._anchor_field = field_state.F.copy()
        self._last_input_tokens = tuple(tokens)
        self._last_resolved_input_tokens = tuple(resolved_tokens)
        self._last_input_versor = field_state.F.copy()
        self.vault.store(
            field_state.F,
            {"turn": self.turn, "role": "user"},
            epistemic_status=EpistemicStatus.SPECULATIVE,
        )
        return field_state

    def ingest(self, tokens: list[str]) -> FieldState:
        """Backward-compatible committing ingest."""
        return self.commit_ingest(tokens)

    def record_dialogue(self, proposition: Proposition) -> DialogueTurn:
        from generate.dialogue import DialogueTurn as _DT

        blade = proposition.relation
        turn = _DT(proposition=proposition, outer_product_blade=blade)
        self._dialogue_history_compat.append(turn)

        if self.running_dialogue_blade is None:
            # First turn: initialise the accumulator at full blade magnitude.
            self.running_dialogue_blade = blade.copy()
        else:
            # Drift fix 1: magnitude-preserving EMA accumulation.
            #
            # Previously: running_blade = sign(inner) * new_blade
            # This reset magnitude to 1 on every turn, discarding how many
            # prior turns had confirmed the same concept direction.
            #
            # Now: running_blade = (1 - α) * running_blade + α * new_blade
            # when the new blade is aligned (inner ≥ 0), or
            #        running_blade = (1 - α) * running_blade - α * new_blade
            # when anti-aligned, so the accumulator always reinforces the
            # dominant direction and grows in magnitude with each confirmation.
            alpha = _BLADE_EMA_ALPHA
            alignment = cga_inner(self.running_dialogue_blade, blade)
            sign = 1.0 if float(alignment) >= 0.0 else -1.0
            self.running_dialogue_blade = (
                (1.0 - alpha) * self.running_dialogue_blade + alpha * sign * blade
            )

        return turn

    @property
    def last_dialogue_blade(self) -> np.ndarray | None:
        if not self._dialogue_history_compat:
            return None
        return self._dialogue_history_compat[-1].outer_product_blade.copy()

    def _register_result_referent(self, result: GenerationResult) -> None:
        if not result.tokens:
            return
        versors: dict[str, np.ndarray] = {}
        for tok in result.tokens:
            try:
                versors[tok] = self.vocab.get_versor(tok)
            except KeyError:
                pass
        self.referents.register_from_tokens(result.tokens, versors, turn=self.turn)

    def _hemisphere_consistent_field(self, field_state: FieldState) -> FieldState:
        """Ensure field stays in the same CGA hemisphere as the session anchor."""
        if self._anchor_field is None:
            return field_state
        if cga_inner(field_state.F, self._anchor_field) >= 0.0:
            return field_state
        return FieldState(
            F=-field_state.F,
            node=field_state.node,
            step=field_state.step,
            holonomy=field_state.holonomy,
            energy=field_state.energy,
            valence=field_state.valence,
        )

    def _anchor_pull(self, field_state: FieldState) -> FieldState:
        """Drift fix 3: mild rotor-geodesic pull toward the session anchor field.

        Applied after hemisphere correction. Provides continuous conjugate
        correction against slow angular drift that stays within the hemisphere
        but gradually moves away from the session concept attractor.

        Computes the transition rotor R = anchor * reverse(F), scales it to
        R^α via rotor_power (stays on the versor manifold by construction), and
        applies it via versor_apply.  This replaces the previous _slerp_toward
        approach, which interpolated on S^31 rather than on the Spin sub-manifold
        and required a post-hoc unitize_versor to repair the manifold violation.

        α=0.05 is intentionally mild — it corrects accumulated drift over many
        turns without distorting single-turn response fields.
        """
        if self._anchor_field is None:
            return field_state
        try:
            R = word_transition_rotor(field_state.F, self._anchor_field)
        except ValueError:
            return field_state
        R_step = rotor_power(R, _ANCHOR_PULL_ALPHA)
        pulled_F = versor_apply(R_step, field_state.F)
        return FieldState(
            F=pulled_F,
            node=field_state.node,
            step=field_state.step,
            holonomy=field_state.holonomy,
            energy=field_state.energy,
            valence=field_state.valence,
        )

    def finalize_turn(
        self,
        result: GenerationResult,
        *,
        tokens_in: tuple[str, ...] | None = None,
        dialogue_role: str = "assert",
        input_versor: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Finalize assistant output into referents, graph, vault, and state."""
        if self.state is None and input_versor is None:
            raise AssertionError("Call ingest() before finalize_turn().")

        input_F = (
            np.asarray(input_versor, dtype=np.float32).copy()
            if input_versor is not None
            else (self._last_input_versor.copy() if self._last_input_versor is not None else self.state.F.copy())
        )
        turn_tokens = tuple(tokens_in if tokens_in is not None else self._last_input_tokens)
        backward_edges = self.referents.consumed_turns()
        active_slots = self.referents.active_slots()

        self._register_result_referent(result)
        active_slots = self.referents.active_slots() | active_slots

        # Drift fix 3: hemisphere correction + anchor pull (conjugate correction).
        oriented_state = self._hemisphere_consistent_field(result.final_state)
        oriented_state = self._anchor_pull(oriented_state)

        self.graph.add_turn(
            turn_idx=self.turn,
            input_versor=input_F,
            output_versor=oriented_state.F,
            tokens_in=turn_tokens,
            tokens_out=tuple(result.tokens or []),
            dialogue_role=dialogue_role,
            referent_slots=active_slots,
            backward_edges=backward_edges,
        )
        self.state = oriented_state
        payload = {"turn": self.turn, "role": "assistant"}
        if metadata:
            payload.update(metadata)
        # ADR-0148 — persist energy profile so VaultPromotionPolicy can decide
        # promotion eligibility on future turns (after the entry has cooled).
        if oriented_state.energy is not None:
            payload["energy_raw"] = float(oriented_state.energy.raw)
            payload["energy_class"] = oriented_state.energy.energy_class.value
            payload["coherence_residual"] = float(oriented_state.energy.coherence_residual)
        self.vault.store(
            oriented_state.F,
            payload,
            epistemic_status=EpistemicStatus.SPECULATIVE,
        )
        self.turn += 1
        self._last_response_tokens = result.tokens

    def apply_corrected_outputs(self, records) -> None:
        """Synchronize corrected graph records into live session recall surfaces."""
        for record in records:
            self.vault.store(
                record.new_versor,
                {"turn": record.turn_idx, "role": "assistant", "corrected": True},
                epistemic_status=EpistemicStatus.SPECULATIVE,
            )
            self.referents.update_turn_versor(record.turn_idx, record.new_versor)
        if records:
            last = max(records, key=lambda r: r.turn_idx)
            if self.state is not None:
                self.state = FieldState(
                    F=last.new_versor,
                    node=self.state.node,
                    step=self.state.step,
                    holonomy=self.state.holonomy,
                    energy=self.state.energy,
                    valence=self.state.valence,
                )

    def respond(self, max_tokens: int = 128) -> GenerationResult:
        assert self.state is not None, "Call ingest() before respond()."
        input_versor = self._last_input_versor.copy() if self._last_input_versor is not None else self.state.F.copy()
        result = generate(self.state, self.vocab, self.persona, max_tokens, vault=self.vault)
        if self._last_response_tokens is not None and result.tokens == self._last_response_tokens and result.tokens:
            try:
                pivot_node = self.vocab.index_of(result.tokens[0])
            except KeyError:
                pivot_node = self.state.node
            if pivot_node != self.state.node:
                pivot = FieldState(
                    F=self.state.F,
                    node=pivot_node,
                    step=self.state.step,
                    holonomy=self.state.holonomy,
                    energy=self.state.energy,
                    valence=self.state.valence,
                )
                result = generate(pivot, self.vocab, self.persona, max_tokens, vault=self.vault)
        self.finalize_turn(result, input_versor=input_versor, dialogue_role="assert")
        # Drift fix 3 may have rotated/pulled the state inside finalize_turn;
        # re-bind result.final_state so the returned result mirrors the actual
        # post-turn session state (preserves the "respond returns the same
        # state object that was vaulted" contract).
        from dataclasses import replace as _replace
        return _replace(result, final_state=self.state)

    def recall(self, query_tokens: list, top_k: int = 5) -> list:
        query_state = inject(query_tokens, self.vocab)
        return self.vault.recall(query_state.F, top_k=top_k)
