# MVVM + Coordinator → TCA mapping rules

> The View/ViewModel/Model parts are migrated exactly as in [mvvm-to-tca.md](mvvm-to-tca.md).
> This doc covers the **Coordinator** layer → TCA's state-driven navigation. Pair with the
> navigation section of [tca-patterns.md](tca-patterns.md).

## The big idea

A **Coordinator** owns a `UINavigationController` (or SwiftUI nav), creates ViewModels/Views, pushes/
presents them, holds `childCoordinators`, and decides *what comes next* based on ViewModel signals
(delegates/closures). In TCA, **navigation is state**:

- a **flow / stack** of screens → `StackState<Path.State>` + a `@Reducer enum Path` (one case per screen),
- a **modal** → `@Presents var destination: Destination.State?` + `@Reducer enum Destination`,
- the coordinator's "decide what's next" logic → a **parent reducer** that appends to `StackState`
  (or sets the destination) in response to children's `delegate` actions.

There is **no Coordinator object** in TCA — the parent feature *is* the coordinator, and the
`StackState`/`childCoordinators` array *is* the navigation stack.

## Component mapping (the core table)

| MVVM+Coordinator component | TCA target | Notes |
|---|---|---|
| **Coordinator** (`AppCoordinator`, `LoginCoordinator`) | A parent `@Reducer` owning `StackState`/`@Presents` | The coordinator class is **deleted**. |
| `coordinator.start()` | initial `State` (root screen) | The root is just the parent's initial state. |
| `coordinator.showDetail(x)` / `push(vc)` | append to `StackState`: `state.path.append(.detail(.init(x)))` | Triggered by a child `delegate` action. |
| `present(vc, modally)` / `showSheet` | set `@Presents`: `state.destination = .sheet(.init())` | Use `.sheet`/`.fullScreenCover` in the View. |
| `navigationController.popViewController` / `dismiss` | `state.path.removeLast()` / `state.destination = nil` | Or let SwiftUI drive it via the binding. |
| **`childCoordinators: [Coordinator]`** | `StackState<Path.State>` | The stack holds child feature states; no manual array bookkeeping. |
| **child Coordinator** (a sub-flow) | a feature reducer used as a `Path`/`Destination` case (which may itself own a nested `StackState`) | Coordinators nest → reducers nest. |
| ViewModel → Coordinator signal (delegate `didFinishLogin`, closure `onSelect(item)`) | child `delegate(Delegate)` action the parent matches | This is the seam that replaces the coordinator-delegate protocol. |
| `Coordinator` protocol / `Coordinatable` | nothing — composition via `Scope`/`forEach`/`ifLet` | |

## Coordinator flow → parent reducer

The coordinator's branching ("on login success, show home; on logout, pop to root") becomes a
`switch` in the parent reducer over the children's `delegate` actions:

```swift
@Reducer
struct AppFeature {              // == the app's root Coordinator
  @ObservableState
  struct State {
    var path = StackState<Path.State>()
    var login = LoginFeature.State()        // root screen
  }
  enum Action {
    case login(LoginFeature.Action)
    case path(StackActionOf<Path>)
  }
  @Reducer
  enum Path {                    // one case per screen the coordinator could navigate to
    case home(HomeFeature)
    case detail(DetailFeature)
    case settings(SettingsFeature)
  }
  var body: some ReducerOf<Self> {
    Scope(state: \.login, action: \.login) { LoginFeature() }
    Reduce { state, action in
      switch action {
      // coordinator: "on login success → show Home"
      case .login(.delegate(.loggedIn)):
        state.path.append(.home(HomeFeature.State()))
        return .none
      // coordinator: "on Home selecting a row → show Detail"
      case let .path(.element(id: _, action: .home(.delegate(.selected(item))))):
        state.path.append(.detail(DetailFeature.State(item: item)))
        return .none
      // coordinator: "on Settings 'log out' → pop to root"
      case .path(.element(id: _, action: .settings(.delegate(.loggedOut)))):
        state.path.removeAll()
        return .none
      case .login, .path:
        return .none
      }
    }
    .forEach(\.path, action: \.path)
  }
}
```
```swift
// The View is the coordinator's navigationController:
struct AppView: View {
  @Bindable var store: StoreOf<AppFeature>
  var body: some View {
    NavigationStack(path: $store.scope(state: \.path, action: \.path)) {
      LoginView(store: store.scope(state: \.login, action: \.login))
    } destination: { store in
      switch store.case {
      case let .home(s):     HomeView(store: s)
      case let .detail(s):   DetailView(store: s)
      case let .settings(s): SettingsView(store: s)
      }
    }
  }
}
```

## Rules

- **Children never navigate themselves.** A child ViewModel-turned-reducer emits
  `delegate(.somethingHappened)`; only the parent (coordinator) mutates `path`/`destination`.
  This is the #1 thing to get right — don't recreate a `Coordinator` inside a child.
- **Modal vs stack:** push/show → `StackState`; present/sheet/fullScreenCover → `@Presents`.
- **Deep links / programmatic flows** the coordinator handled → set `StackState`/destination directly
  from an action (e.g., `case .openDeepLink(let route): state.path = StackState([...])`).
- **Tab bar coordinators** → a parent with one child feature per tab (`Scope` each), each owning its
  own `StackState`.

## Step-by-step

1. Migrate each screen's View+ViewModel to a feature (per [mvvm-to-tca.md](mvvm-to-tca.md)); give each
   a `delegate` action for the signals its coordinator listened to.
2. For each Coordinator, create a parent reducer with `StackState<Path.State>` (+ `@Presents` for
   modals) and a `@Reducer enum Path`/`Destination` with one case per reachable screen.
3. Translate the coordinator's navigation methods/branches into parent-reducer handling of the
   children's `delegate` actions (append/remove path, set/clear destination).
4. Nested/child coordinators → nested features (a `Path` case whose feature owns its own `StackState`).
5. Build the `NavigationStack(path:)` / `.sheet(item:)` view. Delete every Coordinator + delegate protocol.

## Detection signals (is this MVVM + Coordinator?)

MVVM signals (see [mvvm-to-tca.md](mvvm-to-tca.md)) **plus**: types suffixed `*Coordinator`/
`*FlowCoordinator`; a `Coordinator` protocol; `childCoordinators` arrays; coordinators holding a
`UINavigationController`/`navigationController`; ViewModel→coordinator **delegate protocols**
(`*CoordinatorDelegate`, `didFinish…`) or `onFinish`/`onNext` closures wired in a `*Builder`/
`*Factory`/`AppCoordinator`.
