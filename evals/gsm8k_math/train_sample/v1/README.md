# GSM8K Train-Split Sample (50 cases)

This directory contains a deterministically sampled set of 50 records from the `train` split of the GSM8K dataset.

## Purpose

This sample is **unsealed by design**. It provides the inner-loop gradient signal identified as missing in ADR-0121 and ADR-0126. It is used to run and verify the candidate-graph parser exit criterion, which is:
- `correct >= 10/50`
- `wrong == 0`

By keeping this sample unsealed and separate from the sealed test holdout (`evals/gsm8k_math/holdouts/v1/cases.jsonl.age`), we avoid contamination of our test suite while having a clear development loop target.

## Dataset Version & Metadata

- **Hugging Face Dataset Identifier**: `openai/gsm8k` (aliased to `gsm8k`)
- **Config**: `main`
- **Split**: `train`
- **Commit Hash (Dataset Revision)**: `740312add88f781978c0658806c59bc2815b9866`
- **Hugging Face Datasets Library Version**: `4.8.5`

Note: Due to standard namespace constraints in certain versions of `huggingface_hub`, loading is done via `load_dataset("openai/gsm8k", "main", split="train")` which points to the identical underlying repository and revision hash.

## Selection Rule

The 50 cases are selected deterministically using SHA-256 of the row index combined with a salt, avoiding selection bias:

```python
import hashlib
from datasets import load_dataset

ds = load_dataset("openai/gsm8k", "main", split="train")

SALT = "adr-0126-train-sample-v1"
ranked = sorted(
    range(len(ds)),
    key=lambda i: hashlib.sha256(f"{i}:{SALT}".encode()).hexdigest()
)
sample_indices = sorted(ranked[:50])
```

The resulting sorted sample indices from the `train` split are:
`[9, 229, 560, 685, 967, 1149, 1227, 1252, 1394, 1593, 1634, 1796, 1903, 2020, 2045, 2145, 2369, 2595, 2605, 2714, 3013, 3020, 3222, 3343, 3368, 3460, 3644, 3718, 4006, 4021, 4129, 4215, 4304, 5022, 5371, 5539, 5622, 5720, 5952, 5965, 6058, 6122, 6260, 6293, 6425, 6587, 7137, 7147, 7163, 7444]`

Each case in `cases.jsonl` preserves:
- `case_id`: zero-padded `gsm8k-train-sample-v1-NNNN`
- `source_dataset`: `"gsm8k"`
- `source_split`: `"train"`
- `source_index`: the original row index in the Hugging Face dataset
- `question`: the verbatim question string
- `answer_expression`: the verbatim answer field containing reasoning steps and number suffix
- `answer_numeric`: the integer or float parsed from the `#### N` suffix in the answer expression
