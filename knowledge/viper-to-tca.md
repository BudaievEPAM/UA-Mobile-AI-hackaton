# VIPER → TCA mapping rules

> How to convert each VIPER component into idiomatic TCA. Pair with [tca-patterns.md](tca-patterns.md).
> VIPER = **V**iew, **I**nteractor, **P**resenter, **E**ntity, **R**outer, wired by protocols.

## Component mapping (the core table)

| VIPER component | TCA target | Notes |
|---|---|---|
| **View** (`UIViewController` / `*View` + `ViewInput` protocol) | SwiftUI `View` with `let store: StoreOf<Feature>` | `ViewInput` update methods disappear — the View observes `store` state directly. |
| **Presenter** (`*Presenter`, `ViewOutput` + `InteractorOutput`) | **Folded into the `Reducer`** | Presentation/formatting logic → reducer logic + computed `State` props. The Presenter class is **deleted**, not ported. |
| **Interactor** (`*Interactor`, `InteractorInput`, services) | `@Dependency` client(s) + reducer effects | Each service call → a method on a `@DependencyClient`. Orchestration → `.run` effects. |
| **Entity** | Domain model in `State` / `SharedModels` | Plain `Equatable`/`Sendable` value types. |
| **Router / Wireframe** (`*Router`, `present/push`) | `StackState` / `@Presents` destinations | "navigate to X" methods → Actions that set destination/path state. |
| **Builder / Module / Assembly / Configurator** | `Store(initialState:) { Feature() }` + Tuist module | DI wiring → `@Dependency` live values. |
| **`ViewOutput` methods** (user intents) | `Action` cases | `didTapLogin()` → `case loginButtonTapped`. |
| **`InteractorOutput` callbacks** (results) | `Action` cases | `didFetch(items:)` → `case itemsResponse(Result<[Item], Error>)`. |

## The protocol collapse

VIPER's value is mostly its protocols (`ViewInput/Output`, `InteractorInput/Output`,
`PresenterInput`, `RouterInput`). In TCA these collapse into **two enums**:

- **Inputs to the system** (user taps, lifecycle, results coming back) → `Action` cases.
- **Outputs of the system** (what the user sees) → `State` (observed by the View).

Delete every VIPER protocol. Do **not** create TCA equivalents of them.

## Worked example

**Before (VIPER):**
```swift
// LoginPresenter.swift
protocol LoginViewInput: AnyObject { func showError(_ msg: String); func setLoading(_ on: Bool) }
protocol LoginViewOutput { func didTapLogin(email: String, password: String) }
protocol LoginInteractorInput { func login(email: String, password: String) }
protocol LoginInteractorOutput: AnyObject { func loginSucceeded(token: String); func loginFailed(_ e: Error) }

final class LoginPresenter: LoginViewOutput, LoginInteractorOutput {
  weak var view: LoginViewInput?
  var interactor: LoginInteractorInput!
  var router: LoginRouterInput!
  func didTapLogin(email: String, password: String) {
    view?.setLoading(true); interactor.login(email: email, password: password)
  }
  func loginSucceeded(token: String) { view?.setLoading(false); router.routeToHome() }
  func loginFailed(_ e: Error) { view?.setLoading(false); view?.showError(e.localizedDescription) }
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
    case binding(BindingAction<State>)
    case loginButtonTapped                                   // was didTapLogin
    case loginResponse(Result<String, Error>)               // was Interactor output
    case delegate(Delegate)
    enum Delegate { case loggedIn(token: String) }          // parent handles routing
  }
  @Dependency(\.authClient) var authClient                  // was LoginInteractor

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
      case let .loginResponse(.success(token)):
        state.isLoading = false
        return .send(.delegate(.loggedIn(token: token)))     // routing handled by parent
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
```
`authClient`:
```swift
@DependencyClient
struct AuthClient { var login: (_ email: String, _ password: String) async throws -> String }
extension AuthClient: DependencyKey { static let liveValue = Self(login: { e, p in /* real call */ }) }
extension DependencyValues { var authClient: AuthClient { get { self[AuthClient.self] } set { self[AuthClient.self] = newValue } } }
```

## Routing: Router → delegate-up + state navigation

VIPER Routers call the next module imperatively. In TCA, a **leaf feature does not navigate
itself** — it emits a `delegate` action and the **parent** owns the `StackState`/`@Presents` and
performs the navigation (see stack/tree navigation in tca-patterns.md). This is the single most
common mistake to avoid: don't recreate the Router inside the child.

## Step-by-step procedure (per VIPER module)

1. Identify the 5 files (View/Presenter/Interactor/Entity/Router) + protocols for the module.
2. Create `State` from: Presenter's stored display data + View's rendered fields + Entity models.
3. Create `Action` from: every `ViewOutput` method (intents) + every `InteractorOutput` callback
   (results) + `binding` + a `delegate` enum for things the parent must handle (navigation).
4. Move Interactor service calls into a `@DependencyClient`; move orchestration into `.run` effects.
5. Move Presenter logic into the `Reduce` switch; delete the Presenter.
6. Convert the View to SwiftUI reading `store`.
7. Replace Router navigation with `delegate` actions consumed by the parent's `StackState`/`@Presents`.
8. Delete all VIPER protocols and the Builder; the Tuist module + `Store` replace them.

## Detection signals (is this module VIPER?)

Filenames/suffixes: `*Presenter`, `*Interactor`, `*Router`, `*Wireframe`, `*Builder`,
`*Configurator`, `*ModuleInput/Output`, paired `*ViewInput`/`*ViewOutput` protocols, a `Module`
folder per screen. CocoaPods/Carthage with `Viperit`/`Generamba` templates is a strong signal.
