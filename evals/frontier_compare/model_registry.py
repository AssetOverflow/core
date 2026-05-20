"""Model registry — canonical metadata for every frontier model used in benchmarks.

Why this exists
---------------
Every benchmark report must carry exact, reproducible model identity.  A
floating alias like ``gpt-4o`` is not sufficient because the underlying
weights and behavior can change silently between runs.  This module:

1. Stores a ``ModelCard`` for each model ever used in a CORE benchmark.
2. Provides ``resolve_model_card()`` so a benchmark runner can attach
   full metadata to its report at run time.
3. Acts as the canonical source-of-truth for the docs in
   ``docs/models/``.

Adding a new model
------------------
1. Add an entry to ``_REGISTRY`` below following the existing pattern.
2. Run any benchmark with that provider/model combo — the runner will
   call ``resolve_model_card()`` and embed the card in the report JSON.
3. Update ``docs/models/<provider>.md`` with the card's details.

ADR
---
ADR-0082 — Frontier provider adapters
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Provider = Literal["openai", "anthropic", "ollama", "core"]


@dataclass(frozen=True, slots=True)
class ModelCard:
    """Canonical metadata for one model version used in a benchmark."""

    provider: str
    model_id: str
    """Exact slug used in API calls (e.g. ``gpt-4o-2024-08-06``)."""

    display_name: str
    """Human-readable name for reports and UI."""

    knowledge_cutoff: str
    """ISO date (YYYY-MM) of the model's training knowledge cutoff."""

    context_window: int
    """Maximum context length in tokens."""

    output_tokens: int
    """Maximum output tokens per completion."""

    architecture: str
    """High-level architecture description (e.g. 'GPT-4 class transformer')."""

    sampling: str
    """Sampling behaviour note (e.g. 'stochastic at T>0, near-deterministic at T=0 but not guaranteed')."""

    notes: str = ""
    """Free-form notes: known quirks, benchmark-specific observations, version history."""

    input_usd_per_million_tokens: float | None = None
    """Public list price for input tokens in USD per 1M tokens."""

    output_usd_per_million_tokens: float | None = None
    """Public list price for output tokens in USD per 1M tokens."""

    pricing_source: str = ""
    """Source URL/note for pricing metadata."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Searchable tags, e.g. ('reasoning', 'code', 'vision')."""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d

    @property
    def has_pricing(self) -> bool:
        return (
            self.input_usd_per_million_tokens is not None
            and self.output_usd_per_million_tokens is not None
        )

    def estimate_cost_usd(
        self,
        *,
        input_tokens: int | float,
        output_tokens: int | float,
    ) -> float | None:
        """Compute provider list-price cost for one request.

        Formula:
            cost_usd =
              (input_tokens / 1_000_000) * input_usd_per_million_tokens +
              (output_tokens / 1_000_000) * output_usd_per_million_tokens
        """
        if not self.has_pricing:
            return None
        in_rate = float(self.input_usd_per_million_tokens or 0.0)
        out_rate = float(self.output_usd_per_million_tokens or 0.0)
        return (
            (float(input_tokens) / 1_000_000.0) * in_rate
            + (float(output_tokens) / 1_000_000.0) * out_rate
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# Key format: "<provider>/<model_id>"
# Use the exact model_id string you pass to the API / Ollama tag.

_REGISTRY: dict[str, ModelCard] = {

    # ─── CORE native ──────────────────────────────────────────
    "core/core-native": ModelCard(
        provider="core",
        model_id="core-native",
        display_name="CORE (native)",
        knowledge_cutoff="N/A",
        context_window=0,
        output_tokens=0,
        architecture="Versor engine on Cl(4,1) CGA — deterministic field propagation, no sampling.",
        sampling="Fully deterministic. Same (pack, vault, seed) state always produces byte-identical output.",
        notes="Not a language model. Output is a realized surface from a structured pack graph + vault state.",
        tags=("deterministic", "structured", "grounded", "no-sampling"),
    ),

    # ─── OpenAI ──────────────────────────────────────────────
    "openai/gpt-4o": ModelCard(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o (floating alias)",
        knowledge_cutoff="2024-04",
        context_window=128_000,
        output_tokens=16_384,
        architecture="GPT-4 class transformer, multimodal (text + vision).",
        sampling="Stochastic at T>0. T=0 is near-deterministic but not guaranteed across API calls or model updates.",
        notes=(
            "Floating alias — underlying weights may change without notice. "
            "Use a dated snapshot (e.g. gpt-4o-2024-08-06) for reproducible benchmarks. "
            "Set OPENAI_MODEL=gpt-4o-2024-08-06 in .env."
        ),
        input_usd_per_million_tokens=2.50,
        output_usd_per_million_tokens=10.00,
        pricing_source="https://openai.com/api/pricing (captured 2026-05-20)",
        tags=("frontier", "multimodal", "reasoning", "code"),
    ),
    "openai/gpt-4o-2024-08-06": ModelCard(
        provider="openai",
        model_id="gpt-4o-2024-08-06",
        display_name="GPT-4o (2024-08-06 snapshot)",
        knowledge_cutoff="2024-04",
        context_window=128_000,
        output_tokens=16_384,
        architecture="GPT-4 class transformer, multimodal (text + vision).",
        sampling="Stochastic at T>0. T=0 is near-deterministic for a fixed snapshot but backend routing can still vary.",
        notes="Pinned snapshot. Preferred for reproducible benchmark comparisons.",
        input_usd_per_million_tokens=2.50,
        output_usd_per_million_tokens=10.00,
        pricing_source="https://openai.com/api/pricing (captured 2026-05-20)",
        tags=("frontier", "multimodal", "reasoning", "code", "pinned"),
    ),
    "openai/gpt-4o-mini": ModelCard(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o mini",
        knowledge_cutoff="2024-04",
        context_window=128_000,
        output_tokens=16_384,
        architecture="Smaller GPT-4o class model optimised for latency and cost.",
        sampling="Stochastic at T>0.",
        notes="Useful for cost/latency baseline comparisons in the benchmark cost suite.",
        input_usd_per_million_tokens=0.15,
        output_usd_per_million_tokens=0.60,
        pricing_source="https://openai.com/api/pricing (captured 2026-05-20)",
        tags=("frontier", "fast", "cost-efficient"),
    ),
    "openai/o3": ModelCard(
        provider="openai",
        model_id="o3",
        display_name="OpenAI o3",
        knowledge_cutoff="2024-06",
        context_window=200_000,
        output_tokens=100_000,
        architecture="GPT-4 class transformer with extended chain-of-thought reasoning (o-series).",
        sampling="Uses internal reasoning tokens before output. Surface is stochastic at T>0.",
        notes=(
            "o-series models use a reasoning_effort parameter instead of temperature. "
            "Pass via ProviderConfig.extra = {'reasoning_effort': 'high'} for benchmark use."
        ),
        pricing_source="https://openai.com/api/pricing (captured 2026-05-20)",
        tags=("frontier", "reasoning", "chain-of-thought"),
    ),

    # ─── Anthropic ───────────────────────────────────────────
    "anthropic/claude-opus-4-5": ModelCard(
        provider="anthropic",
        model_id="claude-opus-4-5",
        display_name="Claude Opus 4.5",
        knowledge_cutoff="2025-04",
        context_window=200_000,
        output_tokens=32_000,
        architecture="Claude 4 class transformer (Anthropic). Supports extended thinking.",
        sampling="Stochastic at T>0. Extended thinking mode uses internal scratchpad tokens.",
        notes=(
            "Current highest-capability Anthropic model. "
            "Default ANTHROPIC_MODEL in .env.example. "
            "For extended thinking benchmarks, pass extra={'thinking': {'type': 'enabled', 'budget_tokens': 10000}}."
        ),
        input_usd_per_million_tokens=15.00,
        output_usd_per_million_tokens=75.00,
        pricing_source="https://www.anthropic.com/pricing (captured 2026-05-20)",
        tags=("frontier", "reasoning", "code", "extended-thinking"),
    ),
    "anthropic/claude-sonnet-4-5": ModelCard(
        provider="anthropic",
        model_id="claude-sonnet-4-5",
        display_name="Claude Sonnet 4.5",
        knowledge_cutoff="2025-04",
        context_window=200_000,
        output_tokens=16_000,
        architecture="Claude 4 class transformer (Anthropic). Balanced speed/capability.",
        sampling="Stochastic at T>0.",
        notes="Good default for high-volume benchmark sweeps where Opus cost is prohibitive.",
        input_usd_per_million_tokens=3.00,
        output_usd_per_million_tokens=15.00,
        pricing_source="https://www.anthropic.com/pricing (captured 2026-05-20)",
        tags=("frontier", "balanced", "cost-efficient"),
    ),
    "anthropic/claude-haiku-3-5": ModelCard(
        provider="anthropic",
        model_id="claude-haiku-3-5",
        display_name="Claude Haiku 3.5",
        knowledge_cutoff="2024-07",
        context_window=200_000,
        output_tokens=8_096,
        architecture="Claude 3 class transformer (Anthropic). Optimised for latency.",
        sampling="Stochastic at T>0.",
        notes="Useful for latency/cost baseline comparisons. Lower capability ceiling than Sonnet/Opus.",
        input_usd_per_million_tokens=0.80,
        output_usd_per_million_tokens=4.00,
        pricing_source="https://www.anthropic.com/pricing (captured 2026-05-20)",
        tags=("frontier", "fast", "cost-efficient"),
    ),

    # ─── Ollama / local open-weight ───────────────────────────
    "ollama/llama3.2": ModelCard(
        provider="ollama",
        model_id="llama3.2",
        display_name="Llama 3.2 (latest tag)",
        knowledge_cutoff="2024-03",
        context_window=128_000,
        output_tokens=2_048,
        architecture="Meta Llama 3.2 — transformer decoder, open-weight.",
        sampling="Stochastic at T>0. Local inference — no backend routing nondeterminism, but sampler is stochastic.",
        notes=(
            "Default OLLAMA_MODEL in .env.example. "
            "Tag 'llama3.2' resolves to the latest quantisation Ollama has pulled locally; "
            "pin to 'llama3.2:3b-instruct-q8_0' or similar for reproducibility. "
            "Run 'ollama list' to see exact tags installed."
        ),
        tags=("open-weight", "local", "meta", "llama"),
    ),
    "ollama/llama3.2:3b-instruct-q8_0": ModelCard(
        provider="ollama",
        model_id="llama3.2:3b-instruct-q8_0",
        display_name="Llama 3.2 3B Instruct Q8_0",
        knowledge_cutoff="2024-03",
        context_window=128_000,
        output_tokens=2_048,
        architecture="Meta Llama 3.2 3B — transformer decoder, Q8_0 quantisation.",
        sampling="Stochastic at T>0.",
        notes="Pinned quantisation tag. Preferred over the floating 'llama3.2' tag for benchmarks.",
        tags=("open-weight", "local", "meta", "llama", "pinned", "3b"),
    ),
    "ollama/mistral": ModelCard(
        provider="ollama",
        model_id="mistral",
        display_name="Mistral 7B (latest Ollama tag)",
        knowledge_cutoff="2023-09",
        context_window=32_768,
        output_tokens=4_096,
        architecture="Mistral 7B v0.x — transformer decoder, open-weight.",
        sampling="Stochastic at T>0.",
        notes="Floating Ollama tag. Pin to a specific version for reproducible benchmarks.",
        tags=("open-weight", "local", "mistral", "7b"),
    ),
    "ollama/gemma3:12b": ModelCard(
        provider="ollama",
        model_id="gemma3:12b",
        display_name="Gemma 3 12B",
        knowledge_cutoff="2024-11",
        context_window=128_000,
        output_tokens=8_192,
        architecture="Google Gemma 3 12B — transformer decoder, open-weight.",
        sampling="Stochastic at T>0.",
        notes="Mid-size open-weight model. Good capability/cost tradeoff for local benchmarks.",
        tags=("open-weight", "local", "google", "gemma", "12b"),
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_model_card(provider: str, model_id: str) -> ModelCard | None:
    """Return the ``ModelCard`` for *(provider, model_id)* or ``None``.

    Case-insensitive lookup on both keys.  Returns ``None`` (never raises)
    so callers can embed the result in a report without crashing on an
    unknown model.  Unrecognised models should be added to ``_REGISTRY``
    after the first benchmark run.
    """
    key = f"{provider.lower()}/{model_id}"
    return _REGISTRY.get(key)


def require_model_card(provider: str, model_id: str) -> ModelCard:
    """Like ``resolve_model_card`` but raises ``KeyError`` if not found.

    Use this in benchmark setup code that must refuse to run against an
    unregistered model to prevent undocumented benchmark results.
    """
    card = resolve_model_card(provider, model_id)
    if card is None:
        raise KeyError(
            f"Model '{provider}/{model_id}' is not in the model registry. "
            f"Add a ModelCard entry to evals/frontier_compare/model_registry.py "
            f"before running benchmarks against this model."
        )
    return card


def list_registered_models(provider: str | None = None) -> list[ModelCard]:
    """Return all registered model cards, optionally filtered by *provider*."""
    cards = list(_REGISTRY.values())
    if provider:
        cards = [c for c in cards if c.provider == provider.lower()]
    return cards
