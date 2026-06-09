# Migration task: fill the `{rib_name}` RIB

You are porting one feature of the iOS app **{app}** (architecture: {architecture}) to a Kotlin
Multiplatform project using **RIBs**. The skeleton already exists; your job is to replace every
`// TODO(ios2ribs):` in this RIB with correct Kotlin, preserving behavior exactly.

## Target RIB contract

- Package: `{package}`
- Dependencies (inject, do not use a service locator): {dependencies}
- ViewState fields (from the ViewModel's `@Published`): {state_fields}
- Builder input args: {build_args}
- Navigation (each becomes a Listener method + Router `routeTo`):
{routes}

## Rules (from the knowledge base — follow exactly)

1. `ViewModel` logic → **Interactor**; `@Published` state → **Presenter** `StateFlow<ViewState>`.
2. `Coordinator` routing → **Router** `attachChild`/`detachChild`; route enum cases → **Listener** methods.
3. Combine → coroutines: `AnyPublisher` (one value) → `suspend`; streams → `Flow`;
   `@Published` → `MutableStateFlow`; `.debounce/.removeDuplicates` → `.debounce/.distinctUntilChanged`.
4. No `DIContainer`, no Combine, no SwiftUI symbols in `commonMain`.
5. `didBecomeActive()` must reproduce the Swift `apply(.onAppear)` / `onAppear` behavior.
6. `commonMain` is **multiplatform** — no `java.*` imports and no JVM-only APIs (e.g. `String.format`,
   `java.text.*`). Format numbers with the kotlin stdlib / `kotlin.math` (round + divide) instead.
7. The View is **Compose Multiplatform** (`androidx.compose.*`, `@Composable`) — the `shared` module
   already applies the Compose plugins, so import `androidx.compose.runtime/foundation/material3/ui`.

## Source Swift (the ground truth — match this behavior)

{source_swift}

## Knowledge references (excerpts)

{knowledge}

## Output

Return the full contents of each Kotlin file in this RIB with the TODOs resolved. Do not change the
public types/signatures already scaffolded unless a TODO explicitly asks you to declare them.
