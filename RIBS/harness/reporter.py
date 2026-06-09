"""Human-readable reports: analysis.md, plan.md, and MIGRATION_REPORT.md."""
from __future__ import annotations

import datetime as _dt

from .models import Analysis, MigrationPlan


def analysis_md(a: Analysis) -> str:
    arch = a.architecture
    lines = [
        f"# Analysis — {a.app_name}", "",
        f"Repo: `{a.repo}`  ", f"Generated: {_dt.date.today()}", "",
        "## Summary", "",
        f"- Swift files: **{a.summary.get('swiftFiles')}** ({a.summary.get('totalLines')} lines)",
        f"- Detected architecture: **{arch.get('detected')}**",
        f"- Navigation: **{arch.get('navigationPattern')}**",
        f"- UI features: **{a.summary.get('uiFeatures')}**, candidate modules: "
        f"**{a.summary.get('candidateModules')}**", "",
        "## Architecture scores", "",
        "| signal | score |", "|---|---|",
    ]
    for k, v in arch.get("scores", {}).items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Component counts", "", "| kind | count |", "|---|---|"]
    for k, v in sorted(arch.get("componentCounts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Tech stack", ""]
    for cat, tags in a.stack.items():
        lines.append(f"- **{cat}**: {', '.join(tags)}")
    lines += ["", "## Features", "", "| feature | UI | kinds | routes |", "|---|---|---|---|"]
    for f in a.features:
        kinds = ", ".join(f"{k}×{v}" for k, v in f.kinds.items())
        routes = ", ".join(f.routes) if f.routes else "—"
        lines.append(f"| `{f.name}` | {'✅' if f.is_ui_feature else ''} | {kinds} | {routes} |")
    return "\n".join(lines) + "\n"


def plan_md(p: MigrationPlan) -> str:
    lines = [
        f"# Migration plan — {p.app_name} → KMP + RIBs", "",
        f"Package root: `{p.package_root}`  ", f"Output: `{p.output_dir}`", "",
        "## RIB tree", "", "```",
    ]
    root = next((r for r in p.ribs if r.is_root), None)

    def render(name: str, depth: int, seen: set):
        rib = next((r for r in p.ribs if r.name == name), None)
        pad = "    " * depth
        lines.append(f"{pad}{name}RIB")
        if rib and name not in seen:
            seen.add(name)
            for c in rib.children:
                render(c, depth + 1, seen)

    if root:
        render("Root", 0, set())
    lines += ["```", "", "## RIBs", "",
              "| RIB | package | deps | state | build args | routes |",
              "|---|---|---|---|---|---|"]
    for r in p.ribs:
        deps = ", ".join(r.dependencies) or "—"
        state = ", ".join(r.state_fields) or "—"
        bargs = ", ".join(r.build_args) or "—"
        routes = "; ".join(f"{rt.listener_method}→{rt.child_rib}({rt.transition})"
                           for rt in r.routes) or "—"
        lines.append(f"| {r.name} | `{r.package}` | {deps} | {state} | {bargs} | {routes} |")
    lines += ["", "## Supporting Kotlin artifacts", "", "| kind | file | from |", "|---|---|---|"]
    for art in p.artifacts:
        src = art.source_files[0] if art.source_files else "—"
        lines.append(f"| {art.kind} | `{art.rel_path}` | `{src}` |")
    lines += ["", "## Build / migration order", ""]
    for i, step in enumerate(p.build_order, 1):
        lines.append(f"{i}. `{step}`")
    lines += ["", "## Stack substitutions", "", "| iOS | KMP |", "|---|---|"]
    for k, v in p.stack_substitutions.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines) + "\n"


def migration_report_md(a: Analysis, p: MigrationPlan, scaffold_count: int,
                        agent_summary: dict, verify_result: dict) -> str:
    lines = [
        f"# Migration report — {a.app_name}", "",
        f"Generated: {_dt.datetime.now().isoformat(timespec='seconds')}", "",
        "## Pipeline", "",
        f"1. **analyze** — {a.summary.get('swiftFiles')} Swift files, "
        f"detected `{a.architecture.get('detected')}`, {a.summary.get('uiFeatures')} UI features.",
        f"2. **plan** — {len([r for r in p.ribs if not r.is_root])} feature RIBs + Root, "
        f"{len(p.artifacts)} support artifacts.",
        f"3. **scaffold** — {scaffold_count} files written to `{p.output_dir}`.",
        f"4. **migrate** — {agent_summary.get('prompts_written')} agent prompts written"
        + (f"; agent `{agent_summary.get('agent_cmd')}` run on "
           f"{len(agent_summary.get('ribs_attempted', []))} RIBs."
           if not agent_summary.get('dry_run') else " (dry-run: prompts only, no agent invoked)."),
        f"5. **verify** — gate: **{verify_result.get('status')}** "
        f"({verify_result.get('kotlin_files')} Kotlin files, "
        f"{verify_result.get('open_todos')} open TODOs).", "",
        "## RIB tree generated", "", "```",
    ]
    for r in p.ribs:
        if r.is_root:
            lines.append("Root")
            for c in r.children:
                lines.append(f"  └── {c}")
                child = next((x for x in p.ribs if x.name == c), None)
                for gc in (child.children if child else []):
                    lines.append(f"        └── {gc}")
    lines += ["```", "", "## Verify gate", "",
              f"- status: **{verify_result.get('status')}**",
              f"- kotlin files: {verify_result.get('kotlin_files')}",
              f"- open TODO(ios2ribs) bodies for the agent to fill: "
              f"{verify_result.get('open_todos')}"]
    if verify_result.get("errors"):
        lines += ["", "### Errors"] + [f"- {e}" for e in verify_result["errors"]]
    if verify_result.get("findings"):
        lines += ["", "### Findings"] + [f"- {f}" for f in verify_result["findings"]]
    g = verify_result.get("gradle")
    if g:
        lines += ["", "### Gradle",
                  f"- ran: {g.get('ran')}" + (f" (rc={g.get('returncode')})" if g.get("ran")
                                              else f" — {g.get('reason')}")]
    lines += ["", "## Next step", "",
              "The scaffold is structurally complete and wired. Run the migration agent to fill the "
              "`// TODO(ios2ribs):` bodies:", "",
              "```bash",
              'python -m harness migrate --plan <output>/plan.json --agent-cmd "claude -p"',
              "```", "",
              "Then re-run `python -m harness verify` to drive the gate to GREEN.", ""]
    return "\n".join(lines) + "\n"
