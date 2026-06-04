"""ADR-0179 EX-2 — bare-decimal grounding in the shared round-trip primitive.

`_value_grounds` already grounds the symbol form `$N.NN` (currency) and `N/M`
(fraction); a decimal written without a symbol (`0.75`) was never a single token
(the tokenizer splits on `.`) and so failed to ground — refusing correct products
like 0003 (`48×24×0.75 = 864`). EX-2 grounds a bare decimal when both digit-runs
appear, symmetric with those branches.

This is the ONE shared-primitive (serving-path) change in extraction richness, so
the load-bearing test is wrong=0: serving stays on the current ratified count.
"""

from __future__ import annotations

import json
from pathlib import Path

from generate.math_roundtrip import _tokens, _value_grounds


class TestBareDecimalGrounding:
    def test_decimal_grounds_when_digit_runs_present(self) -> None:
        toks = _tokens("They sell for $0.75 each.")  # -> tokens include "0","75"
        assert _value_grounds("0.75", toks) is True

    def test_decimal_refuses_when_a_run_absent(self) -> None:
        toks = _tokens("They sell for 80 cents.")  # no "0"/"75"
        assert _value_grounds("0.75", toks) is False

    def test_plain_decimal_in_text_grounds(self) -> None:
        toks = _tokens("It moved 2.5 meters.")  # "2","5" present
        assert _value_grounds("2.5", toks) is True

    def test_integer_grounding_unchanged(self) -> None:
        toks = _tokens("He has 48 boxes.")
        assert _value_grounds("48", toks) is True
        assert _value_grounds("49", toks) is False


class TestWrongZeroPreserved:
    def test_serving_byte_identical(self) -> None:
        # the load-bearing obligation: the shared-primitive change must not shift
        # the serving contract.
        from evals.gsm8k_math.train_sample.v1.runner import (
            _CASES_PATH,
            _load_cases,
            build_report,
        )

        counts = build_report(_load_cases(_CASES_PATH))["counts"]
        # ADR-0207 §5 step 2: serving baseline is now 4/46/0 (cv-0005 goal-residual).
        assert counts == {"correct": 4, "wrong": 0, "refused": 46}


class TestUnblocksDecimalProduct:
    def test_0003_class_product_now_resolves(self) -> None:
        # 48 boxes x 24 each x $0.75 each = 864 — previously refused (0.75 ungrounded)
        from generate.derivation.multistep import search_chain

        case = next(
            json.loads(line)
            for line in Path(
                "evals/gsm8k_math/train_sample/v1/cases.jsonl"
            ).read_text().splitlines()
            if "student council" in line
        )
        res = search_chain(case["question"])
        assert res is not None and res.answer == float(case["answer_numeric"])
