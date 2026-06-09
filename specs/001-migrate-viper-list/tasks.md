---
description: "Tasks: migrate the VIPER List module to a TCA feature"
---

# Tasks: Migrate VIPER List module to a TCA feature

**Input**: `specs/001-migrate-viper-list/{spec.md, plan.md}` · **Constitution**: `.specify/memory/constitution.md`

**Tests**: MANDATORY (Constitution V) — Swift Testing + TCA `TestStore`, no XCTest.

**Migration task shape**: one task ≈ one file/type under `workspace/output/`; dependency-ordered
after the Core/foundation modules. Format: `[ID] [P?] [Story] Description (path)`.

## Phase 1 — Foundation: `Core/SharedModels` (blocks everything)

- **T001** `[P]` `[Setup]` Create the SharedModels Tuist module (`Core/SharedModels/Project.swift` via `Project.core`).
- **T002** `[P]` `[US1]` Add `TodoItem` value model (`Core/SharedModels/Sources/TodoItem.swift`).
- **T003** `[P]` `[US1]` Add `NearTermDateRelation` enum + title/image/`displayOrder` (`.../NearTermDateRelation.swift`).
- **T004** `[US1]` Port the date logic — `nearTermRelation(for:relativeToToday:)` and `upcomingSections(from:today:)` from `NSCalendar+CalendarAdditions` / `UpcomingDisplayDataCollection` (`.../Sources/Upcoming.swift`).
- **T005** `[US1]` Tests: relation buckets (today/tomorrow/later-this-week/next-week/out-of-range) + section ordering (`.../Tests/UpcomingTests.swift`). → satisfies SC-001, SC-002.

## Phase 2 — `Core/Persistence`

- **T006** `[P]` Create the Persistence module (`Core/Persistence/Project.swift`, deps: TCA + SharedModels).
- **T007** Define `TodosClient` `@DependencyClient` (`fetch(start,end)`, `add(item)`) + in-memory `liveValue`; replaces `ListDataManager`/CoreData (`.../Persistence/Sources/TodosClient.swift`). `TODO(migration)`: CoreData backing.

## Phase 3 — `Features/List`

- **T008** Create the List module (`Features/List/Project.swift`, deps: TCA + SharedModels + Persistence; **not** Add).
- **T009** `[US1]` `ListFeature` reducer: `onAppear`/`refresh` → `todosClient.fetch` (window via `@Dependency(\.date)` + `\.calendar`) → `itemsResponse`; `State.sections`/`isEmpty` computed (`Features/List/Sources/ListFeature.swift`). → FR-001..FR-004.
- **T010** `[US2]` `addButtonTapped` → `delegate(.addTodoRequested)` (parent owns the sheet) (same file). → FR-005.
- **T011** `[US1]` `ListView`: grouped sections, no-content state, Add toolbar button (`Features/List/Sources/ListView.swift`).
- **T012** `[US1]` Tests: loads items on appear; Add button emits the delegate (`Features/List/Tests/ListFeatureTests.swift`).

## Phase 4 — Gate

- **T013** Run `scripts/build_check.sh workspace/output List` → must reach `BUILD_CHECK: GREEN` (Constitution VII). → SC-003, SC-004.

## Dependencies

- T001 → T002–T005; T006 → T007; (T002, T004, T007) → T008–T012; all → T013.
- Reload-on-save (FR-006/FR-007) is wired in the **App** (owns the Add `@Presents` sheet, maps `Add.delegate(.saved)` → `List.refresh`) — tracked in a separate Add/App feature, out of scope for this file.

## Parallel example

`T001`, `T006` (module scaffolds) and `T002`, `T003` (independent model files) can run in parallel `[P]`.
