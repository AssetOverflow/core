"""Carried-handle acquisition seam for served ASK (Stage 2).

The missing-boundary analysis
(``docs/analysis/ask-runtime-wiring-missing-boundary-2026-06-10.md``) established
that the serving turn has no lawful way to obtain a ``QUESTION_NEEDED``
``ContemplationResult``: the only producer is the off-serving contemplation pass,
and scanning the ``teaching/questions`` sink would be new, unspecified acquisition
logic. This module is the recommended unblocking slice — **carried-handle
acquisition**: an explicit, caller-carried reference to one already-produced Q1-D
``DeliveredQuestion`` artifact is *resolved* (never produced, never rendered,
never discovered by scan) into an acquisition-compatible candidate for the
existing ASK serving stack.

The handle's provenance is the Q1-D artifact's own content address. The producer
(:mod:`core.epistemic_questions.delivery`) writes each artifact to
``{content_hash}.json`` where ``content_hash`` is
``sha256(f"{blocking_reason}:{slot_name}:{text}")`` over the artifact's own
fields. Resolution therefore verifies three independent things:

1. the handle is structurally valid (non-empty path, 64-hex content hash, and the
   path's filename is exactly the producer's content-addressed name);
2. the referenced artifact exists and parses as a JSON object;
3. the artifact's body re-hashes to the handle's content hash — a stale,
   replaced, or tampered artifact fails closed here.

Everything else — ``status == "question_only"``, ``requires_review``,
``served is False``, ``answer_binding`` absence, question text/slot validity, the
``question_path != proposal_path`` collision — is **delegated** to
:func:`core.epistemic_disclosure.ask_serving.evaluate_served_ask` via
:func:`core.epistemic_disclosure.ask_acquisition.acquire_served_ask_candidate`.
This seam owns handle resolution only; it duplicates no artifact serving policy.

**Trust boundary.** A handle is trusted plumbing state, never user text: it must
be constructed by a reviewed production path (a future producer→serving plumbing
slice), not parsed out of a chat turn. The Q1-D artifact carries no turn/case
provenance fields today, so the handle is *content-addressed*, not *turn-stamped*
— turn-addressability is exactly the explicitness of carrying the handle into the
turn. If a future slice adds turn provenance to the artifact, resolution should
check it here.

**Forbidden moves this module never makes:** call
``generate.contemplation.pass_manager.contemplate``; import or call
``core.epistemic_questions.render`` / ``render_question`` /
``deliver_ask``; construct question prose; scan ``teaching/questions`` or any
other sink (no glob/iterdir/listdir — the only filesystem access is reading the
single explicitly-named artifact, and only after the default-dark
``ask_serving_enabled`` gate passes).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.epistemic_disclosure.ask_acquisition import (
    AskAcquisitionDecision,
    acquire_served_ask_candidate,
)
from core.epistemic_questions.serving_gate import ask_serving_enabled

#: The producer's content address is a sha256 hex digest — nothing else is a
#: structurally valid handle hash.
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

#: String form of ``Terminal.QUESTION_NEEDED``. Deliberately a literal: importing
#: ``generate.contemplation`` from this serving-side seam would import the
#: off-serving pass manager package, which the boundary forbids.
#: ``evaluate_served_ask`` compares the stringified terminal, so the literal is
#: contract-equivalent.
_QUESTION_NEEDED = "QUESTION_NEEDED"


@dataclass(frozen=True, slots=True)
class AskArtifactHandle:
    """An explicit, carried reference to one already-produced Q1-D artifact.

    ``question_path`` names the single artifact file; ``content_hash`` is the
    producer's content address for it (also its filename stem). ``proposal_path``
    is carried through so the downstream adapter can enforce the
    question/proposal collision rule — it is ``None`` for a pure ASK delivery
    (the Q1-D producer never co-assigns the two).
    """

    question_path: str
    content_hash: str
    proposal_path: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedAskCandidate:
    """An acquisition-compatible candidate produced by handle resolution.

    Duck-types exactly the fields ``evaluate_served_ask`` reads off a
    ``ContemplationResult`` (``terminal`` / ``question_path`` /
    ``proposal_path``); ``terminal`` is always the ``QUESTION_NEEDED`` string. It
    carries no question text — the served surface is read from the artifact by
    the adapter, never constructed here.
    """

    terminal: str
    question_path: str
    proposal_path: str | None = None


@dataclass(frozen=True, slots=True)
class AskHandleResolution:
    """The typed outcome of resolving one carried handle.

    ``reason`` is a stable snake_case token naming the verification step that
    rejected the handle (or ``"resolved"``). ``candidate`` is populated iff
    ``resolved`` is True.
    """

    resolved: bool
    reason: str
    candidate: ResolvedAskCandidate | None = None


def _rejected(reason: str) -> AskHandleResolution:
    return AskHandleResolution(resolved=False, reason=reason, candidate=None)


def _paths_name_same_file(question_path: Path, proposal_path_value: str) -> bool:
    """Canonical-path collision check for the question/proposal pair.

    Compares *resolved* canonical paths, not raw string spellings, so an absolute
    ``question_path`` and a relative ``proposal_path`` (or any two differently
    spelled paths) that name the same file collide and fail closed. Resolution is
    best-effort (``strict=False``); if a path cannot be canonicalized (e.g. a
    symlink loop), fall back to the raw-spelling comparison, which still catches
    the exact-string collision.
    """
    try:
        return question_path.resolve(strict=False) == Path(proposal_path_value).resolve(
            strict=False
        )
    except (OSError, RuntimeError, ValueError):
        return str(question_path) == str(proposal_path_value)


def _recompute_content_hash(payload: Any) -> str | None:
    """Recompute the producer's content address from the artifact body.

    Mirrors ``DeliveredQuestion.content_hash`` exactly: the digest payload is
    ``f"{blocking_reason}:{slot_name}:{text}"`` with a slot-less artifact
    contributing the empty string for ``slot_name`` (the producer serializes that
    case as ``null``). Returns ``None`` when the fields needed to re-derive the
    address are absent or mistyped — a malformed body, by construction.
    """
    if not isinstance(payload, dict):
        return None
    blocking_reason = payload.get("blocking_reason")
    question = payload.get("question")
    if not isinstance(blocking_reason, str) or not isinstance(question, dict):
        return None
    slot_name = question.get("slot_name")
    if slot_name is None:
        slot_name = ""
    text = question.get("text")
    if not isinstance(slot_name, str) or not isinstance(text, str):
        return None
    digest_payload = f"{blocking_reason}:{slot_name}:{text}"
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def resolve_served_ask_handle(config: Any, handle: Any) -> AskHandleResolution:
    """Resolve an explicit carried handle into an acquisition-compatible candidate.

    Gate-first: while ``ask_serving_enabled`` is false (the default), this
    function performs **no filesystem access at all** and rejects with
    ``"gate_disabled"`` — the seam is side-effect free under default runtime
    configuration. Past the gate, the handle is verified structurally, the named
    artifact is read (one explicit path, never a scan), and the body must
    re-hash to the handle's content address. Any failure rejects with a typed
    reason; resolution never raises on bad input.

    The returned candidate has passed *identity* checks only. Q1-D field policy
    (status/review/served/answer-binding/text/slot/collision) is still owned by
    ``evaluate_served_ask`` downstream — pass the candidate through
    :func:`acquire_served_ask_from_handle` or
    ``acquire_served_ask_candidate(..., contemplation_result=candidate)``.
    """
    if not ask_serving_enabled(config):
        return _rejected("gate_disabled")
    if handle is None:
        return _rejected("missing_handle")

    question_path_value = getattr(handle, "question_path", None)
    content_hash_value = getattr(handle, "content_hash", None)
    proposal_path_value = getattr(handle, "proposal_path", None)

    if not isinstance(question_path_value, str) or not question_path_value.strip():
        return _rejected("malformed_handle")
    if (
        not isinstance(content_hash_value, str)
        or _CONTENT_HASH_RE.fullmatch(content_hash_value) is None
    ):
        return _rejected("malformed_handle")
    if proposal_path_value is not None and not isinstance(proposal_path_value, str):
        return _rejected("malformed_handle")

    question_path = Path(question_path_value)
    if question_path.name != f"{content_hash_value}.json":
        # Not the producer's content-addressed filename for this hash — the
        # handle does not name a producer-written artifact identity.
        return _rejected("handle_address_mismatch")
    if proposal_path_value is not None and _paths_name_same_file(
        question_path, proposal_path_value
    ):
        return _rejected("path_collision")

    if not question_path.is_file():
        return _rejected("missing_artifact")
    try:
        payload = json.loads(question_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _rejected("malformed_artifact")

    recomputed = _recompute_content_hash(payload)
    if recomputed is None:
        return _rejected("malformed_artifact")
    if recomputed != content_hash_value:
        # The file at the named path is not the artifact the handle was issued
        # for — stale, replaced, or tampered. Fail closed.
        return _rejected("content_hash_mismatch")

    return AskHandleResolution(
        resolved=True,
        reason="resolved",
        candidate=ResolvedAskCandidate(
            terminal=_QUESTION_NEEDED,
            question_path=str(question_path),
            proposal_path=proposal_path_value,
        ),
    )


def acquire_served_ask_from_handle(
    config: Any,
    *,
    handle: Any,
    fallback_surface: str,
) -> AskAcquisitionDecision:
    """Resolve a carried handle and pass the candidate through the existing stack.

    The lawful provider boundary in one call: an unresolved handle (gate dark,
    structural failure, missing/stale artifact) yields the standing fallback
    decision from ``acquire_served_ask_candidate`` with no candidate — the
    fallback surface is returned unchanged. A resolved candidate is handed to the
    existing acquisition seam, which delegates all Q1-D artifact policy to
    ``evaluate_served_ask``. No serving rule is re-implemented here.
    """
    resolution = resolve_served_ask_handle(config, handle)
    return acquire_served_ask_candidate(
        config,
        fallback_surface=fallback_surface,
        contemplation_result=resolution.candidate,
    )


__all__ = [
    "AskArtifactHandle",
    "AskHandleResolution",
    "ResolvedAskCandidate",
    "acquire_served_ask_from_handle",
    "resolve_served_ask_handle",
]
