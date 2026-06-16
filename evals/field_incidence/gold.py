"""Independent gold + a fair, same-grammar symbolic control for the incidence probe.

Both are EXACT integer/rational arithmetic and share NO code with the field reader
(no ``algebra`` import). Two structurally-distinct rational methods are used so the
ablation is honest:

- ``gold_consistency`` — the ground truth, via the cross-product collinearity test
  ``(B-A) x (P-A) == 0``.
- ``control_consistency`` — the FAIR same-grammar control a symbolic reader would run,
  via a different rational method (the line-equation residual), to show that even two
  independent *arithmetic* readers agree — so any field "win" must be over a strawman,
  not a fair control.

Coordinates are integers, so every check is exact (no tolerance).
"""

from __future__ import annotations


def _collinear_crossproduct(p, a, b) -> bool:
    # (B-A) x (P-A) == 0  (z-component of the 2-D cross product)
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) == 0


def _collinear_line_equation(p, a, b) -> bool:
    # Line through A,B: (y-a_y)*(b_x-a_x) - (x-a_x)*(b_y-a_y) == 0, evaluated at P.
    # Algebraically equal to the cross product, but written independently.
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (p[1] - a[1]) * dx - (p[0] - a[0]) * dy == 0


def _decide(points: dict, incidences: list, collinear) -> str:
    for p_name, a_name, b_name in incidences:
        if not collinear(points[p_name], points[a_name], points[b_name]):
            return "inconsistent"
    return "consistent"


def gold_consistency(points: dict, incidences: list) -> str:
    """Ground truth (cross-product method)."""
    return _decide(points, incidences, _collinear_crossproduct)


def control_consistency(points: dict, incidences: list) -> str:
    """The fair same-grammar symbolic control (line-equation method)."""
    return _decide(points, incidences, _collinear_line_equation)
