# Feature Specification: Restaurants Map Feature

**Feature Branch**: `005-restaurants-map`

**Created**: 2026-06-06

**Status**: Draft

**Input**: CoolRestaurants VIPER→TCA migration — Features/RestaurantsMap module

## Migration Context

- **Source feature**: `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/UI/RestaurantsMap/`
  - `RestaurantsMapContracts.swift` — View/UserActionsListener/Router protocols
  - `RestaurantsMapPresenter.swift` — location state machine, restaurant fetch with dedup, routing
  - `RestaurantsMapViewController.swift` — MKMapView, annotation selection, region change callbacks
  - `RestaurantsMapCoordinator.swift` — wires VC+Presenter, starts UINavigationController
- **Source architecture**: VIPER — Presenter (business logic) + Coordinator (routing + wiring) + UIViewController (View). RxSwift `DisposeBag` manages subscriptions.
- **Target TCA module**: `Features/RestaurantsMap` (depends on `Core/SharedModels`, `Core/Networking`)
- **Component mapping**:

  | Source component | → TCA target |
  |---|---|
  | `RestaurantsMapPresenter.checkLocationPermission()` | `.onAppear` + `.onResume` actions → `LocationClient.getLocationAuthorizationStatus()` effect → `.locationAuthorizationResponse` |
  | `RestaurantsMapPresenter.requestLocationPermission()` | `.locationAuthorizationResponse(.notDetermined)` → `LocationClient.requestLocationAuthorization()` effect |
  | `RestaurantsMapPresenter.onLocationPermissionSuccess()` | `.locationAuthorizationResponse(.authorizedWhen*)` → `LocationClient.getCurrentLocation()` effect → `.locationResponse` |
  | `RestaurantsMapPresenter.fetchRestaurants(region:)` + `restaurantRegion` dedup | `.mapRegionChanged(region)` → effect guarded by `state.fetchedRegion?.contains(region.center)` |
  | `restaurantsMapView?.showLocationNeededAlert()` | `state.alert = AlertState { … }` via `@Presents` |
  | `restaurantsMapView?.showLocationErrorAlert()` | `state.alert = AlertState { … }` (different message) |
  | `userTappedGoToSettings()` → `UIApplication.open` | `.openSettingsButtonTapped` → `@Dependency(\.openURL).callAsFunction(settingsURL)` |
  | `userDidSelectRestaurant(restaurant:)` | `.restaurantAnnotationTapped(restaurant)` → `.send(.delegate(.showDetail(restaurant)))` |
  | `RestaurantsMapRouter.goToRestaurantDetail` | `.delegate(.showDetail(Restaurant))` consumed by parent `AppFeature` |
  | `RestaurantsMapCoordinator` wiring | `Store(initialState:) { RestaurantsMapFeature() }` at composition root |
  | `DisposeBag` + `RxSwift.Single` subscriptions | TCA `.run { send in … }` effects using `async/await` |

- **Behavior to preserve**:
  - Check location on `viewDidLoad` (→ `onAppear`) AND `viewWillAppear` (→ `onResume`).
  - Location state machine: `notDetermined` → request → re-check; `authorized*` → get location → centre map; `denied/restricted` → show settings alert.
  - Restaurant fetch deduplicated: skip if `region.center` is contained within the previously-fetched region's span.
  - On fetch error: reset `fetchedRegion` to nil (allow retry on next region change).
  - Annotation tap → navigate to detail.

## User Scenarios & Testing

### User Story 1 — Discover restaurants near current location (Priority: P1)

On launch, the app requests location permission (if needed), centres the map on the user's location, and loads nearby restaurant annotations as the user pans.

**Why this priority**: Primary user journey and the entire purpose of the app.

**Independent Test**: Inject `LocationClient` (returns `.authorizedWhenInUse` then Amsterdam) + `RestaurantClient` (returns 3 mock restaurants); send `onAppear`; assert `state.userLocation` is set, `state.restaurants` contains 3 items.

**Acceptance Scenarios**:

1. **Given** location is `.authorizedWhenInUse`, **When** the map appears, **Then** the map is centred on the device location and restaurant annotations are loaded for the visible region.
2. **Given** the user pans to a new region outside the previously fetched area, **When** the region changes, **Then** a new restaurant fetch is triggered and annotations are updated.
3. **Given** the user pans within the previously fetched region, **When** the region changes, **Then** no new fetch is triggered (dedup).

---

### User Story 2 — Handle denied location permission gracefully (Priority: P1)

When location permission is denied, the user sees an actionable alert with a button to open Settings.

**Why this priority**: Required for a complete user experience — silently failing on denied location is unacceptable.

**Independent Test**: Inject `LocationClient` returning `.denied`; send `onAppear`; assert `state.alert` is set with the expected title.

