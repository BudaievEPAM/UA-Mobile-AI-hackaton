# Knowledge base — the migration quality lever

Canonical, version-pinned rules + exemplars that **both** the Spec Kit templates (constitution /
spec / plan / tasks) **and** the RUFLO worker skills cite. Authored against **TCA 1.25.2** and
**Tuist 4.139**. Keep this the single source of truth; if TCA/Tuist drift, update here first.

| File | Purpose |
|---|---|
| [tca-patterns.md](tca-patterns.md) | Canonical modern TCA (`@Reducer`, `@ObservableState`, `@Dependency`, navigation, effects) + anti-patterns to reject. |
| [viper-to-tca.md](viper-to-tca.md) | VIPER (View/Interactor/Presenter/Entity/Router) → TCA mapping table + worked example + per-module procedure. |
| [clean-to-tca.md](clean-to-tca.md) | Clean (Domain/Data/Presentation, UseCase/Repository/DIContainer/FlowCoordinator) → TCA. |
| [mvvm-to-tca.md](mvvm-to-tca.md) | MVVM (View/ViewModel/Model, `ObservableObject`/`@Published`/Combine/RxSwift, Input-Output) → `@Reducer`/`State`/`Effect`/`@Dependency`. |
| [mvvm-coordinator-to-tca.md](mvvm-coordinator-to-tca.md) | MVVM + **Coordinator** (Coordinator/childCoordinators/nav flows) → state-driven `StackState`/`@Presents` navigation. |
| [swift-testing-tca.md](swift-testing-tca.md) | Swift Testing (`@Suite`/`@Test`/`#expect`) + TCA `TestStore`; XCTest→Swift Testing table. |
| [tuist-templates/](tuist-templates/) | Tuist 4.x `Workspace`/`Tuist`/`Package` manifests + `Project.feature/core/app` factories + module graph. |

## How it's consumed

1. **Spec layer** — `scripts/load_knowledge.sh` seeds the Spec Kit constitution; the mapping
   tables shape `templates/{spec,plan,tasks}-template.md`.
2. **Execution layer** — `load_knowledge.sh` loads these into RUFLO **AgentDB** (`memory_store`)
   so every swarm worker can retrieve them (RAG). Worker skills also reference the file paths
   directly, so the system works even if AgentDB load is unavailable.

## Editing rules

- Change **API/version** facts here, not in the skills.
- Add a new source-architecture? Add a `*-to-tca.md` with a mapping table + worked example +
  detection signals, then list it here and in `scripts/load_knowledge.sh`.
