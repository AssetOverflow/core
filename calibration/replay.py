"""Replay eval cases under a given parameter set and return metrics."""

from __future__ import annotations

from core.config import RuntimeConfig, DEFAULT_CONFIG
from calibration.params import CalibrationParams
from evals.metrics import EvalReport
from evals.run_cognition_eval import load_cases, run_eval


def replay_with_params(
    params: CalibrationParams,
    cases: list[dict] | None = None,
) -> EvalReport:
    """Run the eval harness under a specific parameter configuration.

    Builds a RuntimeConfig from the CalibrationParams and passes it
    through to run_eval, which creates fresh ChatRuntime instances
    per case.
    """
    if cases is None:
        cases = load_cases()

    config = RuntimeConfig(
        input_packs=DEFAULT_CONFIG.input_packs,
        output_language=DEFAULT_CONFIG.output_language,
        frame_pack=DEFAULT_CONFIG.frame_pack,
        max_tokens=DEFAULT_CONFIG.max_tokens,
        allow_cross_language_recall=DEFAULT_CONFIG.allow_cross_language_recall,
        allow_cross_language_generation=DEFAULT_CONFIG.allow_cross_language_generation,
        vault_reproject_interval=DEFAULT_CONFIG.vault_reproject_interval,
        use_salience=DEFAULT_CONFIG.use_salience,
        salience_top_k=params.salience_top_k,
        inhibition_threshold=params.inhibition_threshold,
    )
    return run_eval(cases, config=config)
