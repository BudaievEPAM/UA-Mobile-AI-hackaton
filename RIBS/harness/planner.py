"""Stage 2 — plan.

Turn an :class:`Analysis` into a :class:`MigrationPlan`: one RIB per UI feature plus a Root RIB,
the RIB attach/detach tree (derived from each Coordinator's route enum), the supporting Kotlin
artifacts (domain models, use cases, repositories, remotes, networking), and a build order that
respects the dependency layers documented in knowledge/clean-to-kmp.md.
"""
from __future__ import annotations

import os
import re

from . import config
from .models import (Analysis, KotlinArtifact, MigrationPlan, RibPlan, RibRoute,
                     Transition)

_SWIFT_TO_KOTLIN_TYPE = {
    "String": "String", "Int": "Int", "Double": "Double", "Bool": "Boolean",
    "Float": "Float", "Date": "kotlinx.datetime.Instant", "URL": "String", "Data": "ByteArray",
}

_ROUTE_CASE_RE = re.compile(r"\bcase\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?")
# A dependency is a *type* (uppercase-initial) ending in a known role suffix; this avoids matching
# lowercase argument values like `coinDetailUsecase: coinDetailUsecase`.
_DEP_RE = re.compile(r":\s*([A-Z][A-Za-z0-9_]*(?:Usecase|UseCase|Repository)(?:Protocol|Prorocol)?)\b")


