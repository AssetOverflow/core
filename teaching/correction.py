"""Correction capture — extract a typed correction from dialogue context.

A CorrectionCandidate binds the correction text to the prior turn it
corrects, carrying both the intent classification and the prior turn's
proposition for downstream review.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from generate.intent import DialogueIntent, IntentTag


@dataclass(frozen=True, slots=True)
class CorrectionCandidate:
    correction_text: str
    intent: DialogueIntent
    prior_surface: str
    prior_turn: int
    candidate_id: str

    def as_dict(self) -> dict[str, object]:
        return {
            "correction_text": self.correction_text,
            "intent_tag": self.intent.tag.value,
            "intent_subject": self.intent.subject,
            "prior_surface": self.prior_surface,
            "prior_turn": self.prior_turn,
            "candidate_id": self.candidate_id,
        }


def _candidate_id(correction_text: str, prior_surface: str, prior_turn: int) -> str:
    payload = json.dumps(
        {"correction_text": correction_text, "prior_surface": prior_surface, "prior_turn": prior_turn},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def extract_correction(
    correction_text: str,
    intent: DialogueIntent,
    prior_surface: str,
    prior_turn: int,
) -> CorrectionCandidate | None:
    """Extract a correction candidate from a correction-tagged intent.

    Returns None if the intent is not a correction.
    """
    if intent.tag is not IntentTag.CORRECTION:
        return None

    return CorrectionCandidate(
        correction_text=correction_text,
        intent=intent,
        prior_surface=prior_surface,
        prior_turn=prior_turn,
        candidate_id=_candidate_id(correction_text, prior_surface, prior_turn),
    )
