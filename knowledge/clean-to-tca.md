# Clean Architecture (+ MVVM) → TCA mapping rules

> How to convert Clean Architecture layers into idiomatic TCA. Pair with
> [tca-patterns.md](tca-patterns.md). Reference shape =
> [kudoleh/iOS-Clean-Architecture-MVVM](https://github.com/kudoleh/iOS-Clean-Architecture-MVVM):
> **Domain** (Entities, UseCases, Repository interfaces) · **Data** (Repository impls, API, DTOs,
> Persistence) · **Presentation** (ViewModels, Views), wired by a **DIContainer** + **FlowCoordinator**.

## Component mapping (the core table)

| Clean / MVVM component | TCA target | Notes |
|---|---|---|
| **Entity** (Domain) | Domain model in `SharedModels` / feature `State` | `Equatable`, `Sendable` value types. Keep pure. |
| **Repository protocol** (Domain) | A `@DependencyClient` struct | The protocol's methods become closure properties. |
| **Repository impl + API + DTO + Mapper** (Data) | The client's `liveValue` | DTO decoding + DTO→Entity mapping happen **inside** the live closure. DTOs stay in `Core/Networking`, never leak into `State`. |
| **UseCase** (Domain) | Usually a method on a `@DependencyClient`; sometimes reducer logic | A pure orchestration UseCase with no I/O → fold into the reducer/effect. An I/O UseCase → a dependency method. |
| **ViewModel** (Presentation, MVVM) | `@Reducer` (`State` + `Action` + effects) | `@Published`/`Observable` props → `@ObservableState`; intent methods → `Action`; `async` calls → `.run` effects. **Delete the ViewModel class.** |
| **View** (`UIView`/SwiftUI/Storyboard) | SwiftUI `View` with `StoreOf<Feature>` | Storyboards/UIKit → SwiftUI. |
| **FlowCoordinator** | `StackState` / `@Presents` | `coordinator.showDetail(x)` → Action setting path/destination state. |
| **DIContainer** (`*DIContainer`, `makeX()` factories) | `@Dependency` + `DependencyValues` | Each registration → a `DependencyKey.liveValue`. The container is **deleted**. |
| **Errors** (Domain error types) | Keep; surface via `Action` result + `State` | Map Data errors → Domain errors inside the client. |

## Layer dependency rule (preserved, but realized differently)

Clean's rule "Presentation → Domain ← Data" becomes Tuist module edges:
`Feature → SharedModels` and `Feature → Core/Networking` (for the client *interface*), with the
**live** client wired only in the composition root (App). Reducers depend on the *client struct*,
not its implementation — same dependency-inversion benefit, no protocols.

## Worked example (UseCase + Repository → dependency client + reducer)

**Before (Clean + MVVM):**
```swift
// Domain
protocol MoviesRepository { func fetchMovies(query: String) async throws -> [Movie] }
protocol SearchMoviesUseCase { func execute(query: String) async throws -> [Movie] }
final class DefaultSearchMoviesUseCase: SearchMoviesUseCase {
  let repository: MoviesRepository
  func execute(query: String) async throws -> [Movie] { try await repository.fetchMovies(query: query) }
}
// Presentation (MVVM)
final class MoviesListViewModel: ObservableObject {
  @Published var items: [Movie] = []
  @Published var isLoading = false
  let useCase: SearchMoviesUseCase
  func search(_ query: String) async {
    isLoading = true; defer { isLoading = false }
    items = (try? await useCase.execute(query: query)) ?? []
  }
}
```

**After (TCA):**
```swift
// Core/Networking: the repository interface as a dependency client (live impl decodes DTO -> Entity)
@DependencyClient
struct MoviesClient {
  var fetchMovies: (_ query: String) async throws -> [Movie]
}
extension MoviesClient: DependencyKey {
  static let liveValue = Self(
    fetchMovies: { query in
      let dto: MoviesResponseDTO = try await API.get("/search", ["q": query])
      return dto.results.map(Movie.init(dto:))            // DTO -> Entity mapping lives here
    }
  )
}
extension DependencyValues { var moviesClient: MoviesClient { get { self[MoviesClient.self] } set { self[MoviesClient.self] = newValue } } }

// Feature module: the ViewModel becomes a reducer
@Reducer
struct MoviesListFeature {
  @ObservableState
  struct State: Equatable {
    var query = ""
    var items: IdentifiedArrayOf<Movie> = []
    var isLoading = false
  }
  enum Action: BindableAction {
    case binding(BindingAction<State>)
    case searchSubmitted
    case moviesResponse(Result<[Movie], Error>)
  }
  @Dependency(\.moviesClient) var moviesClient

  var body: some ReducerOf<Self> {
    BindingReducer()
    Reduce { state, action in
      switch action {
      case .searchSubmitted:
        state.isLoading = true
        return .run { [q = state.query] send in
          await send(.moviesResponse(Result { try await moviesClient.fetchMovies(q) }))
        }
      case let .moviesResponse(.success(movies)):
        state.isLoading = false
        state.items = IdentifiedArray(uniqueElements: movies)
        return .none
      case .moviesResponse(.failure):
        state.isLoading = false
        return .none
      case .binding:
        return .none
      }
    }
  }
}
```

## When a UseCase is *not* just a repository pass-through

If a UseCase composes multiple repositories or adds non-trivial business rules:
- Pure rules (no I/O) → put them in the reducer (or a free `func` in the Domain/SharedModels module).
- Multi-source orchestration → a single `@DependencyClient` method whose live impl calls the
  several lower-level clients, **or** an effect that `await`s multiple `@Dependency` clients.
Keep the reducer readable; push I/O to dependencies.

## Detection signals (is this module Clean / MVVM?)

Folder names `Domain/`, `Data/`, `Presentation/`, `Infrastructure/`; suffixes `*UseCase`,
`*Repository`, `*DTO`, `*Mapper`, `*ViewModel`, `*DIContainer`, `*FlowCoordinator`,
`*Coordinator`; `ObservableObject`/`@Published` view models; repository **protocols** in Domain
with implementations in Data.
