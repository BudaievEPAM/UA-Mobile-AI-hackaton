"""Command-line entry point for the iOS -> KMP/RIBs harness.

    python -m harness run      --input <ios-repo> [--output <dir>] [--agent-cmd "claude -p"]
    python -m harness analyze  --input <ios-repo> [--output <dir>]
    python -m harness plan     --input <ios-repo> [--output <dir>]
    python -m harness scaffold --plan <plan.json>
    python -m harness migrate  --plan <plan.json> [--agent-cmd "claude -p"]
    python -m harness verify   --plan <plan.json> [--no-gradle]

`run` executes the whole pipeline (analyze -> plan -> scaffold -> migrate(prompts) -> verify ->
report). Each stage also persists its artifacts (analysis.json/.md, plan.json/.md,
MIGRATION_REPORT.md) so stages can be run independently.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import agent, analyzer, planner, reporter, scaffolder, verifier
from .config import DEFAULT_OUTPUT
from .models import KotlinArtifact, MigrationPlan, RibPlan, RibRoute


# --------------------------------------------------------------------------- #
# (de)serialisation helpers
# --------------------------------------------------------------------------- #
def _dump(obj, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def _load_plan(path: str) -> MigrationPlan:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    ribs = []
    for r in d["ribs"]:
        routes = [RibRoute(**rt) for rt in r.get("routes", [])]
        r = {**r, "routes": routes}
        ribs.append(RibPlan(**r))
    artifacts = [KotlinArtifact(**a) for a in d.get("artifacts", [])]
    return MigrationPlan(
        app_name=d["app_name"], package_root=d["package_root"], output_dir=d["output_dir"],
        ribs=ribs, artifacts=artifacts, build_order=d.get("build_order", []),
        stack_substitutions=d.get("stack_substitutions", {}),
    )


# --------------------------------------------------------------------------- #
# stages
# --------------------------------------------------------------------------- #
def _do_analyze(repo: str, output: str, include_tests: bool):
    a = analyzer.analyze(repo, include_tests=include_tests)
    _dump(a.to_dict(), os.path.join(output, "analysis.json"))
    with open(os.path.join(output, "analysis.md"), "w", encoding="utf-8") as fh:
        fh.write(reporter.analysis_md(a))
    return a


def _do_plan(a, output: str):
    p = planner.plan(a, output_dir=output)
    _dump(p.to_dict(), os.path.join(output, "plan.json"))
    with open(os.path.join(output, "plan.md"), "w", encoding="utf-8") as fh:
        fh.write(reporter.plan_md(p))
    return p


def cmd_analyze(args):
    a = _do_analyze(args.input, args.output, args.include_tests)
    print(f"[analyze] {a.app_name}: {a.summary['swiftFiles']} files, "
          f"arch={a.architecture['detected']}, {a.summary['uiFeatures']} UI features")
    print(f"          -> {os.path.join(args.output, 'analysis.json')}")


def cmd_plan(args):
    a = _do_analyze(args.input, args.output, args.include_tests)
    p = _do_plan(a, args.output)
    print(f"[plan] {len([r for r in p.ribs if not r.is_root])} feature RIBs + Root, "
          f"{len(p.artifacts)} artifacts -> {os.path.join(args.output, 'plan.json')}")


def cmd_scaffold(args):
    p = _load_plan(args.plan)
    files = scaffolder.scaffold(p)
    print(f"[scaffold] wrote {len(files)} files to {p.output_dir}")


def cmd_migrate(args):
    p = _load_plan(args.plan)
    apath = os.path.join(os.path.dirname(args.plan), "analysis.json")
    repo, arch = _repo_arch(apath)
    summary = agent.run_agent(p, repo, arch, args.agent_cmd)
    _dump(summary, os.path.join(p.output_dir, "agent_summary.json"))
    mode = "dry-run (prompts only)" if summary["dry_run"] else f"agent={summary['agent_cmd']}"
    print(f"[migrate] {summary['prompts_written']} prompts; {mode}")


def cmd_verify(args):
    p = _load_plan(args.plan)
    res = verifier.verify(p, run_gradle=not args.no_gradle)
    _dump(res, os.path.join(p.output_dir, "verify.json"))
    print(f"[verify] status={res['status']} files={res['kotlin_files']} "
          f"todos={res['open_todos']} errors={len(res['errors'])}")
    for e in res["errors"][:20]:
        print(f"   ! {e}")
    return 0 if res["status"] != "RED" else 1


def cmd_run(args):
    out = args.output
    os.makedirs(out, exist_ok=True)
    a = _do_analyze(args.input, out, args.include_tests)
    p = _do_plan(a, out)
    files = scaffolder.scaffold(p)
    agent_summary = agent.run_agent(p, a.repo, a.architecture["detected"], args.agent_cmd)
    _dump(agent_summary, os.path.join(out, "agent_summary.json"))
    res = verifier.verify(p, run_gradle=not args.no_gradle)
    _dump(res, os.path.join(out, "verify.json"))
    with open(os.path.join(out, "MIGRATION_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(reporter.migration_report_md(a, p, len(files), agent_summary, res))
    print("=" * 64)
    print(f"  {a.app_name}: {a.architecture['detected']} -> KMP + RIBs")
    print(f"  RIBs: {', '.join(r.name for r in p.ribs)}")
    print(f"  scaffold: {len(files)} files | prompts: {agent_summary['prompts_written']} | "
          f"verify: {res['status']} ({res['open_todos']} TODOs)")
    print(f"  output: {out}")
    print(f"  report: {os.path.join(out, 'MIGRATION_REPORT.md')}")
    print("=" * 64)
    return 0 if res["status"] != "RED" else 1


def _repo_arch(analysis_path: str):
    try:
        with open(analysis_path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d.get("repo", ""), d.get("architecture", {}).get("detected", "mvvm+coordinator")
    except OSError:
        return "", "mvvm+coordinator"


def build_parser() -> argparse.ArgumentParser:
    pp = argparse.ArgumentParser(prog="harness", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = pp.add_subparsers(dest="cmd", required=True)

    def add_io(sp, need_input=True, need_plan=False):
        if need_input:
            sp.add_argument("--input", required=True, help="path to the iOS source repo")
            sp.add_argument("--output", default=DEFAULT_OUTPUT, help="output project dir")
            sp.add_argument("--include-tests", action="store_true")
        if need_plan:
            sp.add_argument("--plan", required=True, help="path to plan.json")

    s = sub.add_parser("analyze"); add_io(s); s.set_defaults(func=cmd_analyze)
    s = sub.add_parser("plan"); add_io(s); s.set_defaults(func=cmd_plan)
    s = sub.add_parser("scaffold"); add_io(s, need_input=False, need_plan=True); s.set_defaults(func=cmd_scaffold)
    s = sub.add_parser("migrate"); add_io(s, need_input=False, need_plan=True)
    s.add_argument("--agent-cmd", default=None); s.set_defaults(func=cmd_migrate)
    s = sub.add_parser("verify"); add_io(s, need_input=False, need_plan=True)
    s.add_argument("--no-gradle", action="store_true"); s.set_defaults(func=cmd_verify)
    s = sub.add_parser("run"); add_io(s)
    s.add_argument("--agent-cmd", default=None)
    s.add_argument("--no-gradle", action="store_true"); s.set_defaults(func=cmd_run)
    return pp


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    rc = args.func(args)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
