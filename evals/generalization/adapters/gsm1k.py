"""Adapter for loading local GSM1K benchmark files."""

from __future__ import annotations

import json
from pathlib import Path

from evals.generalization.item_schema import GeneralizationAuditItem


def load_gsm1k_items(
    *,
    local_cache: Path,
    split: str,
    max_items: int | None = None,
) -> tuple[GeneralizationAuditItem, ...]:
    """Load and normalize GSM1K items from a local cache directory or file.

    Args:
        local_cache: Path to the cache directory or file.
        split: The requested dataset split (e.g. 'test').
        max_items: Optional maximum number of items to load.

    Returns:
        A tuple of loaded GeneralizationAuditItem records.
    """
    if not local_cache.exists():
        raise FileNotFoundError(
            f"Local cache path does not exist: {local_cache}"
        )

    target_file = None
    if local_cache.is_file():
        target_file = local_cache
    elif local_cache.is_dir():
        # Check standard file naming conventions for local cache
        candidate_jsonl = local_cache / f"{split}.jsonl"
        candidate_json = local_cache / f"{split}.json"
        if candidate_jsonl.is_file():
            target_file = candidate_jsonl
        elif candidate_json.is_file():
            target_file = candidate_json
        else:
            # Fallback search for files containing the split name in their filename
            all_files = sorted(local_cache.glob("*"))
            for f in all_files:
                if (
                    f.is_file()
                    and split in f.name
                    and f.suffix in (".jsonl", ".json")
                ):
                    target_file = f
                    break

    if not target_file:
        raise FileNotFoundError(
            f"No JSON or JSONL file found for split {split!r} in {local_cache}"
        )

    try:
        content = target_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Failed to read local GSM1K file {target_file}: {exc}"
        ) from exc

    # Parse as JSONL first, fallback to JSON array
    raw_records = []
    lines = content.strip().splitlines()
    is_jsonl = True
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
            # JSONL lines must be objects (mappings)
            if not isinstance(parsed, dict):
                is_jsonl = False
                break
            raw_records.append(parsed)
        except Exception:
            is_jsonl = False
            break

    if not is_jsonl or not raw_records:
        try:
            data = json.loads(content)
            if isinstance(data, list):
                raw_records = data
                # Since it parsed successfully as a JSON array, it's not JSONL format
                is_jsonl = False
            elif isinstance(data, dict):
                raw_records = [data]
                is_jsonl = False
            else:
                raise ValueError("JSON root must be a list or dictionary.")
        except Exception as exc:
            raise ValueError(
                f"Failed to parse GSM1K file {target_file} as JSON/JSONL: {exc}"
            ) from exc

    items: list[GeneralizationAuditItem] = []
    for idx, rec in enumerate(raw_records):
        if max_items is not None and len(items) >= max_items:
            break

        # Extract question (query)
        question = rec.get("question") or rec.get("prompt")
        if question is None:
            raise ValueError(
                f"GSM1K record at index {idx} in {target_file.name} is missing 'question' or 'prompt' field."
            )

        # Extract answer
        answer = rec.get("answer") or rec.get("grade") or rec.get("label")
        if answer is None:
            raise ValueError(
                f"GSM1K record at index {idx} in {target_file.name} is missing 'answer', 'grade', or 'label' field."
            )

        # Resolve stable item ID
        item_id = str(rec.get("id") or rec.get("item_id") or idx)

        # Build stable opaque prompt reference
        prompt_ref = f"gsm1k:{split}:{item_id}"

        # Setup metadata safely storing prompt/answer content out of aggregate report
        metadata_list = [
            ("source_format", "jsonl" if is_jsonl else "json"),
            ("question", str(question)),
            ("answer", str(answer)),
        ]

        if "grade" in rec:
            metadata_list.append(("grade", str(rec["grade"])))
        if "domain" in rec:
            metadata_list.append(("domain", str(rec["domain"])))

        items.append(
            GeneralizationAuditItem(
                dataset="GSM1K",
                split=split,
                item_id=item_id,
                prompt_ref=prompt_ref,
                answer_kind="numeric_text",
                metadata=tuple(metadata_list),
            )
        )

    return tuple(items)
