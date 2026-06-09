# Migrator — native macOS GUI for the iOS → TCA migration pipeline

A single-window SwiftUI app that drives the repo's migration scripts from a chat
interface, so you can run migrations and **sequentially append new functionality**
without memorising shell invocations.

```
┌──────────────────┬────────────────────────────────────────────┐
│ Recent requests  │  Agent: Migrating the List feature…         │
│  • Migrate List   │  🔧 Bash · swift test                       │
│  • Analyze input  │  ↳ Test Suite 'UpcomingTests' passed        │
│  • Build check    │  ✓ done · $0.42 · 95s · 14 turns            │
│                  │ ────────────────────────────────────────── │
│  [ + New Request]│  [Migrate ▾]  type a request…      [ Send ] │
└──────────────────┴────────────────────────────────────────────┘
```

- **Left** — every request you've made, persisted across launches.
- **Right** — a live transcript of what the scripts do (Claude `stream-json` is
  parsed into readable agent / tool / result bubbles; plain scripts stream raw),
  with the command picker + input box at the bottom.

## Run

```bash
cd gui
./run.sh            # build (release) + launch; auto-detects the project root (..)
# or, for a debug build:
swift run
```

The app auto-detects the project root (the folder that contains
`scripts/single_claude_agent_migrate.sh`). Override with `MIGRATOR_PROJECT_ROOT`,
or change it at runtime via the folder button in the toolbar.

## Commands

Pick one in the input bar, or type its `/keyword` as a prefix to switch on the fly:

| Command | `/keyword` | Runs |
|---|---|---|
| **Migrate** | `/migrate` | `scripts/single_claude_agent_migrate.sh "<objective>"` (stream-json) |
| **Swarm** | `/swarm` | `scripts/swarm_migrate.sh "<objective>"` (RUFLO hive-mind) |
| **Analyze** | `/analyze` | `scripts/code_map.sh [repo]` |
| **Build check** | `/build` | `scripts/build_check.sh [output-dir]` |
| **Shell** | `/sh` | `bash -lc "<command>"` (free-form, in the project root) |

Plain text with no `/keyword` is sent to the currently selected command. A blank
objective for **Migrate** uses the script's built-in default demo.

Auth for the agent runs (`ANTHROPIC_API_KEY` in the environment / gitignored
`.env`, or a logged-in `claude` session) is handled by the scripts themselves —
the GUI just inherits your environment.

`⌘↵` send · `⌘.` stop · `⌘N` new request.

## Adding new functionality

The command set is a single registry — `Sources/Migrator/Models/Command.swift`,
`AppCommand.registry`. Append one `AppCommand { … }` entry (title, SF Symbol,
`/keyword`, and a closure that returns the `CommandSpec` to launch) and it shows
up in the picker and the slash-prefix resolver automatically.

## Layout

```
Sources/Migrator/
  MigratorApp.swift          @main App + AppDelegate (regular-app activation)
  Models/
    ChatModels.swift         MessageRole / ChatMessage / ChatSession
    Command.swift            AppCommand registry + slash resolver
    AppModel.swift           @Observable state, run loop, persistence, root resolution
  Services/
    ProcessRunner.swift      Process → AsyncStream<RunEvent> (merged stdout/stderr)
    StreamJSON.swift         Claude stream-json → readable bubbles (tolerant)
    Store.swift              sessions.json in Application Support
  Views/
    RootView.swift           NavigationSplitView + toolbar
    SidebarView.swift        recent requests
    ChatView.swift           transcript + empty state
    MessageRow.swift         role-styled rows
    InputBar.swift           command picker + input + send/stop
```