def _camel(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _read(repo: str, rel: str) -> str:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _kotlin_type(swift: str) -> str:
    swift = swift.strip().rstrip("?").replace("[", "List<").replace("]", ">")
    return _SWIFT_TO_KOTLIN_TYPE.get(swift, swift or "Unit")


def _interface_name(swift_protocol: str) -> str:
    """`MarketPriceUsecaseProtocol` -> `MarketPriceUseCase` (drop Protocol, normalise Usecase)."""
    n = swift_protocol
    n = re.sub(r"Proro?col$|Protocol$", "", n)        # tolerate the repo's "Prorocol" typo
    n = n.replace("Usecase", "UseCase")
    return n


def plan(analysis: Analysis, output_dir: str) -> MigrationPlan:
    app = analysis.app_name
    pkg_root = "com." + re.sub(r"[^a-z0-9]", "", app.lower())

    ui_features = [f for f in analysis.features if f.is_ui_feature]

    # --- per-feature parse: routes, deps, state, build args -------------------
    feature_info: dict[str, dict] = {}
    for f in ui_features:
        coord_text, vm_text, feat_text = "", "", ""
        deps: set[str] = set()
        for rel in f.files:
            txt = _read(analysis.repo, rel)
            feat_text += "\n" + txt
            low = rel.lower()
            if "coordinator" in low:
                coord_text += "\n" + txt
            if "viewmodel" in low:
                vm_text += "\n" + txt
                for m in _DEP_RE.finditer(txt):
                    deps.add(_interface_name(m.group(1)))
        # the route enum may live in the View while the content/transition switch is in the
        # Coordinator — fall back to the whole feature when there is no coordinator file.
        switch_src = coord_text if coord_text.strip() else feat_text
        state = _state_fields(analysis, f.files)
        feature_info[f.name] = {
            "coord": switch_src, "feat": feat_text, "vm": vm_text,
            "deps": sorted(deps), "state": state,
        }

    feature_names = {f.name for f in ui_features}

    # --- build RIBs -----------------------------------------------------------
    ribs: list[RibPlan] = []
    child_of: dict[str, str] = {}            # child feature -> parent feature
    build_args_for: dict[str, list[str]] = {}

    for f in ui_features:
        info = feature_info[f.name]
        routes = _routes_from_coordinator(info["coord"], info["feat"], f.name, feature_names)
        child_routes = [r for r in routes if not r.external and r.child_rib]
        rib = RibPlan(
            name=f.name,
            package=f"features.{f.name.lower()}",
            source_feature=f.name,
            dependencies=info["deps"],
            state_fields=info["state"],
            routes=routes,
            children=[r.child_rib for r in child_routes],
            source_files=f.files,
        )
        ribs.append(rib)
        for r in child_routes:
            child_of[r.child_rib] = f.name
            if r.arg_type:
                build_args_for.setdefault(r.child_rib, [])
                arg_name = _arg_name_for(r)
                if arg_name not in [a.split(":")[0] for a in build_args_for[r.child_rib]]:
                    build_args_for[r.child_rib].append(f"{arg_name}: {r.arg_type}")

    rib_by_name = {r.name: r for r in ribs}
    for child, args in build_args_for.items():
        if child in rib_by_name:
            rib_by_name[child].build_args = args

    # --- Root RIB: parent of every feature that is nobody's child -------------
    roots = [f.name for f in ui_features if f.name not in child_of]
    root = RibPlan(
        name="Root",
        package="app",
        is_root=True,
        children=roots,
        routes=[RibRoute(listener_method=f"{r[0].lower()}{r[1:]}Requested",
                         child_rib=r, transition=Transition.ROOT.value)
                for r in (rn for rn in roots)],
    )
    # the Root simply attaches the entry feature(s); typically the first UI feature
    ribs.insert(0, root)

    # --- supporting Kotlin artifacts (domain/data/network) --------------------
    all_deps: list[str] = []
    for r in ribs:
        for d in r.dependencies:
            if d not in all_deps:
                all_deps.append(d)
    artifacts = _artifacts(analysis, pkg_root, all_deps)

    # --- build order ----------------------------------------------------------
    order = ["core-ribs", "core-network", "domain-model"]
    order += [f"data:{a.symbols[0]}" for a in artifacts if a.kind in ("remote", "repository") and a.symbols]
    order += [f"usecase:{a.symbols[0]}" for a in artifacts if a.kind == "usecase" and a.symbols]
    # leaf RIBs before parents before root
    leaves = [r.name for r in ribs if not r.children and not r.is_root]
    parents = [r.name for r in ribs if r.children and not r.is_root]
    order += [f"rib:{n}" for n in leaves]
    order += [f"rib:{n}" for n in parents]
    order += ["rib:Root", "app", "verify"]

    return MigrationPlan(
        app_name=app,
        package_root=pkg_root,
        output_dir=output_dir,
        ribs=ribs,
        artifacts=artifacts,
        build_order=order,
        stack_substitutions=dict(config.STACK.substitutions),
    )


def _state_fields(analysis: Analysis, files: list[str]) -> list[str]:
    out: list[str] = []
    for sf in analysis.files:
        if sf.rel_path in files:
            for p in sf.publishes:
                if p not in out and not p.lower().endswith("subject"):
                    out.append(p)
    return out


def _routes_from_coordinator(coord_text: str, feat_text: str, feature: str,
                             feature_names: set[str]) -> list[RibRoute]:
    """Map a feature's route enum cases -> RibRoutes (child RIB + transition + payload).

    The route enum (`enum Routes { case first(...) }`) may be declared in the View, while the
    `content`/`transition` switch that says *what* each case shows lives in the Coordinator —
    so cases are read from the whole feature, switches from the coordinator text.
    """
    routes: list[RibRoute] = []
    # case payloads from any Route(s) enum anywhere in the feature
    case_payloads: dict[str, str] = {}
    for em in re.finditer(r"enum\s+\w*Route\w*\s*[:{](.*?)\n\s*\}", feat_text, re.S):
        for cm in _ROUTE_CASE_RE.finditer(em.group(1)):
            case_payloads[cm.group(1)] = (cm.group(2) or "").strip()
    for m in re.finditer(r"navigateSubject\.send\(\.([A-Za-z_][A-Za-z0-9_]*)", feat_text):
        case_payloads.setdefault(m.group(1), "")

    # which child each case targets: look at the Destination `content` switch
    content_switch = ""
    cm = re.search(r"var\s+content\s*:\s*some View\s*\{(.*?)\n\s*\}", coord_text, re.S)
    if cm:
        content_switch = cm.group(1)
    # transition switch
    trans_switch = ""
    tm = re.search(r"var\s+transition\s*:\s*Transition\s*\{(.*?)\n\s*\}", coord_text, re.S)
    if tm:
        trans_switch = tm.group(1)

    for case, payload in case_payloads.items():
        # find target view/coordinator referenced for this case
        child = _child_for_case(case, content_switch, feature_names)
        transition = _transition_for_case(case, trans_switch)
        arg_type = _payload_type(payload)
        src = f"{case}({payload})" if payload else case
        # .url / system presentations, or a target that is not a known UI feature, become an
        # external (Listener-only) intent — no child RIB is attached to the tree.
        is_known_feature = child in feature_names
        if transition == Transition.URL.value or not is_known_feature:
            routes.append(RibRoute(
                listener_method=f"{_camel(case)}Requested",
                child_rib="", transition=Transition.URL.value if transition == Transition.URL.value
                else transition, arg_type=arg_type, source_case=src, external=True))
            continue
        routes.append(RibRoute(
            listener_method=f"{_camel(case)}Requested",
            child_rib=child,
            transition=transition,
            arg_type=arg_type,
            source_case=src,
        ))
    return routes


def _child_for_case(case: str, content_switch: str, feature_names: set[str]) -> str | None:
    # locate the `case .<case>` arm and read the type it constructs
    m = re.search(rf"case\s+\.{re.escape(case)}[^\n:]*:(.*?)(?=case\s+\.|\Z)", content_switch, re.S)
    arm = m.group(1) if m else content_switch
    # prefer an explicit feature name appearing as <Feature>View / <Feature>Coordinator
    for fn in sorted(feature_names, key=len, reverse=True):
        if re.search(rf"\b{re.escape(fn)}(View|Coordinator)\b", arm):
            return fn
    # generic: a constructed type ending in View/Coordinator
    g = re.search(r"\b([A-Z][A-Za-z0-9]*?)(?:View|Coordinator)\b", arm)
    if g:
        name = g.group(1)
        return name if name else None
    return None


def _transition_for_case(case: str, trans_switch: str) -> str:
    m = re.search(rf"case\s+\.{re.escape(case)}[^\n:]*:\s*return\s+\.([A-Za-z]+)", trans_switch)
    if m:
        val = m.group(1)
        return {"push": Transition.PUSH.value, "bottomSheet": Transition.SHEET.value,
                "url": Transition.URL.value}.get(val, Transition.PUSH.value)
    return Transition.PUSH.value


def _payload_type(payload: str) -> str | None:
    if not payload:
        return None
    # "item: MarketsPrice" or "id: String" -> kotlin type of the first labelled arg
    first = payload.split(",")[0]
    if ":" in first:
        swift_t = first.split(":", 1)[1].strip()
        return _kotlin_type(swift_t)
    return None


def _arg_name_for(route: RibRoute) -> str:
    if route.source_case and "(" in route.source_case:
        inner = route.source_case[route.source_case.index("(") + 1: -1]
        if ":" in inner:
            return inner.split(":")[0].strip() or "arg"
    return "arg"


def _artifacts(analysis: Analysis, pkg_root: str,
               dep_names: list[str] | None = None) -> list[KotlinArtifact]:
    dep_names = dep_names or []
    base = pkg_root.replace(".", "/")
    arts: list[KotlinArtifact] = []
    # always-present infra
    arts.append(KotlinArtifact(rel_path="core/ribs/Ribs.kt", kind="network",
                               symbols=["Interactor", "Router", "Builder"]))
    arts.append(KotlinArtifact(rel_path="core/network/HttpClient.kt", kind="network",
                               symbols=["createHttpClient", "ApiException"]))

    seen: set[str] = set()

    def add(kind: str, sub: str):
        for sf in analysis.files:
            if sf.kind != kind:
                continue
            sym = sf.types[0] if sf.types else os.path.splitext(os.path.basename(sf.rel_path))[0]
            name = _interface_name(sym) if kind in ("usecase", "repository", "remote") else sym
            if name in seen:
                continue
            seen.add(name)
            arts.append(KotlinArtifact(
                rel_path=f"{sub}/{name}.kt", kind=kind,
                source_files=[sf.rel_path], symbols=[name]))

    add("entity", "domain/model")
    add("usecase", "domain/usecase")
    add("repository", "data/repository")
    add("remote", "data/remote")

    # Ensure every RIB dependency has a generated interface (some are referenced but the impl file
    # carries a different name, e.g. a `CacheRepositoryProtocol` with no `CacheRepository.swift`).
    for dep in dep_names:
        if dep in seen:
            continue
        seen.add(dep)
        if dep.endswith("Repository"):
            arts.append(KotlinArtifact(rel_path=f"data/repository/{dep}.kt", kind="repository",
                                       symbols=[dep]))
        else:
            arts.append(KotlinArtifact(rel_path=f"domain/usecase/{dep}.kt", kind="usecase",
                                       symbols=[dep]))
    return arts
