// swift-tools-version: 6.0
import PackageDescription

// Tuist-managed external dependencies. Lives at `Tuist/Package.swift`.
// `tuist install` resolves these; reference them with `.external(name: "ComposableArchitecture")`.

#if TUIST
import struct ProjectDescription.PackageSettings

let packageSettings = PackageSettings(
    // TCA must be a dynamic framework to avoid duplicate-symbol issues across modules.
    productTypes: [
        "ComposableArchitecture": .framework
    ]
)
#endif

let package = Package(
    name: "Dependencies",
    dependencies: [
        // TCA 1.25.2 is current (June 2026). Switch `from:` -> `exact:` for full reproducibility.
        .package(
            url: "https://github.com/pointfreeco/swift-composable-architecture",
            from: "1.25.2"
        ),
    ]
)
