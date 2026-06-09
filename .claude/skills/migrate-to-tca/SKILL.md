---
name: migrate-to-tca
description: Orchestrate a full iOS app migration (VIPER, Clean, MVVM, or MVVM+Coordinator) to modular TCA + Tuist + Swift Testing. Use when asked to migrate an iOS repo to TCA, run the migration pipeline, or drive the analyze→spec→execute→report flow. Invoke with $migrate-to-tca <repo-url-or-path>.
---

# migrate-to-tca — pipeline orchestrator

Drives the three-layer system: **Spec Kit** (spec) → **RUFLO** (swarm execution) → **iOS/TCA
domain skills**. Source of truth for rules: [`knowledge/`](../../../knowledge/README.md) +
[`.specify/memory/constitution.md`](../../../.specify/memory/constitution.md).

## Inputs
A git URL or local path of the iOS app to migrate (VIPER or Clean/MVVM).

## Pipeline
1. **Ingest** — clone the repo into `workspace/input/` (`git clone --depth 1 <url> workspace/input/<name>`).
2. **Analyze** — `$agent-ios-arch-analyzer`: `bash scripts/code_map.sh workspace/input workspace/analysis.json`,
   then read key files → `workspace/analysis.md` (per-feature mapping + migration order).
3. **Spec** (Spec Kit, reviewable):
   - `/speckit-specify` — one migration spec per feature (uses the Migration Context block).
   - `/speckit-plan` — target Tuist module graph.
   - `/speckit-tasks` — dependency-ordered task list (one task ≈ one feature module).
4. **Load knowledge** — `bash scripts/load_knowledge.sh` (RUFLO AgentDB; skills also read files directly).
5. **Execute** — drive the tasks. Two equivalent paths:
   - **RUFLO swarm** (autonomous; spawns a Claude Code worker — needs an API key, since the worker
     can't use the harness/OAuth session):
     `ANTHROPIC_API_KEY=sk-ant-... scripts/swarm_migrate.sh "Execute specs/**/tasks.md per .specify/memory/constitution.md → modular TCA in workspace/output, build & test green, using agent-tca-*/agent-ios-* skills"`
     (the wrapper passes the key through to the worker; without it the worker 401s — see the direct path).
   - **Direct (reliable fallback):** run the domain skills in order:
     `$agent-tuist-scaffolder` → `$agent-tca-feature-migrator` (per feature) → `$agent-swift-test-author` → `$agent-ios-build-doctor`.
6. **Verify** — `$agent-ios-build-doctor` loops `bash scripts/build_check.sh workspace/output` until
   `BUILD_CHECK: GREEN` (tuist generate + build + test via xcsift).
7. **Report** — `$agent-migration-reporter` → `workspace/output/MIGRATION_REPORT.md`.

## Scope discipline (Constitution VII)
Migrate the foundation + a representative set of features **to green**; scaffold the rest as
compiling `// TODO(migration):` stubs with tracked tasks. A green subset beats a broad broken migration.

## Preflight
`Xcode`, `tuist`, `xcsift`, `swift`, `uv`, `git`, `python3`. RUFLO runtime in `.claude-flow/`; MCP
server `claude-flow` in `.mcp.json`.

## Output
`workspace/output/` — a generating, building, tested modular TCA project + `MIGRATION_REPORT.md`.
