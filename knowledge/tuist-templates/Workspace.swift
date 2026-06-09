import ProjectDescription

// Root workspace — globs every project. Place at the generated project root.
//
// `AllTests` is a shared scheme that aggregates EVERY module's test target, so `Cmd+U` in Xcode
// builds + runs the whole suite and the Test Navigator (Cmd+6) lists all tests in one place.
// Without it, Xcode only has per-target schemes, and Cmd+U runs just the *selected* scheme's tests
// — and the app scheme has none, so the suite looks empty. Always emit this scheme.
//
// SCAFFOLDER RULE: add one `.testableTarget` entry (and a matching build `.project` entry) for
// EACH module that has a `Tests/` target — i.e. every `Project.feature(...)` and any
// `Project.core(...)` left at `hasTests: true`. Update the lists as features are scaffolded.
// Reference targets as `.project(path: "<module dir relative to root>", target: "<TargetName>")`.
let allTests = Scheme.scheme(
    name: "AllTests",
    shared: true,
    buildAction: .buildAction(targets: [
        .project(path: "Core/SharedModels", target: "SharedModels"),
        .project(path: "Features/MoviesList", target: "MoviesList"),
        .project(path: "Features/MovieDetail", target: "MovieDetail"),
    ]),
    testAction: .targets([
        .testableTarget(target: .project(path: "Core/SharedModels", target: "SharedModelsTests")),
        .testableTarget(target: .project(path: "Features/MoviesList", target: "MoviesListTests")),
        .testableTarget(target: .project(path: "Features/MovieDetail", target: "MovieDetailTests")),
    ])
)

let workspace = Workspace(
    name: "MovieApp",
    projects: [
        "App",
        "Core/**",
        "Features/**",
    ],
    schemes: [allTests]
)
