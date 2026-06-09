"""Stage 1 — analyze.

Walk an iOS source repo, classify Swift files, detect architecture + tech stack, and group
files into candidate feature modules. Pure stdlib; no parsing of Xcode project files required.
"""
from __future__ import annotations

import collections
import os
import re

from . import config
from .models import Analysis, FeatureModule, Kind, SwiftFile

_TYPE_RE = re.compile(r"^\s*(?:public\s+|final\s+|open\s+|internal\s+)*"
                      r"(?:struct|class|enum|protocol|actor)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
_PUBLISHED_RE = re.compile(r"@Published[^\n]*?\bvar\s+([A-Za-z_][A-Za-z0-9_]*)")
_SUBJECT_RE = re.compile(r"\bvar\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
                         r"(?:PassthroughSubject|CurrentValueSubject)")
# navigateSubject.send(.first(item:)) / .send(.second(id:))  and  enum Routes { case first... }
_ROUTE_SEND_RE = re.compile(r"navigateSubject\.send\(\.([A-Za-z_][A-Za-z0-9_]*)")
_ROUTE_CASE_RE = re.compile(r"\bcase\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?")


def _classify(filename: str, content: str) -> str:
    stem = filename[:-6] if filename.endswith(".swift") else filename
    # longest matching suffix wins (e.g. "RepositoryImpl" before "Repository")
    best = None
    for suffix, kind in config.SUFFIX_KIND.items():
        if stem.endswith(suffix) and (best is None or len(suffix) > len(best[0])):
            best = (suffix, kind)
    if best:
        return best[1]
    # content fallbacks
    if "navigateSubject" in content or re.search(r":\s*CoordinatorProtocol|: Coordinatable", content):
        return Kind.COORDINATOR.value
    if "@Published" in content and ("ObservableObject" in content or "ViewModel" in content):
        return Kind.VIEWMODEL.value
    if "some View" in content or ": View" in content:
        return Kind.VIEW.value
    low_dir = filename.lower()
    if "extension" in low_dir:
        return Kind.EXTENSION.value
    return Kind.OTHER.value


def _route_cases_for_feature(files_content: dict[str, str]) -> list[tuple[str, str]]:
    """Return [(case_name, payload_signature)] for a feature, from its Routes enum + sends."""
    sent: set[str] = set()
    cases: dict[str, str] = {}
    for content in files_content.values():
        for m in _ROUTE_SEND_RE.finditer(content):
            sent.add(m.group(1))
        # only look at enums that look like route enums
        for em in re.finditer(r"enum\s+\w*Route\w*\s*[:{][^}]*\}", content, re.S):
            block = em.group(0)
            for cm in _ROUTE_CASE_RE.finditer(block):
                cases.setdefault(cm.group(1), (cm.group(2) or "").strip())
    # union: prefer cases that are actually sent; include declared ones too
    out: list[tuple[str, str]] = []
    for name in sorted(set(cases) | sent):
        out.append((name, cases.get(name, "")))
    return out


def analyze(repo: str, include_tests: bool = False) -> Analysis:
    repo = os.path.abspath(repo)
    app_name = _guess_app_name(repo)

    files: list[SwiftFile] = []
    contents: dict[str, str] = {}          # rel_path -> content
    kinds = collections.Counter()
    stack: dict[str, set[str]] = collections.defaultdict(set)
    arch_scores = collections.Counter()
    dir_clean_hits = collections.Counter()
    total_lines = 0

    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in config.SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            if not fn.endswith(".swift"):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), repo)
            low = rel.lower()
            if not include_tests and ("test" in low or "mock" in low or "stub" in low or "dummy" in low):
                continue
            try:
                with open(os.path.join(dp, fn), encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue
            contents[rel] = content
            nlines = content.count("\n") + 1
            total_lines += nlines
            kind = _classify(fn, content)
            kinds[kind] += 1

            sf = SwiftFile(
                rel_path=rel,
                kind=kind,
                lines=nlines,
                types=_TYPE_RE.findall(content),
                imports=sorted(set(_IMPORT_RE.findall(content))),
                publishes=_PUBLISHED_RE.findall(content) + _SUBJECT_RE.findall(content),
                routes=[m.group(1) for m in _ROUTE_SEND_RE.finditer(content)],
            )
            files.append(sf)

            # stack detection
            for pattern, (cat, tag) in config.STACK_SIGNALS.items():
                if re.search(pattern, content):
                    stack[cat].add(tag)
            # architecture directory signals
            for part in rel.lower().split(os.sep):
                if part in config.ARCH_DIR_SIGNALS:
                    dir_clean_hits[part] += 1

    # architecture scoring
    arch_scores["viper"] = (kinds["presenter"] * 2 + kinds["interactor"] * 2
                            + kinds["router"] * 2 + kinds["builder"])
    arch_scores["mvvm"] = kinds["viewmodel"] * 3 + kinds["view"]
    arch_scores["clean"] = (kinds["usecase"] * 2 + kinds["repository"] * 2
                            + len(dir_clean_hits) * 2 + kinds["entity"])
    has_coordinator = kinds["coordinator"] > 0
    detected = _detect_arch(arch_scores, has_coordinator)

    features = _group_features(files, contents)

    summary = {
        "swiftFiles": len(files),
        "totalLines": total_lines,
        "uiFeatures": sum(1 for f in features if f.is_ui_feature),
        "candidateModules": len(features),
    }
    architecture = {
        "detected": detected,
        "scores": dict(arch_scores),
        "navigationPattern": "coordinator" if has_coordinator else "uikit/swiftui",
        "componentCounts": {k: v for k, v in kinds.items() if v},
        "cleanDirs": dict(dir_clean_hits),
    }
    return Analysis(
        repo=repo,
        app_name=app_name,
        summary=summary,
        architecture=architecture,
        stack={k: sorted(v) for k, v in stack.items()},
        features=features,
        files=files,
    )


def _detect_arch(scores: collections.Counter, has_coordinator: bool) -> str:
    viper, mvvm, clean = scores["viper"], scores["mvvm"], scores["clean"]
    if viper >= mvvm and viper >= clean and viper > 0:
        base = "viper"
    elif clean > mvvm and clean > 0 and mvvm == 0:
        base = "clean"
    else:
        base = "mvvm"
    if base == "mvvm" and clean > 0:
        base = "mvvm+clean"
    if has_coordinator and "mvvm" in base:
        base += "+coordinator"
    elif has_coordinator and base == "clean":
        base = "mvvm+coordinator"
    return base


_INFRA_NAMES = {"common", "components", "base", "shared", "support", "theme", "core",
                "networking", "di", "dimanager", "resources", "extensions", "utils"}
# anchors that denote an actual UI feature folder (vs. a layer/infra folder)
_FEATURE_ANCHORS = ("presentation", "scenes", "modules", "features")
_LAYER_ANCHORS = ("domain", "data", "persistance", "persistence", "core", "networking")


def _group_features(files: list[SwiftFile], contents: dict[str, str]) -> list[FeatureModule]:
    """Group files under Presentation/<Feature> (UI features) and Domain/Data/Core (support)."""
    groups: dict[str, FeatureModule] = {}
    feature_anchored: set[str] = set()       # names discovered via a real feature anchor

    def feature_key(rel: str):
        parts = rel.split(os.sep)
        low = [p.lower() for p in parts]
        for anchor in _FEATURE_ANCHORS:
            if anchor in low:
                i = low.index(anchor)
                if i + 1 < len(parts) and low[i + 1] not in _INFRA_NAMES:
                    return parts[i + 1], os.sep.join(parts[: i + 2]), True
        # support layers grouped by their top dir
        for layer in _LAYER_ANCHORS:
            if layer in low:
                i = low.index(layer)
                return parts[i].capitalize(), os.sep.join(parts[: i + 1]), False
        return None

    for sf in files:
        key = feature_key(sf.rel_path)
        if key is None:
            continue
        name, path, is_feature = key
        fm = groups.setdefault(name, FeatureModule(name=name, path=path))
        fm.kinds[sf.kind] = fm.kinds.get(sf.kind, 0) + 1
        fm.files.append(sf.rel_path)
        if is_feature:
            feature_anchored.add(name)

    # A group is a UI feature only if it came from a real feature anchor AND has a View +
    # (ViewModel or Coordinator). Infrastructure layers (Core, Common, ...) never qualify.
    for fm in groups.values():
        fm.is_ui_feature = (
            fm.name in feature_anchored
            and fm.name.lower() not in _INFRA_NAMES
            and fm.kinds.get("view", 0) > 0
            and (fm.kinds.get("viewmodel", 0) > 0 or fm.kinds.get("coordinator", 0) > 0)
        )
        if fm.is_ui_feature:
            fc = {p: contents.get(p, "") for p in fm.files}
            fm.routes = [f"{name}({sig})" if sig else name
                         for name, sig in _route_cases_for_feature(fc)]

    # stable ordering: UI features first (by name), then support layers
    ui = sorted((f for f in groups.values() if f.is_ui_feature), key=lambda f: f.name)
    support = sorted((f for f in groups.values() if not f.is_ui_feature), key=lambda f: f.name)
    return ui + support


def _guess_app_name(repo: str) -> str:
    # prefer an .xcodeproj name, else the repo dir name
    for entry in os.listdir(repo) if os.path.isdir(repo) else []:
        if entry.endswith(".xcodeproj") or entry.endswith(".xcworkspace"):
            return entry.rsplit(".", 1)[0]
    return os.path.basename(repo.rstrip(os.sep))
