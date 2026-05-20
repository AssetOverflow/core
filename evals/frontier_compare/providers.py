"""Frontier provider adapters for CORE benchmark comparisons.

Design contract
---------------
Every adapter exposes a single callable::

    adapter(prompt: str) -> str

The return value is a raw surface string — no metadata, no JSON envelope.
Callers in the benchmark runner treat this identically to a CORE surface;
the comparison layer handles diffing.

All provider configuration is read from environment variables (loaded via
``_env()``).  No provider credentials appear in benchmark source code.

Model identity is *always* resolved to a pinned slug (the exact version
string the provider returns or that is configured).  Adapters refuse to
run if the slug is absent — callers must set ``OPENAI_MODEL``,
``ANTHROPIC_MODEL``, or ``OLLAMA_MODEL`` explicitly.  This ensures every
benchmark report carries an exact model identifier in its metadata rather
than a floating alias like ``gpt-4o`` whose underlying weights may change.

Usage
-----
::

    from evals.frontier_compare.providers import build_adapter, ProviderConfig
    from evals.frontier_compare.model_registry import resolve_model_card

    cfg = ProviderConfig.from_env("openai")
    adapter = build_adapter(cfg)
    card = resolve_model_card(cfg.provider, cfg.model)

    # Warm up (optional — some providers have cold-start overhead)
    _ = adapter("What is truth?")

    # Use in a benchmark
    surface = adapter("What is knowledge?")

Provider keys
-------------
* ``openai``    — OpenAI REST API (requires ``openai`` package)
* ``anthropic`` — Anthropic REST API (requires ``anthropic`` package)
* ``ollama``    — Local Ollama server (requires ``httpx`` or ``requests``)
* ``core``      — CORE's own ChatRuntime (no external dependency)

ADR
---
ADR-0081 — Frontier provider adapters
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    """Read an env var, stripping surrounding whitespace."""
    return os.environ.get(key, default).strip()


def _require_env(key: str) -> str:
    val = _env(key)
    if not val:
        raise EnvironmentError(
            f"Required environment variable {key!r} is not set or empty. "
            f"Copy .env.example to .env and fill in the value."
        )
    return val


# ---------------------------------------------------------------------------
# ProviderConfig — the resolved identity of one adapter instance
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Fully-resolved provider + model identity used for one benchmark run.

    All fields are immutable after construction so a config can be hashed,
    stored in a report, and compared across runs.
    """

    provider: str
    """One of: openai, anthropic, ollama, core."""

    model: str
    """Exact model slug as it will appear in every benchmark report.

    For OpenAI this should be a dated snapshot like ``gpt-4o-2024-08-06``
    rather than a floating alias.  For Ollama this is the tag as returned
    by ``ollama list``.
    """

    temperature: float = 0.0
    """Sampling temperature passed to the provider.  CORE ignores this."""

    max_tokens: int = 512
    """Maximum completion tokens requested."""

    extra: dict = None  # type: ignore[assignment]
    """Provider-specific overrides (e.g. base_url for OpenAI)."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", self.extra or {})

    @classmethod
    def from_env(cls, provider: str) -> "ProviderConfig":
        """Build a ProviderConfig by reading the standard env vars for
        *provider*.  Raises ``EnvironmentError`` if required vars are absent.
        """
        provider = provider.lower().strip()
        temperature = float(_env("BENCHMARK_TEMPERATURE", "0"))
        if provider == "openai":
            model = _env("OPENAI_MODEL", "gpt-4o")
            if not model:
                raise EnvironmentError("OPENAI_MODEL must be set for openai provider.")
            extra: dict = {}
            base_url = _env("OPENAI_BASE_URL")
            if base_url:
                extra["base_url"] = base_url
            return cls(provider=provider, model=model, temperature=temperature, extra=extra)

        if provider == "anthropic":
            model = _env("ANTHROPIC_MODEL", "claude-opus-4-5")
            if not model:
                raise EnvironmentError("ANTHROPIC_MODEL must be set for anthropic provider.")
            return cls(provider=provider, model=model, temperature=temperature)

        if provider == "ollama":
            model = _env("OLLAMA_MODEL", "llama3.2")
            if not model:
                raise EnvironmentError("OLLAMA_MODEL must be set for ollama provider.")
            return cls(
                provider=provider,
                model=model,
                temperature=temperature,
                extra={
                    "url": _env("OLLAMA_URL", "http://localhost:11434"),
                    "api_key": _env("OLLAMA_API_KEY", ""),
                },
            )

        if provider == "core":
            return cls(provider=provider, model="core-native")

        raise ValueError(
            f"Unknown provider {provider!r}. "
            f"Valid values: openai, anthropic, ollama, core."
        )

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


# ---------------------------------------------------------------------------
# Adapter builders
# ---------------------------------------------------------------------------

def _build_core_adapter(cfg: ProviderConfig) -> Callable[[str], str]:
    """CORE ChatRuntime adapter.  Fresh runtime per call — no session bleed."""
    from chat.runtime import ChatRuntime

    def adapter(prompt: str) -> str:
        rt = ChatRuntime()
        resp = rt.chat(prompt, max_tokens=cfg.max_tokens)
        return resp.surface or ""

    return adapter


def _build_openai_adapter(cfg: ProviderConfig) -> Callable[[str], str]:
    """OpenAI Chat Completions adapter.

    Requires: ``pip install openai``
    Env vars:  OPENAI_API_KEY, OPENAI_MODEL (see .env.example)
    """
    try:
        import openai  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "openai package is required for the OpenAI adapter. "
            "Install it with: pip install openai"
        ) from exc

    api_key = _require_env("OPENAI_API_KEY")
    client_kwargs: dict = {"api_key": api_key}
    if "base_url" in cfg.extra:
        client_kwargs["base_url"] = cfg.extra["base_url"]
    client = openai.OpenAI(**client_kwargs)

    def adapter(prompt: str) -> str:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    return adapter


def _build_anthropic_adapter(cfg: ProviderConfig) -> Callable[[str], str]:
    """Anthropic Messages adapter.

    Requires: ``pip install anthropic``
    Env vars:  ANTHROPIC_API_KEY, ANTHROPIC_MODEL (see .env.example)
    """
    try:
        import anthropic as ant  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "anthropic package is required for the Anthropic adapter. "
            "Install it with: pip install anthropic"
        ) from exc

    api_key = _require_env("ANTHROPIC_API_KEY")
    client = ant.Anthropic(api_key=api_key)

    def adapter(prompt: str) -> str:
        message = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            # Anthropic uses a top_p/temperature combo; temperature is supported
            # on most models as of 2025.  Clip to valid range [0, 1].
            temperature=max(0.0, min(1.0, cfg.temperature)),
        )
        block = message.content[0] if message.content else None
        return (getattr(block, "text", "") or "").strip()

    return adapter


def _build_ollama_adapter(cfg: ProviderConfig) -> Callable[[str], str]:
    """Ollama local model adapter (HTTP /api/chat endpoint).

    Requires: ``pip install httpx``  (already present in most Python envs)
    Env vars:  OLLAMA_URL, OLLAMA_API_KEY (empty for local), OLLAMA_MODEL

    The adapter posts to ``{OLLAMA_URL}/api/chat`` using the OpenAI-compatible
    messages format that Ollama >= 0.1.14 supports.
    """
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "httpx is required for the Ollama adapter. "
            "Install it with: pip install httpx"
        ) from exc

    base_url = (cfg.extra.get("url") or "http://localhost:11434").rstrip("/")
    api_key = cfg.extra.get("api_key") or ""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    def adapter(prompt: str) -> str:
        payload = {
            "model": cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": cfg.temperature},
        }
        resp = httpx.post(
            f"{base_url}/api/chat",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("message", {}).get("content") or "").strip()

    return adapter


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

_BUILDERS = {
    "core": _build_core_adapter,
    "openai": _build_openai_adapter,
    "anthropic": _build_anthropic_adapter,
    "ollama": _build_ollama_adapter,
}


def build_adapter(cfg: ProviderConfig) -> Callable[[str], str]:
    """Return a ``(prompt: str) -> str`` callable for the given config.

    This is the single entry point for all benchmark runner code.  The
    callable is stateless per-call (each invocation is independent) so
    it is safe to pass to ``compare_to_llm`` and the frontier_compare
    runner suites.
    """
    builder = _BUILDERS.get(cfg.provider)
    if builder is None:
        raise ValueError(
            f"No adapter builder registered for provider {cfg.provider!r}. "
            f"Registered: {', '.join(sorted(_BUILDERS))}."
        )
    return builder(cfg)


def load_dotenv_if_present(path: str = ".env") -> None:
    """Minimal .env loader — no external dependency on ``python-dotenv``.

    Reads KEY=VALUE lines from *path* and sets them in ``os.environ`` only
    if the key is not already set (so shell exports always win).  Comments
    and blank lines are skipped.  Quoted values have the quotes stripped.

    Call this once at the top of any benchmark entrypoint script::

        from evals.frontier_compare.providers import load_dotenv_if_present
        load_dotenv_if_present()  # reads .env from repo root
    """
    import pathlib

    p = pathlib.Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
