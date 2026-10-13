"""The compiler. Usage: python -m backplane <validate|plan|apply|report> [--model PATH]

validate  LinkML validation plus reference checks. Changes nothing.
plan      What would change in the tenant to match the model. Changes nothing.
apply     Make the changes in the plan, then re-plan to confirm nothing is left.
report    Conformance report, including deal rooms people have opened.

Runs as the platform owner: `az` and `m365` use the owner's own signed-in sessions.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import entra, fabric, report, semantic, termstore
from .model import DEFAULT_MODEL, linkml_validate, load, reference_errors

TARGETS = (("groups", entra), ("fabric", fabric), ("term store", termstore), ("data", semantic))


def validate(path: pathlib.Path) -> bool:
    ok, output = linkml_validate(path)
    print(f"LinkML validation: {'passed' if ok else 'FAILED'}")
    if not ok:
        print(output)
    errors = reference_errors(load(path))
    print(f"Reference check: {'passed' if not errors else 'FAILED'}")
    for error in errors:
        print(f"  - {error}")
    return ok and not errors


def main() -> int:
    parser = argparse.ArgumentParser(prog="backplane")
    parser.add_argument("command", choices=["validate", "plan", "apply", "report"])
    parser.add_argument("--model", type=pathlib.Path, default=DEFAULT_MODEL)
    parser.add_argument("--json", action="store_true", help="report as JSON")
    args = parser.parse_args()

    if not validate(args.model):
        return 1
    if args.command == "validate":
        return 0
    model = load(args.model)

    if args.command == "report":
        result = report.build(model)
        print(json.dumps(result, indent=2) if args.json else report.render(result))
        return 0 if result["conformant"] else 2

    pending = 0
    for name, target in TARGETS:
        steps = [s for s in target.plan(model) if s["op"] != "drift"]
        drift = [s for s in target.plan(model) if s["op"] == "drift"]
        print(f"\n{name}: {len(steps)} change(s)")
        for step in steps:
            detail = (step.get("term") or step.get("table") or step.get("set") or step.get("group")
                      or step.get("item_name") or step.get("tag") or step.get("name") or step.get("domain") or "")
            print(f"  {step['op']:<14} {detail}")
        for step in drift:
            print(f"  drift          {step['term']}: {step['detail']} (fix by hand or in the model)")
        if args.command == "apply" and steps:
            applied = target.apply(model, steps) if target is semantic else target.apply(steps)
            for line in applied:
                print(f"  done: {line}")
            remaining = [s for s in target.plan(model) if s["op"] != "drift"]
            print(f"  re-plan: {'nothing left to do' if not remaining else f'{len(remaining)} change(s) still pending'}")
            pending += len(remaining)
        elif args.command == "plan":
            pending += len(steps)
    return 0 if args.command == "plan" or pending == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
