# Modern TCA Patterns (canonical reference)

> Source of truth for **idiomatic, current** TCA. Every migrated feature must match these
> patterns. Target: `swift-composable-architecture` 1.17+ (Observation-based). Swift 6 language
> mode, `@MainActor` UI. **Pin the exact version** in `Tuist/Package.swift`.

## Non-negotiables (the "constitution" in code form)

- Use the `@Reducer` macro on the feature type and `@ObservableState` on `State`.
- **No `ViewStore` / `WithViewStore`** — Observation makes them obsolete. Views read `store.x`
  directly and use `@Bindable var store` for bindings.
- One `Store` per feature; child features are composed with `Scope` / `ifLet` / `forEach`.
- All side effects go through `Effect` (`.run`, `.send`, cancellation) and all I/O is a
  `@Dependency`. **No singletons, no direct `URLSession`/`UserDefaults` in a reducer.**
- `State: Equatable`, value types only. `Action` is a plain enum of *facts* (what happened),
  not commands.
- Navigation is state-driven: `@Presents` (tree) or `StackState` (stack). No `UINavigationController`,
  no imperative `present(_:)`.

## Feature skeleton

```swift
import ComposableArchitecture

@Reducer
struct CounterFeature {
  @ObservableState
  struct State: Equatable {
    var count = 0
    var fact: String?
    var isLoading = false
  }

  enum Action {
    case incrementButtonTapped
    case factButtonTapped
    case factResponse(Result<String, Error>)
  }

  @Dependency(\.numberFact) var numberFact

  var body: some ReducerOf<Self> {
    Reduce { state, action in
      switch action {
      case .incrementButtonTapped:
        state.count += 1
        return .none

      case .factButtonTapped:
        state.isLoading = true
        return .run { [count = state.count] send in
          await send(.factResponse(Result { try await numberFact.fetch(count) }))
        }

      case let .factResponse(.success(fact)):
        state.isLoading = false
        state.fact = fact
        return .none

      case .factResponse(.failure):
        state.isLoading = false
        return .none
      }
    }
  }
}
```

## View (Observation, no ViewStore)

```swift
import ComposableArchitecture
import SwiftUI

struct CounterView: View {
  let store: StoreOf<CounterFeature>

  var body: some View {
    Form {
      Text("\(store.count)")
      Button("Increment") { store.send(.incrementButtonTapped) }
      if store.isLoading { ProgressView() }
      if let fact = store.fact { Text(fact) }
    }
  }
}
```

## Bindings (BindableAction + BindingReducer)

```swift
enum Action: BindableAction {
  case binding(BindingAction<State>)
  case saveButtonTapped
}

var body: some ReducerOf<Self> {
  BindingReducer()
  Reduce { state, action in /* ... */ }
}
```
```swift
// View:
@Bindable var store: StoreOf<SettingsFeature>
TextField("Name", text: $store.name)
Toggle("Enabled", isOn: $store.isEnabled)
```

## Dependencies (the home for VIPER Interactors / Clean Repositories & UseCases)

Define every external service as a `@DependencyClient` struct with `liveValue` (real) and a test
value (use `unimplemented`-style failing closures so tests must override what they use).

```swift
import Dependencies
import DependenciesMacros

@DependencyClient
struct NumberFactClient {
  var fetch: (_ number: Int) async throws -> String
}

extension NumberFactClient: DependencyKey {
  static let liveValue = Self(
    fetch: { number in
      let (data, _) = try await URLSession.shared
        .data(from: URL(string: "http://numbersapi.com/\(number)")!)
      return String(decoding: data, as: UTF8.self)
    }
  )
}

extension DependencyValues {
  var numberFact: NumberFactClient {
    get { self[NumberFactClient.self] }
    set { self[NumberFactClient.self] = newValue }
  }
}
```
`@DependencyClient` synthesizes an unimplemented `testValue` automatically. Provide `previewValue`
for SwiftUI previews when helpful.

