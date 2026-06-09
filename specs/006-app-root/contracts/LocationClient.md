# Contract: LocationClient

**Module**: `Core/Networking`
**Kind**: `@DependencyClient` (TCA dependency)
**Registered as**: `\.locationClient` on `DependencyValues`

## Interface

```swift
@DependencyClient
struct LocationClient {
    /// Returns the current `CLAuthorizationStatus` synchronously.
    var getLocationAuthorizationStatus: () async throws -> CLAuthorizationStatus

    /// Requests "when in use" authorization. Returns the status after the user responds.
    var requestLocationAuthorization: () async throws -> CLAuthorizationStatus

    /// Obtains the device's current location (one-shot).
    var getCurrentLocation: () async throws -> CLLocation
}
```

## Implementations

| Key | Behavior |
|---|---|
| `liveValue` | `getLocationAuthorizationStatus`: returns `CLLocationManager.authorizationStatus()` synchronously (wrapped in `async`). `requestLocationAuthorization`: creates a one-shot `CLLocationManager` with a delegate bridge using `withCheckedThrowingContinuation`; resolves when status transitions from `.notDetermined`. `getCurrentLocation`: one-shot `CLLocationManager.requestLocation()` with delegate bridge. |
| `previewValue` | Always returns `.authorizedWhenInUse`; `getCurrentLocation` returns Amsterdam (52.370216, 4.895168) — matches `MockLocationRepositoryImplementation`. |
| `testValue` (synthesized) | All closures throw `Unimplemented` — forces test authors to inject. |

## Status Mapping

| Source status | Reducer action | Reducer response |
|---|---|---|
| `.notDetermined` | `locationAuthorizationResponse(.success(.notDetermined))` | → call `requestLocationAuthorization()` |
| `.authorizedWhenInUse` / `.authorizedAlways` | `locationAuthorizationResponse(.success(.authorized*))` | → call `getCurrentLocation()` |
| `.denied` / `.restricted` | `locationAuthorizationResponse(.success(.denied/.restricted))` | → set `state.alert = locationNeededAlert` |
| Any throw | `locationAuthorizationResponse(.failure(error))` | → set `state.alert = locationErrorAlert` |

## Error Behavior

- Authorization request denied by OS (impossible via API; denial comes as a status) — handled as status `.denied`.
- `getCurrentLocation` failure → throws `CLError` → reducer sets `locationErrorAlert`.
