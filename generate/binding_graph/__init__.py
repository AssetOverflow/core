"""ADR-0132/0133/0134/0135 — Semantic-Symbolic Binding Graph.

**The universal problem-structure interlingua** (see
``docs/analysis/universal-structure-and-field-symbol-coherence-gate-2026-06-04.md``).
This is the one typed, field-agnostic structure that every reader (math,
deductive logic, future modalities) compiles *into* and every solver/verifier
operates *on*: a unit-aware, provenance-carrying (:class:`SourceSpanLink`),
acyclic, refusal-first DAG. It is the corpus callosum where holistic
comprehension commits to an inspectable, checkable form and hands off to
analysis — not the master and not a mere servant.

**Neutrality doctrine (enforced by INV-26).** The interlingua must depend on
neither the field engine, nor any one domain's reader, nor the eval/runtime: the
core model imports nothing from ``field`` / ``algebra`` / ``evals`` / ``vault`` /
``chat``, and only the designated *bridge* modules (:mod:`.adapter`,
:mod:`.question_target`) may import a domain reader. Servants propose into the
structure and check it; they never become the structure. Keeping the meeting
point neutral is what lets two independent decodings (geometric field and
symbolic ROBDD) agree *here* — the coherence that makes a committed answer
``wrong == 0``-safe.

Phase 1 (ADR-0132): pure data layer (frozen dataclasses, deterministic
allocator, refusal-first construction; no I/O, no parser, no algebra,
no ``Polynomial`` coupling — symbolic expressions held as canonical
strings only).

Phase 2 (ADR-0133): pure-function adapter
:func:`bind_math_problem_graph` translating
:class:`generate.math_problem_graph.MathProblemGraph` (ADR-0115) into a
:class:`SemanticSymbolicBindingGraph`. Still no runtime wiring.

Phase 3 (ADR-0134): unit-aware admissibility on equations.

Phase 4 (ADR-0135): question-target binding refinement —
:class:`BoundUnknown` now carries ``state_index`` + ``question_form``
fields resolved by :func:`bound_unknown_from_math_problem_graph`.

Phase 5 (bounded-grammar / B3 integration) deferred.
"""

from __future__ import annotations

from .acyclicity import CIRCULAR_DEPENDENCY, find_cycle
from .adapter import (
    INTRODUCED_BY,
    REFUSED_UNIT_PROOF,
    SYNTHETIC_SOURCE_ID,
    AdapterError,
    bind_math_problem_graph,
)
from .admissibility import (
    ADMISSIBILITY_REASONS,
    AdmissibilityError,
    UnitProof,
    check_admissibility,
)
from .allocation import allocate_symbols
from .model import (
    ADMISSIBILITY_STATUSES,
    QUESTION_FORMS,
    SEMANTIC_ROLES,
    STATE_INDEX_LABELS,
    BindingGraphError,
    BoundConstraint,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    Operation,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    StateIndex,
    SymbolBinding,
)
from .question_target import (
    QUESTION_TARGET_REASONS,
    QuestionTargetError,
    bound_unknown_from_math_problem_graph,
    infer_question_form,
    resolve_state_index,
)
from .units import (
    BASE_DIMENSIONS,
    DIMENSIONLESS,
    UnitAlgebraError,
    UnitVector,
    parse_unit,
    unit_inverse,
    unit_product,
    unit_quotient,
    units_equal,
)

__all__ = (
    "ADMISSIBILITY_REASONS",
    "ADMISSIBILITY_STATUSES",
    "CIRCULAR_DEPENDENCY",
    "BASE_DIMENSIONS",
    "DIMENSIONLESS",
    "INTRODUCED_BY",
    "QUESTION_FORMS",
    "QUESTION_TARGET_REASONS",
    "REFUSED_UNIT_PROOF",
    "SEMANTIC_ROLES",
    "STATE_INDEX_LABELS",
    "SYNTHETIC_SOURCE_ID",
    "AdapterError",
    "AdmissibilityError",
    "BindingGraphError",
    "BoundConstraint",
    "BoundEquation",
    "BoundFact",
    "BoundUnknown",
    "Operation",
    "QuestionTargetError",
    "SemanticSymbolicBindingGraph",
    "SourceSpanLink",
    "StateIndex",
    "SymbolBinding",
    "UnitAlgebraError",
    "UnitProof",
    "UnitVector",
    "allocate_symbols",
    "bind_math_problem_graph",
    "bound_unknown_from_math_problem_graph",
    "check_admissibility",
    "find_cycle",
    "infer_question_form",
    "parse_unit",
    "resolve_state_index",
    "unit_inverse",
    "unit_product",
    "unit_quotient",
    "units_equal",
)
