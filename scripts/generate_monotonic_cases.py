"""Generate the monotonic-learning cases.jsonl files for dev / public / holdouts.

Protocol shape (per split):

    cycle 0:               probe all probes (baseline)
    cycle 1..cycle_count:  one teach step (rotating domains) + probe all

Layout written:
    evals/monotonic_learning/dev/cases.jsonl
    evals/monotonic_learning/public/v1/cases.jsonl
    evals/monotonic_learning/holdouts/v1/cases.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence


def _probe(cycle: int, domain: str, probe_id: str, prompt: str, terms: list[str]) -> dict:
    return {
        "cycle": cycle,
        "op": "probe",
        "domain": domain,
        "id": probe_id,
        "prompt": prompt,
        "expected_terms": terms,
    }


def _teach(cycle: int, domain: str, prime: list[str], prompt: str) -> dict:
    return {
        "cycle": cycle,
        "op": "teach",
        "domain": domain,
        "prime": prime,
        "prompt": prompt,
    }


def build_split(
    *,
    out_path: Path,
    probes_per_domain: dict[str, list[tuple[str, str, list[str]]]],
    teaching_steps_per_domain: dict[str, list[tuple[list[str], str]]],
    cycle_count: int,
) -> int:
    domains: Sequence[str] = list(probes_per_domain.keys())
    teach_cursor: dict[str, int] = {d: 0 for d in domains}

    rows: list[dict] = []

    # Cycle 0: baseline probes only
    for d in domains:
        for probe_id, prompt, terms in probes_per_domain[d]:
            rows.append(_probe(0, d, probe_id, prompt, terms))

    # Cycles 1..N: one teach (rotating domain) + all probes
    for cycle in range(1, cycle_count + 1):
        teach_domain = domains[(cycle - 1) % len(domains)]
        steps = teaching_steps_per_domain[teach_domain]
        prime, prompt = steps[teach_cursor[teach_domain] % len(steps)]
        teach_cursor[teach_domain] += 1
        rows.append(_teach(cycle, teach_domain, prime, prompt))

        for d in domains:
            for probe_id, prompt_p, terms in probes_per_domain[d]:
                rows.append(_probe(cycle, d, probe_id, prompt_p, terms))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows)


# Domain definitions: probes are deterministic queries; teaching steps are
# (prime turns, correction prompt) pairs.

_DOMAIN_TRUTH_PROBES = [
    ("PT-1", "What is truth?",           ["truth"]),
    ("PT-2", "Is truth coherent?",       ["truth"]),
    ("PT-3", "Why does truth matter?",   ["truth"]),
]

_DOMAIN_LIGHT_PROBES = [
    ("PL-1", "What is light?",            ["light"]),
    ("PL-2", "Why does light reveal?",    ["light"]),
    ("PL-3", "Is light revelation?",      ["light"]),
]

_DOMAIN_WISDOM_PROBES = [
    ("PW-1", "What is wisdom?",            ["wisdom"]),
    ("PW-2", "Is wisdom valuable?",        ["wisdom"]),
    ("PW-3", "Compare wisdom and knowledge", ["wisdom", "knowledge"]),
]

_DOMAIN_CREATION_PROBES = [
    ("PC-1", "What is creation?",          ["creation"]),
    ("PC-2", "Why does creation matter?",  ["creation"]),
    ("PC-3", "Is creation ongoing?",       ["creation"]),
]

_DOMAIN_KNOWLEDGE_PROBES = [
    ("PK-1", "What is knowledge?",         ["knowledge"]),
    ("PK-2", "Is knowledge wisdom?",       ["knowledge"]),
    ("PK-3", "Why does knowledge matter?", ["knowledge"]),
]

# v2 additions — extra domains for deeper-cycle stress
_DOMAIN_ORDER_PROBES = [
    ("PO-1", "What is order?",             ["order"]),
    ("PO-2", "Is order coherence?",        ["order"]),
    ("PO-3", "Why does order matter?",     ["order"]),
    ("PO-4", "Compare order and chaos",    ["order"]),
]

_DOMAIN_MEMORY_PROBES = [
    ("PM-1", "What is memory?",            ["memory"]),
    ("PM-2", "Is memory recall?",          ["memory"]),
    ("PM-3", "Why does memory matter?",    ["memory"]),
    ("PM-4", "Compare memory and forgetting", ["memory"]),
]

_DOMAIN_REASON_PROBES = [
    ("PR-1", "What is reason?",            ["reason"]),
    ("PR-2", "Is reason inference?",       ["reason"]),
    ("PR-3", "Why does reason matter?",    ["reason"]),
    ("PR-4", "Compare reason and intuition", ["reason"]),
]

_DOMAIN_SPIRIT_PROBES = [
    ("PS-1", "What is spirit?",            ["spirit"]),
    ("PS-2", "Is spirit life?",            ["spirit"]),
    ("PS-3", "Why does spirit matter?",    ["spirit"]),
    ("PS-4", "Compare spirit and matter",  ["spirit"]),
]

# v3 additions — finer-grained probe sets for deepest-cycle stress
_DOMAIN_MEANING_PROBES = [
    ("PMG-1", "What is meaning?",          ["meaning"]),
    ("PMG-2", "Is meaning identity?",      ["meaning"]),
    ("PMG-3", "Why does meaning matter?",  ["meaning"]),
    ("PMG-4", "Compare meaning and noise", ["meaning"]),
]

_DOMAIN_IDENTITY_PROBES = [
    ("PID-1", "What is identity?",         ["identity"]),
    ("PID-2", "Is identity coherence?",    ["identity"]),
    ("PID-3", "Why does identity matter?", ["identity"]),
    ("PID-4", "Compare identity and self", ["identity"]),
]

_DOMAIN_PRINCIPLE_PROBES = [
    ("PPR-1", "What is principle?",         ["principle"]),
    ("PPR-2", "Is principle a constraint?", ["principle"]),
    ("PPR-3", "Why does principle matter?", ["principle"]),
    ("PPR-4", "Compare principle and rule", ["principle"]),
]

_DOMAIN_JUDGMENT_PROBES = [
    ("PJ-1", "What is judgment?",          ["judgment"]),
    ("PJ-2", "Is judgment inference?",     ["judgment"]),
    ("PJ-3", "Why does judgment matter?",  ["judgment"]),
    ("PJ-4", "Compare judgment and opinion", ["judgment"]),
]


def _teach_steps_for(domain: str) -> list[tuple[list[str], str]]:
    """Three teaching examples per domain (rotated as cycles advance)."""
    base = f"What is {domain}?"
    return [
        ([base], f"Actually {domain} is more than that."),
        ([base], f"No, {domain} requires deeper understanding."),
        ([base], f"Actually {domain} relates to coherence."),
    ]


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "evals" / "monotonic_learning"

    # Public v1: three domains x three probes, 12 cycles -> 9 + 12*(1+9) = 129 rows
    public_domains = {
        "truth":  _DOMAIN_TRUTH_PROBES,
        "light":  _DOMAIN_LIGHT_PROBES,
        "wisdom": _DOMAIN_WISDOM_PROBES,
    }
    public_teaching = {d: _teach_steps_for(d) for d in public_domains}
    n_public = build_split(
        out_path=root / "public" / "v1" / "cases.jsonl",
        probes_per_domain=public_domains,
        teaching_steps_per_domain=public_teaching,
        cycle_count=12,
    )

    # Dev: two domains x two probes, 10 cycles -> 4 + 10*(1+4) = 54 rows
    dev_domains = {
        "truth":  _DOMAIN_TRUTH_PROBES[:2],
        "light":  _DOMAIN_LIGHT_PROBES[:2],
    }
    dev_teaching = {d: _teach_steps_for(d) for d in dev_domains}
    n_dev = build_split(
        out_path=root / "dev" / "cases.jsonl",
        probes_per_domain=dev_domains,
        teaching_steps_per_domain=dev_teaching,
        cycle_count=10,
    )

    # Holdouts v1: distinct domains (creation, knowledge), three probes each,
    # 12 cycles -> 6 + 12*(1+6) = 90 rows
    holdout_domains = {
        "creation":  _DOMAIN_CREATION_PROBES,
        "knowledge": _DOMAIN_KNOWLEDGE_PROBES,
    }
    holdout_teaching = {d: _teach_steps_for(d) for d in holdout_domains}
    n_holdout = build_split(
        out_path=root / "holdouts" / "v1" / "cases.jsonl",
        probes_per_domain=holdout_domains,
        teaching_steps_per_domain=holdout_teaching,
        cycle_count=12,
    )

    print(f"wrote dev: {n_dev} rows")
    print(f"wrote public/v1: {n_public} rows")
    print(f"wrote holdouts/v1: {n_holdout} rows")

    # v2 splits — deeper cycle counts, more domains, more probes.
    # Public v2: five domains x ~3-4 probes, 20 cycles.
    public_v2_domains = {
        "truth":   _DOMAIN_TRUTH_PROBES,
        "light":   _DOMAIN_LIGHT_PROBES,
        "wisdom":  _DOMAIN_WISDOM_PROBES,
        "order":   _DOMAIN_ORDER_PROBES,
        "memory":  _DOMAIN_MEMORY_PROBES,
    }
    public_v2_teaching = {d: _teach_steps_for(d) for d in public_v2_domains}
    n_public_v2 = build_split(
        out_path=root / "public" / "v2" / "cases.jsonl",
        probes_per_domain=public_v2_domains,
        teaching_steps_per_domain=public_v2_teaching,
        cycle_count=20,
    )

    # Holdouts v2: four distinct domains, 18 cycles.
    holdouts_v2_domains = {
        "creation":  _DOMAIN_CREATION_PROBES,
        "knowledge": _DOMAIN_KNOWLEDGE_PROBES,
        "reason":    _DOMAIN_REASON_PROBES,
        "spirit":    _DOMAIN_SPIRIT_PROBES,
    }
    holdouts_v2_teaching = {d: _teach_steps_for(d) for d in holdouts_v2_domains}
    n_holdouts_v2 = build_split(
        out_path=root / "holdouts" / "v2" / "cases.jsonl",
        probes_per_domain=holdouts_v2_domains,
        teaching_steps_per_domain=holdouts_v2_teaching,
        cycle_count=18,
    )

    print(f"wrote public/v2: {n_public_v2} rows")
    print(f"wrote holdouts/v2: {n_holdouts_v2} rows")

    # v3 splits — deepest cycle counts, broadest domain coverage.
    # Public v3: seven domains x ~4 probes, 30 cycles.
    public_v3_domains = {
        "truth":     _DOMAIN_TRUTH_PROBES,
        "light":     _DOMAIN_LIGHT_PROBES,
        "wisdom":    _DOMAIN_WISDOM_PROBES,
        "order":     _DOMAIN_ORDER_PROBES,
        "memory":    _DOMAIN_MEMORY_PROBES,
        "meaning":   _DOMAIN_MEANING_PROBES,
        "identity":  _DOMAIN_IDENTITY_PROBES,
    }
    public_v3_teaching = {d: _teach_steps_for(d) for d in public_v3_domains}
    n_public_v3 = build_split(
        out_path=root / "public" / "v3" / "cases.jsonl",
        probes_per_domain=public_v3_domains,
        teaching_steps_per_domain=public_v3_teaching,
        cycle_count=30,
    )

    # Holdouts v3: six distinct domains, 25 cycles.
    holdouts_v3_domains = {
        "creation":  _DOMAIN_CREATION_PROBES,
        "knowledge": _DOMAIN_KNOWLEDGE_PROBES,
        "reason":    _DOMAIN_REASON_PROBES,
        "spirit":    _DOMAIN_SPIRIT_PROBES,
        "principle": _DOMAIN_PRINCIPLE_PROBES,
        "judgment":  _DOMAIN_JUDGMENT_PROBES,
    }
    holdouts_v3_teaching = {d: _teach_steps_for(d) for d in holdouts_v3_domains}
    n_holdouts_v3 = build_split(
        out_path=root / "holdouts" / "v3" / "cases.jsonl",
        probes_per_domain=holdouts_v3_domains,
        teaching_steps_per_domain=holdouts_v3_teaching,
        cycle_count=25,
    )

    print(f"wrote public/v3: {n_public_v3} rows")
    print(f"wrote holdouts/v3: {n_holdouts_v3} rows")


if __name__ == "__main__":
    main()