## Tree navigation (push/present a single destination)

```swift
@Reducer
struct ListFeature {
  @ObservableState
  struct State: Equatable {
    var items: IdentifiedArrayOf<Item> = []
    @Presents var destination: Destination.State?
  }
  enum Action {
    case itemTapped(Item.ID)
    case destination(PresentationAction<Destination.Action>)
  }

  @Reducer
  enum Destination {
    case detail(DetailFeature)
    case edit(EditFeature)
  }

  var body: some ReducerOf<Self> {
    Reduce { state, action in
      switch action {
      case let .itemTapped(id):
        guard let item = state.items[id: id] else { return .none }
        state.destination = .detail(DetailFeature.State(item: item))
        return .none
      case .destination:
        return .none
      }
    }
    .ifLet(\.$destination, action: \.destination)
  }
}
```
```swift
// View modifiers:
.sheet(item: $store.scope(state: \.destination?.edit, action: \.destination.edit)) { EditView(store: $0) }
.navigationDestination(item: $store.scope(state: \.destination?.detail, action: \.destination.detail)) { DetailView(store: $0) }
```

## Stack navigation (the home for VIPER Routers / Clean FlowCoordinators)

```swift
@Reducer
struct AppFeature {
  @ObservableState
  struct State: Equatable {
    var path = StackState<Path.State>()
    var root = HomeFeature.State()
  }
  enum Action {
    case path(StackActionOf<Path>)
    case root(HomeFeature.Action)
  }
  @Reducer
  enum Path {
    case detail(DetailFeature)
    case settings(SettingsFeature)
  }
  var body: some ReducerOf<Self> {
    Scope(state: \.root, action: \.root) { HomeFeature() }
    Reduce { state, action in /* react to navigation */ }
      .forEach(\.path, action: \.path)
  }
}
```
```swift
// View:
NavigationStack(path: $store.scope(state: \.path, action: \.path)) {
  HomeView(store: store.scope(state: \.root, action: \.root))
} destination: { store in
  switch store.case {
  case let .detail(store): DetailView(store: store)
  case let .settings(store): SettingsView(store: store)
  }
}
```

## Lists of features

`IdentifiedArrayOf<ChildFeature.State>` in State + `.forEach(\.rows, action: \.rows)` +
`ForEach(store.scope(state: \.rows, action: \.rows))` in the View.

## Effects & concurrency

- `return .run { send in … }` for async work; capture only the state you need (`[id = state.id]`).
- Cancellation: `.cancellable(id: CancelID.fetch)` and `.cancel(id:)`. Define `enum CancelID`.
- Debounce search with `.debounce`. Use `@Dependency(\.continuousClock)` — **never** `Task.sleep`
  directly (so tests control time).
- Long-running streams: `for await … in client.events()` inside `.run`.

## Composition rules

- A parent embeds a child with `Scope(state:action:) { Child() }`.
- Optional child: `ifLet`. Identified collection: `forEach`. Presented: `ifLet(\.$destination, …)`.
- Keep features small; one screen ≈ one feature. Shared state across features → `@Shared`.

## App entry point

```swift
@main
struct MyApp: App {
  static let store = Store(initialState: AppFeature.State()) { AppFeature() }
  var body: some Scene { WindowGroup { AppView(store: Self.store) } }
}
```

## Anti-patterns to reject during migration

- ❌ `ViewStore`, `WithViewStore`, `viewStore.send` → ✅ `store.send`, direct `store.x`.
- ❌ Business logic in the View or in a "Presenter" class → ✅ in the reducer.
- ❌ Protocol-based DI containers, Interactor/Presenter/Router protocols → ✅ `@Dependency` + Actions.
- ❌ `@Published`/Combine `ObservableObject` view models → ✅ `@ObservableState` + reducer.
- ❌ Imperative navigation (`pushViewController`, delegates) → ✅ `StackState` / `@Presents`.
- ❌ Completion-handler callbacks → ✅ `async`/`await` in `.run` effects.
