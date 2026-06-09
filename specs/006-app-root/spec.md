# Feature Specification: App Root (Composition Root + Navigation)

**Feature Branch**: `006-app-root`

**Created**: 2026-06-06

**Status**: Draft

**Input**: CoolRestaurants VIPER→TCA migration — App module (composition root, StackState navigation)

## Migration Context

- **Source feature**:
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/AppDelegate.swift` — `UIApplicationMain`, `UIWindow` bootstrap, `#if MOCK` injection, `RestaurantsMapCoordinator(window:).start()`
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/UI/Common/BaseCoordinator.swift` + `Coordinator.swift` — coordinator tree root
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/UI/RestaurantsMap/RestaurantsMapCoordinator.swift` — sets `window.rootViewController = UINavigationController(...)`
- **Source architecture**: VIPER — `AppDelegate` as composition root + `BaseCoordinator`/`RestaurantsMapCoordinator` for navigation. No UISceneDelegate.
- **Target TCA module**: `App` (depends on all feature modules + `Core/*`; is the composition root)
- **Component mapping**:

  | Source component | → TCA target |
  |---|---|
  | `AppDelegate` / `UIWindow` bootstrap | `@main` SwiftUI `App` struct + `WindowGroup` |
  | `RestaurantsMapCoordinator.start()` sets root VC | `NavigationStack` driven by `AppFeature` `StackState` |
  | `RestaurantsMapCoordinator.goToRestaurantDetail` (push) | `AppFeature` handles `.map(.delegate(.showDetail(r)))` → `path.append(.detail(State(restaurant:r)))` |
  | `RestaurantsDetailCoordinator.close()` (pop) | SwiftUI stack pop (automatic on `.navigationDestination`) |
  | `#if MOCK` → `RepositoryInjection.shared.restaurantRepositoy = MockRestaurantRepositoryImplementation.instance` | `withDependencies { $0.restaurantClient = .previewValue; $0.locationClient = .previewValue }` in the `App` struct under `#if DEBUG` |
  | All `BaseCoordinator` / `Coordinator` protocol files | deleted |

- **Behavior to preserve**:
  - App launches directly to the map screen (no splash/onboarding).
  - Selecting a restaurant navigates to the detail screen (push, back button returns to map).
  - `#if MOCK` build flag behaviour reproduced via `#if DEBUG` + `withDependencies` override.

## User Scenarios & Testing

### User Story 1 — App launches to the restaurant map (Priority: P1)

The app starts and the first screen the user sees is the restaurants map, centred on their location.

**Why this priority**: The initial launch experience — nothing else works without this.

**Independent Test**: `AppFeature` `TestStore` with initial `path = []`; assert the map feature state is present as the root; no unexpected actions fire on init.

**Acceptance Scenarios**:

1. **Given** the app is cold-launched, **When** the root view appears, **Then** the `RestaurantsMapView` is displayed as the root screen.
2. **Given** the app is launched with `#if DEBUG` mock dependencies, **When** the map appears, **Then** mock Amsterdam location + mock restaurants are used.

---

### User Story 2 — Navigate from map to restaurant detail (Priority: P1)

Tapping an annotation on the map navigates to the detail screen; back navigation returns to the map.

**Why this priority**: Core navigation flow connecting the two features.

**Independent Test**: `AppFeature` `TestStore`; send `.map(.delegate(.showDetail(mockRestaurant)))`; assert `state.path` contains one `.detail` entry with the expected restaurant.

**Acceptance Scenarios**:

1. **Given** the map is showing and a restaurant is selected, **When** `delegate(.showDetail(restaurant))` is received, **Then** `path` gains a `.detail(State(restaurant:))` entry and the detail view is pushed.
2. **Given** the detail view is shown, **When** the user taps the back button, **Then** `path` is popped and the map is shown again.

---

### Edge Cases

- Deep back-navigation: if somehow `path` has multiple entries, popping all returns to the map root.
- `#if DEBUG` mock flag must not affect release builds.

## Requirements

### Functional Requirements

- **FR-001**: `AppFeature` MUST use `StackState<AppFeature.Path>` for navigation with path cases `.detail(RestaurantsDetailFeature.State)`.
- **FR-002**: `AppFeature.body` MUST scope the `RestaurantsMapFeature` as the root and handle its `delegate` actions to push onto the stack.
- **FR-003**: `.navigationDestination(store:)` MUST be used (TCA navigation API) — no `NavigationLink` with value.
- **FR-004**: The `@main` `App` struct MUST use `WindowGroup { NavigationStackStore(…) { AppView() } }`.
- **FR-005**: Under `#if DEBUG`, `withDependencies` MUST override `restaurantClient` and `locationClient` with their `previewValue` when the `MOCK` compilation flag is set.
- **FR-006**: All `BaseCoordinator`, `Coordinator`, `BasePresenter`, `BaseContract` files MUST NOT appear in the TCA output.
- **FR-007**: `AppDelegate` is replaced by the SwiftUI `@main App` struct; no `UIApplicationDelegate`.
- **FR-008**: The module MUST compile under Swift 6 strict concurrency with no warnings.
- **FR-009**: No `import XCTest`; `AppFeature` tests use Swift Testing + `TestStore`.

### Key Entities

- **AppFeature.Path**: `@Reducer enum` with cases `.detail(RestaurantsDetailFeature)`.
- **AppFeature.State**: contains `mapState: RestaurantsMapFeature.State` (always present as root) + `path: StackState<Path.State>`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `App` module generates and builds with zero errors and zero warnings.
- **SC-002**: `tuist generate` succeeds; `xcodebuild build` succeeds for the App scheme.
- **SC-003**: A Swift Testing suite passes with: ≥1 launch test (initial state has map as root), ≥1 navigation test (delegate → path entry), ≥1 back-navigation test (path popped).
- **SC-004**: `scripts/build_check.sh workspace/output` reports `BUILD_CHECK: GREEN`.

## Assumptions

- The Tuist `App` target links all feature and core modules; no dynamic frameworks for this migration scope.
- The `#if MOCK` compilation condition from source is reproduced as a custom Tuist build setting `MOCK=1` in a Debug/Mock configuration, toggling `withDependencies` at the `App` struct level.
- No UIScene / multi-window support is required.
- TCA's built-in `StackState` navigation is sufficient; no custom navigation container is needed.
