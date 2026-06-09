# MVVM → TCA mapping rules

> How to convert SwiftUI/UIKit **MVVM** (View + ViewModel + Model) into idiomatic TCA. Pair with
> [tca-patterns.md](tca-patterns.md). For navigation owned by a Coordinator, see
> [mvvm-coordinator-to-tca.md](mvvm-coordinator-to-tca.md).

## Component mapping (the core table)

| MVVM component | TCA target | Notes |
|---|---|---|
| **Model** (entities/DTOs) | Domain model in `State` / `SharedModels` | Value types, `Equatable`/`Sendable`. |
| **View** (SwiftUI `View` / `UIViewController`) | SwiftUI `View` with `StoreOf<Feature>` | Reads `store.x` directly; `@Bindable` for two-way bindings. |
| **ViewModel** (`ObservableObject`, `@Published`, methods) | **`@Reducer`** (`State` + `Action` + `body`) | The class is **deleted** — its state, intents, and effects move into the reducer. |
| `@Published var x` (outputs the View observes) | `var x` in `@ObservableState struct State` | One property per `@Published`. |
| `@Published var text` (two-way bound, `$vm.text`) | `var text` + `BindingReducer` / `BindableAction` | `TextField("", text: $store.text)`. |
| ViewModel **method** (`func load()`, `didTapSave()`) | `Action` case (`case load`, `case saveTapped`) | Method body → reducer `case` logic. |
| `async`/`await` calls, `Task { }` in the VM | `Effect` (`.run { send in … }`) | |
| **Combine** pipeline (`publisher.sink/assign`, `$x.map…`) | `Effect` (`.run` + `for await … in stream`) or a derived `State` computed property | Debounce → `@Dependency(\.continuousClock)`. |
| Injected **services / use-cases / repositories** (init params) | `@Dependency` clients (live + test) | No singletons; `@DependencyClient`. |
| `@Published var isLoading / errorMessage` | `State.isLoading` / `State.errorMessage` | |
| **Input/Output** VM (`transform(input:) -> Output`, Rx/Combine) | Inputs → `Action` cases; Outputs → `State`; `transform` logic → reducer/effects | Drop the `Input`/`Output` structs and the `transform` boilerplate. |
| VM → outside world (delegate/closure `onFinish`, `onSelect`) | `delegate(Delegate)` action handled by the parent | The parent owns navigation (see coordinator doc). |

## The core shift

An MVVM `ObservableObject` already *is* "state + behavior" — TCA just makes the state a value type,
the methods an `Action` enum, and the side effects explicit `Effect`s with injected `@Dependency`.
The `@Published` properties the View observes become `@ObservableState` properties; the View changes
from `@StateObject var vm` to `let store: StoreOf<Feature>` and reads `store.x` identically.

## Worked example

**Before (SwiftUI MVVM):**
```swift
final class LoginViewModel: ObservableObject {
  @Published var email = ""
  @Published var password = ""
  @Published var isLoading = false
  @Published var errorMessage: String?

  private let auth: AuthService
  init(auth: AuthService) { self.auth = auth }

  @MainActor func login() async {
    isLoading = true; defer { isLoading = false }
    do { _ = try await auth.login(email, password); onLoggedIn?() }
    catch { errorMessage = error.localizedDescription }
  }
  var onLoggedIn: (() -> Void)?    // navigation signal to the coordinator/parent
}

struct LoginView: View {
  @StateObject var vm: LoginViewModel
  var body: some View {
    Form {
      TextField("Email", text: $vm.email)
      SecureField("Password", text: $vm.password)
      Button("Log in") { Task { await vm.login() } }
      if vm.isLoading { ProgressView() }
      if let e = vm.errorMessage { Text(e).foregroundStyle(.red) }
    }
  }
}
```

**After (TCA):**
```swift
@Reducer
struct LoginFeature {
  @ObservableState
  struct State: Equatable {
    var email = ""
    var password = ""
    var isLoading = false
    var errorMessage: String?
  }
  enum Action: BindableAction {
    case binding(BindingAction<State>)     // was the $vm.email / $vm.password bindings
    case loginButtonTapped                 // was vm.login()
    case loginResponse(Result<Void, Error>)
    case delegate(Delegate)
    @CasePathable enum Delegate: Equatable { case loggedIn }   // was onLoggedIn closure
  }
  @Dependency(\.authClient) var authClient                     // was injected AuthService

  var body: some ReducerOf<Self> {
    BindingReducer()
    Reduce { state, action in
      switch action {
      case .loginButtonTapped:
        state.isLoading = true
        state.errorMessage = nil
        return .run { [email = state.email, password = state.password] send in
          await send(.loginResponse(Result { try await authClient.login(email, password) }))
        }
      case .loginResponse(.success):
        state.isLoading = false
        return .send(.delegate(.loggedIn))
      case let .loginResponse(.failure(error)):
        state.isLoading = false
        state.errorMessage = error.localizedDescription
        return .none
      case .binding, .delegate:
        return .none
      }
    }
  }
}

struct LoginView: View {
  @Bindable var store: StoreOf<LoginFeature>
  var body: some View {
    Form {
      TextField("Email", text: $store.email)
      SecureField("Password", text: $store.password)
      Button("Log in") { store.send(.loginButtonTapped) }
      if store.isLoading { ProgressView() }
      if let e = store.errorMessage { Text(e).foregroundStyle(.red) }
    }
  }
}
```
`authClient`: a `@DependencyClient` wrapping `AuthService` (`liveValue` = the real impl).

## Combine → Effects

| Combine in the ViewModel | TCA |
|---|---|
| `$query.debounce(...).map{…}.sink{ self.results = … }` | `.run` effect with `@Dependency(\.continuousClock)` debounce → `send(.results(...))` |
| `service.publisher().sink { self.x = $0 }` | `for await v in service.stream() { await send(.update(v)) }` in `.run` |
| `Just(x).delay(...)` | `try await clock.sleep(for:)` in `.run` |
| `@Published` derived from others (`$a.combineLatest($b)`) | a **computed property** on `State` (no stored prop, no Combine) |

Prefer `async`/`await` + computed `State` over porting Combine graphs verbatim.

## Step-by-step (per ViewModel)

1. Create `State` from every `@Published` property (value types). Derived `@Published` → computed.
2. Create `Action` from every public method/intent + each async result + `binding` + a `delegate`
   enum for navigation signals (closures/delegates the VM exposed).
3. Move injected services into `@DependencyClient`s; method bodies → reducer `case`s; async work → `.run`.
4. Convert two-way bound `@Published` via `BindingReducer()` + `@Bindable store`.
5. Replace the View's `@StateObject`/`@ObservedObject var vm` with `let store: StoreOf<Feature>`
   (or `@Bindable` if it binds); read `store.x`.
6. Delete the ViewModel class and any `Input`/`Output`/`transform` scaffolding.

## Detection signals (is this module MVVM?)

Suffixes `*ViewModel`, `*VM`, `*ViewModelType`/`*ViewModelProtocol`; `: ObservableObject`,
`@Published`, `@StateObject`/`@ObservedObject`; Combine (`AnyCancellable`, `.sink`, `.assign`,
`PassthroughSubject`) or RxSwift (`Driver`, `BehaviorRelay`); Input/Output structs with a
`transform(input:)`. No Presenter/Interactor/Router (that's VIPER) and no UseCase/Repository-heavy
Domain/Data split (that's Clean) — though MVVM is often layered on top of Clean's domain.
