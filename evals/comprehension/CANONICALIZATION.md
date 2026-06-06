# Noun-phrase canonicalization contract (comprehension lanes)

The comprehension reader (`generate/meaning_graph/reader.py`) and the staged gold
lanes (`evals/{set_membership,syllogism,total_ordering}/v1`) share **one** rule for
turning a surface noun phrase into a term/entity id. This contract is what makes
multi-word noun phrases `wrong=0`-safe: the reader and the gold canonicalize the
*same* way, so a committed answer can only match gold or refuse — it can never
silently mean something different.

## The rule

A noun-phrase slot (the tokens a template isolates between its function words)
becomes an id by:

1. lowercasing every token;
2. for a **plural class slot** (the subject/predicate of `all/no/some … are …`),
   singularizing the **head** (final) token — `objects → object`, `people → person`;
   item and individual slots are **not** singularized;
3. joining the resulting tokens with `_`.

| surface | role | canonical id |
|---|---|---|
| `metal objects` | class | `metal_object` |
| `soft objects` | class | `soft_object` |
| `North station` | item | `north_station` |
| `Level one` | item | `level_one` |
| `Red rank` | item | `red_rank` |
| `red car` | individual | `red_car` |
| `squares` | class | `square` |

## Why join, not head-word-only

An earlier (implicit) gold used head-word-only in places (`metal objects → metal`,
`North station → north`). That is **information-destroying** and an active
`wrong=0` hazard: `metal objects` and `metal tools` both collapse to `metal`,
creating a *false identity* the oracle would then reason over. Joining preserves
the distinction, so distinct phrases stay distinct ids.

## Refusal cases (still parse-or-refuse)

The reader refuses rather than guess when:

- a multi-token slot contains a **reserved function word** (article, comparator,
  quantifier, `is/are/than/with/not/the/from/to/order/in/of/on/at/by/and/or`) —
  e.g. `Compare beta with beta in the same order` → the right slot
  `beta in the same order` leaks `in/the/order`, so refuse (never
  `beta_in_the_same_order`). A **single-token** slot is exempt: a literal item
  named `A` is content even though `a` is also the article.
- a plural class head is not a recognizable plural (e.g. the adjectival predicate
  `trained` in `All pilots are trained`) — cannot singularize → refuse.
- the two class NPs in `Are all <Xs> <Ys>?` are adjacent with no separating
  function word and either is multi-word — the boundary is unknown → refuse.

## Changing this contract

This contract is load-bearing for `wrong=0`. If it changes, the reader **and**
every affected gold case must change together in the same PR, and the
`tests/test_comprehension_wrong_zero_property.py` round-trip (which renders prose
from canonical structures and checks the reader reproduces the oracle's verdict)
must stay green.
