# iOS → TCA Migration Agent

An **agentic system** that migrates an iOS app from **VIPER, Clean, MVVM, or MVVM+Coordinator**
architecture to a modern, modular **TCA** stack — **Tuist** project generation, **Swift Testing**
(no XCTest), one module per feature — and verifies the result by building and testing it until green.

## Repo layout

```
knowledge/            # the quality lever: TCA patterns, VIPER→TCA, Clean→TCA, Swift Testing, Tuist templates
scripts/              # code_map.sh (analyze), build_check.sh (tuist+xcsift gate), load_knowledge.sh (AgentDB)
.claude/skills/
  migrate-to-tca/         # orchestrator (front door)
  agent-ios-arch-analyzer/  agent-tuist-scaffolder/  agent-tca-feature-migrator/
  agent-swift-test-author/  agent-ios-build-doctor/  agent-migration-reporter/   # domain workers
  speckit-*/            # Spec Kit commands (constitution/specify/plan/tasks/implement/…)
.specify/             # Spec Kit: constitution (TCA-migration), customized templates
.claude-flow/         # RUFLO runtime (config, AgentDB, metrics)
workspace/input/      # the cloned source app (read-only reference)
workspace/output/     # the generated modular TCA project (the deliverable)
workspace/analysis.*  # architecture inventory produced by the analyzer
```

## Run it

```bash
# Prereqs: Xcode, tuist, xcsift (brew), uv, node, git, python3
#   (Spec Kit + RUFLO already initialized in this repo)

# Drive the whole pipeline (front door):
#   in Claude Code:  $migrate-to-tca https://github.com/<org>/<ios-app>
#   or step through:  analyze → /speckit-specify → /speckit-plan → /speckit-tasks → execute → report

# Execute autonomously — needs an API key (put it in gitignored .env: ANTHROPIC_API_KEY=sk-ant-...).
# Two interchangeable runners; both inject the constitution + knowledge and run until green:
scripts/swarm_migrate.sh "Execute specs/001-migrate-viper-list/tasks.md → modular TCA, build & test green"          # RUFLO hive-mind worker
scripts/single_claude_agent_migrate.sh "…same objective…"                                                            # plain Claude Code, no swarm

# Or drive it in-session (no API key; uses this Claude Code session):
#   $migrate-to-tca https://github.com/<org>/<ios-app>
#   or step through: analyze → /speckit-specify → /speckit-plan → /speckit-tasks → $agent-* skills

# Verify the generated project (the gate):
bash scripts/build_check.sh workspace/output     # tuist generate + build + test | xcsift
```

Both emit a modular TCA project (`Core/*`, `Features/*`, `App`) with `@Reducer`/`@ObservableState`/
`@Dependency` + Swift Testing. In both, the Presenter/Interactor/WireFrame are **dissolved** into
reducers + dependencies + state-driven navigation. See each output's
`MIGRATION_REPORT.md` for task-by-task results.

## Design notes

- **Coexistence:** Spec Kit owns `.claude/skills/speckit-*` + `.specify/`; RUFLO owns `.claude-flow/`
  + `.mcp.json`. RUFLO's ambient session hooks are disabled during development
  (`.claude/settings.json.ruflo.bak` restores them for a live demo).
- **Reliability:** every domain skill works under the RUFLO swarm *or* via direct invocation, so the
  migration completes even if the alpha swarm wiring misbehaves.
- **Pinned:** TCA 1.25.2 · Tuist 4.139 · Swift 6 · iOS 17. Update [`knowledge/`](knowledge/README.md) first if these drift.
```
