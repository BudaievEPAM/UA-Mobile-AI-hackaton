"""Stage 3 — scaffold.

Materialise the :class:`MigrationPlan` into a real Gradle KMP project: build files, the `core-ribs`
runtime, domain/data artifact stubs, and a complete RIB (Builder/Interactor/Router/Presenter/View/
Listener/Dependency) per feature plus the Root RIB + Component. Every logic body is a traceable
`// TODO(ios2ribs):` for the agent stage to fill.
"""
from __future__ import annotations

import os

from . import templates as T
from .models import MigrationPlan, RibPlan


def _w(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def scaffold(plan: MigrationPlan) -> list[str]:
    out = os.path.abspath(plan.output_dir)
    app = plan.app_name
    pkg = plan.package_root
    pkg_path = pkg.replace(".", "/")
    common = os.path.join(out, "shared", "src", "commonMain", "kotlin", pkg_path)
    android_src = os.path.join(out, "shared", "src", "androidMain", "kotlin", pkg_path)
    ios_src = os.path.join(out, "shared", "src", "iosMain", "kotlin", pkg_path)
    written: list[str] = []

    # --- gradle skeleton ------------------------------------------------------
    written += [
        _w(os.path.join(out, "settings.gradle.kts"), T.settings_gradle(app)),
        _w(os.path.join(out, "build.gradle.kts"), T.root_build_gradle()),
        _w(os.path.join(out, "gradle.properties"), T.gradle_properties()),
        _w(os.path.join(out, "gradle", "libs.versions.toml"), T.libs_versions_toml()),
        _w(os.path.join(out, "shared", "build.gradle.kts"), T.shared_build_gradle(pkg)),
        _w(os.path.join(out, "androidApp", "build.gradle.kts"), T.android_app_build_gradle(pkg)),
    ]

    # --- core runtime ---------------------------------------------------------
    written += [
        _w(os.path.join(common, "core", "ribs", "Ribs.kt"), T.core_ribs(pkg)),
        _w(os.path.join(common, "core", "network", "HttpClient.kt"), T.http_client(pkg)),
        _w(os.path.join(android_src, "core", "network", "HttpClient.android.kt"),
           T.http_engine_actual(pkg, "android")),
        _w(os.path.join(ios_src, "core", "network", "HttpClient.ios.kt"),
           T.http_engine_actual(pkg, "ios")),
    ]

    # --- domain / data artifacts ---------------------------------------------
    for art in plan.artifacts:
        if art.kind in ("network",):
            continue  # already written above
        sym = art.symbols[0] if art.symbols else "Generated"
        src = art.source_files[0] if art.source_files else "—"
        path = os.path.join(common, art.rel_path)
        if art.kind == "entity":
            written.append(_w(path, T.domain_model(pkg, sym, src)))
        elif art.kind == "usecase":
            written.append(_w(path, T.usecase(pkg, sym, src)))
        elif art.kind == "repository":
            written.append(_w(path, T.repository(pkg, sym, src)))
        elif art.kind == "remote":
            written.append(_w(path, T.remote(pkg, sym, src)))

    # --- feature RIBs ---------------------------------------------------------
    feature_ribs = [r for r in plan.ribs if not r.is_root]
    root_rib = next((r for r in plan.ribs if r.is_root), None)

    for rib in feature_ribs:
        rdir = os.path.join(common, *rib.package.split("."))
        written += [
            _w(os.path.join(rdir, f"{rib.name}Dependency.kt"), T.rib_dependency(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}Listener.kt"), T.rib_listener(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}Presenter.kt"), T.rib_presenter(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}Interactor.kt"), T.rib_interactor(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}Router.kt"), T.rib_router(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}Builder.kt"), T.rib_builder(pkg, rib)),
            _w(os.path.join(rdir, f"{rib.name}View.kt"), T.rib_view(pkg, rib)),
        ]

    # --- Root RIB + Component -------------------------------------------------
    if root_rib:
        adir = os.path.join(common, "app")
        written += [
            _w(os.path.join(adir, "RootBuilder.kt"), T.rib_builder(pkg, root_rib)),
            _w(os.path.join(adir, "RootRouter.kt"), T.rib_router(pkg, root_rib)),
            _w(os.path.join(adir, "RootInteractor.kt"),
               T.root_interactor(pkg, root_rib, feature_ribs)),
            _w(os.path.join(adir, "RootComponent.kt"), T.root_component(pkg, plan.ribs)),
        ]

    # --- platform hosts (placeholders) ---------------------------------------
    written += [
        _w(os.path.join(out, "iosApp", "README.md"),
           f"# iOS host\n\nEmbed the `shared` framework and present `RootBuilder(RootComponent()).build()`.\n"
           f"The SwiftUI `@main` App (was `{app}App.swift`) becomes a thin host around the Root RIB.\n"),
        _w(os.path.join(android_src, "App.android.kt"),
           f"package {pkg}.android\n\n"
           f"// Android host: in your Activity, build the root and attach it:\n"
           f"//   val root = {pkg}.app.RootBuilder({pkg}.app.RootComponent()).build()\n"
           f"//   root.load()\n"),
    ]
    return written
