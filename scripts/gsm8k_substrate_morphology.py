#!/usr/bin/env python3
"""Classify GSM8K examples by missing substrate category and plan migrations."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from generate.problem_frame_builder import (
    build_problem_frame,
    recognized_hazard_ids,
    recognized_process_frame_names,
    recognized_scalar_surfaces,
    recognized_unit_surfaces,
)
from generate.process_frames import lookup_frame
from language_packs.loader import lookup_container
from language_packs.scalar_equivalence import list_unsupported_surfaces
from language_packs.unit_dimensions import classify_dimension

_AMBIGUOUS_SURFACES = (
    "half", "quarter", "third", "percent", "percentage points", "times",
    "more than", "less than", "of", "per", "each", "some", "remaining",
    "left", "total", "altogether",
)
_TEMPORAL_SURFACES = ("hour", "hours", "minute", "minutes", "day", "days", "week", "weeks")
_FRAME_TARGETS = {
    "consumption": "percent_partition",
    "partition": "percent_partition",
    "container_packing": "nested_fraction_remainder_total",
    "labor_rate": "temporal_tariff",
    "travel": "temporal_tariff",
    "transaction": "substrate:process_frames",
    "transfer": "substrate:process_frames",
}
_ORGAN_PATHS = {
    "percent_partition": "generate/derivation/percent_partition.py",
    "nested_fraction_remainder_total": "generate/derivation/nested_fraction_remainder_total.py",
    "fraction_decrease": "generate/derivation/fraction_decrease.py",
    "temporal_tariff": "generate/derivation/temporal_tariff.py",
    "extract_shared": "generate/derivation/extract.py",
    "math_candidate_parser": "generate/math_candidate_parser.py",
}
_STOPWORDS = {
    "more", "less", "times", "percent", "percentage", "of", "and", "or",
    "the", "a", "an", "in", "to", "for", "with", "at", "by", "from",
}


def _surface_in_text(surface: str, text_lower: str) -> bool:
    padded = f" {text_lower} "
    token = surface.lower()
    return f" {token} " in padded or text_lower.startswith(f"{token} ") or text_lower.endswith(f" {token}") or text_lower == token


def _registered_frame_present(text_lower: str, expected: set[str]) -> bool:
    for frame_name in expected:
        for frame in lookup_frame(frame_name):
            if any(_surface_in_text(trigger, text_lower) for trigger in frame.trigger_surfaces):
                return True
    for trigger in text_lower.split():
        if any(frame.name in expected for frame in lookup_frame(trigger)):
            return True
    return False


def classify_missing_substrate(problem_text: str) -> tuple[str, ...]:
    labels: set[str] = set()
    text_lower = problem_text.lower()

    if any(surface in problem_text or surface in text_lower for surface in list_unsupported_surfaces()):
        labels.add("missing_scalar_equivalence")
    if re.search(r"\b\d+\s+/\s+\d+\b", problem_text) or re.search(r"\b\.\d+\b", problem_text):
        labels.add("missing_scalar_equivalence")

    for unit in re.findall(r"\b\d+(?:\.\d+)?\s+([a-zA-Z]+)\b", problem_text):
        lowered_unit = unit.lower()
        if lowered_unit in _STOPWORDS:
            continue
        if classify_dimension(lowered_unit) is None and lookup_container(lowered_unit) is None:
            labels.add("missing_unit_dimension")

    if "give" in text_lower and not _registered_frame_present(text_lower, {"transfer"}):
        labels.add("missing_process_frame")
    if "split" in text_lower and not _registered_frame_present(text_lower, {"partition"}):
        labels.add("missing_part_whole_frame")
    if any(w in text_lower for w in ("box", "boxes", "bag", "pack")) and not _registered_frame_present(text_lower, {"container_packing"}):
        labels.add("missing_container_frame")
    if any(_surface_in_text(surface, text_lower) for surface in _TEMPORAL_SURFACES):
        labels.add("missing_temporal_frame")
    if "drive" in text_lower and not _registered_frame_present(text_lower, {"travel"}):
        labels.add("missing_route_frame")
    if "?" not in problem_text and "how many" not in text_lower and "how much" not in text_lower:
        labels.add("missing_question_target")
    if any(_surface_in_text(surface, text_lower) for surface in _AMBIGUOUS_SURFACES):
        labels.add("blocked_ambiguity_hazard")
    if "leap year" in text_lower or "calendar" in text_lower or "world fact" in text_lower:
        labels.add("blocked_provenance_gap")

    return tuple(sorted(labels))


def _legacy_parser_dependency(problem_text: str, process_frames: tuple[str, ...], missing_labels: tuple[str, ...]) -> tuple[str, ...]:
    deps: set[str] = set()
    lowered = problem_text.lower()
    if "%" in problem_text or "percent" in lowered or "other half" in lowered:
        deps.add(_ORGAN_PATHS["percent_partition"])
    if "remaining" in lowered and ("half" in lowered or "quarter" in lowered):
        deps.add(_ORGAN_PATHS["nested_fraction_remainder_total"])
    if "decrease" in lowered or "decreased" in lowered:
        deps.add(_ORGAN_PATHS["fraction_decrease"])
    if "labor_rate" in process_frames or any(t in lowered for t in ("hour", "hours", "per hour", "overtime")):
        deps.add(_ORGAN_PATHS["temporal_tariff"])
    if re.search(r"\d", problem_text):
        deps.add(_ORGAN_PATHS["extract_shared"])
    if "missing_scalar_equivalence" in missing_labels:
        deps.add(_ORGAN_PATHS["math_candidate_parser"])
    return tuple(sorted(deps))


def _target_for_process_frames(process_frames: tuple[str, ...]) -> str | None:
    for frame in process_frames:
        if frame in _FRAME_TARGETS:
            return _FRAME_TARGETS[frame]
    if process_frames:
        return "substrate:process_frames"
    return None


def recommend_migration_target(problem_text: str, process_frames: tuple[str, ...], missing_labels: tuple[str, ...]) -> str:
    lowered = problem_text.lower()
    if "%" in problem_text and ("half" in lowered or "partition" in process_frames or "consumption" in process_frames):
        return "percent_partition"
    if "other half" in lowered and "%" in problem_text:
        return "percent_partition"
    if "missing_scalar_equivalence" in missing_labels:
        return "substrate:scalar_equivalence"
    if "missing_unit_dimension" in missing_labels:
        return "substrate:unit_dimensions"
    if "blocked_provenance_gap" in missing_labels:
        return "substrate:kernel_calendar"
    if "remaining" in lowered and ("half" in lowered or "quarter" in lowered):
        return "nested_fraction_remainder_total"
    if "decrease" in lowered or "decreased" in lowered:
        return "fraction_decrease"
    if "labor_rate" in process_frames or any(t in lowered for t in ("per hour", "hourly", "overtime")):
        return "temporal_tariff"
    target = _target_for_process_frames(process_frames)
    if target is not None:
        return target
    if "blocked_ambiguity_hazard" in missing_labels:
        return "substrate:ambiguity_hazards"
    return "substrate:problem_frame_builder"


def plan_substrate_case(*, case_id: str, problem_text: str, current_verdict: str | None = None) -> dict[str, Any]:
    frame = build_problem_frame(problem_text)
    missing_labels = classify_missing_substrate(problem_text)
    process_frames = recognized_process_frame_names(frame)
    return {
        "case_id": case_id,
        "current_verdict": current_verdict,
        "recognized_scalars": recognized_scalar_surfaces(frame),
        "recognized_units": recognized_unit_surfaces(frame),
        "recognized_process_frames": process_frames,
        "recognized_hazards": recognized_hazard_ids(frame),
        "missing_substrate_labels": missing_labels,
        "legacy_parser_dependency": _legacy_parser_dependency(problem_text, process_frames, missing_labels),
        "recommended_migration_target": recommend_migration_target(problem_text, process_frames, missing_labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify GSM8K cases by missing substrate and migration target.")
    parser.add_argument("--cases", type=str)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--planner", action="store_true")
    args = parser.parse_args()
    if not args.cases:
        return
    for index, line in enumerate(Path(args.cases).read_text(encoding="utf-8").splitlines()):
        if args.limit is not None and index >= args.limit:
            break
        case = json.loads(line)
        text = case.get("question") or case.get("problem_text") or ""
        case_id = case.get("case_id") or f"case_{index}"
        if args.planner:
            print(json.dumps(plan_substrate_case(case_id=case_id, problem_text=text)))
        else:
            print(json.dumps({"case_id": case_id, "problem_text": text, "missing_substrate_labels": classify_missing_substrate(text)}))


if __name__ == "__main__":
    main()
