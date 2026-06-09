#!/usr/bin/env bash
# Migrate with a SINGLE plain Claude Code agent (the `claude` CLI in headless print
# mode) — like scripts/single_claude_agent_migrate.sh, but with MODEL SELECTION as a
# first-class option: pick the model with a flag, an env var, or an interactive menu.
#
# Usage:
#   scripts/claude_migrate.sh [options] ["<objective>"]
#
# Options:
#   -m, --model <model>        Model alias ('sonnet', 'opus', 'haiku') or full name
#                              (e.g. 'claude-opus-4-8'). Default: account default.
#   -f, --fallback-model <m>   Fall back to <m> if the chosen model is overloaded.
#   -l, --list-models          Print the known model aliases and exit.
#       --no-pick              Never show the interactive menu (use the default model).
#       --format <fmt>         Output format: stream-json (default) | text | json.
#   -h, --help                 Show this help and exit.
#
# Model can also come from the environment (flag wins): MODEL / CLAUDE_MODEL.
# When no model is given and the script runs in an interactive terminal, it shows a
# numbered menu. Non-interactively (e.g. launched by the GUI) it uses the default
# unless a model is supplied — so it never blocks waiting for input.
#
# Auth (same as the other runners): ANTHROPIC_API_KEY from the environment or a
# gitignored ./.env; otherwise the logged-in `claude` session (OAuth).
#
# Optional env: MAX_BUDGET_USD=3 caps API spend for the run.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Known models: "alias<TAB>description". `custom` lets you type any full name. ──
MODEL_TABLE=(
  $'default\tYour account default model (no --model passed)'
  $'sonnet\tClaude Sonnet — balanced speed/quality (recommended)'
  $'opus\tClaude Opus — most capable, slower/pricier'
  $'haiku\tClaude Haiku — fastest and cheapest'
)

print_models() {
  echo "Known models (alias → description):"
  for row in "${MODEL_TABLE[@]}"; do
    printf '  %-10s %s\n' "${row%%$'\t'*}" "${row#*$'\t'}"
  done
  echo "  custom     Any full model name, e.g. 'claude-opus-4-8' (pass with -m)"
}

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# ── Parse args ──
MODEL="${MODEL:-${CLAUDE_MODEL:-}}"
FALLBACK=""
FORMAT="${OUTPUT_FORMAT:-stream-json}"
NO_PICK=0
OBJECTIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--model)          MODEL="${2:-}"; shift 2 ;;
    -f|--fallback-model) FALLBACK="${2:-}"; shift 2 ;;
    -l|--list-models)    print_models; exit 0 ;;
    --no-pick)           NO_PICK=1; shift ;;
    --format)            FORMAT="${2:-}"; shift 2 ;;
    -h|--help)           usage; exit 0 ;;
    --)                  shift; OBJECTIVE="$*"; break ;;
    -*)                  echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
    *)                   OBJECTIVE="$1"; shift ;;
  esac
done

# ── Resolve the model: flag/env → interactive menu (TTY only) → default ──
if [ -z "$MODEL" ] && [ "$NO_PICK" -eq 0 ] && [ -t 0 ] && [ -t 1 ]; then
  echo "Choose a model for this migration:"
  i=0; CHOICES=()
  for row in "${MODEL_TABLE[@]}"; do
    i=$((i+1)); alias="${row%%$'\t'*}"; CHOICES+=("$alias")
    printf '  %d) %-10s %s\n' "$i" "$alias" "${row#*$'\t'}"
  done
  printf '  %d) %-10s %s\n' "$((i+1))" "custom" "type a full model name"
  printf 'Selection [1-%d, default 1]: ' "$((i+1))"
  read -r REPLY || REPLY=""
  REPLY="${REPLY:-1}"
  if [ "$REPLY" = "$((i+1))" ]; then
    printf 'Full model name: '; read -r MODEL || MODEL=""
  elif [[ "$REPLY" =~ ^[0-9]+$ ]] && [ "$REPLY" -ge 1 ] && [ "$REPLY" -le "$i" ]; then
    MODEL="${CHOICES[$((REPLY-1))]}"
  else
    MODEL="default"
  fi
fi
# 'default' (or empty) means: don't pass --model at all.
[ "$MODEL" = "default" ] && MODEL=""

# ── Default objective (self-contained; mirrors single_claude_agent_migrate.sh) ──
DEFAULT_OBJ="Migrate the VIPER \"List\" feature following specs/001-migrate-viper-list/{spec.md,plan.md,tasks.md}. Work ONLY inside ./workspace/output-claude-auto. Create a Swift Package Manager package there (UpcomingKit; swift-tools 6.0; platforms macOS .v13; library product UpcomingKit + a test target). Port the date-grouping logic (TodoItem, NearTermDateRelation, pure nearTermRelation(for:relativeToToday:calendar:) and upcomingSections(from:today:calendar:)) from ./workspace/input/VIPER-SWIFT. Add Tests/UpcomingKitTests/UpcomingTests.swift using Swift Testing (import Testing, @Test, #expect) covering today/tomorrow/laterThisWeek/nextWeek/outOfRange. Then run 'swift test' inside ./workspace/output-claude-auto and fix until it passes; print the swift test summary."
OBJECTIVE="${OBJECTIVE:-$DEFAULT_OBJ}"

# ── Auth: API key (env, then ./.env) else fall back to the logged-in claude session ──
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f ./.env ]; then
  ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' ./.env | head -1 | sed 's/^ANTHROPIC_API_KEY=//; s/["'\'' ]//g')"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  export ANTHROPIC_API_KEY
  AUTH_NOTE="api key ****${ANTHROPIC_API_KEY: -4}"
else
  AUTH_NOTE="claude logged-in session (no API key) — if it 401s, run 'claude' once to log in"
fi

command -v claude >/dev/null 2>&1 || { echo "ERROR: 'claude' CLI not found on PATH." >&2; exit 127; }

# ── Migration guardrails (same as the pipeline/skills) ──
SYSTEM="You are migrating an iOS app from VIPER/Clean to modular TCA + Tuist + Swift Testing.
Follow .specify/memory/constitution.md and the references in knowledge/ (tca-patterns.md, viper-to-tca.md, clean-to-tca.md, swift-testing-tca.md). Use idiomatic modern TCA only: @Reducer / @ObservableState / @Dependency; no ViewStore; state-driven navigation; Swift Testing + TestStore (never XCTest). 'Green is done': verify with scripts/build_check.sh (for Tuist projects) or 'swift test' (for SwiftPM packages) and keep fixing until it passes. Do NOT modify workspace/input (read-only source)."

ARGS=(-p "$OBJECTIVE"
      --append-system-prompt "$SYSTEM"
      --dangerously-skip-permissions
      --output-format "$FORMAT")
[ "$FORMAT" = "stream-json" ] && ARGS+=(--verbose)
[ -n "$MODEL" ]              && ARGS+=(--model "$MODEL")
[ -n "$FALLBACK" ]           && ARGS+=(--fallback-model "$FALLBACK")
[ -n "${MAX_BUDGET_USD:-}" ] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

echo "▶ Claude Code migrate — model=${MODEL:-account-default}${FALLBACK:+ (fallback=$FALLBACK)}, format=$FORMAT, auth: $AUTH_NOTE"
exec claude "${ARGS[@]}"
