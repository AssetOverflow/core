from .cl41 import geometric_product, reverse, grade_project, scalar_part, norm_squared, basis_vector
from .versor import versor_apply, normalize_to_versor, versor_condition
from .cga import (
    EMBED_EXACT_MAX,
    cga_inner,
    outer_product,
    is_null,
    null_project,
    embed_point,
    read_scalar_e1,
)
from .holonomy import holonomy_encode, holonomy_similarity
from .rotor import word_transition_rotor
