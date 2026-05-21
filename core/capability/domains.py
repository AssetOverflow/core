from __future__ import annotations

DOMAIN_PACKS: dict[str, tuple[str, ...]] = {
    "systems_software": ("en_systems_software_v1",),
    "mathematics_logic": ("en_mathematics_logic_v1",),
    "physics": ("en_physics_v1",),
    "hebrew_greek_textual_reasoning": (
        "grc_logos_micro_v1",
        "grc_logos_cognition_v1",
        "he_logos_micro_v1",
        "he_core_cognition_v1",
    ),
    "philosophy_theology": ("en_core_cognition_v1", "en_core_meta_v1"),
}

DOMAIN_CORPORA: dict[str, tuple[str, ...]] = {
    "systems_software": (
        "systems_software_chains_v1",
    ),
    "mathematics_logic": (
        "mathematics_logic_chains_v1",
    ),
    "physics": (
        "physics_chains_v1",
    ),
    "hebrew_greek_textual_reasoning": (
        "hebrew_greek_textual_reasoning_chains_v1",
    ),
    "philosophy_theology": (
        "cognition_chains_v1",
        "cross_pack_chains_v1",
        "philosophy_theology_chains_v1",
    ),
}

DOMAIN_CAPABILITY_CORPORA: dict[str, str] = {
    "systems_software_chains_v1": "teaching/domain_chains/systems_software_chains_v1.jsonl",
    "mathematics_logic_chains_v1": "teaching/domain_chains/mathematics_logic_chains_v1.jsonl",
    "physics_chains_v1": "teaching/domain_chains/physics_chains_v1.jsonl",
    "hebrew_greek_textual_reasoning_chains_v1": "teaching/domain_chains/hebrew_greek_textual_reasoning_chains_v1.jsonl",
    "philosophy_theology_chains_v1": "teaching/domain_chains/philosophy_theology_chains_v1.jsonl",
}

DOMAIN_OPERATOR_CLAIMS: dict[str, tuple[str, ...]] = {
    "systems_software": ("transitive", "causal"),
    "mathematics_logic": ("transitive", "proof_chain", "contradiction"),
    "physics": ("causal", "modal"),
    "hebrew_greek_textual_reasoning": ("causal", "contradiction"),
    "philosophy_theology": ("causal", "modal", "contradiction"),
}
