# Swift Testing + TCA `TestStore` patterns

> Target test stack: **Swift Testing** (`import Testing`, `@Suite`, `@Test`, `#expect`,
> `#require`) driving TCA's **`TestStore`**. Replace all XCTest. Pair with
> [tca-patterns.md](tca-patterns.md).

## Why TestStore

`TestStore` asserts an **exhaustive** script: every `send` must declare the exact state mutation,
and every effect that feeds an action back must be `receive`d (with its state mutation). Unhandled
effects/actions fail the test. This makes reducers fully, deterministically testable.

## Migration: XCTest → Swift Testing

| XCTest | Swift Testing |
|---|---|
| `import XCTest` | `import Testing` |
| `final class FooTests: XCTestCase` | `@Suite struct FooTests` (or `@MainActor @Suite`) |
| `func testBar()` | `@Test func bar()` |
| `XCTAssertEqual(a, b)` | `#expect(a == b)` |
| `XCTAssertTrue(x)` / `XCTAssertNil(x)` | `#expect(x)` / `#expect(x == nil)` |
| `XCTUnwrap(x)` | `try #require(x)` |
| `setUp`/`tearDown` | `init()` / `deinit` (per-test instance) |
| `XCTExpectFailure` | `withKnownIssue { }` |

## Canonical reducer test

```swift
import ComposableArchitecture
import Testing

@MainActor
struct CounterFeatureTests {
  @Test
  func increment() async {
    let store = TestStore(initialState: CounterFeature.State()) {
      CounterFeature()
    }
    await store.send(.incrementButtonTapped) {
      $0.count = 1                     // exact expected mutation
    }
  }
}
```

`TestStore` is `@MainActor`-isolated → annotate the suite (or each test) `@MainActor`.

## Effects + dependency overrides

Override **only** the dependencies the test exercises (the synthesized `@DependencyClient`
test value fails on anything you forgot to stub — that's the point).

```swift
@MainActor
struct LoginFeatureTests {
  @Test
  func loginSucceeds() async {
    let store = TestStore(initialState: LoginFeature.State(email: "a@b.c", password: "pw")) {
      LoginFeature()
    } withDependencies: {
      $0.authClient.login = { _, _ in "token-123" }
    }

    await store.send(.loginButtonTapped) {
      $0.isLoading = true
    }
    await store.receive(\.loginResponse.success) {     // effect feeds this back
      $0.isLoading = false
    }
    await store.receive(\.delegate.loggedIn)           // delegate emitted to parent
  }

  @Test
  func loginFails() async {
    struct Boom: Error {}
    let store = TestStore(initialState: LoginFeature.State()) {
      LoginFeature()
    } withDependencies: {
      $0.authClient.login = { _, _ in throw Boom() }
    }
    await store.send(.loginButtonTapped) { $0.isLoading = true }
    await store.receive(\.loginResponse.failure) {
      $0.isLoading = false
      $0.errorMessage = "The operation couldn’t be completed. (…Boom error 1.)"
    }
  }
}
```

## Controlling time / clocks

Use `@Dependency(\.continuousClock)` in the reducer and a `TestClock` in tests:

```swift
let clock = TestClock()
let store = TestStore(initialState: SearchFeature.State()) {
  SearchFeature()
} withDependencies: {
  $0.continuousClock = clock
  $0.moviesClient.fetchMovies = { _ in [.mock] }
}
await store.send(.queryChanged("bat")) { $0.query = "bat" }
await clock.advance(by: .milliseconds(300))            // fire the debounce
await store.receive(\.moviesResponse.success) { $0.items = [.mock] }
```

## Non-exhaustive testing (for big integration-style tests)

```swift
store.exhaustivity = .off            // assert only what you state; ignore the rest
// or .off(showSkippedAssertions: true) to log what was skipped
```

## Shared test helpers

- Put `Item.mock` / `Movie.mock` factories in a `*Testing` support target or `#if DEBUG` extensions
  in `SharedModels`.
- Prefer `IdentifiedArray` in `State` so `receive` mutations stay stable and order-independent.

## Tuist test target shape

Each feature module declares a unit-test target (Swift Testing). See
[tuist-templates/](tuist-templates/). Run via `swift test` or
`xcodebuild test -scheme <Feature>` piped through `xcsift` (see `scripts/build_check.sh`).

## Checklist per migrated feature

- [ ] One `@Suite` per reducer; `@MainActor`.
- [ ] Happy path + at least one failure path, each with exact state mutations.
- [ ] Every effect `receive`d; no unhandled-action failures.
- [ ] Time/randomness/uuid controlled via dependencies (`TestClock`, `.constant`, `.incrementing`).
- [ ] No `import XCTest` remains anywhere.
