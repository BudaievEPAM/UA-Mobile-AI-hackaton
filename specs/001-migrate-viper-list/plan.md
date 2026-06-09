# Implementation Plan: Migrate VIPER List module to a TCA feature

**Branch**: `001-migrate-viper-list` | **Date**: 2026-06-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-migrate-viper-list/spec.md`

## Summary

Replace the VIPER List module (Interactor + Presenter + Wireframe + CoreData DataManager) with a
single TCA feature module. The date-grouping logic (`nearTermRelationForDate` + section assembly)
moves to pure, unit-tested functions in `SharedModels`; data access becomes a `TodosClient`
`@Dependency`; "today" becomes `@Dependency(\.date)`; the Add request and reload-on-save are
delegated to the parent (App). Per the migration constitution, the Presenter/Interactor/Wireframe
are deleted, not ported.

## Technical Context

**Language/Version**: Swift 6 (language mode), `@Reducer`/`@ObservableState` (Observation)

**Primary Dependencies**: `swift-composable-architecture` 1.25.2 (pinned); SwiftUI

**Storage**: `TodosClient` dependency over an in-memory actor store (CoreData backing deferred — `TODO(migration)`)

**Testing**: Swift Testing (`@Suite`/`@Test`/`#expect`) + TCA `TestStore`

**Target Platform**: iOS 17+ (modules multiplatform → also build/test on macOS where no iOS simulator runtime is installed)

**Project Type**: Modular mobile app (Tuist-generated workspace)

**Performance Goals**: N/A (UI feature); date logic is O(n) over the visible window

**Constraints**: No `ViewStore`; no singletons; state-driven navigation only; behavior parity with source

**Scale/Scope**: One feature module + shared model/logic; ~3 reducer actions, 2 dependencies, ≥4 tests

## Constitution Check

*GATE: validated against [.specify/memory/constitution.md](../../.specify/memory/constitution.md).*

- **I. TCA only / no residue**: ✅ Presenter/Interactor/Wireframe deleted; `@Reducer` + `@ObservableState`; no `ViewStore`.
- **II. Modular by feature**: ✅ `Features/List` depends only on `Core/{SharedModels,Persistence}`; never on `Add`.
- **III. State-driven navigation**: ✅ Add is requested via `delegate(.addTodoRequested)`; parent owns the `@Presents` sheet.
- **IV. All I/O is a dependency**: ✅ CoreData/DataManager → `TodosClient`; clock → `@Dependency(\.date)`.
- **V. Swift Testing + TestStore**: ✅ date logic + reducer covered; no XCTest.
- **VI. Behavior parity**: ✅ grouping/order/no-content/reload preserved (spec FR-001..FR-007).
- **VII. Green is done**: ✅ gated by `scripts/build_check.sh` (tuist + xcodebuild + xcsift).

No violations — no complexity-tracking entries required.

## Project Structure

### Source Code (target — generated under `workspace/output/`)

```text
Core/
├── SharedModels/
│   ├── Sources/{TodoItem.swift, NearTermDateRelation.swift, Upcoming.swift}   # pure logic
│   └── Tests/UpcomingTests.swift                                              # date-relation tests
└── Persistence/
    └── Sources/TodosClient.swift                                             # @DependencyClient

Features/
└── List/
    ├── Sources/{ListFeature.swift, ListView.swift}                           # @Reducer + SwiftUI
    └── Tests/ListFeatureTests.swift                                          # TestStore

App/                          # owns the Add @Presents sheet + reload-on-save (separate Add feature)
```

### Key design decisions

- **Pure date logic in `SharedModels`** (free functions) so the trickiest VIPER code is trivially testable.
- **Sections are a computed property** of `State` (`upcomingSections(from:today:)`) — no stored display models.
- **Parent-owned Add**: keeps `List`/`Add` decoupled (Constitution II); the App maps `Add.delegate(.saved)` → `List.refresh`.

## Complexity Tracking

None — the plan introduces no constitution violations or extra projects.
