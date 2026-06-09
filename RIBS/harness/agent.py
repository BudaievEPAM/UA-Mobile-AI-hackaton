"""Stage 4 — migrate (LLM agent orchestration).

For each RIB the harness assembles a self-contained prompt (RIB contract + the originating Swift
source + the relevant knowledge excerpts) and hands it to a coding agent. The agent command is
configurable so the harness stays model-agnostic:

    --agent-cmd "claude -p"          # or any CLI that reads a prompt on stdin and writes code
    env IOS2RIBS_AGENT_CMD=...

With `--dry-run` (the default when no agent command is available) the harness only writes the
prompt files to `<output>/_prompts/` so they can be inspected or run later. This keeps the pipeline
fully functional offline while still owning orchestration + the verify loop.
"""
from __future__ import annotations

import os
import shlex
import subprocess

from . import config
from .models import MigrationPlan, RibPlan


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _knowledge_excerpt() -> str:
    parts = []
    for name in ("mvvm-coordinator-to-ribs.md", "combine-to-coroutines.md", "ribs-patterns.md"):
        txt = _read(os.path.join(config.KNOWLEDGE_DIR, name))
        parts.append(f"### {name}\n\n{txt[:2500]}")
    return "\n\n".join(parts)


def build_prompt(plan: MigrationPlan, rib: RibPlan, analysis_repo: str,
                 architecture: str) -> str:
    tmpl = _read(os.path.join(config.PROMPTS_DIR, "rib_migration.md"))
    routes = "\n".join(
        f"  - {r.listener_method}({r.arg_type or ''}) -> attach {r.child_rib} ({r.transition}); "
        f"was `{r.source_case}`" for r in rib.routes) or "  - (none)"
    source = []
    for rel in rib.source_files:
        body = _read(os.path.join(analysis_repo, rel))
        if body:
            source.append(f"// ===== {rel} =====\n{body}")
    return tmpl.format(
        rib_name=rib.name,
        app=plan.app_name,
        architecture=architecture,
        package=f"{plan.package_root}.{rib.package}",
        dependencies=", ".join(rib.dependencies) or "(none)",
        state_fields=", ".join(rib.state_fields) or "(none)",
        build_args=", ".join(rib.build_args) or "(none)",
        routes=routes,
        source_swift="\n\n".join(source) or "(no source files mapped)",
        knowledge=_knowledge_excerpt(),
    )


def write_prompts(plan: MigrationPlan, analysis_repo: str, architecture: str) -> list[str]:
    pdir = os.path.join(plan.output_dir, "_prompts")
    os.makedirs(pdir, exist_ok=True)
    written = []
    for rib in plan.ribs:
        if rib.is_root:
            continue
        path = os.path.join(pdir, f"{rib.name}.prompt.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build_prompt(plan, rib, analysis_repo, architecture))
        written.append(path)
    return written


def run_agent(plan: MigrationPlan, analysis_repo: str, architecture: str,
              agent_cmd: str | None) -> dict:
    """Write prompts, then (if an agent command is configured) invoke it per RIB.

    Returns a summary dict for the report. The harness never fails the pipeline if the agent is
    unavailable — it degrades to a dry-run so scaffolding + verification still complete.
    """
    prompts = write_prompts(plan, analysis_repo, architecture)
    agent_cmd = agent_cmd or os.environ.get("IOS2RIBS_AGENT_CMD")
    summary = {"prompts_written": len(prompts), "agent_cmd": agent_cmd,
               "ribs_attempted": [], "dry_run": agent_cmd is None}
    if not agent_cmd:
        return summary

    for rib in plan.ribs:
        if rib.is_root:
            continue
        prompt = build_prompt(plan, rib, analysis_repo, architecture)
        try:
            proc = subprocess.run(
                shlex.split(agent_cmd), input=prompt, capture_output=True,
                text=True, timeout=600,
            )
            ok = proc.returncode == 0
            summary["ribs_attempted"].append({"rib": rib.name, "ok": ok,
                                              "stderr": proc.stderr[-500:] if not ok else ""})
        except (OSError, subprocess.SubprocessError) as exc:
            summary["ribs_attempted"].append({"rib": rib.name, "ok": False, "stderr": str(exc)})
    return summary
