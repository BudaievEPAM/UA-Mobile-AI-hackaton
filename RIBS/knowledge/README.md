# Knowledge base — iOS (MVVM+Coordinator / Clean) → Kotlin Multiplatform + RIBs

The quality lever for the harness. The analyzer cites it, the planner derives RIB contracts from it,
and the migration agent is given the relevant files verbatim in its prompt.

| File | Covers |
|---|---|
| [`ribs-patterns.md`](ribs-patterns.md) | RIB anatomy (Builder/Interactor/Router/Presenter/View), the `core-ribs` runtime, wiring rules. |
| [`mvvm-coordinator-to-ribs.md`](mvvm-coordinator-to-ribs.md) | The core component table: ViewModel→Interactor+Presenter, Coordinator→Router, routes enum→Listener+`routeTo`. |
| [`clean-to-kmp.md`](clean-to-kmp.md) | Domain/Data/Persistence/Networking/DI layers → KMP `commonMain` + `expect`/`actual`; stack substitutions. |
| [`combine-to-coroutines.md`](combine-to-coroutines.md) | `@Published`/`Subject`/`AnyPublisher`/`.sink` → `StateFlow`/`SharedFlow`/`suspend`/`Flow`. |
| [`kmp-stack.md`](kmp-stack.md) | Pinned versions, Gradle layout, why `core-ribs` instead of Uber RIBs on KMP. |

Edit these before changing versions or mapping rules — the harness output follows them.
