// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Migrator",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "Migrator",
            path: "Sources/Migrator"
        )
    ]
)
