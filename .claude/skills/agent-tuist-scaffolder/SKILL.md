---
name: agent-tuist-scaffolder
description: Scaffold the modular Tuist + TCA workspace (foundation modules) and gate on a green empty shell — invoke with $agent-tuist-scaffolder
---
---
name: tuist-scaffolder
type: implementer
color: green
description: Emit Tuist manifests + Core modules; verify tuist generate + build green before feature work
capabilities: [tuist-manifests, modularization, spm-dependencies, project-generation]
priority: high
hooks:
  pre: |
    echo "🏗  tuist-scaffolder: scaffolding workspace/output"
  post: |
    echo "🏁 scaffold gate: running build_check (generate + build)"
---

# Tuist Scaffolder

**Role:** Stand up the **generated** project skeleton in `workspace/output/` and prove it
generates + builds **before** any feature is migrated (Constitution VII gate).

## Inputs
- `workspace/migration-plan.md` / `specs/**/plan.md` (target module graph).
- Templates: [`knowledge/tuist-templates/`](../../../knowledge/tuist-templates/) — copy and adapt
  `Workspace.swift`, `Tuist.swift`, `Tuist/Package.swift`, and `ProjectDescriptionHelpers/Project+Module.swift`.

## Procedure
1. Create `workspace/output/` with:
   - `Tuist.swift`, `Workspace.swift`, `Tuist/Package.swift`, `Tuist/ProjectDescriptionHelpers/Project+Module.swift`
     (from the templates; pin TCA 1.25.2).
   - In `Workspace.swift`, declare the shared **`AllTests`** scheme (see the template) with one
     `.testableTarget` entry per module that has a `Tests/` target. Re-sync its lists whenever a
     feature module is added so `Cmd+U` keeps running the whole suite.
   - Foundation modules first: `Core/SharedModels`, `Core/Networking`, `Core/Persistence`,
     `DesignSystem` — each with `Project.swift` (via the factories), a trivial `Sources/` file, and
     an empty `Tests/`.
   - `App/` with a minimal `@main` App that builds an empty root `Store`.
   - Empty `Features/<Name>/` targets for each planned feature (stub reducer + view + test).
2. **Gate:** run `bash scripts/build_check.sh workspace/output`. It must reach `BUILD_CHECK: GREEN`
   (tuist install + generate + build). Fix manifest/SPM errors (read the xcsift JSON in
   `workspace/output/.build-logs/*.json`) until green. Do **not** proceed to feature migration on RED.

## Outputs
- A generating, building `workspace/output/` skeleton.
- `workspace/output/.build-logs/` (xcsift JSON).

## Rules
- One module per feature; Features depend only on `Core/*` + `DesignSystem` (Constitution II).
- Keep TCA a **dynamic** framework (set in `Tuist/Package.swift`).
- Stub reducers compile and are marked `// TODO(migration):` — never leave a target that fails to build.
- `Workspace.swift` **must** ship the shared `AllTests` scheme aggregating every `*Tests` target,
  so Xcode `Cmd+U` runs the full suite (the app scheme has no tests). Verify after generate with
  `xcodebuild -workspace <App>.xcworkspace -list` — `AllTests` must be listed.
- If a Tuist manifest API error appears, confirm signatures against the installed Tuist 4.139
  (`tuist init` in a temp dir) and adjust the factories.
