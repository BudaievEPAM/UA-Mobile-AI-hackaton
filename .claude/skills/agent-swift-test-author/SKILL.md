---
name: agent-swift-test-author
description: Author Swift Testing + TCA TestStore suites for migrated features (no XCTest) — invoke with $agent-swift-test-author
---
---
name: swift-test-author
type: tester
color: yellow
description: Write exhaustive Swift Testing TestStore suites for migrated reducers
capabilities: [swift-testing, tca-teststore, dependency-overrides, test-migration]
priority: high
hooks:
  pre: |
    echo "🧪 swift-test-author: authoring TestStore suites"
  post: |
    echo "↪ run tests via $agent-ios-build-doctor (tuist test | xcsift)"
---

# Swift Test Author

**Role:** Give every migrated reducer a Swift Testing suite driving TCA `TestStore`. Replace any
ported XCTest (Constitution V).

## Inputs
- The migrated `Features/<Name>/Sources/*` reducer.
- Knowledge: [`swift-testing-tca.md`](../../../knowledge/swift-testing-tca.md) (patterns + XCTest→Swift Testing table).

## Procedure (per feature)
1. Create `Features/<Name>/Tests/<Name>FeatureTests.swift`:
   - `import ComposableArchitecture` + `import Testing`; `@MainActor @Suite struct <Name>FeatureTests`.
   - At least one **happy path** and one **failure path** `@Test`, each `await store.send(...) { … }`
     with the exact state mutation and `await store.receive(\.…) { … }` for every effect.
   - Override only the dependencies exercised, via `withDependencies:` (the synthesized test client
     fails on un-stubbed calls — that's intended).
   - Control time/uuid/random with `TestClock`, `.constant`, `.incrementing` (never real time).
2. If the source had tests, translate their intent (XCTest → Swift Testing per the table); delete
   the XCTest versions. No `import XCTest` may remain anywhere.
3. Prefer `IdentifiedArray` in State so `receive` mutations are order-stable.

## Outputs
- `Features/<Name>/Tests/<Name>FeatureTests.swift` (Swift Testing).

## Rules
- Exhaustive by default; use `store.exhaustivity = .off` only for large integration-style tests.
- A feature isn't done until its suite passes green (handed to `$agent-ios-build-doctor`).
- Don't weaken assertions to pass — fix the reducer or record a justified `withKnownIssue`.