**Acceptance Scenarios**:

1. **Given** location permission is `.denied`, **When** the map appears, **Then** an alert is shown explaining why location is needed with a "Settings" button.
2. **Given** the alert is shown, **When** the user taps "Settings", **Then** the system Settings app is opened.
3. **Given** the alert is shown, **When** the user dismisses it, **Then** the alert is cleared from state.

---

### User Story 3 — Navigate to restaurant detail (Priority: P2)

Tapping a restaurant annotation's callout navigates to the detail screen.

**Why this priority**: Completes the primary user journey; depends on RestaurantsDetail feature.

**Independent Test**: Send `.restaurantAnnotationTapped(mockRestaurant)`; assert a `.delegate(.showDetail(mockRestaurant))` action is received by a parent `TestStore`.

**Acceptance Scenarios**:

1. **Given** restaurants are displayed as annotations, **When** the user taps an annotation callout button, **Then** the `delegate(.showDetail(restaurant))` action is emitted.
2. **Given** the delegate action is emitted, **When** the parent `AppFeature` receives it, **Then** the detail screen is pushed onto the navigation stack.

---

### Edge Cases

- Network error during restaurant fetch: `fetchedRegion` resets to nil; next region change retriggers fetch.
- Location error (e.g., device has no GPS fix): `showLocationErrorAlert` state is set.
- `.restricted` authorization status: treated same as `.denied` (show alert).
- Rapid region changes (user panning quickly): only one in-flight fetch at a time (cancellation via `.cancellable(id:)`).

## Requirements

### Functional Requirements

- **FR-001**: `RestaurantsMapFeature.State` MUST contain `restaurants: [Restaurant]`, `userLocation: CLLocationCoordinate2D?`, `fetchedRegion: MKCoordinateRegion?`, `isLoadingLocation: Bool`, and `@Presents var alert: AlertState<Action.Alert>?`.
- **FR-002**: `onAppear` and `onResume` actions MUST trigger `LocationClient.getLocationAuthorizationStatus()`.
- **FR-003**: When status is `.notDetermined`, the reducer MUST call `LocationClient.requestLocationAuthorization()` and then re-check status.
- **FR-004**: When status is `.authorizedAlways` or `.authorizedWhenInUse`, the reducer MUST call `LocationClient.getCurrentLocation()` and set `state.userLocation`.
- **FR-005**: When status is `.denied` or `.restricted`, the reducer MUST set `state.alert` to a location-needed alert.
- **FR-006**: `mapRegionChanged(region:)` MUST be a no-op if `state.fetchedRegion` contains the new region center AND `state.userLocation != nil`.
- **FR-007**: On successful restaurant fetch, `state.restaurants` is replaced and `state.fetchedRegion` is set to the fetched region.
- **FR-008**: On failed restaurant fetch, `state.fetchedRegion` is reset to nil; no alert shown (silent retry on next region change, matching source behavior).
- **FR-009**: `openSettingsButtonTapped` MUST use `@Dependency(\.openURL)` to open the app settings URL.
- **FR-010**: `restaurantAnnotationTapped(restaurant:)` MUST emit `.delegate(.showDetail(restaurant))` with no state mutation.
- **FR-011**: The `MKMapView` MUST be wrapped in a `UIViewRepresentable` coordinator; no direct UIKit navigation.
- **FR-012**: The module MUST compile under Swift 6 strict concurrency with no warnings.
- **FR-013**: No `import XCTest`; all tests use Swift Testing + TCA `TestStore`.

### Key Entities

- **Restaurant**: `Core/SharedModels.Restaurant`
- **RestaurantClient**: `Core/Networking.RestaurantClient`
- **LocationClient**: `Core/Networking.LocationClient`

## Success Criteria

### Measurable Outcomes

- **SC-001**: `Features/RestaurantsMap` generates and builds with zero errors and zero warnings.
- **SC-002**: A Swift Testing `@Suite` passes with: ≥1 happy-path test (authorized → restaurants shown), ≥1 denied-location test (alert set), ≥1 dedup test (second region change in same area → no fetch).
- **SC-003**: All effect paths in the location state machine are covered by `TestStore` assertions.
- **SC-004**: Annotation tap test emits the expected delegate action.

## Assumptions

- `MKCoordinateRegion` "contains" check uses the same `latitudeDelta`/`longitudeDelta` span arithmetic as the source `contains(center:)` extension on `MKCoordinateRegion`.
- In-flight restaurant fetch is cancelled (`.cancellable(id: RestaurantsMapFeature.FetchID.self, cancelInFlight: true)`) on new region change to avoid race conditions.
- The `openURL` dependency is the TCA built-in `\.openURL`; no custom dependency needed.
- Region changes are debounced at the `UIViewRepresentable` level (0.5 s) to reduce spurious fetch actions.
