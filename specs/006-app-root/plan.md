# Implementation Plan: CoolRestaurants — VIPER+RxSwift → TCA Migration

**Branch**: `006-app-root` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Multi-feature migration spanning specs/002–006. Primary feature directory is `specs/006-app-root`; sibling specs cover each module.

## Summary

Migrate the CoolRestaurants iOS app (VIPER/Presenter+Coordinator+Repository, RxSwift, UIKit, CocoaPods) to a modular TCA + Tuist project with SwiftUI, Swift concurrency, and Swift Testing. Five modules in dependency order: `Core/SharedModels` → `Core/Networking` → `Features/RestaurantsDetail` + `Features/RestaurantsMap` → `App`. Output to `workspace/output/CoolRestaurants/`.

## Technical Context

**Language/Version**: Swift 6 (strict concurrency), iOS 17.0 deployment target

**Primary Dependencies**:
- `swift-composable-architecture` 1.25.2 (dynamic framework via Tuist)
- MapKit (system; `UIViewRepresentable` wrapper for `MKMapView`)
- No third-party CocoaPods carried over (FoursquareKit → URLSession; SwiftLocation → CLLocationManager; SDWebImage → `AsyncImage`)

**Storage**: None (no persistence layer in scope; restaurants fetched on demand)

**Testing**: Swift Testing (`@Suite` / `@Test` / `#expect`) + TCA `TestStore`. **No `import XCTest`.**

**Target Platform**: iOS 17.0+, iPhone (no iPad/macOS scope)

**Project Type**: iOS mobile app (SwiftUI + TCA, modular Tuist workspace)

**Performance Goals**: Map annotation refresh < 1 s for ≤ 20 venues. Restaurant fetch debounced/deduped to avoid redundant network calls.

**Constraints**: Swift 6 strict concurrency — no data races; no `@unchecked Sendable` shortcuts. No ViewStore/WithViewStore. State-driven navigation only.

**Scale/Scope**: 2 UI features (Map + Detail), 2 core modules (SharedModels + Networking), 1 App module.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. TCA only — no VIPER residue | PASS | All Presenter/Coordinator/Router/Contract files are deleted; replaced by `@Reducer` features |
| II. Modular by feature (Tuist) | PASS | 5 Tuist modules; features depend only on `Core/*` |
| III. State-driven navigation | PASS | `StackState<AppFeature.Path>` in AppFeature; no `UINavigationController` |
| IV. All I/O is a dependency | PASS | `RestaurantClient` + `LocationClient` as `@DependencyClient`; no singletons |
| V. Swift Testing + TestStore | PASS | No XCTest; each feature has `@Suite` with happy + failure paths |
| VI. Behavior parity | PASS | Location state machine, restaurant dedup, navigation flow preserved |
| VII. Green is done | GATE | `scripts/build_check.sh workspace/output` must report `BUILD_CHECK: GREEN` before marking done |

**No violations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/006-app-root/
├── plan.md              ← this file
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── quickstart.md        ← Phase 1
└── contracts/           ← Phase 1
    ├── RestaurantClient.md
    └── LocationClient.md
```

Sibling specs: `specs/002-shared-models/`, `specs/003-networking-clients/`, `specs/004-restaurants-detail/`, `specs/005-restaurants-map/`.

### Source Code — Target Layout

```text
workspace/output/CoolRestaurants/
├── Workspace.swift                      # Tuist workspace root
├── Tuist/
│   ├── Package.swift                    # SPM deps: TCA 1.25.2
│   └── ProjectDescriptionHelpers/
│       └── Project+Module.swift         # feature/core/app factories
├── Core/
│   ├── SharedModels/
│   │   ├── Project.swift
│   │   ├── Sources/Restaurant.swift
│   │   └── Tests/RestaurantTests.swift
│   └── Networking/
│       ├── Project.swift
│       ├── Sources/
│       │   ├── RestaurantClient.swift   # @DependencyClient
│       │   ├── LocationClient.swift     # @DependencyClient
│       │   └── Internal/
│       │       ├── FoursquareResponse.swift  # Decodable; not exported
│       │       └── MKCoordinateRegion+Radius.swift
│       └── Tests/
│           └── NetworkingTests.swift
├── Features/
│   ├── RestaurantsDetail/
│   │   ├── Project.swift
│   │   ├── Sources/
│   │   │   ├── RestaurantsDetailFeature.swift
│   │   │   └── RestaurantsDetailView.swift
│   │   └── Tests/
│   │       └── RestaurantsDetailFeatureTests.swift
│   └── RestaurantsMap/
│       ├── Project.swift
│       ├── Sources/
│       │   ├── RestaurantsMapFeature.swift
│       │   ├── RestaurantsMapView.swift
│       │   └── MapViewRepresentable.swift
│       └── Tests/
│           └── RestaurantsMapFeatureTests.swift
└── App/
    ├── Project.swift
    └── Sources/
        ├── AppFeature.swift             # StackState navigation
        ├── AppView.swift
        └── CoolRestaurantsApp.swift     # @main
```

**Structure Decision**: Option 3 (modular iOS). Feature modules are static frameworks linked by the App target.

## Complexity Tracking

No constitution violations. No complexity justification needed.
