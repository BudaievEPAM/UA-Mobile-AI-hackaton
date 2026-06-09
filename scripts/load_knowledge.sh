#!/usr/bin/env bash
# Load the iOS→TCA knowledge base into RUFLO AgentDB (collective memory / RAG) so every swarm
# worker can retrieve it. Best-effort: worker skills also read knowledge/*.md directly, so a
# failure here is non-fatal. Run after `ruflo init` and `claude mcp add ruflo`.
#
# Usage: scripts/load_knowledge.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KNOWLEDGE_DIR="$ROOT/knowledge"
NAMESPACE="tca-migration"

# Files to index (markdown only; tuist-templates loaded as one bundle).
FILES=(
  "tca-patterns.md"
  "viper-to-tca.md"
  "clean-to-tca.md"
  "mvvm-to-tca.md"
  "mvvm-coordinator-to-tca.md"
  "swift-testing-tca.md"
  "tuist-templates/README.md"
)

store() {
  # $1 = key, $2 = file path  —  CLI: `ruflo memory store -k <key> -v <value>`
  local key="$1" file="$2"
  [ -f "$file" ] || { echo "  skip (missing): $file"; return 0; }
  if npx ruflo memory store -k "$NAMESPACE/$key" "$(cat "$file")" >/dev/null 2>&1; then  # value is positional (-v = verbose)
    echo "  stored: $NAMESPACE/$key"
  else
    echo "  WARN: could not store '$key' — skills read knowledge/*.md directly."
    return 1
  fi
}

echo "Loading knowledge base into RUFLO AgentDB (namespace: $NAMESPACE)…"
rc=0
for f in "${FILES[@]}"; do
  key="${f%.md}"; key="${key//\//-}"
  store "$key" "$KNOWLEDGE_DIR/$f" || rc=1
done

if [ "$rc" -ne 0 ]; then
  echo "Note: some entries were not stored. This is non-fatal — the agent-skills reference"
  echo "      knowledge/*.md by path. Re-run after confirming the memory CLI: npx ruflo memory --help"
fi
echo "Done."
