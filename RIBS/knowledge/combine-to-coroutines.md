# Combine → kotlinx.coroutines

> EasyCrypto is Combine-heavy: `@Published`, `PassthroughSubject`, `CurrentValueSubject`,
> `AnyPublisher<T, APIError>`, `.debounce`, `.removeDuplicates`, `.sink(store:)`. Map each to a
> coroutine/Flow equivalent.

## Primitive mapping

| Combine | Coroutines | Notes |
|---|---|---|
| `@Published var x` | `private val _x = MutableStateFlow(initial)` + `val x: StateFlow<T> = _x.asStateFlow()` | Hot, always-has-value. |
| `CurrentValueSubject<T, Never>` | `MutableStateFlow<T>` | Same semantics (replays latest). |
| `PassthroughSubject<T, Never>` (e.g. `navigateSubject`) | `MutableSharedFlow<T>(extraBufferCapacity = 1)` | No initial value. For *navigation* prefer a typed `Listener` callback instead of a flow. |
| `AnyPublisher<T, APIError>` (one-shot, e.g. UseCase `execute`) | `suspend fun(): T` returning, or `Result<T>` / throwing a typed exception | One value + completion ⇒ `suspend`. |
| `AnyPublisher<[T], APIError>` (stream, e.g. cache fetch) | `Flow<List<T>>` | Multiple values ⇒ `Flow`. |
| `.sink { }.store(in: subscriber)` | `flow.onEach { }.launchIn(scope)` | `scope` = Interactor's `scope`, cancelled on `willResignActive`. |
| `.subscribe(on: background).receive(on: main)` | `flowOn(Dispatchers.IO)` / collect on `Dispatchers.Main` | `WorkScheduler.backgroundWorkScheduler` → `Dispatchers.IO`. |
| `.debounce(for: 1.0, scheduler:)` | `.debounce(1000)` | Flow operator (kotlinx). |
| `.removeDuplicates()` | `.distinctUntilChanged()` | |
| `.map { }` / `.flatMap { }` | `.map { }` / `.flatMapLatest { }` | |
| `Cancelable` / `Set<AnyCancellable>` | `CoroutineScope` + `Job` (owned by Interactor) | `deactivate()` cancels children. |
| `Future` / `Deferred` | `async { }` / `suspend` | |

## EasyCrypto worked examples

`BaseViewModel.call(...)` (loading + error wrapper):

```swift
func call<T>(argument: AnyPublisher<T, APIError>, callback: @escaping (T)->Void) {
    loadingState.send(.loadStart)
    argument.subscribe(on: bg).receive(on: main)
        .sink(receiveCompletion: { if case .failure(let e) = $0 { loadingState.send(.emptyStateHandler(e.desc)) } },
              receiveValue: { callback($0) }).store(in: subscriber)
}
```

→ Interactor helper:

```kotlin
protected fun <T> load(block: suspend () -> T, onSuccess: (T) -> Unit) {
    scope.launch {
        presenter.setLoadState(LoadState.Loading)
        runCatching { withContext(Dispatchers.IO) { block() } }
            .onSuccess { presenter.setLoadState(LoadState.Idle); onSuccess(it) }
            .onFailure { presenter.setLoadState(LoadState.Error(it.toApiError())) }
    }
}
```

`MainViewModel.bindData()` (debounced search):

```swift
$searchText.debounce(for: 1.0, scheduler: .main).removeDuplicates()
    .sink { [weak self] text in /* search or clear */ }.store(in: subscriber)
```

→ Interactor `didBecomeActive`:

```kotlin
presenter.searchText
    .debounce(1000)
    .distinctUntilChanged()
    .onEach { text -> if (text.isEmpty()) clearSearch() else search(text.lowercase()) }
    .launchIn(scope)
```

`MarketPriceUsecase.execute(...) -> AnyPublisher<[MarketsPrice]?, APIError>`:

```kotlin
interface MarketPriceUseCase {
    suspend fun execute(vsCurrency: String, order: String, perPage: Int, page: Int, sparkline: Boolean): List<MarketsPrice>
}
```

## Rules

1. **One value ⇒ `suspend`; many values ⇒ `Flow`.** Don't model one-shot API calls as `Flow`.
2. **Navigation is not a stream.** `navigateSubject` becomes a `Listener` interface, not a `SharedFlow`.
3. **Errors are exceptions or `Result`, not a failure-typed publisher.** Map `APIError` → a sealed
   `ApiException`; surface via `Result`/`try`.
4. **Scope ownership.** Every `launchIn`/`launch` uses the Interactor's `scope`, cancelled on deactivate
   (replaces `[weak self]` + `Cancelable`).
