"""ADR-0199 §2.2 — the cross-domain learning-arena interfaces.

A subject becomes a learning arena by supplying four domain-specific pieces
(``DomainSolver``, a gold anchor set, capability classes, a Tier-2 verifier)
and reusing the shared engine (:mod:`core.learning_arena.engine`) and the
shared reliability gate (:mod:`core.reliability_gate`) unchanged.

These protocols are structural (PEP 544). A domain provides concrete classes;
the engine never imports a concrete domain. The first instance is GSM8K math
(``evals/gsm8k_math/practice/v1/runner.py``), re-expressed against this
contract with no behavior change.

Note on the ADR's illustrative signatures: the ADR sketched
``is_correct(attempt, problem_id)``. We pass the whole ``DomainProblem`` (which
carries its ``problem_id``) so a tether can reach class/payload without a
separate lookup table — strictly more general, same contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DomainProblem(Protocol):
    """One problem in a practice arena.

    ``class_name`` is the capability axis this problem exercises (the ledger
    key); it is resolved up front by a domain adapter that may consult gold.
    ``payload`` is opaque to the engine — only the domain's solver/tether read
    it.
    """

    problem_id: str
    class_name: str
    payload: Any


@runtime_checkable
class Attempt(Protocol):
    """The result of a single attempt.

    ``committed is False`` means the engine refused (always safe; excluded
    from reliability's denominator per ADR-0175 §4). ``derivations`` are the
    ≥2 structurally-distinct paths a Tier-2 verifier inspects; ``trace_sha256``
    is replayable provenance carrying no raw content beyond hashes.
    """

    committed: bool
    answer: Any
    reason: str
    case_id: str
    derivations: tuple[Any, ...]
    trace_sha256: str


@runtime_checkable
class DomainSolver(Protocol):
    """Attempts a grounded derivation over the subject's operations.

    This is where intelligence lives (ADR-0175 Pivot-2). The engine calls
    :meth:`attempt` once per problem and never inspects how the answer was
    reached beyond the :class:`Attempt` fields.
    """

    domain_id: str

    def attempt(self, problem: DomainProblem) -> Attempt: ...


@runtime_checkable
class GoldTether(Protocol):
    """The Tier-1 truth anchor for a subject.

    ADR-0199 mandate 2: the truth ``is_correct`` consults must come from a
    source **independent of the solver's derivation** (proof obligation L-2).
    For dataset domains the gold is the dataset's own answer; for software it
    is execution; etc.
    """

    domain_id: str

    def is_correct(self, attempt: Attempt, problem: DomainProblem) -> bool: ...

    def gold_answer(self, problem: DomainProblem) -> Any: ...


@dataclass(frozen=True, slots=True)
class Problem:
    """Concrete :class:`DomainProblem` a domain adapter can build directly."""

    problem_id: str
    class_name: str
    payload: Any = None


@dataclass(frozen=True, slots=True)
class BaseAttempt:
    """Concrete :class:`Attempt` for domains that need no extra fields."""

    committed: bool
    answer: Any = None
    reason: str = ""
    case_id: str = ""
    derivations: tuple[Any, ...] = field(default_factory=tuple)
    trace_sha256: str = ""
