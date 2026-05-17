"""Deterministic English morphology for the realizer.

Handles inflection of predicates for tense, aspect, and negation.
This is intentionally rule-based and limited to the seed vocabulary.
Irregular forms are listed explicitly; regular forms follow English rules.
"""
from __future__ import annotations


# Genuinely irregular English verbs (the previous tables held only
# regular forms that the suffix rules already produce correctly).
# Listed as 3rd-person singular present → (past, past_participle).
# Coverage: ~100 common English irregulars including every verb that
# the seed packs and Phase 5 OOD lanes use whose past form does not
# follow the regular -ed rule.  Adding a verb here is the cheap fix
# for english_fluency_ood gaps.md G1.
_IRREGULAR_FORMS: dict[str, tuple[str, str]] = {
    # be / have / do
    "is": ("was", "been"),
    "are": ("were", "been"),
    "has": ("had", "had"),
    "does": ("did", "done"),
    # mental / cognitive
    "thinks": ("thought", "thought"),
    "knows": ("knew", "known"),
    "sees": ("saw", "seen"),
    "hears": ("heard", "heard"),
    "feels": ("felt", "felt"),
    "finds": ("found", "found"),
    "loses": ("lost", "lost"),
    "means": ("meant", "meant"),
    "reads": ("read", "read"),
    "tells": ("told", "told"),
    "says": ("said", "said"),
    "thinks": ("thought", "thought"),
    # motion
    "goes": ("went", "gone"),
    "comes": ("came", "come"),
    "runs": ("ran", "run"),
    "stands": ("stood", "stood"),
    "sits": ("sat", "sat"),
    "lies": ("lay", "lain"),
    "flies": ("flew", "flown"),
    "swims": ("swam", "swum"),
    "rides": ("rode", "ridden"),
    "drives": ("drove", "driven"),
    "rises": ("rose", "risen"),
    "falls": ("fell", "fallen"),
    # giving / taking / holding
    "gives": ("gave", "given"),
    "takes": ("took", "taken"),
    "brings": ("brought", "brought"),
    "buys": ("bought", "bought"),
    "sells": ("sold", "sold"),
    "holds": ("held", "held"),
    "keeps": ("kept", "kept"),
    "leaves": ("left", "left"),
    "lends": ("lent", "lent"),
    "sends": ("sent", "sent"),
    "spends": ("spent", "spent"),
    "puts": ("put", "put"),
    "sets": ("set", "set"),
    "lets": ("let", "let"),
    # building / making / breaking
    "makes": ("made", "made"),
    "builds": ("built", "built"),
    "breaks": ("broke", "broken"),
    "tears": ("tore", "torn"),
    "burns": ("burned", "burned"),
    "shines": ("shone", "shone"),
    "draws": ("drew", "drawn"),
    "writes": ("wrote", "written"),
    "speaks": ("spoke", "spoken"),
    "wins": ("won", "won"),
    "loses": ("lost", "lost"),
    # binding / connecting
    "binds": ("bound", "bound"),
    "winds": ("wound", "wound"),
    "weaves": ("wove", "woven"),
    "flies": ("flew", "flown"),
    "spins": ("spun", "spun"),
    "sticks": ("stuck", "stuck"),
    "swears": ("swore", "sworn"),
    # giving form / shape
    "becomes": ("became", "become"),
    "grows": ("grew", "grown"),
    "blows": ("blew", "blown"),
    "throws": ("threw", "thrown"),
    "shakes": ("shook", "shaken"),
    "wakes": ("woke", "woken"),
    # eating / drinking / cooking
    "eats": ("ate", "eaten"),
    "drinks": ("drank", "drunk"),
    "feeds": ("fed", "fed"),
    "bites": ("bit", "bitten"),
    "freezes": ("froze", "frozen"),
    # cutting / striking
    "cuts": ("cut", "cut"),
    "hits": ("hit", "hit"),
    "shoots": ("shot", "shot"),
    "splits": ("split", "split"),
    "strikes": ("struck", "struck"),
    "fights": ("fought", "fought"),
    "wears": ("wore", "worn"),
    # sleeping / rising / etc
    "sleeps": ("slept", "slept"),
    "wakes": ("woke", "woken"),
    "rises": ("rose", "risen"),
    # finding / hiding
    "hides": ("hid", "hidden"),
    "seeks": ("sought", "sought"),
    "catches": ("caught", "caught"),
    "teaches": ("taught", "taught"),
    "thinks": ("thought", "thought"),
    "brings": ("brought", "brought"),
    # less common / archaic
    "begins": ("began", "begun"),
    "deals": ("dealt", "dealt"),
    "leads": ("led", "led"),
    "meets": ("met", "met"),
    "sits": ("sat", "sat"),
    "swears": ("swore", "sworn"),
    "shoots": ("shot", "shot"),
    "casts": ("cast", "cast"),
    "costs": ("cost", "cost"),
    "hurts": ("hurt", "hurt"),
    "lets": ("let", "let"),
    "quits": ("quit", "quit"),
    "shuts": ("shut", "shut"),
}

