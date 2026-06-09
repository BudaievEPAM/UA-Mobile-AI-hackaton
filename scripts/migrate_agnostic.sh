#!/usr/bin/env bash
# migrate_agnostic.sh — MODEL/PROVIDER-AGNOSTIC iOS → TCA migration runner.
#
# Default target:  workspace/input/EasyCrypto  →  workspace/output/EasyCrypto
# (EasyCrypto is Clean Architecture + MVVM + Coordinator + Combine + SwiftUI + CoreData.)
#
# Unlike the other runners in this repo (claude_migrate.sh / migrate_with_model.sh /
# swarm_migrate.sh) which are locked to Anthropic, this script lets you run the SAME agentic
# migration loop (analyze → scaffold Tuist → migrate features → author Swift Tests → build green)
# on the model/provider of YOUR choice.
#
# How it stays model-agnostic
# ---------------------------
# The agent loop talks the Anthropic Messages API. Non-Anthropic models are reached through an
# Anthropic-COMPATIBLE base URL — either the vendor's own endpoint (DeepSeek / Moonshot / Z.ai all
# publish one), a native cloud switch (Bedrock / Vertex), or a translating proxy such as LiteLLM
# (`litellm`/`custom`) which fronts OpenAI, Google Gemini, Azure, Llama, local Ollama, etc. So the
# orchestration and the "green is done" gate never change; only the model behind them does.
#
# Usage
# -----
#   scripts/migrate_agnostic.sh                                  # EasyCrypto, account-default Anthropic
#   scripts/migrate_agnostic.sh -p anthropic -m opus            # pick a Claude model
#   scripts/migrate_agnostic.sh -p deepseek                     # DeepSeek (needs DEEPSEEK_API_KEY)
#   scripts/migrate_agnostic.sh -p moonshot -m kimi-k2-0905-preview
#   scripts/migrate_agnostic.sh -p zai -m glm-4.6
#   scripts/migrate_agnostic.sh -p bedrock -m us.anthropic.claude-sonnet-4-20250514-v1:0
#   scripts/migrate_agnostic.sh -p litellm -m gpt-4o            # any model via a LiteLLM proxy
#   scripts/migrate_agnostic.sh -p custom --base-url https://host/v1 --auth-env MY_KEY -m my-model
#   scripts/migrate_agnostic.sh --dry-run -p zai -m glm-4.6     # show the resolved env+command only
#   scripts/migrate_agnostic.sh --list-providers
#
# Options
#   -p, --provider <name>   anthropic|bedrock|vertex|deepseek|moonshot|zai|litellm|custom
#                           (default: anthropic)
#   -m, --model <id>        Model id for the chosen provider (default: provider's default; for
#                           anthropic, empty = account default).
#   -f, --fallback-model    Fall back to this model if the primary is overloaded.
#       --base-url <url>    (custom) Anthropic-compatible endpoint, e.g. http://0.0.0.0:4000.
#       --auth-env <NAME>   (custom) Name of the env var holding the bearer token/key.
#   -i, --input <dir>       Source app dir (default: workspace/input/EasyCrypto).
#   -o, --output <dir>      Target dir (default: workspace/output/EasyCrypto).
#       --name <name>       Module/app name for the output (default: basename of --input).
#       --format <fmt>      stream-json (default) | text | json.
#       --dry-run           Print resolved provider/env/objective and the exact command; don't run.
#       --print-objective   Print the migration objective and exit.
#       --list-providers    List provider profiles and exit.
#   -h, --help              Show this help and exit.
#
# Auth (per provider; env first, then a gitignored ./.env):
#   anthropic         ANTHROPIC_API_KEY   (or a logged-in `claude` OAuth session — no key needed)
#   deepseek          DEEPSEEK_API_KEY
#   moonshot          MOONSHOT_API_KEY
#   zai               ZAI_API_KEY
#   litellm           LITELLM_API_KEY     (any value if the proxy is keyless; base url defaults to
#                                          ANTHROPIC_BASE_URL or http://0.0.0.0:4000)
#   custom            whatever --auth-env names
#   bedrock           standard AWS creds (AWS_PROFILE / AWS_* ); AWS_REGION optional
#   vertex            Google ADC; ANTHROPIC_VERTEX_PROJECT_ID + CLOUD_ML_REGION optional
#
# Optional env passed through: MAX_BUDGET_USD=N caps API spend (Anthropic-billed runs).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Provider table: name|base_url|token_env|default_model|extra_env(space-sep KEY=VAL) ──
# base_url empty  → native Anthropic transport (or a cloud switch carried in extra_env).
# token_env empty → provider uses its own cloud credentials (bedrock/vertex).
PROVIDERS=(
  "anthropic||ANTHROPIC_API_KEY||"
  "bedrock|||us.anthropic.claude-sonnet-4-20250514-v1:0|CLAUDE_CODE_USE_BEDROCK=1"
  "vertex|||claude-sonnet-4@20250514|CLAUDE_CODE_USE_VERTEX=1"
  "deepseek|https://api.deepseek.com/anthropic|DEEPSEEK_API_KEY|deepseek-chat|"
  "moonshot|https://api.moonshot.ai/anthropic|MOONSHOT_API_KEY|kimi-k2-0905-preview|"
  "zai|https://api.z.ai/api/anthropic|ZAI_API_KEY|glm-4.6|"
  "litellm|http://0.0.0.0:4000|LITELLM_API_KEY||"
  "custom||||"
)

