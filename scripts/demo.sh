#!/usr/bin/env bash
# End-to-end demo: analyze the VIPER sample, show the migration inventory, then build+test the
# generated TCA project. Assumes the migrated output already exists in workspace/output/.
#
# Usage: scripts/demo.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEMO_URL="https://github.com/amitshekhariitbhu/iOS-Viper-Architecture"

echo "════════════════════════════════════════════════════════════════"
echo " iOS → TCA Migration Agent — demo"
echo "════════════════════════════════════════════════════════════════"

echo; echo "▶ 1. Ingest source (VIPER sample)"
if [ ! -d workspace/input/iOS-Viper-Architecture ]; then
  git clone --depth 1 "$DEMO_URL" workspace/input/iOS-Viper-Architecture
else
  echo "  (already cloned)"
fi

echo; echo "▶ 2. Analyze (scripts/code_map.sh)"
bash scripts/code_map.sh workspace/input workspace/analysis.json
python3 -c "import json;d=json.load(open('workspace/analysis.json'));print('  detected:',d['architecture']['detected'],'| features:',[m['name'] for m in d['modules'] if m['archGuess']=='viper'])"

echo; echo "▶ 3. Migration inventory"
sed -n '1,12p' workspace/analysis.md

echo; echo "▶ 4. Generated TCA project structure"
find workspace/output -name '*.swift' -not -path '*/.build/*' -not -path '*/Tuist/*' | sed "s|workspace/output/||" | sort

echo; echo "▶ 5. Build + test gate (tuist generate + build + test | xcsift)"
bash scripts/build_check.sh workspace/output

echo; echo "▶ 6. Migration report"
[ -f workspace/output/MIGRATION_REPORT.md ] && sed -n '1,30p' workspace/output/MIGRATION_REPORT.md || echo "  (run \$agent-migration-reporter to generate)"

echo; echo "Done."
