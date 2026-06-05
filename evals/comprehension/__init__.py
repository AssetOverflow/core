"""Comprehension scoring lanes — the engine reader under test, scored end-to-end
against the staged independent-gold lanes (Phase 2a, COMPREHEND).

Unlike the ``evals/<domain>`` gold-only lanes (which verify oracle/gold integrity),
these runners drive the general comprehension reader over the lane PROSE and score
its output through the lane's INDEPENDENT oracle. wrong=0 is the floor: the reader
must refuse rather than emit a structure that yields a wrong answer.
"""
