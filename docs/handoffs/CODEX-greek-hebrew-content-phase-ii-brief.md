# Codex Brief - Greek/Hebrew Content Phase II

**Audience:** Same agent or content partner that seeded the original grc/he cognition packs.

**Mission:** Deepen the cognition-tier Greek and Hebrew packs by adding another layer of tightly scoped, semantically aligned lemmas. The current seam is ready; the packs are still skeletal. The target is to move each pack from the current small seed into a more usable content tier without changing the architecture or the runtime.

This is a content-only brief. Do not add new infrastructure, new loaders, or new runtime behavior.

**Target packs:**

- `language_packs/data/grc_logos_cognition_v1`
- `language_packs/data/he_core_cognition_v1`

**Estimated effort:** One content pass per pack plus validation.

---

## Background

The current grc/he cognition packs were intentionally seeded small. They established the core semantic seam and the cross-language collapse lines, but they are still underpopulated relative to their intended teaching and grounding role.

The useful next step is not architecture. It is content depth: more lemmas, better semantic clustering, and cleaner cross-language alignments to existing English cognition lemmas.

The working target is to deepen each pack by about 20-30 lemmas, organized by semantic family, while keeping the existing contract shape intact.

## Phase 0 - Baseline

1. Count current lemmas in both packs.
2. Inventory existing semantic families and alignments.
3. Confirm the current cross-language anchors that already exist in the pack alignments.
4. Capture the baseline counts before editing.

Suggested baseline commands:

```bash
python3 - <<'PY'
from pathlib import Path
import json

for pack in [Path('language_packs/data/grc_logos_cognition_v1'), Path('language_packs/data/he_core_cognition_v1')]:
    lexicon = pack / 'lexicon.jsonl'
    count = sum(1 for line in lexicon.read_text(encoding='utf-8').splitlines() if line.strip())
    print(pack.name, count)
PY
```

## Phase 1 - Greek expansion

Add 20-30 new grc lemmas that cluster around the semantic families already implied by the existing seed:

- intellect and cognition: `νοῦς`, `λόγος`, `σοφία`, `γνῶσις`, `σύνεσις`, `ἐπιστήμη`
- spirit and breath: `πνεῦμα`, `ψυχή`, `πνοή`
- truth and clarity: `ἀλήθεια`, `σαφήνεια`, `φανερότης`
- ordering and measure: `τάξις`, `μέτρον`, `κρίσις`
- relation and response: `ἀπόκρισις`, `κοινωνία`, `πίστις`

For each new lemma:

1. Keep the surface and lemma stable and explicit.
2. Assign semantic domains that fit the existing pack vocabulary.
3. Add or update the relevant cross-language alignment to an existing English cognition lemma when there is a stable target.
4. Avoid forcing an English collapse when the concept does not genuinely collapse cleanly.

Example alignment targets can reuse existing English cognition anchors, such as conceptual entries around mind, word, wisdom, knowledge, spirit, truth, and judgment.

## Phase 2 - Hebrew expansion

Add 20-30 new he lemmas that cluster around the semantic families already implied by the existing seed:

- spirit and breath: `רוח`, `נשמה`, `נפש`
- heart and will: `לב`, `רצון`, `כוונה`
- wisdom and discernment: `חכמה`, `בינה`, `דעת`
- truth and faithfulness: `אמת`, `אמונה`, `נאמנות`
- covenant and steadfastness: `חסד`, `ברית`, `צדק`

For each new lemma:

1. Keep the morphology and lemma choices conservative.
2. Use semantic domains that match the current pack design.
3. Align to the closest existing English cognition lemma only when the mapping is stable and honest.
4. Preserve the existing split between direct collapse and non-collapse relation types.

## Phase 3 - Cross-language alignment

For each newly added lemma, add the most appropriate alignment annotation to the existing English cognition layer.

Rules:

1. Prefer one clear alignment over several weak ones.
2. Use non-collapse relations when English does not genuinely preserve the distinction.
3. Reuse the current evidence style already present in the pack.
4. Do not widen the English pack just to make an alignment easier.

## Phase 4 - Validation

After the content pass:

1. Recount both packs and confirm the intended growth.
2. Verify the lexicon and alignment files are internally consistent.
3. Run the pack validation and relevant cognition checks.
4. Confirm the existing runtime/eval lanes are unchanged by the content-only update.

Suggested checks:

```bash
python3 -m pytest tests/test_pack_glosses_content.py -q
python3 -m pytest tests/test_domain_pack_contract.py -q
python3 -m core.cli eval cognition
```

If any update forces an architectural change, stop and split that out. This brief is for content deepening only.

## Deliverables

1. Expanded `grc_logos_cognition_v1` lexicon/alignment content.
2. Expanded `he_core_cognition_v1` lexicon/alignment content.
3. Validation output showing the packs still load and the cognition lane is stable.

## Hard rules

- Do not change runtime code.
- Do not add new loaders or new pack kinds.
- Do not change the existing cross-language contract shape.
- Do not let English collapse convenience override semantic honesty.
- Do not turn the update into an architecture project.