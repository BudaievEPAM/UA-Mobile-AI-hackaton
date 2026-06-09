# ios2ribs — iOS → Kotlin Multiplatform (RIBs) migration harness

A Python harness that takes an existing **iOS** app (MVVM+Coordinator / Clean / VIPER) and produces
a **Kotlin Multiplatform** project structured with **RIBs** (Router · Interactor · Builder, plus
Presenter + View). It mirrors the sibling iOS→TCA harness in this repo, but is written in Python and
targets KMP instead of Swift/TCA.

```
input :  an iOS repo (e.g. workspace/input/EasyCrypto — SwiftUI + Combine, MVVM + Coordinator + Clean)
output:  a Gradle KMP project (RIBS/output/) — core-ribs runtime, domain/data in commonMain,
         one RIB per feature + a Root RIB, wired and ready for the agent to fill in logic.
```

## Pipeline

```
analyze ─▶ plan ─▶ scaffold ─▶ migrate (LLM agent) ─▶ verify ─▶ report
```

| Stage | What it does | Output |
|---|---|---|
| **analyze** | Walks the Swift repo, classifies files, detects architecture + stack, groups features, extracts `@Published` state, Coordinator routes, and DI dependencies. | `analysis.json` / `analysis.md` |
| **plan** | Builds the RIB tree (one RIB per UI feature + Root), maps each Coordinator route → a Router `attachChild`, each ViewModel dep → constructor injection, and lists supporting Kotlin artifacts in dependency order. | `plan.json` / `plan.md` |
| **scaffold** | Writes a real Gradle KMP project: `core-ribs` runtime, Ktor client, domain/data stubs, and the 7 files of every RIB (Builder/Interactor/Router/Presenter/View/Listener/Dependency) + Root + Component. Logic bodies are traceable `// TODO(ios2ribs):` markers. | the KMP project tree |
| **migrate** | Assembles a per-RIB prompt (RIB contract + originating Swift source + knowledge excerpts) and hands it to a configurable coding agent. Falls back to a **dry-run** (prompts only) when no agent command / API key is present, so the pipeline always completes offline. | `_prompts/*.prompt.md`, `agent_summary.json` |
| **verify** | The gate. Runs `gradle compileKotlinMetadata` if a toolchain exists; otherwise a static gate: structure completeness, Kotlin brace/paren balance, package decls, RIB-wiring integrity, and **no Combine/SwiftUI/DIContainer/@Published in `commonMain`**. Reports GREEN / YELLOW / RED. | `verify.json`, `MIGRATION_REPORT.md` |

## Run it

```bash
cd RIBS

# whole pipeline on the bundled EasyCrypto sample:
python3 -m harness run --input ../workspace/input/EasyCrypto --output ./output

# or step through:
python3 -m harness analyze  --input ../workspace/input/EasyCrypto --output ./output
python3 -m harness plan     --input ../workspace/input/EasyCrypto --output ./output
python3 -m harness scaffold --plan ./output/plan.json
python3 -m harness migrate  --plan ./output/plan.json --agent-cmd "claude -p"   # real translation
python3 -m harness verify   --plan ./output/plan.json
```

No third-party Python dependencies — stdlib only (Python 3.10+).

## What the harness produced for EasyCrypto

`mvvm+clean+coordinator` (94 Swift files) → KMP + RIBs:

```
Root
 └── Main            (was MainViewModel + MainCoordinator + MainView)
      ├── Detail     (.first / push     → DetailView)
      └── CoinDetail (.second / sheet   → CoinDetailCoordinator;  .url → Safari = external)
```

- `MainCoordinator`'s `Destination` switch → `MainRouter.routeToDetail / routeToCoinDetail`.
- `MainViewModel.navigateSubject.send(.first/.second)` → `MainInteractor.firstTapped/secondTapped`
  → `router.routeTo…`.
- `@Published searchText/marketData/…` → `MainPresenter`'s `StateFlow<MainViewState>`.
- `DIContainer.shared.inject(…)` → `RootComponent` constructor injection (no service locator).
- `Domain/Usecase`, `Data/Repository`, `Data/Remote` → `commonMain` interfaces; Combine → coroutines;
  custom `NetworkClient` → Ktor; CoreData → SQLDelight (per `knowledge/`).

The result is **structurally complete and wired** (verify = YELLOW); the `migrate` stage fills the
`// TODO(ios2ribs):` logic bodies and drives the gate toward GREEN.

## Layout

```
RIBS/
├── harness/                 # the Python package
│   ├── cli.py               # `python -m harness <stage>`
│   ├── analyzer.py          # iOS repo -> Analysis
│   ├── planner.py           # Analysis -> MigrationPlan (RIB tree + artifacts + order)
│   ├── templates.py         # Kotlin/Gradle source templates (RIB nodes, core-ribs, Ktor)
│   ├── scaffolder.py        # MigrationPlan -> project tree on disk
│   ├── agent.py             # per-RIB prompt build + subprocess agent hook (model-agnostic)
│   ├── verifier.py          # the build-check gate (gradle or static)
│   ├── reporter.py          # analysis.md / plan.md / MIGRATION_REPORT.md
│   ├── models.py, config.py # dataclasses + pinned stack & heuristics
│   └── prompts/             # agent prompt template
├── knowledge/               # the quality lever — mapping rules the planner & agent cite
└── output/                  # generated KMP + RIBs project (the deliverable)
```

See [`knowledge/`](knowledge/README.md) for the MVVM+Coordinator→RIBs, Clean→KMP,
Combine→coroutines, and stack-substitution rules that govern the mapping.
