# Contract: RestaurantClient

**Module**: `Core/Networking`
**Kind**: `@DependencyClient` (TCA dependency)
**Registered as**: `\.restaurantClient` on `DependencyValues`

## Interface

```swift
@DependencyClient
struct RestaurantClient {
    /// Fetches nearby restaurants for the given map region.
    /// - Parameter region: The visible map region (center + span).
    /// - Returns: Up to 20 `Restaurant` values near the region center.
    /// - Throws: Network or decoding errors.
    var getRestaurants: (_ region: MKCoordinateRegion) async throws -> [Restaurant]
}
```

## Implementations

| Key | Behavior |
|---|---|
| `liveValue` | Calls Foursquare v2 `venues/search` via `URLSession`. Params: `ll`, `limit=20`, `radius` (derived from span). Decodes JSON → `[Restaurant]`. |
| `previewValue` | Returns 11 deterministic mock restaurants around `region.center` (random coordinate offsets matching `MockRestaurantRepositoryImplementation`). No network. |
| `testValue` (synthesized) | All closures call `XCTFail` / `unimplemented` — forces test authors to override. |

## Foursquare API Details

- **Endpoint**: `GET https://api.foursquare.com/v2/venues/search`
- **Required params**: `client_id`, `client_secret`, `v=20190225`, `ll=<lat>,<lon>`, `limit=20`, `radius=<Int meters>`
- **Radius calculation**: `min(latitudinal meters, longitudinal meters)` from `MKCoordinateRegion.span` — see source `RestaurantRepositoryImplementation.getRadiusInMetersForRegion`.
- **Response shape**: `{ "response": { "venues": [ { "id", "name", "location": { "lat", "lng", "formattedAddress": [...] }, "categories": [ { "name", "icon": { "prefix", "suffix" } } ] } ] } }`

## Error Behavior

- Network failure → throws `URLError`
- Non-2xx response → throws `RestaurantClientError.badResponse(statusCode:)`
- Decoding failure → throws `DecodingError`
