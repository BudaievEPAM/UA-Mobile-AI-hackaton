# Tasks: CoolRestaurants — VIPER+RxSwift → TCA Migration

**Input**: Design documents from `specs/006-app-root/` (+ sibling specs 002–005)

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: MANDATORY (Constitution V). Every migrated reducer ships a Swift Testing `TestStore` suite (≥1 happy + ≥1 failure path, `@MainActor`). No `import XCTest`. A module task is done only when it builds and tests pass green (Constitution VII).

**Migration task shape**: one task ≈ one Tuist module under `workspace/output/CoolRestaurants/`, dependency-ordered.

**Output root**: `workspace/output/CoolRestaurants/`

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (no dependency on concurrent tasks)
- **[Story]**: User story label: US-MAP1 (Map US1), US-MAP2 (Map US2), US-MAP3 (Map US3), US-DET1 (Detail US1), US-APP1 (App US1), US-APP2 (App US2)
- All paths relative to `workspace/output/CoolRestaurants/`

---

## Phase 1: Setup — Tuist Workspace

**Purpose**: Create the generating Tuist workspace skeleton. Nothing else can proceed until `tuist generate` succeeds on the empty workspace.

- [ ] T001 Create output directory and Workspace.swift — `Workspace.swift` (projects: App, Core/**, Features/**)
- [ ] T002 Create `Tuist/Package.swift` with TCA 1.25.2 dependency and `ComposableArchitecture: .framework` productType setting
- [ ] T003 Create `Tuist/ProjectDescriptionHelpers/Project+Module.swift` — copy from `knowledge/tuist-templates/ProjectDescriptionHelpers/Project+Module.swift` (feature/core/app factory methods)
- [ ] T004 Verify `tuist generate` succeeds on the empty workspace (zero targets is acceptable; goal is no manifest errors)

**Checkpoint**: `tuist generate` exits 0. Workspace file exists.

---

## Phase 2: Foundational — Core/SharedModels

**Purpose**: `Restaurant` model. **Blocks every other module.**

⚠️ **CRITICAL**: No feature or networking module can be written until this phase is complete and building.

- [ ] T005 Create `Core/SharedModels/Project.swift` — `Project.core(name: "SharedModels", hasTests: true, dependencies: [])`
- [ ] T006 Create `Core/SharedModels/Sources/Restaurant.swift` — `struct Restaurant: Equatable, Sendable, Identifiable` with fields: `id: String` (was `identifier`), `name: String`, `coordinate: CLLocationCoordinate2D`, `address: String?`, `categoryName: String?`, `caregoryIconURL: URL?`; add `var categoryIconURL: URL? { caregoryIconURL }` alias; implement `==` explicitly comparing coordinate lat/lon as Double
- [ ] T007 Create `Core/SharedModels/Tests/RestaurantTests.swift` — `@Suite @MainActor struct RestaurantTests`; `@Test func equalityHolds()`, `@Test func nilFieldsEquality()`, `@Test func identifiableUsesId()` — all using Swift Testing `#expect`
- [ ] T008 Verify `Core/SharedModels` module builds and tests pass: `tuist generate && xcodebuild test -scheme SharedModels | xcsift`

**Checkpoint**: `SharedModelsTests` suite: GREEN. Other modules may now be written.

---

## Phase 3: Core/Networking — RestaurantClient + LocationClient

**Purpose**: Both `@DependencyClient` types. **Blocks `Features/RestaurantsMap`** (not RestaurantsDetail).

- [ ] T009 Create `Core/Networking/Project.swift` — `Project.core(name: "Networking", dependencies: [.project(target: "SharedModels", path: "../../Core/SharedModels"), .external(name: "ComposableArchitecture")])`
- [ ] T010 Create `Core/Networking/Sources/Internal/MKCoordinateRegion+Radius.swift` — port `getRadiusInMetersForRegion` as a free function + `EquatableRegion` struct (Equatable, Sendable) wrapping center lat/lon + span deltas as Doubles; `contains(coordinate:)` method
- [ ] T011 Create `Core/Networking/Sources/Internal/FoursquareResponse.swift` — internal `Decodable` structs for Foursquare v2 `venues/search` JSON response (`FoursquareSearchResponse`, `FoursquareVenue`, `FoursquareLocation`, `FoursquareCategory`, `FoursquareIcon`)
- [ ] T012 Create `Core/Networking/Sources/RestaurantClient.swift` — `@DependencyClient struct RestaurantClient { var getRestaurants: (_ region: MKCoordinateRegion) async throws -> [Restaurant] }`; `liveValue` calls `URLSession.shared.data(from: foursquareURL(region:))` + decodes `FoursquareSearchResponse` → `[Restaurant]`; `previewValue` returns 11 deterministic mock restaurants matching `MockRestaurantRepositoryImplementation` logic; `DependencyValues` extension
- [ ] T013 Create `Core/Networking/Sources/LocationClient.swift` — `@DependencyClient struct LocationClient { var getLocationAuthorizationStatus: () async throws -> CLAuthorizationStatus; var requestLocationAuthorization: () async throws -> CLAuthorizationStatus; var getCurrentLocation: () async throws -> CLLocation }`; `liveValue` uses `CLLocationManager` with `withCheckedThrowingContinuation` delegate bridge; `previewValue` returns `.authorizedWhenInUse` + Amsterdam `CLLocation(52.370216, 4.895168)`; `DependencyValues` extension
- [ ] T014 Create `Core/Networking/Tests/NetworkingTests.swift` — `@Suite @MainActor struct NetworkingTests`; `@Test func previewRestaurantsReturnsMockData()` (11 restaurants, no network); `@Test func previewLocationReturnsAmsterdam()` (coordinate matches mock); `@Test func equatableRegionContains()` (region contains its own center); `@Test func equatableRegionExcludes()` (remote point outside)
- [ ] T015 Verify `Core/Networking` builds and tests pass: `tuist generate && xcodebuild test -scheme Networking | xcsift`

**Checkpoint**: `NetworkingTests` suite: GREEN.

---

## Phase 4a: Features/RestaurantsDetail — Leaf display feature (P1)

**Depends on**: Phase 2 (SharedModels). **Can run in parallel with Phase 4b** once Phase 3 is not yet needed here.

**Goal (US-DET1)**: Display restaurant name, category, address, and icon from `State.restaurant`.

**Independent Test**: `TestStore(initialState: RestaurantsDetailFeature.State(restaurant: mock))` + `onAppear` → no effects, state unchanged.

- [ ] T016 [P] [US-DET1] Create `Features/RestaurantsDetail/Project.swift` — `Project.feature(name: "RestaurantsDetail", dependencies: [.project(target: "SharedModels", path: "../../Core/SharedModels"), .external(name: "ComposableArchitecture")])`
- [ ] T017 [P] [US-DET1] Create `Features/RestaurantsDetail/Sources/RestaurantsDetailFeature.swift` — `@Reducer struct RestaurantsDetailFeature`; `@ObservableState struct State: Equatable { let restaurant: Restaurant }`; `enum Action { case onAppear }`; `body` returns `.none` for `onAppear`
- [ ] T018 [US-DET1] Create `Features/RestaurantsDetail/Sources/RestaurantsDetailView.swift` — `struct RestaurantsDetailView: View { let store: StoreOf<RestaurantsDetailFeature> }`; displays `store.restaurant.name` as `navigationTitle`; `store.restaurant.categoryName ?? ""` as `Text`; `store.restaurant.address ?? ""` as `Text`; `AsyncImage(url: store.restaurant.caregoryIconURL)` with placeholder; `.onAppear { store.send(.onAppear) }`
- [ ] T019 [US-DET1] Create `Features/RestaurantsDetail/Tests/RestaurantsDetailFeatureTests.swift` — `@Suite @MainActor struct RestaurantsDetailFeatureTests`; `@Test func onAppearNoEffects()` — full TestStore assertion; `@Test func nilFieldsDoNotCrash()` — State with all-nil optionals, `onAppear` asserted clean
- [ ] T020 [US-DET1] Verify `Features/RestaurantsDetail` builds and tests pass: `tuist generate && xcodebuild test -scheme RestaurantsDetail | xcsift`

**Checkpoint (US-DET1)**: `RestaurantsDetailFeatureTests` suite: GREEN.

---

## Phase 4b: Features/RestaurantsMap — Main feature (P1)

**Depends on**: Phase 2 (SharedModels) + Phase 3 (Networking). **Can run in parallel with Phase 4a** (different module, different files).

**Goal (US-MAP1/US-MAP2/US-MAP3)**: Location state machine, restaurant fetch with dedup, alert for denied permission, annotation tap → delegate navigation.

**Independent Test (US-MAP1)**: `TestStore` + `LocationClient` (.authorizedWhenInUse, Amsterdam) + `RestaurantClient` (3 mock) → `onAppear` → `state.restaurants.count == 3`.

**Independent Test (US-MAP2)**: `TestStore` + `LocationClient` (.denied) → `onAppear` → `state.alert != nil`.

**Independent Test (US-MAP3)**: `TestStore` → `.restaurantAnnotationTapped(mock)` → `.delegate(.showDetail(mock))` received.

- [ ] T021 [P] [US-MAP1] Create `Features/RestaurantsMap/Project.swift` — `Project.feature(name: "RestaurantsMap", dependencies: [SharedModels, Networking, ComposableArchitecture])`
- [ ] T022 [P] [US-MAP1] Create `Features/RestaurantsMap/Sources/RestaurantsMapFeature.swift` — `@Reducer struct RestaurantsMapFeature`; `@ObservableState struct State: Equatable` with fields per data-model.md (restaurants, userLocation, fetchedRegion: EquatableRegion?, isLoadingLocation, `@Presents var alert: AlertState<Action.Alert>?`); full `Action` enum (onAppear, onResume, locationAuthorizationResponse, locationResponse, mapRegionChanged, restaurantsResponse, restaurantAnnotationTapped, openSettingsButtonTapped, alert, delegate); `body` with complete location state machine + restaurant fetch + cancellable(id: CancelID.restaurantFetch, cancelInFlight: true)
- [ ] T023 [US-MAP1] Create `Features/RestaurantsMap/Sources/MapViewRepresentable.swift` — `struct MapViewRepresentable: UIViewRepresentable`; `Coordinator: NSObject, MKMapViewDelegate`; `makeCoordinator()` captures store; `mapView(_:regionDidChangeAnimated:)` sends `.mapRegionChanged(region)` with 0.5s debounce; `mapView(_:annotationView:calloutAccessoryControlTapped:)` sends `.restaurantAnnotationTapped(restaurant)`; `updateUIView` adds/removes `MKPointAnnotation` subclass wrapping `Restaurant`
- [ ] T024 [US-MAP1] Create `Features/RestaurantsMap/Sources/RestaurantsMapView.swift` — `struct RestaurantsMapView: View { let store: StoreOf<RestaurantsMapFeature> }`; `NavigationStack`-compatible root; embeds `MapViewRepresentable(store: store)`; `.alert($store.scope(state: \.alert, action: \.alert))`; `.onAppear { store.send(.onAppear) }`; `.onDisappear` / scene phase handling for `onResume`
- [ ] T025 [US-MAP1] Create `Features/RestaurantsMap/Tests/RestaurantsMapFeatureTests.swift` — `@Suite @MainActor struct RestaurantsMapFeatureTests` with:
  - `@Test func happyPath_authorizedLocation_restaurantsLoaded()` — TestStore overriding `locationClient` + `restaurantClient`; exhaustive effect assertions
  - `@Test func deniedLocation_alertShown()` — TestStore with denied location client; asserts `state.alert != nil`
  - `@Test func regionChangeDedup_noSecondFetch()` — sends two `mapRegionChanged` with same-area region; asserts only one restaurantsResponse received
  - `@Test func restaurantAnnotationTapped_emitsDelegateAction()` — asserts `.delegate(.showDetail(restaurant))` emitted
  - `@Test func fetchError_resetsFetchedRegion()` — error path; asserts `fetchedRegion == nil`
- [ ] T026 [US-MAP1] Verify `Features/RestaurantsMap` builds and tests pass: `tuist generate && xcodebuild test -scheme RestaurantsMap | xcsift`

**Checkpoint (US-MAP1/2/3)**: `RestaurantsMapFeatureTests` suite (5 tests): GREEN.

---

## Phase 5: App — Composition Root + Stack Navigation

**Depends on**: Phases 4a + 4b both GREEN.

**Goal (US-APP1/US-APP2)**: `@main` App struct; `AppFeature` with `StackState` navigation; map as root; detail pushed on delegate.

**Independent Test (US-APP1)**: `TestStore` for AppFeature; initial `state.path.isEmpty`; `state.map` is a valid `RestaurantsMapFeature.State`.

**Independent Test (US-APP2)**: Send `.map(.delegate(.showDetail(mock)))`; assert `state.path.count == 1`; assert path[0] is `.detail` with correct restaurant.

- [ ] T027 Create `App/Project.swift` — `Project.app(name: "CoolRestaurants", dependencies: [RestaurantsMap, RestaurantsDetail, SharedModels, Networking, ComposableArchitecture])`
- [ ] T028 Create `App/Sources/AppFeature.swift` — `@Reducer struct AppFeature`; `@ObservableState struct State: Equatable { var map = RestaurantsMapFeature.State(); var path = StackState<Path.State>() }`; `enum Action { case map(RestaurantsMapFeature.Action); case path(StackActionOf<Path>) }`; `@Reducer enum Path { case detail(RestaurantsDetailFeature) }`; `body`: `Scope(state: \.map, action: \.map) { RestaurantsMapFeature() }` + `Reduce` handling `.map(.delegate(.showDetail(r)))` → `state.path.append(.detail(.init(restaurant: r)))` + `.forEach(\.path, action: \.path) { Path() }`
- [ ] T029 Create `App/Sources/AppView.swift` — `struct AppView: View { let store: StoreOf<AppFeature> }`; `NavigationStack(path: $store.scope(state: \.path, action: \.path))` with root `RestaurantsMapView(store: store.scope(state: \.map, action: \.map))`; `destination` switch on `store.case`: `.detail(store)` → `RestaurantsDetailView(store: store)`
- [ ] T030 Create `App/Sources/CoolRestaurantsApp.swift` — `@main struct CoolRestaurantsApp: App`; `static let store = Store(initialState: AppFeature.State()) { AppFeature() }`; `#if DEBUG` + `MOCK` flag: `withDependencies { $0.restaurantClient = .previewValue; $0.locationClient = .previewValue } operation: { Self.store }` pattern; `WindowGroup { AppView(store: Self.store) }`
- [ ] T031 Create `App/Sources/AppFeatureTests.swift` (place in `App/Tests/`) — `@Suite @MainActor struct AppFeatureTests`; `@Test func initialState_mapIsRoot()`, `@Test func delegateShowDetail_pushesPath()`, `@Test func pathPopped_returnsToMap()`
- [ ] T032 Verify `App` module builds and full test suite passes: `tuist generate && xcodebuild test -scheme CoolRestaurants | xcsift`

**Checkpoint (US-APP1/APP2)**: All app tests GREEN.

---

## Phase 6: Polish & Green Gate

**Purpose**: Full integration build check, verify constitution compliance, clean up.

- [ ] T033 [P] Run full build check: `bash scripts/build_check.sh workspace/output/CoolRestaurants` — must print `BUILD_CHECK: GREEN`; fix any remaining errors (re-run until green)
- [ ] T034 [P] Verify zero `import XCTest`, zero `ViewStore`, zero `WithViewStore`, zero `UINavigationController` in output: `grep -r "import XCTest\|ViewStore\|UINavigationController\|BasePresenter\|BaseCoordinator" workspace/output/CoolRestaurants/`
- [ ] T035 [P] Verify zero `@unchecked Sendable` in output: `grep -r "@unchecked Sendable" workspace/output/CoolRestaurants/`
- [ ] T036 Run migration reporter: `$agent-migration-reporter` → `workspace/output/CoolRestaurants/MIGRATION_REPORT.md`

**Checkpoint**: `BUILD_CHECK: GREEN`. Zero constitution violations. Report generated.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (SharedModels)         ← blocks everything
        └── Phase 3 (Networking)     ← blocks RestaurantsMap
              ├── Phase 4a (Detail)  ← parallel with 4b; needs only SharedModels
              └── Phase 4b (Map)     ← needs SharedModels + Networking
                    └── Phase 5 (App) ← needs 4a + 4b both green
                          └── Phase 6 (Polish)
```

### User Story → Module Map

| User Story | Module | Phase |
|---|---|---|
| US-DET1: View restaurant details | Features/RestaurantsDetail | 4a |
| US-MAP1: Discover restaurants near location | Features/RestaurantsMap | 4b |
| US-MAP2: Handle denied permission | Features/RestaurantsMap | 4b |
| US-MAP3: Navigate to restaurant detail | Features/RestaurantsMap + App | 4b + 5 |
| US-APP1: App launches to map | App | 5 |
| US-APP2: Map → detail navigation | App | 5 |

### Parallel Opportunities

- **T016–T020** (RestaurantsDetail) can start as soon as Phase 2 is GREEN — no need to wait for Phase 3
- **T021–T026** (RestaurantsMap) must wait for Phase 3 GREEN
- **T016–T020** and **T021–T026** can run concurrently (different Tuist modules, different files)
- **T033–T035** (verification checks) can run in parallel once T032 is complete

---

## Parallel Execution Example: Phases 4a + 4b

```
After Phase 3 (Networking) GREEN:
  Agent A: T016 → T017 → T018 → T019 → T020  (RestaurantsDetail)
  Agent B: T021 → T022 → T023 → T024 → T025 → T026  (RestaurantsMap)
  → both finish → Phase 5 can begin
```

---

## Implementation Strategy

### MVP Scope (single feature demo)

1. Phase 1: Setup workspace
2. Phase 2: SharedModels — GREEN
3. Phase 3: Networking — GREEN
4. Phase 4a: RestaurantsDetail — GREEN (smallest feature, demonstrates migration pattern)
5. **STOP + VALIDATE**: Detail feature is a complete, green TCA module

### Full Migration

1–4 as above, then:
5. Phase 4b: RestaurantsMap — GREEN
6. Phase 5: App — GREEN
7. Phase 6: `BUILD_CHECK: GREEN` + report

### Agent Swarm Strategy

- **Agent 1 (scaffolder)**: T001–T008 (workspace + SharedModels)
- **Agent 2 (networking)**: T009–T015 (Networking clients)
- **Agent 3 (detail migrator)**: T016–T020 (RestaurantsDetail) ← after Agent 1 done
- **Agent 4 (map migrator)**: T021–T026 (RestaurantsMap) ← after Agents 1+2 done
- **Agent 5 (app migrator)**: T027–T032 (App) ← after Agents 3+4 done
- **Agent 6 (build doctor)**: T033–T036 ← after Agent 5 done

---

## Notes

- Constitution VII: **green is done** — a task is not complete until its module's test scheme passes
- All test files use `import Testing` (Swift Testing), never `import XCTest`
- `@DependencyClient` synthesises `testValue` automatically; tests must override only what they exercise
- `EquatableRegion` (in Core/Networking) bridges the gap between `MKCoordinateRegion` (not Equatable) and TCA's `State: Equatable` requirement
- Foursquare API credentials (client_id/secret) copied verbatim from source; not secrets-managed in this scope
- `#if MOCK` compilation condition is reproduced via `MOCK=1` xcconfig in a Debug/Mock Tuist configuration
