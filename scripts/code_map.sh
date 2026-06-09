#!/usr/bin/env bash
# Heuristic structural map of an iOS source repo: detects architecture (VIPER / Clean / MVVM),
# the tech stack, and groups files into candidate feature modules. Emits JSON for the analyzer
# skill (which then reads files for semantics). Fast, dependency-light (python3 stdlib only).
#
# Usage: scripts/code_map.sh [REPO_PATH] [OUT_JSON]
#   REPO_PATH default: workspace/input
#   OUT_JSON  default: workspace/analysis.json   ("-" = stdout)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${1:-$ROOT/workspace/input}"
OUT="${2:-$ROOT/workspace/analysis.json}"

command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 1; }
[ -d "$REPO" ] || { echo "repo not found: $REPO" >&2; exit 1; }

python3 - "$REPO" "$OUT" <<'PY'
import os, re, sys, json, collections

repo, out = sys.argv[1], sys.argv[2]
SKIP = {"Pods","Carthage",".build","DerivedData","build",".git","vendor","Vendor","fastlane",".swiftpm"}

SUFFIX = {  # filename-suffix -> component kind
  "Presenter":"presenter","Interactor":"interactor","Router":"router","Wireframe":"router",
  "Builder":"builder","Configurator":"builder","ViewController":"view","View":"view",
  "ViewModel":"viewmodel","UseCase":"usecase","Repository":"repository","RepositoryImpl":"repository",
  "DTO":"dto","Mapper":"mapper","Entity":"entity","Coordinator":"coordinator",
  "FlowCoordinator":"coordinator","DIContainer":"di","Service":"service","Store":"store",
}
CONTENT = {  # regex -> stack tag
  r'\bAlamofire\b':("networking","Alamofire"), r'\bURLSession\b':("networking","URLSession"),
  r'\bMoya\b':("networking","Moya"),
  r'\bCoreData\b|NSManagedObject':("persistence","CoreData"), r'\bRealm\b':("persistence","Realm"),
  r'\bUserDefaults\b':("persistence","UserDefaults"), r'\bGRDB\b':("persistence","GRDB"),
  r'\bSwinject\b':("di","Swinject"), r'\bDIContainer\b':("di","DIContainer"),
  r'\bUINavigationController\b|pushViewController':("navigation","UIKitNav"),
  r'\bCoordinator\b':("navigation","Coordinator"),
  r'import SwiftUI':("ui","SwiftUI"), r'import UIKit':("ui","UIKit"),
  r'\bCombine\b|@Published':("reactive","Combine"), r'\bRxSwift\b':("reactive","RxSwift"),
  r'ObservableObject':("reactive","ObservableObject"),
}
DIR_SIGNALS = {"domain":"clean","data":"clean","presentation":"clean","infrastructure":"clean"}

swift_files, total_lines = [], 0
kinds = collections.Counter()
stack = collections.defaultdict(collections.Counter)
dir_hits = collections.Counter()
module_kinds = collections.defaultdict(collections.Counter)

for dp, dns, fns in os.walk(repo):
    dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
    for fn in fns:
        if not fn.endswith(".swift"): continue
        path = os.path.join(dp, fn)
        rel = os.path.relpath(path, repo)
        swift_files.append(rel)
        # module = first 1-2 path components under repo
        parts = rel.split(os.sep)
        module = os.sep.join(parts[:-1][:3]) or "(root)"
        # filename suffix classification
        base = fn[:-6]
        for suf, kind in SUFFIX.items():
            if base.endswith(suf):
                kinds[kind] += 1; module_kinds[module][kind] += 1; break
        # dir signal
        for comp in parts[:-1]:
            lc = comp.lower()
            if lc in DIR_SIGNALS: dir_hits[lc] += 1
        # content scan
        try:
            with open(path, "r", errors="ignore") as f: txt = f.read()
        except Exception: txt = ""
        total_lines += txt.count("\n")
        for rx,(cat,tag) in CONTENT.items():
            if re.search(rx, txt): stack[cat][tag] += 1

# architecture scoring
viper = kinds["presenter"]*3 + kinds["interactor"]*3 + kinds["router"]*2 + kinds["builder"]
clean = kinds["usecase"]*3 + kinds["repository"]*3 + kinds["dto"] + kinds["mapper"] + sum(dir_hits.values())
mvvm  = kinds["viewmodel"]*3 + stack["reactive"]["ObservableObject"] + stack["reactive"]["Combine"] + stack["reactive"]["RxSwift"]
scores = {"viper":viper, "clean":clean, "mvvm":mvvm}
detected = max(scores, key=scores.get) if max(scores.values()) > 0 else "unknown"
ranked = sorted(scores.values(), reverse=True)
if len(ranked) > 1 and ranked[0] and ranked[1] >= 0.6*ranked[0]:
    detected = "mixed"
# coordinator navigation layer (commonly paired with MVVM) → mvvm+coordinator
coordinators = kinds["coordinator"]
if coordinators >= 2 and detected in ("mvvm", "mixed", "unknown"):
    detected = "mvvm+coordinator"
elif coordinators >= 2 and detected == "viper":
    detected = "viper"  # VIPER routers already cover navigation; keep viper

def top(counter): return [t for t,_ in counter.most_common()]
modules = []
for m, ck in sorted(module_kinds.items(), key=lambda kv: -sum(kv[1].values())):
    if sum(ck.values()) == 0: continue
    mv = ck["presenter"]+ck["interactor"]+ck["router"]
    mc = ck["usecase"]+ck["repository"]
    vm = ck["viewmodel"]; coord = ck["coordinator"]
    if mv > 0 and mv >= mc:   guess = "viper"
    elif vm > 0:              guess = "mvvm+coordinator" if coord > 0 else "mvvm"
    elif mc > 0:              guess = "clean"
    elif coord > 0:           guess = "coordinator"
    else:                     guess = "ui-only"
    modules.append({"name": m.split(os.sep)[-1], "path": m, "fileKinds": dict(ck), "archGuess": guess})

result = {
  "repo": os.path.abspath(repo),
  "summary": {"swiftFiles": len(swift_files), "totalLines": total_lines, "candidateModules": len(modules)},
  "architecture": {"detected": detected, "scores": scores,
                   "navigationPattern": "coordinator" if coordinators > 0 else ("router" if kinds["router"] > 0 else "state/none"),
                   "cleanDirSignals": dict(dir_hits), "componentCounts": dict(kinds)},
  "stack": {cat: top(c) for cat,c in stack.items()},
  "modules": modules[:60],
}
data = json.dumps(result, indent=2)
if out == "-": print(data)
else:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out,"w").write(data)
    print(f"wrote {out}: {len(swift_files)} swift files, arch={detected}, modules={len(modules)}")
PY
