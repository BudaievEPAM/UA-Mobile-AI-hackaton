# Feature Specification: Shared Models

**Feature Branch**: `002-shared-models`

**Created**: 2026-06-06

**Status**: Draft

**Input**: CoolRestaurants VIPER→TCA migration — Core/SharedModels module

## Migration Context

- **Source feature**: `workspace/input/iOS-VIPER-RxSwift-Example/CoolRestaurants/Model/Restuarant.swift`
- **Source architecture**: VIPER — Entity layer (plain struct, MapKit-dependent)
- **Target TCA module**: `Core/SharedModels` (no TCA dependency; no deps on other modules)
- **Component mapping**:

  | Source component | → TCA target |
  |---|---|
  | `Restaurant` struct (MapKit fields) | `Restaurant` struct: `Equatable`, `Sendable`, `Identifiable` — `CLLocationCoordinate2D` kept as-is (MapKit value type) |
  | `RepositoryInjection` singleton | deleted; replaced by `@Dependency` in feature modules |
  | VIPER protocol files (`*Contract.swift`) | deleted entirely |

- **Behavior to preserve**: `Restaurant` carries `identifier`, `name`, `coordinate`, `address?`, `categoryName?`, `caregoryIconURL?` (typo preserved for source fidelity; internal alias added).

## User Scenarios & Testing

### User Story 1 — Shared data model available across all features (Priority: P1)

All features (RestaurantsMap, RestaurantsDetail) can pass `Restaurant` values through the TCA store, stack state, and test assertions without conversion.

**Why this priority**: Foundation — every other module depends on it.

**Independent Test**: A unit test that creates a `Restaurant` value and asserts equality; confirms `Equatable` and `Identifiable` conformance.

**Acceptance Scenarios**:

1. **Given** a `Restaurant` value with all fields set, **When** compared to an identical copy, **Then** equality holds.
2. **Given** a `Restaurant` in an array, **When** used as `Identifiable` by `id`, **Then** the `identifier` field serves as the stable ID.

---

### Edge Cases

- `address`, `categoryName`, `caregoryIconURL` are all optional — nil values must round-trip through `Equatable` correctly.
- `CLLocationCoordinate2D` is not `Equatable` by default; `Restaurant` equality must handle coordinate comparison explicitly or via a wrapper.

## Requirements

### Functional Requirements

- **FR-001**: `Restaurant` MUST conform to `Equatable`, `Sendable`, and `Identifiable` (using `identifier` as `id`).
- **FR-002**: `Restaurant` MUST be a value type (`struct`) with no mutable reference semantics.
- **FR-003**: All optional fields (`address`, `categoryName`, `caregoryIconURL`) MUST remain optional.
- **FR-004**: The module MUST have no dependency on TCA, RxSwift, or any feature module.
- **FR-005**: The module MUST compile under Swift 6 strict concurrency with no warnings.

### Key Entities

- **Restaurant**: Represents a nearby dining venue. Fields: `identifier: String`, `name: String`, `coordinate: CLLocationCoordinate2D`, `address: String?`, `categoryName: String?`, `caregoryIconURL: URL?`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `Core/SharedModels` generates and builds with zero errors and zero warnings.
- **SC-002**: All other feature modules can import `SharedModels` and use `Restaurant` without bridging code.
- **SC-003**: `Restaurant` equality is correctly verified in at least one Swift Testing test.

## Assumptions

- `CLLocationCoordinate2D` coordinate equality is implemented by comparing `latitude` and `longitude` as `Double` values.
- The source typo `caregoryIconURL` is preserved in the property name to avoid unnecessary diff noise, with a computed alias `categoryIconURL` for new call sites.
- No persistence (Codable) is required in this migration scope.