list_providers() {
  echo "Provider profiles (-p / --provider):"
  printf '  %-10s %-38s %s\n' "NAME" "ANTHROPIC-COMPATIBLE BASE URL" "AUTH ENV / DEFAULT MODEL"
  for row in "${PROVIDERS[@]}"; do
    IFS='|' read -r name url tok model _extra <<<"$row"
    local disp_url="${url:-<native>}" disp_auth="${tok:-<cloud creds>}${model:+  | $model}"
    [ "$name" = custom ] && disp_url="<--base-url>" && disp_auth="<--auth-env>  | -m required"
    printf '  %-10s %-38s %s\n' "$name" "$disp_url" "$disp_auth"
  done
  cat <<'EOF'

  Notes:
   • anthropic / bedrock / vertex use Claude Code's native transports.
   • deepseek / moonshot / zai expose a first-party Anthropic-compatible endpoint.
   • litellm / custom front ANY model (OpenAI, Gemini, Llama, Ollama, Azure…) via a
     translating proxy that speaks the Anthropic Messages API.
EOF
}

# ── Defaults / arg parse ──
PROVIDER="anthropic"; MODEL=""; FALLBACK=""; BASE_URL_OVR=""; AUTH_ENV_OVR=""
INPUT="workspace/input/EasyCrypto"; OUTPUT=""; NAME=""
FORMAT="${OUTPUT_FORMAT:-stream-json}"; DRY_RUN=0; PRINT_OBJ=0
# Print the comment header (lines 2..first non-comment) as help text.
usage() { awk 'NR>=2{ if($0 ~ /^#/){ sub(/^# ?/,""); print } else exit }' "${BASH_SOURCE[0]}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -p|--provider)       PROVIDER="${2:-}"; shift 2 ;;
    -m|--model)          MODEL="${2:-}"; shift 2 ;;
    -f|--fallback-model) FALLBACK="${2:-}"; shift 2 ;;
    --base-url)          BASE_URL_OVR="${2:-}"; shift 2 ;;
    --auth-env)          AUTH_ENV_OVR="${2:-}"; shift 2 ;;
    -i|--input)          INPUT="${2:-}"; shift 2 ;;
    -o|--output)         OUTPUT="${2:-}"; shift 2 ;;
    --name)              NAME="${2:-}"; shift 2 ;;
    --format)            FORMAT="${2:-}"; shift 2 ;;
    --dry-run)           DRY_RUN=1; shift ;;
    --print-objective)   PRINT_OBJ=1; shift ;;
    --list-providers)    list_providers; exit 0 ;;
    -h|--help)           usage; exit 0 ;;
    -*)                  echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
    *)                   echo "Unexpected argument: $1" >&2; usage >&2; exit 64 ;;
  esac
done

# ── Resolve input/output/name ──
[ -d "$INPUT" ] || { echo "ERROR: input dir not found: $INPUT" >&2; exit 66; }
INPUT="$(cd "$INPUT" && pwd)"
NAME="${NAME:-$(basename "$INPUT")}"
OUTPUT="${OUTPUT:-workspace/output/$NAME}"

# ── Resolve provider profile ──
ROW=""; for r in "${PROVIDERS[@]}"; do [ "${r%%|*}" = "$PROVIDER" ] && ROW="$r" && break; done
[ -n "$ROW" ] || { echo "ERROR: unknown provider '$PROVIDER'." >&2; list_providers >&2; exit 64; }
IFS='|' read -r _pname P_URL P_TOKENV P_MODEL P_EXTRA <<<"$ROW"

# Apply overrides (custom or any provider).
[ -n "$BASE_URL_OVR" ] && P_URL="$BASE_URL_OVR"
[ -n "$AUTH_ENV_OVR" ] && P_TOKENV="$AUTH_ENV_OVR"
[ -z "$MODEL" ] && MODEL="$P_MODEL"

