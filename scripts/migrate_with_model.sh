#!/usr/bin/env bash
# Migrate via the Claude Code CLI with YOUR CHOICE OF MODEL.
# Thin model-chooser front-end to scripts/single_claude_agent_migrate.sh (same auth + guardrails),
# so a single plain `claude` agent does the migration on whichever model you pick.
#
# Usage:
#   scripts/migrate_with_model.sh                          # interactive: pick a model, then run
#   scripts/migrate_with_model.sh opus                     # model + default objective
#   scripts/migrate_with_model.sh opus "<objective>"       # model + objective
#   scripts/migrate_with_model.sh -m claude-opus-4-1 "<objective>"
#   scripts/migrate_with_model.sh --list                   # show selectable models and exit
#
# Models: aliases  sonnet | opus | haiku  (latest of each), or a full name
#         (e.g. claude-opus-4-1, claude-sonnet-4-6, claude-haiku-4-5).
# Auth:   ANTHROPIC_API_KEY (env or ./.env)  OR a logged-in `claude` session (no key).
# Extra:  OUTPUT_FORMAT=text|json|stream-json, MAX_BUDGET_USD=N  pass straight through.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"

show_models() {
  cat <<'EOF'
Selectable models (passed to `claude --model`):
  sonnet            balanced (Claude Code default)
  opus              most capable
  haiku             fastest / cheapest
  <full-name>       any exact id, e.g. claude-opus-4-1 / claude-sonnet-4-6 / claude-haiku-4-5
EOF
}

MODEL=""; OBJECTIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--model) MODEL="${2:-}"; shift 2 || { echo "missing model after $1" >&2; exit 64; } ;;
    --list)     show_models; exit 0 ;;
    -h|--help)  sed -n '2,16p' "$0"; exit 0 ;;
    *)          if [ -z "$MODEL" ]; then MODEL="$1"; else OBJECTIVE="${OBJECTIVE:+$OBJECTIVE }$1"; fi; shift ;;
  esac
done

# Interactive picker when no model was given and we have a terminal.
if [ -z "$MODEL" ]; then
  if [ -t 0 ]; then
    echo "Choose a model:"
    echo "  1) sonnet   (balanced — default)"
    echo "  2) opus     (most capable)"
    echo "  3) haiku    (fastest / cheapest)"
    echo "  4) custom   (type a full model name)"
    printf "Selection [1-4]: "; read -r sel
    case "$sel" in
      1|"")  MODEL="sonnet" ;;
      2)     MODEL="opus" ;;
      3)     MODEL="haiku" ;;
      4)     printf "Full model name: "; read -r MODEL ;;
      *)     MODEL="$sel" ;;   # allow typing an alias/name directly
    esac
  else
    MODEL="sonnet"             # non-interactive default
  fi
fi
[ -n "$MODEL" ] || { echo "no model selected" >&2; exit 64; }

echo "▶ migrate via Claude Code CLI · model: $MODEL"
if [ -n "$OBJECTIVE" ]; then
  exec env CLAUDE_MODEL="$MODEL" "$ROOT/scripts/single_claude_agent_migrate.sh" "$OBJECTIVE"
else
  exec env CLAUDE_MODEL="$MODEL" "$ROOT/scripts/single_claude_agent_migrate.sh"
fi
