# Feature Specification: Restaurants Detail Feature

**Feature Branch**: `004-restaurants-detail`

**Created**: 2026-06-06

**Status**: Draft

**Input**: CoolRestaurants VIPER→TCA migration — Features/RestaurantsDetail module

## Migration Context

- **Source feature**: `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/UI/RestaurantsDetail/`
  - `RestaurantsDetailContracts.swift` — `RestaurantsDetailView`, `RestaurantsDetailUserActionsListener`, `RestaurantsDetailRouter` protocols
  - `RestaurantsDetailPresenter.swift` — calls `showTitle(title:)` + `showRestaurant(restaurant:)` on `initialize()`
  - `RestaurantsDetailViewController.swift` — UIKit labels + SDWebImage
  - `RestaurantsDetailCoordinator.swift` — pushes VC onto parent `UINavigationController`
- **Source architecture**: VIPER — Presenter + Coordinator(Router) + UIViewController(View). No Interactor; no async effects.
- **Target TCA module**: `Features/RestaurantsDetail` (depends on `Core/SharedModels` only)
- **Component mapping**:

  | Source component | → TCA target |
  |---|---|
  | `RestaurantsDetailPresenter.initialize()` → `showTitle` + `showRestaurant` | `RestaurantsDetailFeature.body` — `onAppear` action is a no-op beyond conformance; `restaurant` lives in `State` from init |
  | `RestaurantsDetailPresenter.restaurant: Restaurant` (stored property) | `RestaurantsDetailFeature.State.restaurant: Restaurant` |
  | `RestaurantsDetailViewController` (UIKit) | `RestaurantsDetailView` (SwiftUI) reading `store.restaurant` |
  | `SDWebImage` for category icon | SwiftUI `AsyncImage(url: store.restaurant.caregoryIconURL)` |
  | `RestaurantsDetailCoordinator.start()` (push) | Parent `AppFeature` handles stack push; this feature has no routing |
  | `RestaurantsDetailCoordinator.close()` (pop) | SwiftUI stack `.navigationDestination` pop — no action needed |
  | `RestaurantsDetailRouter` (empty protocol) | deleted |

- **Behavior to preserve**: Display restaurant `name` as navigation title, `categoryName` as label, `address` as label, `caregoryIconURL` as async image. All fields may be nil.

## User Scenarios & Testing

### User Story 1 — View restaurant details after selection (Priority: P1)

After tapping a restaurant annotation on the map, the user is navigated to a detail screen showing the restaurant's name, category, address, and category icon.

**Why this priority**: Core user journey — the only purpose of this feature.

**Independent Test**: Create a `TestStore` with a `State` containing a known `Restaurant`; send `onAppear`; verify no unexpected effects fire and state is unchanged (data is already in state from init).

**Acceptance Scenarios**:

1. **Given** a `Restaurant` with all fields populated, **When** the detail view appears, **Then** the name is shown as the navigation title, category and address are shown as text, and the icon image begins loading.
2. **Given** a `Restaurant` with nil `address` and nil `categoryName`, **When** the detail view appears, **Then** those fields display a graceful empty/placeholder state (no crash).
3. **Given** a `Restaurant` with an invalid or nil `caregoryIconURL`, **When** the detail view appears, **Then** a placeholder image is shown (no crash).

---

### Edge Cases

- All optional fields (`address`, `categoryName`, `caregoryIconURL`) being nil simultaneously must not cause a crash.
- Very long restaurant names must not overflow or truncate the navigation title in an unexpected way.

## Requirements

### Functional Requirements

- **FR-001**: `RestaurantsDetailFeature.State` MUST hold `restaurant: Restaurant` as a let constant (no mutation in this feature).
- **FR-002**: The SwiftUI view MUST display `store.restaurant.name` as the navigation title.
- **FR-003**: The SwiftUI view MUST display `store.restaurant.categoryName` (or a placeholder if nil).
- **FR-004**: The SwiftUI view MUST display `store.restaurant.address` (or a placeholder if nil).
- **FR-005**: The SwiftUI view MUST display the category icon from `store.restaurant.caregoryIconURL` using async image loading; a placeholder shown while loading or on error.
- **FR-006**: The feature MUST have no outbound navigation actions (it is a leaf); back navigation is handled by the SwiftUI stack.
- **FR-007**: The module MUST compile under Swift 6 strict concurrency with no warnings.
- **FR-008**: No `import XCTest` may appear in test files; tests use Swift Testing.

### Key Entities

- **Restaurant**: `Core/SharedModels.Restaurant` — passed in as `State.restaurant`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `Features/RestaurantsDetail` generates and builds with zero errors and zero warnings.
- **SC-002**: A Swift Testing `@Suite` with at least one happy-path test and one nil-fields test passes.
- **SC-003**: The SwiftUI preview renders correctly with both a fully-populated and a nil-fields `Restaurant`.

## Assumptions

- The feature receives a fully initialised `Restaurant` from the parent (no loading state needed).
- `SDWebImage` is replaced by native SwiftUI `AsyncImage`; no third-party image library is added to the TCA project.
- The navigation back button (pop) is standard SwiftUI stack behaviour and requires no custom action.
