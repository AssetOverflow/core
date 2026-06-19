#!/usr/bin/env python3
"""Classify GSM8K problems by missing substrate category.

Tranche 1 — broad base-layer foundations.

Labels are semantically honest: ``missing_*`` categories fire only when a
needed substrate lookup actually fails, not merely because a trigger
surface appears in the text.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence

from language_packs.scalar_equivalence import list_unsupported_surfaces
from language_packs.unit_dimensions import classify_dimension
from language_packs.loader import lookup_container
from generate.process_frames import all_frames, lookup_frame


_PROCESS_FRAME_NAMES: frozenset[str] = frozenset({"transfer", "consumption", "transaction"})
_CONTAINER_FRAME_NAMES: frozenset[str] = frozenset({"container_packing"})
_PARTITION_FRAME_NAMES: frozenset[str] = frozenset({"partition"})
_TRAVEL_FRAME_NAMES: frozenset[str] = frozenset({"travel"})

_TEMPORAL_SURFACE_TRIGGERS: tuple[str, ...] = (
    "hour", "hours", "minute", "minutes", "second", "seconds",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
)

_AMBIGUITY_HAZARD_SURFACES: tuple[str, ...] = (
    "half", "quarter", "third", "percent", "percentage points", "times",
    "more than", "less than", "of", "per", "each", "some", "remaining",
    "left", "total", "altogether",
)


def _surface_in_text(surface: str, text_lower: str) -> bool:
    """Return True when *surface* appears as a token/phrase in *text_lower*."""
    token = surface.lower()
    padded = f" {text_lower} "
    return (
        f" {token} " in padded
        or text_lower.startswith(f"{token} ")
        or text_lower.endswith(f" {token}")
        or text_lower == token
    )


def _frame_triggers(frame_names: frozenset[str]) -> tuple[str, ...]:
    triggers: list[str] = []
    for frame in all_frames():
        if frame.name in frame_names:
            triggers.extend(frame.trigger_surfaces)
    return tuple(triggers)


def _missing_frame_for_triggers(
    text_lower: str,
    triggers: Sequence[str],
    frame_names: frozenset[str],
) -> bool:
    """True when text contains category triggers but none resolve to a frame."""
    saw_trigger = False
    for trigger in triggers:
        if not _surface_in_text(trigger, text_lower):
            continue
        saw_trigger = True
        if any(frame.name in frame_names for frame in lookup_frame(trigger)):
            return False
    return saw_trigger


def classify_missing_substrate(problem_text: str) -> tuple[str, ...]:
    """Return sorted tuple of missing substrate labels for a problem.

    Inspects problem text using substrate facades to identify gaps.
    """
    labels: set[str] = set()
    text_lower = problem_text.lower()

    # 1. missing_scalar_equivalence
    for unsup in list_unsupported_surfaces():
        if unsup in problem_text or unsup in text_lower:
            labels.add("missing_scalar_equivalence")

    if re.search(r"\b\d+\s+/\s+\d+\b", problem_text) or re.search(r"\b\.\d+\b", problem_text):
        labels.add("missing_scalar_equivalence")

    # 2. missing_unit_dimension
    matches = re.findall(r"\b\d+(?:\.\d+)?\s+([a-zA-Z]+)\b", problem_text)
    for word in matches:
        word_lower = word.lower()
        if word_lower in {
            "more", "less", "times", "percent", "percentage", "of", "and", "or",
            "the", "a", "an", "in", "to", "for", "with", "at", "by", "from",
        }:
            continue
        if classify_dimension(word_lower) is None and lookup_container(word_lower) is None:
            labels.add("missing_unit_dimension")

    # 3. missing_process_frame — only when process triggers fail lookup
    if _missing_frame_for_triggers(
        text_lower,
        _frame_triggers(_PROCESS_FRAME_NAMES),
        _PROCESS_FRAME_NAMES,
    ):
        labels.add("missing_process_frame")

    # 4. missing_part_whole_frame — partition triggers must fail lookup
    if _missing_frame_for_triggers(
        text_lower,
        _frame_triggers(_PARTITION_FRAME_NAMES),
        _PARTITION_FRAME_NAMES,
    ):
        labels.add("missing_part_whole_frame")

    # 5. missing_container_frame — container triggers must fail lookup
    if _missing_frame_for_triggers(
        text_lower,
        _frame_triggers(_CONTAINER_FRAME_NAMES),
        _CONTAINER_FRAME_NAMES,
    ):
        labels.add("missing_container_frame")

    # 6. missing_temporal_frame — temporal surfaces with no registered frame
    for trigger in _TEMPORAL_SURFACE_TRIGGERS:
        if _surface_in_text(trigger, text_lower) and not lookup_frame(trigger):
            labels.add("missing_temporal_frame")
            break

    # 7. missing_route_frame — travel triggers must fail lookup
    if _missing_frame_for_triggers(
        text_lower,
        _frame_triggers(_TRAVEL_FRAME_NAMES),
        _TRAVEL_FRAME_NAMES,
    ):
        labels.add("missing_route_frame")

    # 8. missing_question_target
    if "?" not in problem_text and "how many" not in text_lower and "how much" not in text_lower:
        labels.add("missing_question_target")

    # 9. blocked_ambiguity_hazard
    for hazard_surf in _AMBIGUITY_HAZARD_SURFACES:
        if _surface_in_text(hazard_surf, text_lower):
            labels.add("blocked_ambiguity_hazard")
            break

    # 10. blocked_provenance_gap
    if "leap year" in text_lower or "calendar" in text_lower or "world fact" in text_lower:
        labels.add("blocked_provenance_gap")

    return tuple(sorted(labels))


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify GSM8K problems by missing substrate.")
    parser.add_argument("--cases", type=str, help="Path to JSONL cases file")
    parser.add_argument("--out", type=str, help="Path to write classified output JSONL")
    parser.add_argument("--limit", type=int, help="Limit number of cases to process")

    args = parser.parse_args()

    if not args.cases:
        print("No cases path provided.")
        return

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Cases file not found at {args.cases}")
        return

    out_lines = []
    count = 0
    with cases_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            problem_text = case.get("question") or case.get("problem_text") or ""
            if not problem_text:
                continue

            labels = classify_missing_substrate(problem_text)
            case_id = case.get("case_id") or f"case_{count}"
            out_lines.append({
                "case_id": case_id,
                "problem_text": problem_text,
                "missing_substrate_labels": labels
            })

            count += 1
            if args.limit and count >= args.limit:
                break

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for item in out_lines:
                f.write(json.dumps(item) + "\n")
        print(f"Wrote {len(out_lines)} classified cases to {args.out}")
    else:
        for item in out_lines:
            print(json.dumps(item))


if __name__ == "__main__":
    main()