# Legacy compatibility — historic call sites use these names.  All
# regular-verb entries here match the suffix-rule output, so removing
# them is purely cosmetic; new irregulars live in `_IRREGULAR_FORMS`.
_IRREGULAR_PAST: dict[str, str] = {v: forms[0] for v, forms in _IRREGULAR_FORMS.items()}

_IRREGULAR_PARTICIPLE: dict[str, str] = {
    # Present-participle (-ing) is almost always regular.  Only handle
    # the truly weird cases (lie→lying handled by the suffix rule;
    # be→being is the one English present-participle that needs a
    # special entry, but `is` doesn't normally surface as a content
    # predicate in our realizer pipeline).
}

_IRREGULAR_PAST_PARTICIPLE: dict[str, str] = {v: forms[1] for v, forms in _IRREGULAR_FORMS.items()}


# Short -ies verbs whose base is -ie (not -y).  English's "ies → y"
# rule (cries→cry, flies→fly) breaks for these short stems where the
# original lemma keeps the -ie (dies→die, lies→lie, ties→tie).
_IES_KEEP_IE: frozenset[str] = frozenset({"dies", "lies", "ties", "vies", "pies", "hies"})


def _base_form(verb_3sg: str) -> str:
    if verb_3sg in _IES_KEEP_IE:
        return verb_3sg[:-1]
    if verb_3sg.endswith("ies"):
        return verb_3sg[:-3] + "y"
    if verb_3sg.endswith("es"):
        return verb_3sg[:-2] if verb_3sg[:-2].endswith(("s", "sh", "ch", "x", "z", "o")) else verb_3sg[:-1]
    if verb_3sg.endswith("s"):
        return verb_3sg[:-1]
    return verb_3sg


def past_tense(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[verb_3sg]
    base = _base_form(verb_3sg)
    if base.endswith("e"):
        return base + "d"                  # make → made? no — make is irregular; bake → baked
    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ied"            # cry → cried
    if _is_cvc_ending(base):
        return base + base[-1] + "ed"       # stop → stopped, plan → planned
    return base + "ed"


_VOWELS = frozenset("aeiou")


def _is_cvc_ending(base: str) -> bool:
    """True if `base` ends in consonant-vowel-consonant (excluding w/x/y),
    the trigger pattern for doubling the final consonant before -ing /
    -ed in English."""
    if len(base) < 3:
        return False
    c1, v, c2 = base[-3], base[-2], base[-1]
    if c2 in {"w", "x", "y"}:
        return False
    return (c1 not in _VOWELS) and (v in _VOWELS) and (c2 not in _VOWELS)


def present_participle(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PARTICIPLE:
        return _IRREGULAR_PARTICIPLE[verb_3sg]
    base = _base_form(verb_3sg)
    if base.endswith("ie"):
        return base[:-2] + "ying"          # die → dying, lie → lying
    if base.endswith("e") and not base.endswith("ee"):
        return base[:-1] + "ing"            # make → making
    if _is_cvc_ending(base):
        return base + base[-1] + "ing"      # run → running, swim → swimming
    return base + "ing"


def past_participle(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PAST_PARTICIPLE:
        return _IRREGULAR_PAST_PARTICIPLE[verb_3sg]
    return past_tense(verb_3sg)


def base_form(verb_3sg: str) -> str:
    return _base_form(verb_3sg)
