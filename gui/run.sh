#!/usr/bin/env bash
# Build + launch the Migrator macOS app. The project root (the folder containing
# scripts/) is auto-detected as the parent of gui/, or set MIGRATOR_PROJECT_ROOT.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
: "${MIGRATOR_PROJECT_ROOT:=$(cd .. && pwd)}"
export MIGRATOR_PROJECT_ROOT
echo "▶ project root: $MIGRATOR_PROJECT_ROOT"
swift run -c release Migrator
