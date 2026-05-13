"""
core — Versor Engine top-level package.

Cl(4,1) Conformal Geometric Algebra field system.

Two primitives:
    versor_apply(V, F) = V * F * reverse(V)   — the only field transition
    cga_inner(X, Y)   = -d^2 / 2              — the only distance metric

Core invariant: ||F * reverse(F) - 1||_F < 1e-6 at all times.

Layer map:
    algebra/    Cl(4,1) multivector math, versor ops, CGA, holonomy
    ingest/     Single injection gate — the only normalization site
    field/      FieldState dataclass and propagation loop
    vocab/      Word-to-versor manifold, edge rotors
    vault/      Exact CGA inner product memory store
    persona/    Persona as CGA motor (screw motion)
    generate/   Token streaming loop
    session/    Session binding: field + vault + vocab + persona
    physics/    Field physics operators (salience, attention, drive, etc.)
"""
