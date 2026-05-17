"""``core formation`` CLI handlers.

The CLI exposes seven verbs (``new``, ``mine``, ``smelt``, ``forge``,
``compose``, ``run``, ``promote``) plus the convenience verb ``autorun``
and ``status``.  The internal ``compile`` step is not exposed — it runs
inside ``run``.

Stages 1, 2, 8 (mine/smelt/llm), and 9 (full autorun chaining) are
scaffolded here as advisory helpers that call the underlying modules where
they exist, and report ``not implemented`` for the front-half adapters that
are not online yet.
"""

from __future__ import annotations

import argparse
import json

from formation.cache import default_cache


def _stub_spec_yaml(subject_id: str) -> str:
    """Return a hand-edited starter Subject Spec YAML."""
    return (
        "# Subject Spec — scaffolded by `core formation new`.\n"
        "# Edit before running `core formation mine`.\n"
        f"subject_id: {subject_id}\n"
        f"title: \"\"\n"
        "target_depth: introductory\n"
        "requires_courses: []\n"
        "anti_requisites: []\n"
        "identity_axis_constraints: []\n"
    )


def cmd_formation_new(args: argparse.Namespace) -> int:
    cache = default_cache()
    spec_path = cache.root / args.subject_id / "spec.yaml"
    if spec_path.exists() and not args.force:
        print(
            f"refusing to overwrite {spec_path}; pass --force to scaffold again",
            file=__import__("sys").stderr,
        )
        return 2
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(_stub_spec_yaml(args.subject_id), encoding="utf-8")
    if args.json:
        print(json.dumps({
            "subject_id": args.subject_id,
            "spec_path": str(spec_path),
        }))
    else:
        print(f"scaffolded {spec_path}")
    return 0


def cmd_formation_status(args: argparse.Namespace) -> int:
    cache = default_cache()
    subject_dir = cache.root / args.subject_id
    info: dict[str, object] = {"subject_id": args.subject_id, "stages": {}}
    if not subject_dir.exists():
        info["error"] = "no cache entries; run `core formation new` first"
    else:
        stages: dict[str, list[str]] = {}
        for child in sorted(subject_dir.iterdir()):
            if child.is_dir():
                stages[child.name] = sorted(p.name for p in child.iterdir())
        info["stages"] = stages
    if args.json:
        print(json.dumps(info, sort_keys=True))
    else:
        print(f"subject: {info['subject_id']}")
        for stage, files in (info.get("stages") or {}).items():
            print(f"  {stage}: {len(files)} artifact(s)")
        if "error" in info:
            print(info["error"])
    return 0


def _not_implemented(verb: str) -> int:
    print(
        f"`core formation {verb}` is scaffolded but not wired to live adapters yet. "
        f"See docs/formation_pipeline_plan.md §3.",
    )
    return 0


def cmd_formation_mine(args: argparse.Namespace) -> int:
    return _not_implemented("mine")


def cmd_formation_smelt(args: argparse.Namespace) -> int:
    return _not_implemented("smelt")


def cmd_formation_forge(args: argparse.Namespace) -> int:
    return _not_implemented("forge")


def cmd_formation_compose(args: argparse.Namespace) -> int:
    return _not_implemented("compose")


def cmd_formation_run(args: argparse.Namespace) -> int:
    return _not_implemented("run")


def cmd_formation_promote(args: argparse.Namespace) -> int:
    return _not_implemented("promote")


def cmd_formation_autorun(args: argparse.Namespace) -> int:
    return _not_implemented("autorun")


def register(subparsers: argparse._SubParsersAction) -> None:
    """Attach the ``core formation`` subcommand tree to a top-level parser."""
    formation = subparsers.add_parser(
        "formation",
        help="content-addressed, trust-bounded data foundry pipeline",
        description="content-addressed, trust-bounded data foundry pipeline",
    )
    sub = formation.add_subparsers(
        dest="formation_command", metavar="formation-command", required=True,
    )

    new = sub.add_parser("new", help="scaffold a Subject Spec stub")
    new.add_argument("subject_id")
    new.add_argument("--force", action="store_true",
                     help="overwrite an existing spec.yaml")
    new.add_argument("--json", action="store_true")
    new.set_defaults(func=cmd_formation_new)

    status = sub.add_parser("status", help="show cache state per stage")
    status.add_argument("subject_id")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_formation_status)

    for verb, helptext, fn in [
        ("mine", "Stage 1: fan out source adapters", cmd_formation_mine),
        ("smelt", "Stage 2: extract candidates from ore", cmd_formation_smelt),
        ("forge", "Stage 3: validate candidates (trust boundary)", cmd_formation_forge),
        ("compose", "Stage 4: emit deterministic Course YAML", cmd_formation_compose),
        ("run", "Stages 5-7: compile, run, ratify", cmd_formation_run),
        ("promote", "Stages 8-9: bridge SPECULATIVE -> COHERENT", cmd_formation_promote),
        ("autorun", "Stages 1-7 (pauses before promote)", cmd_formation_autorun),
    ]:
        parser = sub.add_parser(verb, help=helptext)
        parser.add_argument("target", help="subject_id (or report_sha for promote)")
        parser.add_argument("--json", action="store_true")
        parser.set_defaults(func=fn)
