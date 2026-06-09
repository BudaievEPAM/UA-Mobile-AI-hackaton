# Data Model: CoolRestaurants TCA Migration

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

## Entities

### Restaurant (Core/SharedModels)

```swift
struct Restaurant: Equatable, Sendable, Identifiable {
    let id: String            // was `identifier` in source; exposed as `id` for Identifiable
    let name: String
    let coordinate: CLLocationCoordinate2D  // Equatable via Double pair comparison
    let address: String?
    let categoryName: String?
    let caregoryIconURL: URL?  // typo preserved; alias `categoryIconURL` added
}
```

**Validation**: None at model level — all optionals accepted as-is.
**Relationships**: Used in `RestaurantsMapFeature.State.restaurants` and `RestaurantsDetailFeature.State.restaurant`.

---

### EquatableRegion (Core/Networking — internal)

Custom wrapper to allow `MKCoordinateRegion` in `Equatable` state:

```swift
struct EquatableRegion: Equatable, Sendable {
    let centerLatitude: Double
    let centerLongitude: Double
    let latitudeDelta: Double
    let longitudeDelta: Double

    init(_ region: MKCoordinateRegion) { … }
    var region: MKCoordinateRegion { … }

    func contains(coordinate: CLLocationCoordinate2D) -> Bool {
        // same logic as source MKCoordinateRegion+Extensions contains(center:)
    }
}
```

---

## Feature States

### RestaurantsMapFeature.State

| Field | Type | Source analog | Notes |
|---|---|---|---|
| `restaurants` | `[Restaurant]` | Presenter shows via `showRestaurants` | Replaced/updated on each fetch |
| `userLocation` | `CLLocationCoordinate2D?` | `userCurrentLocation: CLLocation?` | nil until location obtained |
| `fetchedRegion` | `EquatableRegion?` | `restaurantRegion: MKCoordinateRegion?` | Dedup guard |
| `isLoadingLocation` | `Bool` | implicit in RxSwift disposeBag | Shows activity indicator |
| `alert` | `AlertState<Action.Alert>?` | `showLocationNeededAlert` / `showLocationErrorAlert` | `@Presents` |

### RestaurantsDetailFeature.State

| Field | Type | Source analog | Notes |
|---|---|---|---|
| `restaurant` | `Restaurant` | `RestaurantsDetailPresenter.restaurant` | Immutable; set at init from parent |

### AppFeature.State

| Field | Type | Source analog | Notes |
|---|---|---|---|
| `map` | `RestaurantsMapFeature.State` | Root coordinator starts map | Always present |
| `path` | `StackState<AppFeature.Path.State>` | `UINavigationController` stack | TCA stack navigation |

---

## State Transitions (RestaurantsMapFeature)

```
Initial: restaurants=[], userLocation=nil, fetchedRegion=nil, alert=nil

onAppear / onResume
  → [effect] LocationClient.getLocationAuthorizationStatus()
  → locationAuthorizationResponse(.notDetermined)
       → [effect] LocationClient.requestLocationAuthorization()
       → locationAuthorizationResponse(.authorized*)
  → locationAuthorizationResponse(.authorized*)
       → [effect] LocationClient.getCurrentLocation()
       → locationResponse(.success(loc))
            userLocation = loc.coordinate
       → locationResponse(.failure)
            alert = locationErrorAlert
  → locationAuthorizationResponse(.denied | .restricted)
       alert = locationNeededAlert

mapRegionChanged(region):
  guard userLocation != nil else { → .none }
  guard !fetchedRegion?.contains(region.center) else { → .none }
  fetchedRegion = EquatableRegion(region)
  → [effect cancellable] RestaurantClient.getRestaurants(region)
  → restaurantsResponse(.success(list)):  restaurants = list
  → restaurantsResponse(.failure):        fetchedRegion = nil  (allow retry)

restaurantAnnotationTapped(r) → delegate(.showDetail(r))
openSettingsButtonTapped      → openURL(settingsURL)
alert(.dismiss)               → alert = nil
```

---

## Navigation State Transitions (AppFeature)

```
Initial: path = []

map delegate(.showDetail(r)):
  path.append(.detail(RestaurantsDetailFeature.State(restaurant: r)))

SwiftUI back (automatic):
  path.removeLast()
```
