# Clean architecture layers (iOS) → Kotlin Multiplatform modules

> EasyCrypto already has clean layers — `Domain` (Entity, UseCase), `Data` (Remote, Repository),
> `Persistance` (CoreData), `Core/Networking`. These move almost 1:1 into KMP `commonMain`; only the
> platform-specific edges (HTTP engine, DB driver) use `expect`/`actual`.

## Layer mapping

| iOS layer | KMP location | Translation |
|---|---|---|
| `Domain/Entity/*` (structs: `MarketsPrice`, `Coin`, `SearchMarket`, `CoinUnit`) | `shared/commonMain/.../domain/model` | Swift `struct` → Kotlin `data class`. `Codable` → `@Serializable` (kotlinx.serialization). Optionals `T?` → `T?`. |
| `Domain/Usecase/*` (`MarketPriceUsecase`, `SearchMarketUsecase`, `CoinMarketUsecase`) | `shared/commonMain/.../domain/usecase` | Protocol → `interface`; `execute(...) -> AnyPublisher<T?,APIError>` → `suspend fun execute(...): Result<T>` **or** `fun execute(...): Flow<T>`. See [combine-to-coroutines.md](combine-to-coroutines.md). |
| `Data/Repository/*` (`MarketPriceRepository`, `CoinDetailRepository`, `SearchMarketRepository`) | `shared/commonMain/.../data/repository` | `protocol …RepositoryProtocol` → `interface …Repository`; impl uses the Ktor client + serialization. |
| `Data/Remote/*` (`MarketPriceRemote`, …) | `shared/commonMain/.../data/remote` | Endpoint definitions → Ktor request builders / a sealed `Endpoint`. |
| `Core/Networking/*` (custom Combine `NetworkClient`, `NetworkTarget`, `RequestBuilder`, `APIError`) | `shared/commonMain/.../core/network` | Replace with **Ktor** `HttpClient`. `NetworkTarget`→ request DSL; `APIError`→ Kotlin sealed class; `Encoding`→ Ktor content negotiation. |
| `Persistance/*` (CoreData: `CoreDataManager`, fetch/save/delete publishers) | `shared/commonMain` interface + `expect`/`actual` driver | Replace CoreData with **SQLDelight** (`.sq` schema → generated queries). Cache repository → SQLDelight-backed impl returning `Flow`. |
| `DIManager/AppDependencyContainer` (`DIContainer.shared` service locator) | RIB **Component** graph (constructor injection) | Each `register(type:component:)` becomes a provider in a Component; each `inject(type:)` becomes a constructor parameter. No global singleton. |
| `Core/Components/ImageDownloader`, `CurrencyFormatter`, `DecimalFormatter` | `commonMain` utils (formatters) / Compose `AsyncImage` (image) | Pure formatters port directly; image loading → Coil (Compose) or platform `actual`. |
| `Support/Extension/*` | `commonMain` extension functions | Most port directly; UI extensions (`Color+`, `View+`) go to the View layer. |
| `Theme/*` | Compose theme (`commonMain`) | Colors/fonts → Compose `MaterialTheme`. |

## Stack substitutions (iOS → KMP)

| iOS | KMP replacement |
|---|---|
| Custom Combine `NetworkClient` / URLSession | **Ktor** (`io.ktor:ktor-client-core` + engine `actual`) |
| `Codable` | **kotlinx.serialization** (`@Serializable`) |
| CoreData | **SQLDelight** |
| Combine | **kotlinx.coroutines** (`Flow`, `suspend`) |
| `DIContainer` service locator | RIB **Component** (hand-rolled) or **Koin** if the user prefers a DI lib |
| GCD / `WorkScheduler` (background/main) | `Dispatchers.IO` (`actual`) / `Dispatchers.Main` |
| SwiftUI | **Compose Multiplatform** |

## Module layout produced

```
shared/
  src/commonMain/kotlin/<pkg>/
    core/network/      (Ktor client, Endpoint, ApiError)
    core/ribs/         (Interactor/Router/Builder base — see ribs-patterns.md)
    domain/model/      (data classes)
    domain/usecase/    (interfaces + impls)
    data/remote/       (Ktor request builders)
    data/repository/   (interfaces + impls)
    features/<feature>/ (one package per RIB: Builder/Interactor/Router/Presenter/View)
    app/               (Root RIB + Component)
  src/androidMain/     (actual: Ktor engine = OkHttp, SQLDelight = AndroidSqliteDriver, Dispatchers.IO)
  src/iosMain/         (actual: Ktor engine = Darwin, SQLDelight = NativeSqliteDriver)
```

## Dependency order (build + migrate in this order)

1. `core/network` + `core/ribs` (no feature deps)
2. `domain/model` (entities)
3. `domain/usecase` + `data/repository` + `data/remote` (depend on model + network)
4. leaf feature RIBs (depend on usecases)
5. parent feature RIBs (depend on leaf RIBs)
6. `app` Root RIB + Component (depends on everything)
