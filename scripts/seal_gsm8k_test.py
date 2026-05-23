"""ADR-0119.7 — seal the real GSM8K test set as the gsm8k_math holdout.

Loads the GSM8K test split via Hugging Face ``datasets``, converts each
row to the lane-runner JSONL schema (id / problem / expected_answer /
expected_unit), and encrypts the result against the recipient key
registered in ``docs/holdout_recipients.txt``.

The plaintext never lands on disk — it's held in memory only during
encryption. The final artifact is
``evals/gsm8k_math/holdouts/v1/cases.jsonl.age``.

Per ADR-0119 §5.7 the seal is one-way: development MUST operate blind
to the test contents until a release event signed-by-reviewer opens
the lane.

Usage:

    uv run python scripts/seal_gsm8k_test.py [--split test|train] \\
        [--recipient <age recipient string>]

The default split is ``test``. Use ``--split train --limit N`` to
seal a small chunk of train for sanity-check purposes (does NOT
overwrite the real test seal).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RECIPIENTS_FILE = _REPO_ROOT / "docs" / "holdout_recipients.txt"
_GSM8K_SEAL_PATH = _REPO_ROOT / "evals" / "gsm8k_math" / "holdouts" / "v1" / "cases.jsonl.age"


# GSM8K answer pattern: each `answer` field ends with "#### N" where N is the
# final numeric answer. Numbers may be integers, decimals, or carry thousands
# separators (commas) like "2,125".
_GSM8K_FINAL_ANSWER_RE = re.compile(r"####\s*(-?[\d,]+(?:\.\d+)?)\s*$")


def _extract_answer(answer_text: str) -> float:
    """Pull the final numeric answer from a GSM8K answer string.

    Strips comma thousands-separators. Raises ValueError if the
    "#### N" marker is absent.
    """
    match = _GSM8K_FINAL_ANSWER_RE.search(answer_text)
    if not match:
        raise ValueError(
            f"no '#### N' final-answer marker in answer text: "
            f"{answer_text[-80:]!r}"
        )
    raw = match.group(1).replace(",", "")
    if "." not in raw:
        return int(raw)
    return float(raw)


def _convert_to_lane_schema(
    rows: list[dict], prefix: str
) -> list[dict]:
    """Convert GSM8K rows → lane-runner case dicts.

    Each case carries:
        id              — "{prefix}-{i:04d}" (deterministic ordering)
        problem         — the GSM8K question, verbatim
        expected_answer — the integer (or float) after "####"
        expected_unit   — "" (sentinel; runner skips unit check)

    No ground_truth_graph is emitted — GSM8K problems generally require
    rate/comparison reasoning the ADR-0115 parser does not handle, so
    most cases will refuse rather than parse. That's the expected
    behavior; the wrong-count discipline is preserved by the runner.
    """
    cases: list[dict] = []
    for i, row in enumerate(rows, start=1):
        question = row["question"]
        answer = row["answer"]
        try:
            expected_answer = _extract_answer(answer)
        except ValueError as exc:
            raise ValueError(f"case {prefix}-{i:04d}: {exc}") from exc
        cases.append({
            "id": f"{prefix}-{i:04d}",
            "problem": question,
            "expected_answer": expected_answer,
            "expected_unit": "",
        })
    return cases


def _load_recipient() -> str:
    """Read the recipient public key from docs/holdout_recipients.txt.

    Format (per ADR-0119.1):
        # <comment lines>
        fabrication_control: age1xxx...

    For ADR-0119.7 we use the SAME recipient as fabrication_control
    by default (single key per repo). A future amendment could split
    per-lane keys if needed.
    """
    if not _RECIPIENTS_FILE.exists():
        raise FileNotFoundError(
            f"recipients file missing: {_RECIPIENTS_FILE}. "
            "Run ADR-0119.1 first to establish the keypair."
        )
    text = _RECIPIENTS_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        # "lane_name: age1xxx" or just "age1xxx"
        if ":" in line:
            _, _, value = line.partition(":")
            value = value.strip()
        else:
            value = line
        if value.startswith("age1"):
            return value
    raise ValueError(
        f"no age1... recipient key found in {_RECIPIENTS_FILE}"
    )


def _encrypt_to_age(plaintext: bytes, recipient_str: str) -> bytes:
    """Encrypt plaintext bytes to age ciphertext under the recipient."""
    try:
        import pyrage
        from pyrage.x25519 import Recipient
    except ImportError as exc:
        raise RuntimeError(
            "pyrage not installed; required for ADR-0119.7 sealing"
        ) from exc
    recipient = Recipient.from_str(recipient_str)
    return pyrage.encrypt(plaintext, [recipient])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seal the GSM8K test set as the gsm8k_math holdout"
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["test", "train"],
        help="GSM8K split to seal (default: test). Use 'train' for "
             "sanity-check sealing; never overwrites the test seal.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of rows sealed (for sanity-check runs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override the output path (default: "
             "evals/gsm8k_math/holdouts/v1/cases.jsonl.age for test split; "
             "a sibling path for train)",
    )
    parser.add_argument(
        "--recipient",
        default=None,
        help="age recipient string (default: read from "
             "docs/holdout_recipients.txt)",
    )
    args = parser.parse_args()

    try:
        from datasets import load_dataset  # type: ignore[import-not-found]
    except ImportError:
        print(
            "datasets package not installed. Run: uv add datasets",
            file=sys.stderr,
        )
        return 2

    # Resolve output path
    if args.output is not None:
        output_path = args.output
    elif args.split == "test":
        output_path = _GSM8K_SEAL_PATH
    else:
        # Sanity-check sealing of train → distinct path
        suffix = f"-train{f'-limit{args.limit}' if args.limit else ''}"
        output_path = _GSM8K_SEAL_PATH.with_name(
            f"cases{suffix}.jsonl.age"
        )

    # Refuse to overwrite the test seal accidentally
    if (
        args.split == "train"
        and output_path == _GSM8K_SEAL_PATH
    ):
        print(
            f"refusing to write a train-derived seal to the test path "
            f"{output_path}; use --output to override",
            file=sys.stderr,
        )
        return 2

    recipient_str = args.recipient or _load_recipient()
    print(f"recipient: {recipient_str}", file=sys.stderr)

    print(f"loading GSM8K {args.split} split...", file=sys.stderr)
    ds = load_dataset("openai/gsm8k", "main")
    rows = list(ds[args.split])
    if args.limit is not None:
        rows = rows[:args.limit]
    print(f"loaded {len(rows)} rows", file=sys.stderr)

    prefix = f"gsm8k-{args.split}"
    cases = _convert_to_lane_schema(rows, prefix=prefix)
    print(f"converted to {len(cases)} lane-schema cases", file=sys.stderr)

    plaintext = (
        "\n".join(
            json.dumps(c, sort_keys=True, separators=(",", ":")) for c in cases
        )
        + "\n"
    ).encode("utf-8")
    print(f"plaintext size: {len(plaintext)} bytes", file=sys.stderr)

    ciphertext = _encrypt_to_age(plaintext, recipient_str)
    print(f"ciphertext size: {len(ciphertext)} bytes", file=sys.stderr)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ciphertext)
    print(f"wrote sealed file: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
