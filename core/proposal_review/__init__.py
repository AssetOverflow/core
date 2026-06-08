"""Read-only proposal review reporter (RPT) — surfaces comprehension-failure proposals for review.

Observes ``teaching/proposals/comprehension_failures/*.json`` (emitted by the contemplation pass,
N5), validates them, and reports pending review obligations. It is **read-only**: it does not
advance the teaching loop, ratify, mount, modify readers, or affect serving. It is **not** an
``idle_tick`` (``ChatRuntime.idle_tick`` remains the only one) and **not** L10 — it is the review
surface that keeps proposal artifacts from becoming inert files. A future PR may call this reporter
from ``idle_tick`` as a read-only sub-pass.
"""

from __future__ import annotations

from core.proposal_review.model import MalformedArtifact, PendingProposal
from core.proposal_review.scan import DEFAULT_SINK, default_sink, scan

__all__ = ["DEFAULT_SINK", "MalformedArtifact", "PendingProposal", "default_sink", "scan"]
