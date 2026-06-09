# Research: CoolRestaurants VIPER→TCA Migration

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

All NEEDS CLARIFICATION items resolved below.

---

## Decision 1: Foursquare API without FoursquareKit CocoaPod

**Decision**: Use `URLSession` directly in `RestaurantClient.liveValue`. Foursquare v2 API endpoint `GET https://api.foursquare.com/v2/venues/search` with params `client_id`, `client_secret`, `v=20190225`, `ll=<lat>,<lon>`, `limit=20`, `radius=<meters>`.

**Rationale**: FoursquareKit is a CocoaPod with no SPM support; porting its HTTP logic (a simple GET + JSON decode) is 20 lines with `URLSession` + `JSONDecoder`. This removes CocoaPods from the entire project.

**Alternatives considered**: Keeping FoursquareKit via a local SPM wrapper — rejected because it adds complexity for trivial benefit; the API call is straightforward.

---

## Decision 2: CLLocationManager strategy for LocationClient

**Decision**: One-shot `CLLocationManager` wrapped with `withCheckedThrowingContinuation` for `getCurrentLocation()`. Authorization request uses a `CLLocationManagerDelegate` bridge. `getLocationAuthorizationStatus()` is synchronous (`CLLocationManager.authorizationStatus()`).

**Rationale**: SwiftLocation (CocoaPod, no SPM) is removed. The app only needs a single current location fix + authorization check — not a continuous stream — so a continuation-based approach is simpler than `AsyncStream`.

**Alternatives considered**: Using `CLLocationUpdate.liveUpdates()` (iOS 17 API) — viable but adds `@available` guards; the continuation pattern is compatible with iOS 16+ for future back-deploy flexibility.

---

## Decision 3: MKMapView + UIViewRepresentable

**Decision**: Wrap `MKMapView` in a `UIViewRepresentable` named `MapViewRepresentable`. The `Coordinator` class (UIViewRepresentable's coordinator, not VIPER) handles `MKMapViewDelegate` callbacks and sends `store.send(.mapRegionChanged(region))` / `store.send(.restaurantAnnotationTapped(restaurant))` via a store reference captured in the coordinator.

**Rationale**: SwiftUI's native `Map` view (iOS 17) supports annotations but lacks `MKMapViewDelegate.regionDidChangeAnimated` events needed for region-based fetch triggering. `UIViewRepresentable` provides full control.

**Alternatives considered**: SwiftUI `Map` with `MapReader` — limited region change callbacks in iOS 17; not sufficient for this use case.

---

## Decision 4: Region dedup implementation

**Decision**: `MKCoordinateRegion` has no `Equatable` conformance. Store `fetchedRegion` as `MKCoordinateRegion?` in state. The dedup check in the reducer: `if let fetched = state.fetchedRegion, fetched.contains(center: newRegion.center) { return .none }`. Implement `MKCoordinateRegion.contains(center:)` as a pure helper in `Core/Networking` (internal). **`MKCoordinateRegion` cannot conform to `Equatable` in state directly** — store the span and center as value types or use a custom `EquatableRegion` wrapper.

**Rationale**: The Presenter's `restaurantRegion` guard is the key behavioral invariant to preserve. A custom `EquatableRegion` wrapper (struct with `center: CLLocationCoordinate2D` + `span: MKCoordinateSpan`, both `Equatable`-able as Double pairs) is the cleanest approach.

**Alternatives considered**: Skipping dedup in TCA — rejected; the source behavior explicitly avoids redundant API calls.

---

## Decision 5: Alert state pattern

**Decision**: `@Presents var alert: AlertState<Action.Alert>?` in `RestaurantsMapFeature.State`. Alert actions enum: `case dismissAlert`. Two alert constructors: `locationNeededAlert()` and `locationErrorAlert()`. Presented with `.alert($store.scope(state: \.alert, action: \.alert))`.

**Rationale**: This is the canonical TCA pattern from `tca-patterns.md`. Keeps alert state in the reducer, fully testable via `TestStore`.

---

## Decision 6: Cancellation for restaurant fetch

**Decision**: `enum CancelID { case restaurantFetch }` in `RestaurantsMapFeature`. Apply `.cancellable(id: CancelID.restaurantFetch, cancelInFlight: true)` to the restaurant fetch effect. This automatically cancels an in-flight request when a new region change arrives.

**Rationale**: Prevents race conditions when user pans quickly. Matches `tca-patterns.md` guidance.

---

## Decision 7: Swift 6 concurrency for CLLocationCoordinate2D and MKCoordinateRegion

**Decision**: `CLLocationCoordinate2D` and `MKCoordinateRegion` are `Sendable` (MapKit marks them as such in Xcode 15+). `CLLocation` is a reference type but `@Sendable`-safe to pass across actor boundaries. No `@unchecked Sendable` annotations needed.

**Rationale**: MapKit structs are `Sendable` since they are plain C structs bridged to Swift. Verified against Swift 6 MapKit headers.

---

## Decision 8: Tuist version + package resolution

**Decision**: Tuist 4.139.x (latest as of June 2026) per constitution pinning. `tuist install` resolves TCA 1.25.2 from SPM. `tuist generate` produces a `.xcworkspace`. Build via `xcodebuild -workspace CoolRestaurants.xcworkspace -scheme CoolRestaurants -destination 'platform=iOS Simulator,name=iPhone 16'`.

**Rationale**: Matches constitution §II and the `tuist-templates/` knowledge files.
