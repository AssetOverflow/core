"""Provider-agnostic frontier runner for the B1 head-to-head.

Each provider adapter takes a single B1 case ``{expression_a,
expression_b}`` and returns a verdict string in
``{"equivalent", "not_equivalent", "refused"}``. The runner caches
every provider response at
``evals/math_symbolic_equivalence/v1/frontier/responses/<provider>/<model>.jsonl``
so that subsequent runs replay deterministically; if the cache file
exists, the API is not re-called.

The provider's natural-language reply is parsed by
:func:`parse_provider_verdict`, which is the single load-bearing
boundary that converts free-form text into the closed CORE verdict
vocabulary. The parser is conservative: ambiguous replies are
classified ``refused`` (not coerced to a polarized verdict). This
mirrors B1's refusal-first contract.

The runner deliberately does not score — scoring against
``case.expected`` happens in :mod:`comparison` so the cached responses
remain a faithful record of what the provider actually said,
independent of B1's expected-verdict shape.

No live API call happens at test or import time. To run a real
head-to-head:

    FRONTIER_ANTHROPIC_KEY=... python3 -m \\
        evals.math_symbolic_equivalence.v1.frontier.frontier_runner \\
        --provider anthropic --model claude-opus-4-7
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, Mapping


_HERE: Final[Path] = Path(__file__).resolve().parent
_RESPONSES_DIR: Final[Path] = _HERE / "responses"


class FrontierRunError(RuntimeError):
    """Typed error for misconfiguration or API-side refusal."""


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """How to call one provider.

    ``invoke`` is the function that takes ``(prompt, api_key, model)``
    and returns the raw text reply. It is injected here as a callable
    so tests can supply a deterministic stub without import-time
    network deps.
    """

    provider_id: str
    env_key: str
    default_model: str
    invoke: Callable[[str, str, str], str]


def _prompt_for(expression_a: str, expression_b: str) -> str:
    """The closed, deterministic prompt every provider receives."""
    return (
        "You are evaluating whether two mathematical expressions are "
        "algebraically equivalent. The expressions use only standard "
        "operators (+, -, *, **, parentheses).\n\n"
        f"Expression A: {expression_a}\n"
        f"Expression B: {expression_b}\n\n"
        "Reply with exactly one word on its own line, no explanation:\n"
        "  EQUIVALENT   — if A and B denote the same expression\n"
        "  NOT_EQUIVALENT — if they denote different expressions\n"
        "  REFUSED      — if either expression is malformed, out of "
        "scope, or you cannot decide\n"
    )


_VERDICT_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(EQUIVALENT|NOT_EQUIVALENT|REFUSED)\b",
    flags=re.IGNORECASE,
)


def parse_provider_verdict(reply: str) -> str:
    """Map a free-form provider reply to the closed CORE vocabulary.

    Returns one of ``equivalent`` / ``not_equivalent`` / ``refused``.

    Discipline:

    - If the reply contains exactly one of the three sentinel tokens,
      that's the verdict.
    - If the reply contains multiple distinct sentinel tokens (e.g.
      a chain-of-thought that mentions "NOT_EQUIVALENT" then concludes
      "EQUIVALENT"), the **last** token wins — frontier models often
      conclude after deliberation.
    - If the reply contains none of the three tokens, the verdict is
      ``refused`` (the conservative choice — never coerce to a
      polarized verdict).
    """
    if not isinstance(reply, str) or not reply.strip():
        return "refused"
    matches = _VERDICT_TOKEN_RE.findall(reply)
    if not matches:
        return "refused"
    last = matches[-1].upper()
    return {
        "EQUIVALENT": "equivalent",
        "NOT_EQUIVALENT": "not_equivalent",
        "REFUSED": "refused",
    }[last]


def _anthropic_invoke(prompt: str, api_key: str, model: str) -> str:
    """Anthropic adapter — imported lazily so the package loads
    cleanly without the ``anthropic`` SDK installed.
    """
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FrontierRunError(
            "anthropic SDK not installed; "
            "`pip install anthropic` to enable this provider"
        ) from exc
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=256,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    # Concatenate all text blocks in the response.
    parts: list[str] = []
    for block in getattr(message, "content", ()):
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)


def _openai_invoke(prompt: str, api_key: str, model: str) -> str:
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FrontierRunError(
            "openai SDK not installed; "
            "`pip install openai` to enable this provider"
        ) from exc
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=256,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    choice = response.choices[0]
    content = getattr(choice.message, "content", None) or ""
    return content


def _google_invoke(prompt: str, api_key: str, model: str) -> str:
    try:
        import google.generativeai as genai  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FrontierRunError(
            "google-generativeai SDK not installed; "
            "`pip install google-generativeai` to enable this provider"
        ) from exc
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(model)
    response = gmodel.generate_content(
        prompt,
        generation_config={"max_output_tokens": 256, "temperature": 0.0},
    )
    text = getattr(response, "text", None)
    if not isinstance(text, str):
        return ""
    return text


PROVIDERS: Final[Mapping[str, ProviderSpec]] = {
    "anthropic": ProviderSpec(
        provider_id="anthropic",
        env_key="FRONTIER_ANTHROPIC_KEY",
        default_model="claude-opus-4-7",
        invoke=_anthropic_invoke,
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        env_key="FRONTIER_OPENAI_KEY",
        default_model="gpt-4o",
        invoke=_openai_invoke,
    ),
    "google": ProviderSpec(
        provider_id="google",
        env_key="FRONTIER_GOOGLE_KEY",
        default_model="gemini-1.5-pro",
        invoke=_google_invoke,
    ),
}


def _cache_path(provider_id: str, model: str) -> Path:
    return _RESPONSES_DIR / provider_id / f"{model}.jsonl"


def _load_cache(provider_id: str, model: str) -> dict[str, dict[str, Any]]:
    path = _cache_path(provider_id, model)
    if not path.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rec = json.loads(line)
        cache[rec["case_id"]] = rec
    return cache


def _append_cache(provider_id: str, model: str, record: dict[str, Any]) -> None:
    path = _cache_path(provider_id, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True))
        fh.write("\n")


def run_frontier(
    provider_id: str,
    *,
    model: str | None = None,
    cases: list[dict[str, Any]],
    invoke_override: Callable[[str, str, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Run one provider against the B1 dataset.

    Cached responses (keyed by ``case_id``) are reused unconditionally;
    only uncached cases hit the live API. The API key is read from the
    provider's documented environment variable at call time; if absent,
    a :class:`FrontierRunError` is raised before any case is queried.

    ``invoke_override`` is an injection seam for tests: supply a
    deterministic stub to exercise scoring/caching paths without
    touching the network or requiring an SDK.
    """
    spec = PROVIDERS.get(provider_id)
    if spec is None:
        raise FrontierRunError(
            f"unknown provider {provider_id!r}; "
            f"known: {sorted(PROVIDERS)}"
        )
    resolved_model = model or spec.default_model
    cache = _load_cache(provider_id, resolved_model)

    invoke = invoke_override or spec.invoke
    api_key: str | None = None
    if any(c["case_id"] not in cache for c in cases):
        # Only require the key if we actually need to call the API.
        api_key = os.environ.get(spec.env_key)
        if not api_key and invoke_override is None:
            raise FrontierRunError(
                f"set {spec.env_key} to run live; cached responses "
                f"insufficient ({len(cache)}/{len(cases)} cases hit)"
            )

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["case_id"]
        if case_id in cache:
            results.append(cache[case_id])
            continue
        prompt = _prompt_for(case["expression_a"], case["expression_b"])
        try:
            reply = invoke(prompt, api_key or "", resolved_model)
        except FrontierRunError:
            raise
        except Exception as exc:  # noqa: BLE001 — wrap provider errors
            raise FrontierRunError(
                f"provider {provider_id!r} model {resolved_model!r} "
                f"failed on case {case_id!r}: {exc}"
            ) from exc
        verdict = parse_provider_verdict(reply)
        record = {
            "case_id": case_id,
            "provider": provider_id,
            "model": resolved_model,
            "verdict": verdict,
            "raw_reply": reply,
        }
        _append_cache(provider_id, resolved_model, record)
        results.append(record)
    return results


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)

    cases_path = _HERE.parent / "cases.jsonl"
    cases: list[dict[str, Any]] = []
    for raw in cases_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            cases.append(json.loads(line))
    results = run_frontier(args.provider, model=args.model, cases=cases)
    spec = PROVIDERS[args.provider]
    resolved = args.model or spec.default_model
    print(
        f"{args.provider}/{resolved}: ran {len(results)} cases "
        f"(cache file: {_cache_path(args.provider, resolved)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
