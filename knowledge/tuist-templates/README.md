# Tuist module templates (target Tuist 4.139.x)

Reference manifests for the **generated** TCA project (`workspace/output/`). Copy these into the
output root and adapt. Per-module manifests stay ~3 lines thanks to the factories in
`ProjectDescriptionHelpers/Project+Module.swift`.

## Target module graph

```
App  (.app, composition root: builds the root Store, wires live @Dependency values)
 ├─ Features/<Name>      (.framework + Swift Testing target)  — one TCA feature per screen/flow
 │     ├─ Core/SharedModels
 │     ├─ Core/Networking      (dependency-client interfaces + live impls + DTOs/mappers)
 │     ├─ Core/Persistence
 │     └─ DesignSystem
 ├─ Core/SharedModels    (.framework) — Entities/domain value types, mocks (#if DEBUG)
 ├─ Core/Networking      (.framework) — @DependencyClient defs, API, DTO, mappers
 ├─ Core/Persistence     (.framework) — storage clients
 └─ DesignSystem         (.framework) — shared SwiftUI components, theme
```
Rule: Features never depend on each other directly; cross-feature flow lives in `App` (or a
parent feature) via `StackState`/`@Presents`. Features depend only on `Core/*` + `DesignSystem`.

## Generated layout

```
workspace/output/
  Tuist.swift                         # config (this folder's Tuist.swift)
  Workspace.swift                     # workspace (this folder's Workspace.swift)
  Tuist/
    Package.swift                     # external deps (this folder's Package.swift)
    ProjectDescriptionHelpers/
      Project+Module.swift            # the factories
  App/
    Project.swift
    Sources/…   Resources/…
  Core/
    SharedModels/{Project.swift,Sources/**,Tests/**}
    Networking/{Project.swift,Sources/**,Tests/**}
    Persistence/{Project.swift,Sources/**,Tests/**}
  DesignSystem/{Project.swift,Sources/**}
  Features/
    MoviesList/{Project.swift,Sources/**,Tests/**}
    MovieDetail/{Project.swift,Sources/**,Tests/**}
```

## Per-module `Project.swift` (using the factories)

**Core/SharedModels/Project.swift**
```swift
import ProjectDescription
import ProjectDescriptionHelpers
let project = Project.core(name: "SharedModels", dependencies: [])
```

**Core/Networking/Project.swift**
```swift
import ProjectDescription
import ProjectDescriptionHelpers
let project = Project.core(name: "Networking", dependencies: [
    .external(name: "ComposableArchitecture"),                       // for @Dependency plumbing
    .project(target: "SharedModels", path: "../SharedModels"),
])
```

**Features/MoviesList/Project.swift**
```swift
import ProjectDescription
import ProjectDescriptionHelpers
let project = Project.feature(name: "MoviesList", dependencies: [
    .external(name: "ComposableArchitecture"),
    .project(target: "SharedModels", path: "../../Core/SharedModels"),
    .project(target: "Networking",   path: "../../Core/Networking"),
    .project(target: "DesignSystem", path: "../../DesignSystem"),
])
```

**App/Project.swift**
```swift
import ProjectDescription
import ProjectDescriptionHelpers
let project = Project.app(name: "MovieApp", dependencies: [
    .external(name: "ComposableArchitecture"),
    .project(target: "MoviesList",  path: "../Features/MoviesList"),
    .project(target: "MovieDetail", path: "../Features/MovieDetail"),
])
```

## Aggregate test scheme (`AllTests`) — required

`Workspace.swift` must declare a **shared `AllTests` scheme** that aggregates every module's test
target. Without it, Tuist only emits per-target schemes, so Xcode's **Cmd+U** runs just the
*selected* scheme's tests — and since the default `App` scheme has none, the suite looks empty in
the Test Navigator (Cmd+6). With it, selecting **AllTests** builds + runs the whole suite at once.

```swift
let allTests = Scheme.scheme(
    name: "AllTests", shared: true,
    buildAction: .buildAction(targets: [
        .project(path: "Core/SharedModels",   target: "SharedModels"),
        .project(path: "Features/MoviesList",  target: "MoviesList"),
        // …one entry per module that has tests…
    ]),
    testAction: .targets([
        .testableTarget(target: .project(path: "Core/SharedModels",  target: "SharedModelsTests")),
        .testableTarget(target: .project(path: "Features/MoviesList", target: "MoviesListTests")),
        // …one entry per *Tests target…
    ])
)
let workspace = Workspace(name: "MovieApp", projects: ["App", "Core/**", "Features/**"], schemes: [allTests])
```

**Rule:** one `.testableTarget` (and matching build `.project`) entry per module with a `Tests/`
target — every `Project.feature(...)` plus any `Project.core(...)` left at `hasTests: true`. Keep
the lists in sync as features are added. Run on the **My Mac** destination (modules are
multiplatform; an iOS Simulator runtime may be absent). Verify with
`xcodebuild -workspace <App>.xcworkspace -list` → `AllTests` should appear.

## Generate & verify

```bash
cd workspace/output
tuist install      # resolves SPM deps (TCA) declared in Tuist/Package.swift
tuist generate     # produces .xcworkspace / .xcodeproj
# build/test gate (see scripts/build_check.sh):
tuist build 2>&1 | xcsift
```
Add `--force-resolved-versions` to `tuist install` on CI for deterministic dependency resolution.

## Notes / gotchas

- These target **Tuist 4.139**. If `tuist generate` reports a manifest API error, run a throwaway
  `tuist init` in a temp dir to confirm the exact current `Tuist`/`generationOptions` signatures
  and mirror them — the API is stable but evolves.
- `deploymentTargets: .iOS("17.0")` keeps modern Observation simple. TCA back-deploys Observation
  to iOS 13 if a lower target is required — lower it in `Project+Module.swift` if the source app does.
- Keep TCA as a **dynamic** `.framework` (set in `Tuist/Package.swift`) to avoid duplicate symbols
  when many modules link it.

### Build-loop gotchas (Xcode 26 + TCA + Tuist) — proven during migration

- **Drive `xcodebuild` directly, not `tuist build`.** `tuist build/test` destination inference can
  pass an empty `-destination`; build the generated `*.xcworkspace` with an explicit
  `-destination` instead (see `scripts/build_check.sh`).
- **Disable explicit modules:** Xcode 26's explicit-modules clang scanning fails on TCA's mixed
  static/dynamic deps (`Clocks-Swift.h`/`CombineSchedulers-Swift.h not found`). Pass
  `SWIFT_ENABLE_EXPLICIT_MODULES=NO` to xcodebuild.
- **Trust macros non-interactively:** add `-skipMacroValidation` (TCA is macro-heavy).
- **No matching iOS Simulator runtime?** If the toolchain's SDK (e.g. iOS 26.5) has no installed
  simulator runtime, xcodebuild finds *no* iOS destination. Make modules **multiplatform**
  (`[.iPhone, .iPad, .mac]` + `.multiplatform(iOS:macOS:)`) and validate on `platform=macOS` —
  TCA/SwiftUI modules are platform-agnostic. The shipping app still targets iOS.
- **Simulator builds:** `CODE_SIGNING_ALLOWED=NO` avoids signing for build/test gates.
- **Retry once on a fresh DerivedData.** The first build can lose a parallel race generating a
  dependency framework's `-Swift.h` (e.g. `Clocks-Swift.h not found` / "could not build module
  'Clocks'"). A single retry continues from the partial build and succeeds — `build_check.sh`
  retries the build step automatically.