# custom must be fully specified.
if [ "$PROVIDER" = "custom" ]; then
  [ -n "$P_URL" ]    || { echo "ERROR: custom provider needs --base-url." >&2; exit 64; }
  [ -n "$P_TOKENV" ] || { echo "ERROR: custom provider needs --auth-env <ENV_NAME>." >&2; exit 64; }
fi
if [ -n "$P_URL" ] && [ -z "$MODEL" ]; then
  echo "ERROR: provider '$PROVIDER' needs a model id (-m/--model)." >&2; exit 64
fi

# ── Resolve the auth token: env first, then ./.env (for the provider's token env var) ──
read_env_file() { [ -f ./.env ] && grep -E "^$1=" ./.env | head -1 | sed "s/^$1=//; s/[\"' ]//g"; }
TOKEN_VALUE=""
if [ -n "$P_TOKENV" ]; then
  TOKEN_VALUE="$(printenv "$P_TOKENV" || true)"
  [ -z "$TOKEN_VALUE" ] && TOKEN_VALUE="$(read_env_file "$P_TOKENV")"
fi

# ── Build the environment the `claude` agent will run under ──
declare -a RUN_ENV=()
AUTH_NOTE=""
case "$PROVIDER" in
  anthropic)
    if [ -n "$TOKEN_VALUE" ]; then
      RUN_ENV+=("ANTHROPIC_API_KEY=$TOKEN_VALUE"); AUTH_NOTE="api key ****${TOKEN_VALUE: -4}"
    else
      AUTH_NOTE="claude logged-in session (no API key) — run 'claude' once to log in if it 401s"
    fi
    ;;
  bedrock|vertex)
    AUTH_NOTE="cloud credentials (${PROVIDER})"
    ;;
  *)  # base-url providers: deepseek/moonshot/zai/litellm/custom
    if [ -z "$TOKEN_VALUE" ]; then
      echo "ERROR: \$$P_TOKENV not set (env or ./.env) — required for provider '$PROVIDER'." >&2
      exit 1
    fi
    # Route Claude Code at the Anthropic-compatible endpoint via bearer token; clear the native
    # x-api-key so we never leak an Anthropic key to a third-party host.
    RUN_ENV+=("ANTHROPIC_BASE_URL=$P_URL" "ANTHROPIC_AUTH_TOKEN=$TOKEN_VALUE" "ANTHROPIC_API_KEY=")
    [ -n "$MODEL" ] && RUN_ENV+=("ANTHROPIC_MODEL=$MODEL")
    AUTH_NOTE="$P_TOKENV ****${TOKEN_VALUE: -4} @ $P_URL"
    ;;
esac
# Provider extra env (e.g. CLAUDE_CODE_USE_BEDROCK=1).
if [ -n "$P_EXTRA" ]; then for kv in $P_EXTRA; do RUN_ENV+=("$kv"); done; fi

# ── Migration guardrails (constitution + knowledge) — provider-independent ──
SYSTEM="You are migrating an iOS app to modular TCA + Tuist + Swift Testing.
Follow .specify/memory/constitution.md and the references in knowledge/ (tca-patterns.md, clean-to-tca.md, mvvm-to-tca.md, mvvm-coordinator-to-tca.md, swift-testing-tca.md; viper-to-tca.md if relevant) and knowledge/tuist-templates/. Use idiomatic modern TCA only: @Reducer / @ObservableState / @Dependency; NO ViewStore/WithViewStore; state-driven navigation (StackState/@Presents); Swift Testing + TestStore only (never import XCTest). 'Green is done': verify with 'bash scripts/build_check.sh $OUTPUT' and keep fixing until it prints 'BUILD_CHECK: GREEN'. Do NOT modify $INPUT (read-only source). Write only inside $OUTPUT."

# ── Migration objective (self-contained; EasyCrypto-aware, generic for any --input) ──
OBJECTIVE="Migrate the iOS app at '$INPUT' (module/app name: $NAME) into an idiomatic, modular TCA project at '$OUTPUT'.

Source architecture: Clean Architecture + MVVM + Coordinator, SwiftUI + Combine, CoreData cache (Domain/{Entity,Usecase}, Data/{Remote,Repository}, Presentation/<Feature>/{View,ViewModel,Coordinator}, Core/Networking, DIManager, Persistance). Map it to TCA like this:
 - Each Usecase / Repository / Remote (network) and the CoreData cache become @DependencyClient dependencies (LiveValue + testValue/previewValue); no singletons, no DIManager.
 - Each ViewModel (ObservableObject/@Published, Combine pipelines) becomes a @Reducer with @ObservableState + an Action enum; async work via .run effects and @Dependency.
 - Coordinators (MainCoordinator/CoinDetailCoordinator) become state-driven navigation: StackState<Path>/@Presents in the App/root feature — no UIKit navigation.
 - Domain Entities → plain Sendable models in a Core/SharedModels module.
 - Feature areas to cover: Main (crypto list with search + sort), CoinDetail, Detail (price). Preserve behavior parity (fetch, cache-then-network, search/sort, navigation).

