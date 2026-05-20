# ADR-0081 — Frontier Provider Adapters

**Status:** Ratified  
**Date:** 2026-05-20  
**Author:** Shay

---

## Context

Wave 1 of the frontier comparison benchmark family (`evals/frontier_compare/`) was deliberately local and CORE-native — it required no API keys and made no external calls.  The README called out `feat/frontier-compare-provider-adapters` as the intended next wave.

We now have API credentials for OpenAI, Anthropic, and a local Ollama install.  To run the Wave 1 suites (and future suites) against real frontier models, we need:

1. A consistent interface so any benchmark can call any provider with the same `(prompt: str) -> str` shape.
2. A `.env.example` that documents every env var the codebase consumes so a new operator knows exactly what to set.
3. A model registry that enforces documented, pinned model identity in every benchmark report — floating aliases like `gpt-4o` are banned in report metadata because the underlying weights can change silently.
4. `.gitignore` coverage for `.env` files so secrets are never committed.

---

## Decision

### Provider adapter module: `evals/frontier_compare/providers.py`

A single module exposes:

- **`ProviderConfig`** — immutable, hashable dataclass carrying `(provider, model, temperature, max_tokens, extra)`.  Built from env vars via `ProviderConfig.from_env(provider_name)`.  Serialises to a stable dict for embedding in report JSON.
- **`build_adapter(cfg: ProviderConfig) -> Callable[[str], str]`** — the single entry point for all benchmark code.  Returns a stateless `(prompt) -> surface` callable.  Registered builders: `core`, `openai`, `anthropic`, `ollama`.
- **`load_dotenv_if_present(path)`** — minimal `.env` reader with no external dependency.  Shell exports always win over `.env` values.

Adapter behaviour per provider:

| Provider | Package required | Auth env var | Notes |
|---|---|---|---|
| `core` | none | none | Fresh `ChatRuntime` per call; deterministic |
| `openai` | `openai` | `OPENAI_API_KEY` | Uses `client.chat.completions.create` |
| `anthropic` | `anthropic` | `ANTHROPIC_API_KEY` | Uses `client.messages.create` |
| `ollama` | `httpx` | `OLLAMA_API_KEY` (optional) | POSTs to `{OLLAMA_URL}/api/chat` |

### Model registry: `evals/frontier_compare/model_registry.py`

Every model ever used in a CORE benchmark must have a `ModelCard` entry before it can be used via `require_model_card()`.  Fields:

- `provider`, `model_id` (exact API slug)
- `display_name`, `knowledge_cutoff`, `context_window`, `output_tokens`
- `architecture` — plain-English description
- `sampling` — note on determinism/stochasticity
- `notes` — known quirks, version history, benchmark-specific observations
- `tags` — searchable taxonomy

Initially registered models:

| Key | Display name |
|---|---|
| `core/core-native` | CORE (native) |
| `openai/gpt-4o` | GPT-4o (floating alias) |
| `openai/gpt-4o-2024-08-06` | GPT-4o (2024-08-06 snapshot) |
| `openai/gpt-4o-mini` | GPT-4o mini |
| `openai/o3` | OpenAI o3 |
| `anthropic/claude-opus-4-5` | Claude Opus 4.5 |
| `anthropic/claude-sonnet-4-5` | Claude Sonnet 4.5 |
| `anthropic/claude-haiku-3-5` | Claude Haiku 3.5 |
| `ollama/llama3.2` | Llama 3.2 (latest tag) |
| `ollama/llama3.2:3b-instruct-q8_0` | Llama 3.2 3B Instruct Q8_0 |
| `ollama/mistral` | Mistral 7B |
| `ollama/gemma3:12b` | Gemma 3 12B |

### `.env.example`

Documents all env vars in one place:

```
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=          # optional proxy/Azure override

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-opus-4-5

OLLAMA_URL=http://localhost:11434
OLLAMA_API_KEY=           # empty for local installs
OLLAMA_MODEL=llama3.2

BENCHMARK_PROVIDERS=core  # comma-separated: core,openai,anthropic,ollama
BENCHMARK_RUNS=3
BENCHMARK_TEMPERATURE=0
BENCHMARK_REPORT_DIR=reports
```

### `.gitignore` additions

```gitignore
.env
.env.local
.env.*.local
reports/
```

---

## How to run a multi-provider benchmark

```python
from evals.frontier_compare.providers import load_dotenv_if_present, ProviderConfig, build_adapter
from evals.frontier_compare.model_registry import require_model_card
from evals.frontier_compare.runner import run_all
from benchmarks.replay_vs_llm import compare_to_llm, DEFAULT_LONGFORM_PROMPTS

# 1. Load .env
load_dotenv_if_present()

# 2. Build an adapter (will raise if API key is missing)
cfg = ProviderConfig.from_env("openai")
card = require_model_card(cfg.provider, cfg.model)  # enforces registry entry
adapter = build_adapter(cfg)

# 3. Run the replay determinism comparison
report = compare_to_llm(
    list(DEFAULT_LONGFORM_PROMPTS),
    llm_callable=adapter,
    runs=5,
)
print(report.summary())

# 4. The frontier_compare runner can also accept a provider adapter
# directly in future suite extensions — the ProviderConfig.as_dict()
# embeds cleanly into BenchmarkReport metadata.
```

---

## Consequences

- **Good:** Any benchmark file can call `build_adapter(cfg)` and receive a uniform callable.  No provider SDK leaks into benchmark logic.
- **Good:** `require_model_card()` enforces that unregistered models cannot produce undocumented benchmark results.  This is the key discipline addition.
- **Good:** `load_dotenv_if_present()` requires no new dependency (`python-dotenv` is not added).  Shell env always wins.
- **Good:** `.env.example` is the single source of truth for all secrets and tuning knobs; it lives at the repo root so any operator finds it immediately.
- **Neutral:** Provider SDK packages (`openai`, `anthropic`, `httpx`) are not added to `pyproject.toml` as hard dependencies — they are soft requirements that the adapter import will surface with a clear error message.  This keeps the base install lean and avoids forcing all CI runs to hold API keys.
- **Watch:** Floating model aliases (e.g. bare `gpt-4o`) are registered with a warning note but not banned at the registry level.  The discipline is enforced by convention: benchmark operators should pin to dated snapshots.

---

## Non-goals

- This ADR does not add async adapter support (synchronous calls are sufficient for current benchmark volumes).
- It does not add streaming.
- It does not add retry/backoff logic (callers can wrap `build_adapter` output with tenacity or similar).
- It does not modify `ChatRuntime` or any pack/lens behaviour.
- It does not add provider SDK packages to `pyproject.toml` hard dependencies.
