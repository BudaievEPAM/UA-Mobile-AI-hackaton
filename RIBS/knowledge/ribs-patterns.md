# RIBs anatomy (Kotlin Multiplatform target)

> Reference for every generated RIB. RIBs = **R**outer · **I**nteractor · **B**uilder, plus an
> optional **Presenter** + **View**. Business + navigation logic lives in `commonMain` (pure Kotlin,
> no UI framework); only the View is platform-specific.

## The five files of a RIB

| File | Responsibility | Lives in |
|---|---|---|
| **Builder** | Dependency injection + construction. `build(...)` wires the Component, creates Interactor/Router/Presenter, returns the `Router`. | `commonMain` |
| **Interactor** | Business logic + lifecycle (`didBecomeActive` / `willResignActive`). Holds child *listeners*, calls UseCases, drives the Presenter, asks the Router to attach/detach children. | `commonMain` |
| **Router** | Navigation only. `attachChild` / `detachChild`. Owns child Routers. Translates Interactor intent into RIB tree mutations. | `commonMain` |
| **Presenter / Presentable** | Maps domain state → `ViewModel`/`ViewState` the View renders; exposes a `PresentableListener` the View calls back on. Often folded into the Interactor via a `Presentable` interface. | `commonMain` |
| **View** | Renders `ViewState`, forwards user intent to the listener. Compose Multiplatform in `commonMain`, or `expect`/`actual` per platform. | `commonMain` (Compose) or platform source sets |

## Wiring contract (the seams)

```kotlin
// ---- Scope / DI ----
interface MainDependency {                 // what this RIB needs from its parent
    val marketPriceUseCase: MarketPriceUseCase
    val searchMarketUseCase: SearchMarketUseCase
}

// ---- Builder ----
class MainBuilder(dependency: MainDependency) : Builder<MainDependency>(dependency) {
    fun build(): MainRouter {
        val presenter = MainPresenter()
        val interactor = MainInteractor(presenter, dependency.marketPriceUseCase, dependency.searchMarketUseCase)
        return MainRouter(interactor, presenter, CoinDetailBuilder(dependency))
    }
}

// ---- Interactor ----
class MainInteractor(
    private val presenter: MainPresentable,
    private val marketPriceUseCase: MarketPriceUseCase,
    private val searchMarketUseCase: SearchMarketUseCase,
) : Interactor<MainPresentable>(presenter), MainPresentableListener {
    var listener: MainListener? = null            // parent communication
    override fun didBecomeActive() { /* load data, collect flows */ }
}

// ---- Router ----
class MainRouter(
    interactor: MainInteractor,
    private val presenter: MainPresentable,
    private val coinDetailBuilder: CoinDetailBuilder,
) : Router<MainInteractor>(interactor) {
    fun routeToCoinDetail(id: String) { attachChild(coinDetailBuilder.build(id)) }
    fun routeToDetail(item: MarketsPrice) { attachChild(detailBuilder.build(item)) }
}

// ---- Listener (child → parent) ----
interface MainListener {                   // implemented by the parent Interactor
    fun coinDetailRequested(id: String)
}
```

## Minimal runtime base classes

The harness scaffolds a tiny `core-ribs` module so generated code is self-contained (no Uber
RIBs Android-only dependency, which does not support KMP):

```kotlin
abstract class Interactor<P : Any>(protected val presenter: P) {
    private val _scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    protected val scope: CoroutineScope get() = _scope
    var active = false; private set
    fun activate() { if (!active) { active = true; didBecomeActive() } }
    fun deactivate() { if (active) { active = false; _scope.coroutineContext.cancelChildren(); willResignActive() } }
    protected open fun didBecomeActive() {}
    protected open fun willResignActive() {}
}

abstract class Router<I : Any>(val interactor: I) {
    private val children = mutableListOf<Router<*>>()
    fun load() { interactorActivate() }
    protected open fun interactorActivate() {}
    fun attachChild(child: Router<*>) { children += child; child.load() }
    fun detachChild(child: Router<*>) { children -= child; child.detach() }
    open fun detach() { children.forEach { it.detach() }; children.clear() }
}

abstract class Builder<D>(protected val dependency: D)
```

## Rules

1. **The Coordinator is dissolved.** No Coordinator class survives — its construction logic → Builder,
   its navigation logic → Router, its "what comes next" decisions → Interactor + Listener.
2. **Navigation is a tree mutation, not a stack push.** A route becomes `router.attachChild(child)`;
   dismissal becomes `router.detachChild(child)`.
3. **No UI imports in `commonMain` logic.** Interactor/Router/Builder never import Compose/SwiftUI.
4. **All I/O is injected.** UseCases, repositories, clients arrive through the `Dependency` interface
   and Component — never a global service locator.
5. **Child→parent talks through a `Listener`; parent→child through Builder args / Interactor calls.**
