"""core.physics.valence — ADR-0007 valence bundle and deterministic lifting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Mapping


class ForceClass(str, Enum):
    DECLARATIVE = "declarative"
    PERFORMATIVE = "performative"
    IMPERATIVE = "imperative"
    COHORTATIVE = "cohortative"
    JUSSIVE = "jussive"
    INTERROGATIVE = "interrogative"
    OPTATIVE = "optative"
    EXPRESSIVE = "expressive"
    COMMISSIVE = "commissive"


@dataclass(frozen=True, slots=True)
class EmphasisProfile:
    focus_element: str | None = None
    mechanism: str = "unmarked"
    degree: str = "unmarked"


@dataclass(frozen=True, slots=True)
class PolaritySpec:
    value: str = "positive"
    kind: str | None = None


@dataclass(frozen=True, slots=True)
class OrientationSpec:
    direction: str = "within"
    target: str | None = None
    preposition_source: str | None = None


@dataclass(frozen=True, slots=True)
class ValenceBundle:
    affective: frozenset[str] = field(default_factory=frozenset)
    force: ForceClass = ForceClass.DECLARATIVE
    emphasis: EmphasisProfile = field(default_factory=EmphasisProfile)
    polarity: PolaritySpec = field(default_factory=PolaritySpec)
    orientation: OrientationSpec = field(default_factory=OrientationSpec)

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["affective"] = sorted(self.affective)
        payload["force"] = self.force.value
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), sort_keys=True, separators=(",", ":"))


_NEGATIVE_PARTICLES = {
    "lo": "absolute",
    "לֹא": "absolute",
    "al": "prohibitive",
    "אַל": "prohibitive",
    "ou": "factual",
    "οὐ": "factual",
    "me": "conditional",
    "μή": "conditional",
}

_ORIENTATION_BY_PREPOSITION = {
    "pros": "toward",
    "πρός": "toward",
    "en": "within",
    "ἐν": "within",
    "ek": "from",
    "ἐκ": "from",
    "apo": "from",
    "ἀπό": "from",
    "dia": "through",
    "διά": "through",
    "hypo": "under",
    "ὑπό": "under",
    "epi": "upon",
    "ἐπί": "upon",
    "para": "alongside",
    "παρά": "alongside",
}


def lift_valence(
    *,
    lemma: str,
    language: str,
    features: Mapping[str, object] | None = None,
    notes: str | None = None,
) -> ValenceBundle:
    """Lift valence deterministically from morphology and pack notes."""
    features = dict(features or {})
    lower_lemma = lemma.lower()
    lower_notes = (notes or "").lower()
    mood = str(features.get("mood", "")).lower()
    stem = str(features.get("stem", "")).lower()
    tense = str(features.get("tense", "")).lower()
    force = ForceClass.DECLARATIVE
    if "divine" in lower_notes and ("create" in lower_notes or "creation" in lower_notes):
        force = ForceClass.PERFORMATIVE
    elif mood == "imperative":
        force = ForceClass.IMPERATIVE
    elif mood == "cohortative":
        force = ForceClass.COHORTATIVE
    elif mood == "jussive":
        force = ForceClass.JUSSIVE
    elif mood == "optative":
        force = ForceClass.OPTATIVE

    affective: set[str] = set()
    if "divine" in lower_notes or lower_lemma in {"θεός", "god"}:
        affective.add("awe")
    if "truth" in lower_notes or lower_lemma in {"אמת", "ἀλήθεια", "truth"}:
        affective.add("peace")
    if "life" in lower_notes or lower_lemma in {"ζωή", "life"}:
        affective.add("exultation")

    mechanism = "unmarked"
    degree = "unmarked"
    if stem in {"piel", "intensive"}:
        mechanism = "stem_intensification"
        degree = "strong"
    elif "front" in lower_notes:
        mechanism = "fronting"
        degree = "strong"
    elif "anarthrous" in lower_notes:
        mechanism = "particle"
        degree = "light"

    neg_kind = _NEGATIVE_PARTICLES.get(lower_lemma)
    polarity = PolaritySpec(
        value="negative" if neg_kind else "positive",
        kind=neg_kind,
    )
    direction = _ORIENTATION_BY_PREPOSITION.get(lower_lemma, "within")
    orientation = OrientationSpec(
        direction=direction,
        preposition_source=lemma if direction != "within" or lower_lemma in _ORIENTATION_BY_PREPOSITION else None,
    )
    if tense in {"imperfect", "present"} and force is ForceClass.DECLARATIVE:
        degree = "light" if degree == "unmarked" else degree
    return ValenceBundle(
        affective=frozenset(affective),
        force=force,
        emphasis=EmphasisProfile(focus_element=lemma, mechanism=mechanism, degree=degree),
        polarity=polarity,
        orientation=orientation,
    )
