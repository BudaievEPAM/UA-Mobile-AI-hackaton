#!/usr/bin/env bash
# Build/test gate for the generated TCA project: tuist generate -> build -> test, every step's
# output parsed by xcsift into token-efficient JSON for the build-doctor skill. Writes per-step
# JSON to workspace/output/.build-logs/ and prints a compact summary. Exit code reflects failure.
#
# Usage: scripts/build_check.sh [OUTPUT_DIR] [SCHEME]
#   OUTPUT_DIR default: workspace/output
#   SCHEME     optional: restrict build/test to one scheme (e.g. a single feature module)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR_IN="${1:-$ROOT/workspace/output}"
OUT_DIR="$(cd "$OUT_DIR_IN" 2>/dev/null && pwd)" || { echo "{\"error\":\"output dir not found: $OUT_DIR_IN\"}"; exit 1; }
SCHEME="${2:-}"
LOG_DIR="$OUT_DIR/.build-logs"   # absolute, survives the cd below

command -v tuist  >/dev/null 2>&1 || { echo '{"error":"tuist not installed"}'; exit 127; }
HAVE_XCSIFT=1; command -v xcsift >/dev/null 2>&1 || HAVE_XCSIFT=0
[ -d "$OUT_DIR" ] || { echo "{\"error\":\"output dir not found: $OUT_DIR\"}"; exit 1; }
mkdir -p "$LOG_DIR"
cd "$OUT_DIR" || exit 1

# Run a command, capture combined output + exit code, post-process through xcsift.
run_step() {
  local name="$1"; shift
  local raw="$LOG_DIR/$name.raw.log" json="$LOG_DIR/$name.json"
  echo "▶ $name: $*"
  "$@" >"$raw" 2>&1; local code=$?
  if [ "$HAVE_XCSIFT" -eq 1 ]; then
    xcsift <"$raw" >"$json" 2>/dev/null || cp "$raw" "$json"
  else
    cp "$raw" "$json"
  fi
  if [ "$code" -ne 0 ]; then
    echo "  ✗ $name failed (exit $code). Diagnostics: $json"
    [ "$HAVE_XCSIFT" -eq 1 ] && tail -c 2000 "$json"
  else
    echo "  ✓ $name ok"
  fi
  return $code
}

overall=0
run_step "install"  tuist install || overall=$?
run_step "generate" tuist generate --no-open || overall=$?

# Drive xcodebuild on the generated workspace directly (tuist build destination inference is
# unreliable). -skipMacroValidation: trust TCA's macros non-interactively.
if [ "$overall" -eq 0 ]; then
  WS="$(ls -d "$OUT_DIR"/*.xcworkspace 2>/dev/null | head -1)"
  [ -z "$WS" ] && { echo "no .xcworkspace generated"; exit 1; }
  SCH="${SCHEME:-$(basename "$WS" .xcworkspace)}"

  # Prefer an eligible iOS Simulator; fall back to native macOS (modules are multiplatform), which
  # needs no simulator runtime. Override with BUILD_DEST=... if desired.
  if [ -n "${BUILD_DEST:-}" ]; then
    DEST="$BUILD_DEST"
  else
    SIM_ID="$(xcodebuild -showdestinations -workspace "$WS" -scheme "$SCH" 2>/dev/null | grep 'platform:iOS Simulator' | grep -v placeholder | grep -oE 'id:[0-9A-Fa-f-]+' | head -1 | cut -d: -f2)"
    if [ -n "$SIM_ID" ]; then DEST="platform=iOS Simulator,id=$SIM_ID"; else DEST="platform=macOS"; fi
  fi
  echo "workspace: $(basename "$WS") | scheme: $SCH | destination: $DEST"

  # SWIFT_ENABLE_EXPLICIT_MODULES=NO: avoid Xcode-26 explicit-module clang scanning failures on
  # TCA's mixed static/dynamic framework deps (Clocks/CombineSchedulers -Swift.h not found).
  XCB=(xcodebuild -workspace "$WS" -scheme "$SCH" -destination "$DEST" -configuration Debug
       -skipMacroValidation CODE_SIGNING_ALLOWED=NO SWIFT_ENABLE_EXPLICIT_MODULES=NO)
  # Retry the build once: a fresh DerivedData can lose a parallel race generating a dependency
  # framework's -Swift.h header (e.g. Clocks). The retry continues from artifacts and wins it.
  run_step "build" "${XCB[@]}" build
  bc=$?
  if [ "$bc" -ne 0 ]; then
    echo "  ↻ build failed (exit $bc) — retrying once (transient module-header race)…"
    run_step "build" "${XCB[@]}" build; bc=$?
  fi
  [ "$bc" -ne 0 ] && overall=$bc
  [ "$overall" -eq 0 ] && { run_step "test" "${XCB[@]}" test || overall=$?; }
fi

echo "---"
if [ "$overall" -eq 0 ]; then echo "BUILD_CHECK: GREEN"; else echo "BUILD_CHECK: RED (exit $overall) — see $LOG_DIR/*.json"; fi
exit "$overall"
