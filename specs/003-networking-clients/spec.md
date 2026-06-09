# Feature Specification: Networking Clients

**Feature Branch**: `003-networking-clients`

**Created**: 2026-06-06

**Status**: Draft

**Input**: CoolRestaurants VIPER→TCA migration — Core/Networking module (RestaurantClient + LocationClient)

## Migration Context

- **Source feature**:
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/Repositories/RestaurantRepository.swift` + `Implementations/RestaurantRepositorryImplementation.swift` + `Mock Implementations/MockRestaurantRepositoryImplementation.swift`
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/Repositories/LocationRepository.swift` + `Implementations/LocationRepositoryImplementation.swift` + `Mock Implementations/MockLocationRepositoryImplementation.swift`
  - `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/Repositories/RepositoryInjection.swift`
- **Source architecture**: VIPER Repository/Interactor layer — protocol + `RxSwift.Single<T>` + singleton `RepositoryInjection` DI container
- **Target TCA module**: `Core/Networking` (depends on `Core/SharedModels`; no TCA framework dep beyond `@DependencyClient` macro)
- **Component mapping**:

  | Source component | → TCA target |
  |---|---|
  | `RestaurantRepository` protocol + `Single<[Restaurant]>` | `RestaurantClient` `@DependencyClient` with `async throws -> [Restaurant]` |
  | `RestaurantRepositoryImplementation` (FoursquareKit CocoaPod) | `RestaurantClient.liveValue` — wraps Foursquare `venues/search` via `URLSession` (replaces CocoaPod) |
  | `MockRestaurantRepositoryImplementation` | `RestaurantClient.previewValue` — returns 11 mock restaurants around a given center |
  | `LocationRepository` protocol + `Single<CLAuthorizationStatus/CLLocation>` | `LocationClient` `@DependencyClient` with three `async throws` endpoints |
  | `LocationRepositoryImplementation` (SwiftLocation CocoaPod) | `LocationClient.liveValue` — wraps `CLLocationManager` via `AsyncStream` directly |
  | `MockLocationRepositoryImplementation` (Amsterdam hardcoded) | `LocationClient.previewValue` — returns `.authorizedWhenInUse` + Amsterdam coordinates |
  | `RepositoryInjection` singleton | deleted; `@Dependency(\.restaurantClient)` / `@Dependency(\.locationClient)` |

- **Behavior to preserve**:
  - Restaurant fetch: `ll`, `limit=20`, `radius` derived from `MKCoordinateRegion` span → same calculation ported in pure Swift.
  - Location: `requestLocationAuthorization` → `requestWhenInUseAuthorization`; `getLocationAuthorizationStatus` → synchronous `authorizationStatus`; `getCurrentLocation` → first non-nil location fix.
  - All `Single<T>` → `async throws -> T` (no RxSwift).

## User Scenarios & Testing

### User Story 1 — Restaurant search delivers results for a map region (Priority: P1)

Given a map region (center + span), the client fetches nearby restaurants from the Foursquare Venues Search API and returns a list of `Restaurant` values.

**Why this priority**: Core data path — the entire map feature depends on it.

**Independent Test**: Inject a `RestaurantClient` with a test implementation returning a fixed array; call it from a `TestStore`; verify the returned restaurants appear in state.

**Acceptance Scenarios**:

1. **Given** a valid map region, **When** `getRestaurants(region:)` is called, **Then** a non-empty `[Restaurant]` is returned within a reasonable time.
2. **Given** a network error, **When** `getRestaurants(region:)` is called, **Then** an error is thrown and no restaurants are returned.

---

### User Story 2 — Location authorization lifecycle (Priority: P1)

The app can check the current authorization status, request it when undetermined, and retrieve the device's current location.

**Why this priority**: Without location, the map cannot be centred and restaurants cannot be fetched.

**Independent Test**: Inject `LocationClient.previewValue` (always authorized, Amsterdam) into a `TestStore`; verify `onAppear` results in a centred-map state update.

**Acceptance Scenarios**:

1. **Given** location is `.notDetermined`, **When** `requestLocationAuthorization()` is called, **Then** the system prompt is shown and the resulting status is returned.
2. **Given** location is `.authorizedWhenInUse`, **When** `getCurrentLocation()` is called, **Then** a `CLLocation` is returned.
3. **Given** location is `.denied`, **When** `getLocationAuthorizationStatus()` is called, **Then** `.denied` is returned immediately.

---

### Edge Cases

- Network request for restaurants with a very small region (radius < 100 m) should still succeed.
- `CLLocationManager.authorizationStatus` may change while app is in background — the client is not expected to stream status changes; one-shot reads only.
- FoursquareKit CocoaPod is replaced with direct `URLSession`; the Foursquare v2 API endpoint `venues/search` requires `client_id`, `client_secret`, `v` (date), `ll`, `limit`, `radius` parameters.

## Requirements

### Functional Requirements

- **FR-001**: `RestaurantClient` MUST expose `getRestaurants(_ region: MKCoordinateRegion) async throws -> [Restaurant]`.
- **FR-002**: `LocationClient` MUST expose `requestLocationAuthorization() async throws -> CLAuthorizationStatus`, `getLocationAuthorizationStatus() async throws -> CLAuthorizationStatus`, and `getCurrentLocation() async throws -> CLLocation`.
- **FR-003**: Both clients MUST provide a `liveValue` (real device/network) and a `previewValue` (deterministic mock for SwiftUI previews and tests).
- **FR-004**: The `testValue` of each client MUST be a failing stub (throws `Unimplemented`) so test authors must explicitly provide all dependencies.
- **FR-005**: `RepositoryInjection` singleton MUST be deleted; both clients registered via `DependencyValues` extensions.
- **FR-006**: Neither client MAY import RxSwift.
- **FR-007**: The radius calculation from `MKCoordinateRegion.span` MUST produce the same integer-meter value as the source `getRadiusInMetersForRegion` implementation.
- **FR-008**: The module MUST compile under Swift 6 strict concurrency with no warnings.

### Key Entities

- **RestaurantClient**: `@DependencyClient` struct with one async throwing function.
- **LocationClient**: `@DependencyClient` struct with three async throwing functions.
- **FoursquareVenueSearchResponse**: internal `Decodable` struct mapping the Foursquare JSON response to `Restaurant` values (not exported from the module).

## Success Criteria

### Measurable Outcomes

- **SC-001**: `Core/Networking` generates and builds with zero errors and zero warnings.
- **SC-002**: Feature test suites for RestaurantsMap can inject `LocationClient` and `RestaurantClient` test values and exercise every effect path without making real network/location calls.
- **SC-003**: `previewValue` returns a deterministic set of mock restaurants within 100 ms.

## Assumptions

- Foursquare API credentials (client ID + secret) are kept as compile-time constants in `RestaurantClient.liveValue` matching the source values.
- `getCurrentLocation` uses a one-shot `CLLocationManager` delegate with `withCheckedThrowingContinuation`; no streaming needed.
- The `v` (versioning) parameter for Foursquare API is set to a fixed date string `"20190225"` (matching source era).
- CocoaPods (`FoursquareKit`, `SwiftLocation`) are not carried into the TCA project; their logic is re-implemented inline in `liveValue`.
