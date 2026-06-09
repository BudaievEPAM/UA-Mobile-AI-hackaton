#!/usr/bin/env bash
# Run a RUFLO hive-mind swarm with an Anthropic API key passed through to the spawned Claude Code
# worker, so it can authenticate and run autonomously (the worker is a child `claude` process; the
# harness/OAuth session is NOT inherited, so it needs ANTHROPIC_API_KEY in its environment).
#
# Key resolution (first found wins):
#   1. ANTHROPIC_API_KEY already in the environment
#   2. ANTHROPIC_API_KEY in a gitignored ./.env  (KEY=VALUE)
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... scripts/swarm_migrate.sh "<objective>" [worker_count]
#   # or put ANTHROPIC_API_KEY=sk-ant-... in ./.env, then:
#   scripts/swarm_migrate.sh "<objective>"
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OBJECTIVE="${1:-}"
COUNT="${2:-1}"
RUFLO_VERSION="3.7.0-alpha.8"

if [ -z "$OBJECTIVE" ]; then
  echo "Usage: ANTHROPIC_API_KEY=sk-ant-... $0 \"<objective>\" [worker_count]" >&2
  exit 64
fi

# Resolve the key: env first, then ./.env
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f ./.env ]; then
  # shellcheck disable=SC1091
  ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' ./.env | head -1 | cut -d= -f2- | tr -d '"'"'"'[:space:]')"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  cat >&2 <<'EOF'
ERROR: ANTHROPIC_API_KEY is not set.
The hive-mind worker is a spawned `claude` process that cannot use the harness/OAuth session,
so it must authenticate with an API key. Provide one of:
  export ANTHROPIC_API_KEY=sk-ant-...     # then re-run
  echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env   # gitignored; then re-run
EOF
  exit 1
fi

export ANTHROPIC_API_KEY   # inherited by npx -> ruflo -> spawned claude (apiKeySource: ANTHROPIC_API_KEY)
echo "▶ hive-mind spawn: $COUNT worker(s), API key passed through (****${ANTHROPIC_API_KEY: -4})"
exec npx -y "ruflo@${RUFLO_VERSION}" hive-mind spawn --claude --non-interactive -n "$COUNT" -o "$OBJECTIVE"
