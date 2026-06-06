"""Relational-predicate gold lane — binary-relation prose with independent gold.

The gold ``(predicate, subject, object)`` triples in ``v1/cases.jsonl`` are authored
by reading English semantics, INDEPENDENTLY of ``generate/meaning_graph/relational.py``
(INV-25 independent gold / INV-27 reader-disjoint): the reader never produced them.
``v1/refusals.jsonl`` holds adversarial inputs that must REFUSE (the #596 fabrication
class) — consumed by the dedicated falsification test, not the coverage metric.
"""
