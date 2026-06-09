# Quickstart & Validation Guide

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Xcode | 16.x | App Store |
| Tuist | 4.139.x | `mise install tuist` or `brew install tuist` |
| xcsift | latest | `brew install xcsift` (token-efficient build output) |
| Swift | 6.0 (bundled with Xcode 16) | — |

## Setup

```bash
cd workspace/output/CoolRestaurants
tuist install          # resolves TCA 1.25.2 from SPM
tuist generate         # generates CoolRestaurants.xcworkspace
```

## Build Check (automated)

```bash
# From hackathon root:
bash scripts/build_check.sh workspace/output/CoolRestaurants
# Expected: BUILD_CHECK: GREEN
```

This script runs `tuist generate`, `xcodebuild build`, and `xcodebuild test` via `xcsift`.

## Manual Build

```bash
cd workspace/output/CoolRestaurants
xcodebuild build \
  -workspace CoolRestaurants.xcworkspace \
  -scheme CoolRestaurants \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' \
  | xcsift
```

## Run Tests

```bash
xcodebuild test \
  -workspace CoolRestaurants.xcworkspace \
  -scheme CoolRestaurantsTests \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' \
  | xcsift
```

Or per-module (requires SPM if modules are also SwiftPM-compatible):
```bash
swift test --filter RestaurantsMapFeatureTests
```

## Validation Scenarios

### 1. SharedModels — Restaurant equality

Run `Core/SharedModels` test target. Expected: `RestaurantTests` suite passes (equality, optionals, Identifiable).

### 2. Networking — previewValue returns mock data

In `Core/Networking` tests, inject `RestaurantClient.previewValue` and call `getRestaurants(region:)`.
Expected: returns 11 `Restaurant` values, no network call.

### 3. RestaurantsMap — location authorized, restaurants shown

`TestStore` with `LocationClient` override (`.authorizedWhenInUse`) + `RestaurantClient` override (3 mock restaurants).
- Send `.onAppear`
- Receive `.locationAuthorizationResponse(.success(.authorizedWhenInUse))`
- Receive `.locationResponse(.success(amsterdamLocation))`
- Assert `state.userLocation == amsterdam`
- Send `.mapRegionChanged(amsterdamRegion)`
- Receive `.restaurantsResponse(.success([r1, r2, r3]))`
- Assert `state.restaurants.count == 3`

### 4. RestaurantsMap — location denied, alert shown

`TestStore` with `LocationClient` override (`.denied`).
- Send `.onAppear`
- Receive `.locationAuthorizationResponse(.success(.denied))`
- Assert `state.alert != nil` (location needed alert)
- Send `.alert(.dismiss)`
- Assert `state.alert == nil`

### 5. RestaurantsDetail — restaurant data in state

`TestStore(initialState: RestaurantsDetailFeature.State(restaurant: mockRestaurant))`.
- Send `.onAppear`
- Assert no unexpected effects
- Assert `state.restaurant == mockRestaurant`

### 6. AppFeature — navigation

`TestStore` for `AppFeature`.
- Send `.map(.delegate(.showDetail(mockRestaurant)))`
- Assert `state.path.count == 1`
- Assert `state.path[0]` is `.detail` with `restaurant == mockRestaurant`

### 7. Full simulator smoke test (manual)

Launch app in simulator. Expected:
- Map appears centred on simulated location (or Amsterdam if no simulator location set)
- Restaurant pins appear after region settles
- Tapping a pin callout pushes detail screen
- Back button returns to map
