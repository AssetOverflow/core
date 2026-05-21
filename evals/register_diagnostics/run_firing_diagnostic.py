"""Diagnose seeded register marker firing across ratified register packs.

For every selected register pack and every :class:`generate.intent.IntentTag`,
run three representative prompts through the real chat runtime, replay the
seeded decoration selector against the same pre-decoration surface, and emit a
JSON matrix describing whether opening / closing markers engaged or fell
through to ``""``.

The tool is read-only: it loads ratified register packs and runtime language
packs, but never mutates pack JSON, mastery reports, vault state, or tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from chat.register_variation import decorate_surface
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.intent import IntentTag, classify_intent
from packs.register.loader import (
    RegisterPack,
    available_register_packs,
    load_register_pack,
)


REPRESENTATIVE_PROMPTS: Mapping[IntentTag, tuple[str, str, str]] = {
    IntentTag.DEFINITION: (
        "What is light?",
        "Define knowledge.",
        "Explain memory.",
    ),
    IntentTag.CAUSE: (
        "Why does light exist?",
        "What causes recall?",
        "How does memory work?",
    ),
    IntentTag.PROCEDURE: (
        "How do I define knowledge?",
        "How can we compare claims?",
        "How should you verify memory?",
    ),
    IntentTag.COMPARISON: (
        "Compare knowledge and wisdom.",
        "Compare light versus darkness.",
        "Compare memory with recall.",
    ),
    IntentTag.CORRECTION: (
        "Actually, light is not darkness.",
        "Correction: memory is not storage.",
        "That's wrong: knowledge is not noise.",
    ),
    IntentTag.RECALL: (
        "Remember truth.",
        "Remember light.",
        "Remember knowledge.",
    ),
    IntentTag.VERIFICATION: (
        "Does memory require recall?",
        "Is truth coherent?",
        "Can light reveal form?",
    ),
    IntentTag.TRANSITIVE_QUERY: (
        "Where does parent belong?",
        "What does light reveal?",
        "What does cause precede?",
    ),
    IntentTag.FRAME_TRANSFER: (
        "What does child belong to in family?",
        "What does premise support in argument?",
        "What does signal reveal in memory?",
    ),
    IntentTag.NARRATIVE: (
        "Tell me about memory.",
        "Describe knowledge.",
        "What can you say about truth?",
    ),
    IntentTag.EXAMPLE: (
        "Give me an example of knowledge.",
        "Show me an instance of recall.",
        "Example of verification.",
    ),
    IntentTag.UNKNOWN: (
        "blue inward maybe",
        "unparsed glyph cluster",
        "stone silence green",
    ),
}


def ratified_register_ids() -> tuple[str, ...]:
    """Return discoverable register IDs that declare ratification."""

    return tuple(
        str(entry["register_id"])
        for entry in available_register_packs()
        if bool(entry.get("ratified"))
    )


def _bucket_stats(pack: RegisterPack, bucket_name: str) -> dict[str, int]:
    bucket = getattr(pack.discourse_markers, bucket_name)
    non_empty = [entry for entry in bucket if entry]
    return {
        "size": len(bucket),
        "non_empty_size": len(non_empty),
        "empty_size": len(bucket) - len(non_empty),
    }


def _selected_cell(
    *,
    register: RegisterPack,
    runtime: ChatRuntime,
    intent: IntentTag,
    prompt: str,
) -> dict[str, Any]:
    turn_idx = len(runtime.turn_log)
    response = runtime.chat(prompt)
    seed_surface = response.pre_decoration_surface or response.surface
    selected = decorate_surface(seed_surface, register, turn_idx=turn_idx)
    classified = classify_intent(prompt)
    return {
        "prompt": prompt,
        "representative_intent": intent.name,
        "classified_intent": classified.tag.name,
        "classified_subject": classified.subject,
        "turn_idx": turn_idx,
        "grounding_source": response.grounding_source,
        "pre_decoration_surface": seed_surface,
        "surface": response.surface,
        "opening": selected.opening,
        "closing": selected.closing,
        "opening_fired": bool(selected.opening),
        "closing_fired": bool(selected.closing),
        "variant_id": selected.variant_id,
        "runtime_variant_id": response.register_variant_id,
        "variant_id_matches_runtime": (
            selected.variant_id == response.register_variant_id
        ),
    }


def _intent_summary(
    *,
    register_id: str,
    intent: IntentTag,
    cells: Sequence[Mapping[str, Any]],
    opening_stats: Mapping[str, int],
    closing_stats: Mapping[str, int],
) -> dict[str, Any]:
    opening_fire_count = sum(1 for cell in cells if cell["opening_fired"])
    closing_fire_count = sum(1 for cell in cells if cell["closing_fired"])
    gap_buckets: list[str] = []
    if opening_stats["non_empty_size"] > 0 and opening_fire_count == 0:
        gap_buckets.append("openings")
    if closing_stats["non_empty_size"] > 0 and closing_fire_count == 0:
        gap_buckets.append("closings")
    return {
        "register_id": register_id,
        "intent": intent.name,
        "prompt_count": len(cells),
        "openings": {
            **dict(opening_stats),
            "fire_count": opening_fire_count,
            "fell_through_count": len(cells) - opening_fire_count,
        },
        "closings": {
            **dict(closing_stats),
            "fire_count": closing_fire_count,
            "fell_through_count": len(cells) - closing_fire_count,
        },
        "gap_buckets": gap_buckets,
        "has_contract_gap": bool(gap_buckets),
        "variant_id_mismatches": [
            cell["prompt"]
            for cell in cells
            if not cell["variant_id_matches_runtime"]
        ],
    }


def build_report(
    *,
    register_ids: Iterable[str] | None = None,
    intents: Iterable[IntentTag] | None = None,
) -> dict[str, Any]:
    """Build the marker-firing diagnostic report."""

    selected_register_ids = tuple(register_ids or ratified_register_ids())
    selected_intents = tuple(intents or IntentTag)
    matrix: dict[str, dict[str, list[dict[str, Any]]]] = {}
    summaries: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    variant_mismatches: list[dict[str, Any]] = []

    for register_id in selected_register_ids:
        register = load_register_pack(register_id)
        opening_stats = _bucket_stats(register, "openings")
        closing_stats = _bucket_stats(register, "closings")
        register_matrix: dict[str, list[dict[str, Any]]] = {}
        for intent in selected_intents:
            runtime = ChatRuntime(config=RuntimeConfig(register_pack_id=register_id))
            prompts = REPRESENTATIVE_PROMPTS[intent]
            cells = [
                _selected_cell(
                    register=register,
                    runtime=runtime,
                    intent=intent,
                    prompt=prompt,
                )
                for prompt in prompts
            ]
            register_matrix[intent.name] = cells
            summary = _intent_summary(
                register_id=register_id,
                intent=intent,
                cells=cells,
                opening_stats=opening_stats,
                closing_stats=closing_stats,
            )
            summaries.append(summary)
            if summary["has_contract_gap"]:
                gaps.append(
                    {
                        "register_id": register_id,
                        "intent": intent.name,
                        "gap_buckets": summary["gap_buckets"],
                    }
                )
            if summary["variant_id_mismatches"]:
                variant_mismatches.append(
                    {
                        "register_id": register_id,
                        "intent": intent.name,
                        "prompts": summary["variant_id_mismatches"],
                    }
                )
        matrix[register_id] = register_matrix

    return {
        "schema_version": "1.0.0",
        "diagnostic": "register_marker_firing",
        "registers": list(selected_register_ids),
        "intents": [intent.name for intent in selected_intents],
        "representative_prompts": {
            intent.name: list(REPRESENTATIVE_PROMPTS[intent])
            for intent in selected_intents
        },
        "matrix": matrix,
        "summaries": summaries,
        "gaps": gaps,
        "variant_mismatches": variant_mismatches,
        "all_marker_contracts_supported": not gaps,
        "all_replayed_variants_match_runtime": not variant_mismatches,
    }


def _parse_intents(values: Sequence[str] | None) -> tuple[IntentTag, ...] | None:
    if not values:
        return None
    parsed: list[IntentTag] = []
    by_name = {tag.name: tag for tag in IntentTag}
    by_value = {tag.value: tag for tag in IntentTag}
    for value in values:
        key = value.strip()
        tag = by_name.get(key.upper()) or by_value.get(key.lower())
        if tag is None:
            known = ", ".join(tag.name for tag in IntentTag)
            raise SystemExit(f"unknown intent {value!r}; expected one of: {known}")
        parsed.append(tag)
    return tuple(parsed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a JSON matrix showing whether register opening/closing "
            "markers fire across representative prompts for each intent."
        )
    )
    parser.add_argument(
        "--register",
        action="append",
        dest="register_ids",
        help=(
            "register ID to diagnose; repeatable. Defaults to every "
            "discoverable ratified register pack."
        ),
    )
    parser.add_argument(
        "--intent",
        action="append",
        dest="intents",
        help=(
            "IntentTag name or value to diagnose; repeatable. Defaults to "
            "every IntentTag."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional path to write the JSON report; stdout is always used otherwise",
    )
    parser.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="exit 1 when any non-empty marker bucket never fires for a cell",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_report(
        register_ids=tuple(args.register_ids) if args.register_ids else None,
        intents=_parse_intents(args.intents),
    )
    payload = json.dumps(report, indent=2, sort_keys=True, default=str)
    if args.output is not None:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.fail_on_gap and not report["all_marker_contracts_supported"]:
        return 1
    if not report["all_replayed_variants_match_runtime"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
