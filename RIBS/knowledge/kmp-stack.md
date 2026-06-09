# KMP + RIBs target stack (pinned)

The harness generates a Gradle Kotlin-Multiplatform project against this stack. Update this file
first if versions drift; the scaffolder and the agent both read it.

| Concern | Choice | Version |
|---|---|---|
| Language | Kotlin (multiplatform) | 2.0.21 |
| Build | Gradle + Kotlin DSL | 8.9 |
| Targets | `androidTarget()`, `iosX64/iosArm64/iosSimulatorArm64` | — |
| UI | Compose Multiplatform | 1.7.x |
| Async | kotlinx-coroutines | 1.9.x |
| HTTP | Ktor client (engines: Darwin / OkHttp) | 3.0.x |
| JSON | kotlinx-serialization | 1.7.x |
| DB | SQLDelight | 2.0.x |
| DI | RIBs `Component` (hand-rolled) — Koin optional | — |
| RIBs runtime | `core-ribs` (generated, KMP-friendly base classes) | in-repo |

## Why a hand-rolled `core-ribs` and not Uber RIBs

Uber's `com.uber.rib:rib-base` is Android/JVM-only (depends on the Android framework + RxJava/Dagger).
It cannot compile in `commonMain`. The harness emits a tiny, coroutine-based `core-ribs` (≈3 base
classes — see [ribs-patterns.md](ribs-patterns.md)) so the *architecture* (Builder/Interactor/Router,
attach/detach tree, lifecycle) is faithful and the code is genuinely multiplatform. Teams that ship
Android-only can later swap `core-ribs` for Uber RIBs with minimal change to feature code.

## Project skeleton

```
<Project>/
├── settings.gradle.kts
├── build.gradle.kts            (root: plugin versions)
├── gradle/libs.versions.toml   (version catalog — values above)
├── gradle.properties
├── shared/
│   ├── build.gradle.kts        (KMP module: targets + deps)
│   └── src/{commonMain,androidMain,iosMain}/kotlin/...
├── androidApp/                 (Android entry point + Activity host)
└── iosApp/                     (placeholder; SwiftUI host that embeds the shared framework)
```

## Conventions

- Package root: `com.<org>.<app>` (derived from the source app name, lowercased).
- One Kotlin package per feature RIB; files: `XBuilder.kt`, `XInteractor.kt`, `XRouter.kt`,
  `XPresenter.kt`, `XView.kt`, `XListener.kt` (+ `XComponent`/`XDependency`).
- `commonMain` holds all logic + Compose UI; `androidMain`/`iosMain` hold only `actual` declarations.
- Tests use `kotlin.test` + coroutines-test (`runTest`) under `commonTest`.
