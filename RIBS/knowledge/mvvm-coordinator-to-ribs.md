# MVVM + Coordinator (iOS) → RIBs (Kotlin Multiplatform)

> The core mapping. EasyCrypto-style apps put a `ViewModel` (Combine `@Published` + a
> `navigateSubject`) behind a `View`, and a `Coordinator` that owns a routes enum and turns
> ViewModel navigation signals into `push`/`sheet` transitions. RIBs splits those same concerns
> across Builder / Interactor / Router / Presenter / Listener.

## Component mapping (the core table)

| iOS MVVM+Coordinator component | RIB target | Notes |
|---|---|---|
| **Coordinator** (`MainCoordinator`, `CoinDetailCoordinator`) | dissolved → **Router** (+ **Builder**) | The class is deleted. Its `body`/`Destination` switch → Router `routeToX`. |
| `CoordinatorProtocol` / `Coordinatable` / `AppRouter` ViewModifier | `core-ribs` base `Router` + the RIB tree | The whole routing protocol family collapses into `attachChild`/`detachChild`. |
| **`Destination` / `Routes` enum** (`case .first(item)`, `case .second(id)`) | one **`routeToX()`** per case on the Router | `.push` → attach as full-screen child; `.bottomSheet` → attach as sheet child; `.url` → `SafariView`-equivalent leaf RIB / platform handler. |
| `viewModel.navigateSubject.send(.second(id))` (Combine `PassthroughSubject`) | Interactor calls `listener?.coinDetailRequested(id)` → parent Router attaches child | The subject → a typed **Listener** callback. No global subject. |
| **ViewModel** (`MainViewModel: DefaultViewModel`) | **Interactor** (logic/lifecycle) + **Presenter** (state shaping) | `@Published` state → Presenter `StateFlow<ViewState>`; methods → Interactor functions. |
| `@Published var marketData` / `searchText` / `rankSort` | `MutableStateFlow` inside Presenter, exposed as `StateFlow<MainViewState>` | See [combine-to-coroutines.md](combine-to-coroutines.md). |
| `func apply(_ input: .onAppear)` (`DataFlowProtocol`) | `Interactor.didBecomeActive()` | RIB lifecycle replaces `onAppear`. |
| `loadingState: CurrentValueSubject<ViewModelStatus,_>` (`BaseViewModel`) | `StateFlow<LoadState>` on the Presenter (`Idle/Loading/Error`) | `BaseViewModel.call(...)` → an Interactor helper that wraps a `suspend`/`Flow` call and maps errors. |
| **View** (`MainView`, SwiftUI) | **View** (Compose Multiplatform) implementing `MainPresentable` render | `body` → `@Composable fun MainScreen(state, listener)`. |
| Subviews (`CryotoCell`, `SearchBar`, `SortView`) | private `@Composable`s in the View file | Pure UI, no logic. |
| **`DIContainer.shared.inject(type:)`** service locator | constructor injection via the RIB **Component / Dependency** interface | Global locator is removed; see [clean-to-kmp.md](clean-to-kmp.md). |
| `@StateObject var viewModel` lifecycle ownership | Builder constructs Interactor; `core-ribs` owns lifecycle | View no longer owns the VM. |

## The navigation translation (worked example, EasyCrypto `MainCoordinator`)

iOS:

```swift
// MainCoordinator.Destination
case .first(let item):  DetailView(item: item)                                  // .push
case .second(let data): CoinDetailCoordinator(viewModel: ..., id: data)         // .bottomSheet
// MainViewModel
func didTapFirst(item)  { navigateSubject.send(.first(item: item)) }
func didTapSecond(id)   { navigateSubject.send(.second(id: id)) }
```

RIBs (generated):

```kotlin
// MainListener — parent (App) implements; child Main RIB calls it
interface MainListener {
    fun detailRequested(item: MarketsPrice)     // was .first / .push
    fun coinDetailRequested(id: String)         // was .second / .bottomSheet
}

// MainInteractor — was MainViewModel's navigation intent
fun didTapFirst(item: MarketsPrice)  { listener?.detailRequested(item) }
fun didTapSecond(id: String)         { listener?.coinDetailRequested(id) }

// AppRouter — was the Coordinator's Destination switch
override fun detailRequested(item: MarketsPrice) {
    attachChild(detailBuilder.build(item))                 // push child
}
override fun coinDetailRequested(id: String) {
    attachChild(coinDetailBuilder.build(id), asSheet = true) // bottom-sheet child
}
```

The transition kind (`.push` / `.bottomSheet` / `.url`) is preserved as metadata on the attach call
so the platform View layer can present it correctly; the *logic* (when to navigate) is identical.

## RIB tree (derived from the Coordinator graph)

EasyCrypto's coordinators (`MainCoordinator` → presents `DetailView` and `CoinDetailCoordinator`)
become:

```
RootRIB (App)
└── MainRIB                 (was MainCoordinator + MainView + MainViewModel)
    ├── DetailRIB           (was .first/.push → DetailView + DetailViewModel)
    └── CoinDetailRIB       (was .second/.bottomSheet → CoinDetailCoordinator + CoinDetailViewModel)
```

One RIB per (View + ViewModel [+ Coordinator]) triple. A Coordinator that only wraps a single
screen merges into that screen's RIB; a Coordinator that fans out to several screens becomes the
parent Router of those child RIBs.

## Checklist per feature RIB

- [ ] `Dependency` interface lists exactly the UseCases/repositories the old ViewModel pulled from `DIContainer`.
- [ ] `Builder.build(...)` takes the same "input" the Coordinator passed (e.g. `id`, `item`).
- [ ] Every `navigateSubject.send(case)` has a matching `Listener` method + Router `routeTo`.
- [ ] Every `@Published` is in the Presenter's `ViewState`; `private(set)` ones are read-only there.
- [ ] `didBecomeActive()` reproduces `apply(.onAppear)` (bind + first load).
- [ ] No `DIContainer`, no Combine, no SwiftUI symbols remain in `commonMain`.