Pipeline (you may also use the repo's skills \$agent-ios-arch-analyzer, \$agent-tuist-scaffolder, \$agent-tca-feature-migrator, \$agent-swift-test-author, \$agent-ios-build-doctor if available, but do not depend on them):
 1. Analyze: 'bash scripts/code_map.sh $INPUT workspace/analysis.json' then read the key source files.
 2. Scaffold a modular Tuist + TCA workspace in '$OUTPUT' (Core/SharedModels → Core/Networking → Features/* → App), TCA 1.25.2 pinned, Swift 6, iOS 17. Use knowledge/tuist-templates/.
 3. Migrate the features in dependency order per the knowledge mapping files.
 4. Author Swift Testing suites (@Suite/@Test/#expect + TCA TestStore) — happy + failure paths. Never import XCTest.
 5. Verify: run 'bash scripts/build_check.sh $OUTPUT' and fix until it prints 'BUILD_CHECK: GREEN'.
 6. Write '$OUTPUT/MIGRATION_REPORT.md' summarizing the before/after structure and task-by-task results.

Scope discipline (Constitution VII): take the foundation + a representative set of features to GREEN; scaffold the rest as compiling '// TODO(migration):' stubs with tracked tasks. A green subset beats a broad broken migration. Do NOT modify '$INPUT'."

if [ "$PRINT_OBJ" -eq 1 ]; then printf '%s\n' "$OBJECTIVE"; exit 0; fi

# ── Preflight (warn-only; the green gate needs these, the agent run does not) ──
command -v claude >/dev/null 2>&1 || { echo "ERROR: 'claude' CLI not found on PATH." >&2; exit 127; }
MISSING=""
for t in tuist xcsift swift git python3; do command -v "$t" >/dev/null 2>&1 || MISSING="$MISSING $t"; done
[ -n "$MISSING" ] && echo "⚠ preflight: missing for the build gate →$MISSING (the agent can still run; build_check will be RED until installed)" >&2

# ── Assemble the claude invocation ──
ARGS=(-p "$OBJECTIVE"
      --append-system-prompt "$SYSTEM"
      --dangerously-skip-permissions
      --output-format "$FORMAT")
[ "$FORMAT" = "stream-json" ] && ARGS+=(--verbose)
[ -n "$MODEL" ]              && ARGS+=(--model "$MODEL")
[ -n "$FALLBACK" ]          && ARGS+=(--fallback-model "$FALLBACK")
[ -n "${MAX_BUDGET_USD:-}" ] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

echo "▶ migrate (model-agnostic)"
echo "   provider : $PROVIDER"
echo "   model    : ${MODEL:-account-default}${FALLBACK:+  (fallback=$FALLBACK)}"
echo "   auth     : $AUTH_NOTE"
echo "   input    : $INPUT  (read-only)"
echo "   output   : $OUTPUT"
echo "   format   : $FORMAT${MAX_BUDGET_USD:+   budget=\$$MAX_BUDGET_USD}"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "   --- DRY RUN (no model called) ---"
  echo "   env overrides:"
  if [ "${#RUN_ENV[@]}" -gt 0 ]; then
    for kv in "${RUN_ENV[@]}"; do
      case "$kv" in
        *TOKEN=|*API_KEY=)   printf '     %s  (cleared)\n' "${kv%%=*}";;            # emptied on purpose
        *TOKEN=*|*API_KEY=*) printf '     %s=****%s\n' "${kv%%=*}" "${kv: -4}";;     # redact secrets
        *) printf '     %s\n' "$kv";;
      esac
    done
  else
    echo "     (none — native Anthropic / cloud creds)"
  fi
  echo "   command:"
  echo "     claude -p '<objective>' --append-system-prompt '<guardrails>' --dangerously-skip-permissions --output-format $FORMAT$([ "$FORMAT" = stream-json ] && echo ' --verbose')${MODEL:+ --model $MODEL}${FALLBACK:+ --fallback-model $FALLBACK}${MAX_BUDGET_USD:+ --max-budget-usd $MAX_BUDGET_USD}"
  exit 0
fi

# ── Run the agent under the resolved provider environment ──
mkdir -p "$OUTPUT"
if [ "${#RUN_ENV[@]}" -gt 0 ]; then
  exec env "${RUN_ENV[@]}" claude "${ARGS[@]}"
else
  exec claude "${ARGS[@]}"
fi
