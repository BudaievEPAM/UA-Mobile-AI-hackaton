#!/usr/bin/env bash
# Alternative to scripts/swarm_migrate.sh: run the migration with a SINGLE, plain Claude Code agent
# (no RUFLO swarm / hive-mind) — just the `claude` CLI in headless print mode.
#
# Same key resolution as swarm_migrate.sh: ANTHROPIC_API_KEY from the environment or a gitignored
# ./.env. The agent runs from the project root, so it can read knowledge/, .specify/, workspace/input/
# and write workspace/output*.
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... scripts/single_claude_agent_migrate.sh "<objective>"
#   scripts/single_claude_agent_migrate.sh "<objective>"     # key from ./.env
#   scripts/single_claude_agent_migrate.sh                    # uses the default demo objective
#
# Optional env:
#   CLAUDE_MODEL=sonnet|opus|claude-...     model override (default: account default)
#   MAX_BUDGET_USD=3                         cap API spend for this run
#   OUTPUT_FORMAT=stream-json|text|json      default: stream-json (full, monitorable record)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEFAULT_OBJ="Migrate the VIPER \"List\" feature following specs/001-migrate-viper-list/{spec.md,plan.md,tasks.md}. Work ONLY inside ./workspace/output-claude-auto. Create a Swift Package Manager package there (UpcomingKit; swift-tools 6.0; platforms macOS .v13; library product UpcomingKit + a test target). Port the date-grouping logic (TodoItem, NearTermDateRelation, pure nearTermRelation(for:relativeToToday:calendar:) and upcomingSections(from:today:calendar:)) from ./workspace/input/VIPER-SWIFT (Classes/Common/Categories/NSCalendar+CalendarAdditions.swift, Classes/Common/Model/NearTermDateRelation.swift, Classes/Modules/List/.../UpcomingDisplayDataCollection.swift). Add Tests/UpcomingKitTests/UpcomingTests.swift using Swift Testing (import Testing, @Test, #expect) covering today/tomorrow/laterThisWeek/nextWeek/outOfRange with dates anchored to the day after a week start. Then run 'swift test' inside ./workspace/output-claude-auto and fix until it passes; print the swift test summary."
OBJECTIVE="${1:-$DEFAULT_OBJ}"

# Auth: prefer an API key (env, then ./.env); otherwise fall back to `claude`'s logged-in session
# (OAuth) — so on a machine where you've run `claude` and logged in, NO API KEY is required.
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f ./.env ]; then
  ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' ./.env | head -1 | sed 's/^ANTHROPIC_API_KEY=//; s/["'\'' ]//g')"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  export ANTHROPIC_API_KEY
  AUTH_NOTE="api key ****${ANTHROPIC_API_KEY: -4}"
else
  AUTH_NOTE="claude logged-in session (no API key) — if it 401s, run 'claude' once to log in (or 'claude setup-token')"
fi

command -v claude >/dev/null 2>&1 || { echo "ERROR: 'claude' CLI not found on PATH." >&2; exit 127; }

# Inject the same migration guardrails the pipeline/skills use.
SYSTEM="You are migrating an iOS app from VIPER/Clean to modular TCA + Tuist + Swift Testing.
Follow .specify/memory/constitution.md and the references in knowledge/ (tca-patterns.md, viper-to-tca.md, clean-to-tca.md, swift-testing-tca.md). Use idiomatic modern TCA only: @Reducer / @ObservableState / @Dependency; no ViewStore; state-driven navigation; Swift Testing + TestStore (never XCTest). 'Green is done': verify with scripts/build_check.sh (for Tuist projects) or 'swift test' (for SwiftPM packages) and keep fixing until it passes. Do NOT modify workspace/input (read-only source)."

FORMAT="${OUTPUT_FORMAT:-stream-json}"
ARGS=(-p "$OBJECTIVE"
      --append-system-prompt "$SYSTEM"
      --dangerously-skip-permissions
      --output-format "$FORMAT")
[ "$FORMAT" = "stream-json" ] && ARGS+=(--verbose)
[ -n "${CLAUDE_MODEL:-}" ]   && ARGS+=(--model "$CLAUDE_MODEL")
[ -n "${MAX_BUDGET_USD:-}" ] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

echo "▶ single Claude Code agent (no swarm) — model=${CLAUDE_MODEL:-default}, format=$FORMAT, auth: $AUTH_NOTE"
exec claude "${ARGS[@]}"
