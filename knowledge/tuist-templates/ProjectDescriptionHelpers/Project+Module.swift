import ProjectDescription

// Shared manifest helpers — lives in `Tuist/ProjectDescriptionHelpers/`.
// Keeps every per-module `Project.swift` to ~3 lines. Targets Tuist 4.139.x.

public extension Project {
    /// A feature module: one framework + one Swift Testing unit-test target.
    static func feature(
        name: String,
        dependencies: [TargetDependency] = []
    ) -> Project {
        module(
            name: name,
            bundleIdSuffix: "feature.\(name.lowercased())",
            hasTests: true,
            dependencies: dependencies
        )
    }

    /// A core/shared module (Networking, Persistence, SharedModels, DesignSystem).
    static func core(
        name: String,
        hasTests: Bool = true,
        dependencies: [TargetDependency] = []
    ) -> Project {
        module(
            name: name,
            bundleIdSuffix: "core.\(name.lowercased())",
            hasTests: hasTests,
            dependencies: dependencies
        )
    }

    /// The application module (the composition root).
    static func app(
        name: String,
        dependencies: [TargetDependency] = []
    ) -> Project {
        Project(
            name: name,
            targets: [
                .target(
                    name: name,
                    destinations: .iOS,
                    product: .app,
                    bundleId: "com.example.\(name.lowercased())",
                    deploymentTargets: .iOS("17.0"),
                    infoPlist: .extendingDefault(with: [
                        "UILaunchScreen": ["UIColorName": ""]
                    ]),
                    sources: ["Sources/**"],
                    resources: ["Resources/**"],
                    dependencies: dependencies
                )
            ]
        )
    }

    /// Generic module factory shared by `feature`/`core`.
    static func module(
        name: String,
        bundleIdSuffix: String,
        product: Product = .framework,
        hasTests: Bool,
        dependencies: [TargetDependency]
    ) -> Project {
        var targets: [Target] = [
            .target(
                name: name,
                destinations: .iOS,
                product: product,
                bundleId: "com.example.\(bundleIdSuffix)",
                deploymentTargets: .iOS("17.0"),
                infoPlist: .default,
                sources: ["Sources/**"],
                resources: [],
                dependencies: dependencies
            )
        ]
        if hasTests {
            targets.append(
                .target(
                    name: "\(name)Tests",
                    destinations: .iOS,
                    product: .unitTests,
                    bundleId: "com.example.\(bundleIdSuffix).tests",
                    deploymentTargets: .iOS("17.0"),
                    infoPlist: .default,
                    sources: ["Tests/**"],
                    dependencies: [.target(name: name)]
                )
            )
        }
        return Project(name: name, targets: targets)
    }
}
