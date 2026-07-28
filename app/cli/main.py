"""Banana Lab 2.0 command line.

    bananalab status [issue]     production state of every issue, read from disk
    bananalab validate           schemas, panel scripts, manifest, hygiene
    bananalab schemas            list available schemas
    bananalab comfy              probe the local ComfyUI and report capability
    bananalab dashboard [--out]  write the static HTML production dashboard

The CLI is a view. It reads the filesystem and reports. It does not move work
forward, and it cannot approve anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core import paths

TICK = "[x]"
CROSS = "[ ]"
PARTIAL = "[~]"

MARKS = {"complete": TICK, "partial": PARTIAL, "not_started": CROSS}


def cmd_status(args: argparse.Namespace) -> int:
    from app.services.issue_status import all_issues, load_issue

    if args.issue:
        target = paths.ISSUES / args.issue
        if not target.is_dir():
            print(f"no such issue: {args.issue}", file=sys.stderr)
            return 1
        issues = [load_issue(target)]
    else:
        issues = all_issues()

    if not issues:
        print("no issues found under issues/")
        return 0

    for issue in issues:
        print(f"\n{issue.issue_id}: {issue.title}")
        print("-" * (len(issue.issue_id) + len(issue.title) + 2))
        for state in issue.stages:
            mark = MARKS[state.status]
            gate = ""
            if state.stage.human_gate:
                gate = " (approved)" if state.approved else " (awaiting approval)"
            print(f"  {mark} {state.stage.title}{gate}")
            if args.verbose and state.missing:
                for item in state.missing:
                    print(f"        missing: {item}")

        print(f"\n  {issue.completed_count}/{len(issue.stages)} stages complete")
        current = issue.current_stage
        if current:
            print(f"  next: {current.stage.title} - {current.stage.purpose}")
            for reason in issue.blockers():
                print(f"  blocked: {reason}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from app.services import validation

    failures = 0

    print("== schema validation ==")
    results = validation.validate_documents()
    if not results:
        print("  no bound documents found")
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"  [{status}] {result.document} ({result.schema_id})")
        for finding in result.errors:
            print(f"      {finding}")
        if args.verbose:
            for finding in result.warnings:
                print(f"      {finding}")
        failures += len(result.errors)

    print("\n== panel scripts ==")
    scripts = sorted(paths.ISSUES.glob("*/03_script/panel-script.yaml"))
    if not scripts:
        print("  none found")
    for script in scripts:
        result = validation.validate_panel_script(script)
        status = "OK" if result.ok else "FAIL"
        rel = script.relative_to(paths.REPO_ROOT).as_posix()
        print(f"  [{status}] {rel}")
        for finding in result.errors:
            print(f"      {finding}")
        if args.verbose:
            for finding in result.warnings:
                print(f"      {finding}")
        failures += len(result.errors)

    print("\n== comic format standard ==")
    issue_dirs = [
        d for d in sorted(paths.ISSUES.iterdir())
        if d.is_dir() and d.name != "templates"
    ] if paths.ISSUES.is_dir() else []
    if not issue_dirs:
        print("  no issues found")
    for issue_dir in issue_dirs:
        result = validation.validate_issue_format(issue_dir)
        status = "OK" if result.ok else "FAIL"
        print(f"  [{status}] {issue_dir.name}")
        for finding in result.errors:
            print(f"      {finding}")
        for finding in result.warnings:
            print(f"      {finding}")
        failures += len(result.errors)

    print("\n== imported source integrity ==")
    checked, problems = validation.validate_manifest()
    print(f"  {checked} files re-hashed against the manifest")
    for problem in problems:
        print(f"      {problem}")
    failures += len(problems)

    print("\n== repository hygiene ==")
    report = validation.validate_hygiene()
    if report.ok:
        print("  clean")
    for rel, size in report.large_files:
        print(f"      LARGE  {rel} ({size / 1e6:.1f} MB)")
    for rel in report.suspicious_paths:
        print(f"      SECRET-LIKE  {rel}")
    for rel, detail in report.absolute_paths_in_config:
        print(f"      ABSOLUTE PATH  {rel}: {detail}")
    failures += len(report.large_files) + len(report.suspicious_paths)
    failures += len(report.absolute_paths_in_config)

    print(f"\n{'PASS' if failures == 0 else 'FAIL'} - {failures} problem(s)")
    return 0 if failures == 0 else 1


def cmd_schemas(_: argparse.Namespace) -> int:
    from app.services.validation import registry

    reg = registry()
    for schema_id in reg.ids():
        schema = reg[schema_id]
        required = sum(1 for rule in schema.fields.values() if rule.get("required"))
        print(f"  {schema_id:12s} v{schema.version}  {len(schema.fields):3d} fields "
              f"({required} required)  - {schema.title}")
    return 0


def cmd_comfy(args: argparse.Namespace) -> int:
    from app.adapters.comfyui import probe

    report = probe(args.host)
    if not report.reachable:
        print(f"ComfyUI not reachable at {args.host}: {report.error}")
        return 1

    print(f"ComfyUI {report.version} at {args.host}")
    for device in report.devices:
        print(f"  device: {device}")
    print(f"  node types: {report.node_count}")
    print(f"  checkpoints: {', '.join(report.checkpoints) or 'none'}")
    print(f"  loras: {', '.join(report.loras) or 'NONE - no style model installed'}")
    print(f"  controlnets: {', '.join(report.controlnets) or 'none'}")
    print(f"  ip-adapters: {', '.join(report.ipadapters) or 'none'}")
    print("  capabilities:")
    for name, present in sorted(report.capabilities.items()):
        print(f"    {'yes' if present else 'no ':3s}  {name}")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    from app.ui.dashboard import write_dashboard

    out = Path(args.out) if args.out else paths.REPO_ROOT / "workspace" / "dashboard.html"
    path = write_dashboard(out)
    print(f"wrote {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bananalab", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="show warnings and detail")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="production state of every issue")
    p_status.add_argument("issue", nargs="?", help="issue directory name")
    p_status.set_defaults(func=cmd_status)

    p_validate = sub.add_parser("validate", help="run every validation gate")
    p_validate.set_defaults(func=cmd_validate)

    p_schemas = sub.add_parser("schemas", help="list schemas")
    p_schemas.set_defaults(func=cmd_schemas)

    p_comfy = sub.add_parser("comfy", help="probe the local ComfyUI")
    p_comfy.add_argument("--host", default="http://127.0.0.1:8188")
    p_comfy.set_defaults(func=cmd_comfy)

    p_dash = sub.add_parser("dashboard", help="write the static HTML dashboard")
    p_dash.add_argument("--out", help="output path")
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
