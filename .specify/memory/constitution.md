# TCA Migration Constitution

The governing principles for migrating an iOS app — **VIPER, Clean, MVVM, or MVVM+Coordinator** —
to a modular **TCA + Tuist + Swift Testing** project. Every spec, plan, task, and generated file
must comply. Canonical rules and exemplars live in [`knowledge/`](../../knowledge/README.md)
(per-architecture `*-to-tca.md`); this constitution is the short, enforceable summary that the
spec/plan/tasks and the RUFLO workers cite.

## Core Principles

### I. TCA is the only architecture (no source-architecture residue)
Every screen/flow is a TCA feature: `@Reducer` + `@ObservableState` State + `Action` enum + `body`.
**Delete**, never port, VIPER Presenters/Interactors/Routers and Clean ViewModels/DIContainers/
Coordinators. No `ViewStore`/`WithViewStore` (Observation only). Views are SwiftUI reading `store`.

### II. Modular by feature (Tuist)
One Tuist module per feature (`Features/<Name>`), plus shared `Core/SharedModels`,
`Core/Networking`, `Core/Persistence`, `DesignSystem`. Features depend only on `Core/*` +
`DesignSystem`, never on each other. The `App` module is the composition root.

### III. State-driven navigation (NON-NEGOTIABLE)
Navigation is data: `@Presents` (tree) or `StackState` (stack). No `UINavigationController`, no
coordinator/router objects, no imperative `present/push`. A leaf feature requests navigation via a
`delegate` action; the parent owns the path/destination.

### IV. All I/O is a dependency
Every network/persistence/system call is a `@DependencyClient` with a `liveValue` and a failing
test value. No singletons, no direct `URLSession`/`UserDefaults`/`CoreData` inside a reducer.
Clean Repositories/UseCases and VIPER Interactors become dependency clients.

### V. Swift Testing + TestStore (NON-NEGOTIABLE)
Tests use Swift Testing (`@Suite`/`@Test`/`#expect`/`#require`) driving TCA `TestStore`. Exhaustive
assertions: every effect is `receive`d, every mutation declared. **No `import XCTest` may remain.**
Each migrated feature ships a `@MainActor` suite with ≥1 happy path and ≥1 failure path. The
generated `Workspace.swift` ships a shared **`AllTests`** scheme aggregating every `*Tests` target,
so Xcode `Cmd+U` runs the full suite in one place (the app scheme alone has no tests).

### VI. Behavior parity
A migrated feature reproduces the observable behavior of the source feature (same screens, inputs,
outputs, network/persistence effects). When behavior is ambiguous, preserve the source's; record
the assumption in the feature spec.

### VII. Green is the definition of done
A feature/module is "done" only when `tuist generate` succeeds, it builds with **0 errors**
(via `xcsift`), and its `swift test`/`xcodebuild test` suite passes. Unfinished work is a scaffolded
reducer with an explicit `// TODO(migration):` and a tracked task — never a broken build.

## Technology Stack (pinned)

- **TCA** `swift-composable-architecture` 1.25.2 · **Tuist** 4.139.x · **Swift** 6 · **iOS** 17.0
  deployment target (lower only if the source requires it; TCA back-deploys Observation).
- Build/diagnostics: `tuist` + **`xcsift`** (token-efficient JSON). Project gen: Tuist manifests
  (`Workspace.swift`, per-module `Project.swift` via `ProjectDescriptionHelpers` factories).

## Migration Workflow (Spec Kit → RUFLO)

1. **Analyze** the source repo (`scripts/code_map.sh` + analyzer) → `workspace/analysis.json`.
2. **Specify / Plan / Tasks** (Spec Kit) → reviewable per-feature spec, target module graph, and a
   dependency-ordered task list (one task ≈ one feature module).
3. **Execute** (RUFLO swarm) the tasks: scaffold → per-feature migrate (fan-out) → author tests →
   build/test/repair loop until green.
4. **Report** task-by-task traceability in `workspace/output/MIGRATION_REPORT.md`.

Scope discipline: fully migrate the foundation + a representative set of features **to green**;
scaffold the rest as `TODO(migration)` tasks. A green subset beats a broad broken migration.

## Governance

This constitution supersedes convenience. Generated code that violates a principle must be fixed or
explicitly waived in the feature spec with justification. Update [`knowledge/`](../../knowledge/README.md)
**first** when TCA/Tuist facts change; this file and the workers cite it.

**Version**: 1.0.0 | **Ratified**: 2026-06-04 | **Last Amended**: 2026-06-04
