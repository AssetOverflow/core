# placeholder implementation for bound replay adapter

from generate.replay_adapter import ReplayAdapterInput, ReplayAdapterRefusal, CONTRACT_PROOF_REPLAY_POLICY_VERSION


def build_replay_adapter_input_from_binding(*, run, binding, candidate_operator_result, proof_obligation_refs=(), schema_versions=(), replay_policy_version=CONTRACT_PROOF_REPLAY_POLICY_VERSION):
    """Binding-aware replay input builder (stub).
    TODO: full ADR-compliant implementation.
    """
    raise NotImplementedError("build_replay_adapter_input_from_binding not yet implemented")
