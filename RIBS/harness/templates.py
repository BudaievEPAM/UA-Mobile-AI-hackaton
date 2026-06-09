"""Kotlin / Gradle source templates for the generated KMP + RIBs project.

Every template returns a string. Business-logic bodies the LLM agent should fill are marked with
`// TODO(ios2ribs):` and carry a reference to the originating Swift file so the agent (and a human
reviewer) can trace the migration.
"""
from __future__ import annotations

from .config import STACK
from .models import MigrationPlan, RibPlan, Transition

TODO = "// TODO(ios2ribs):"


# --------------------------------------------------------------------------- #
# Gradle project skeleton
# --------------------------------------------------------------------------- #
def settings_gradle(app: str) -> str:
    return f'''pluginManagement {{
    repositories {{ google(); mavenCentral(); gradlePluginPortal() }}
}}
dependencyResolutionManagement {{
    repositories {{ google(); mavenCentral() }}
}}

rootProject.name = "{app}"
include(":shared")
include(":androidApp")
'''


def root_build_gradle() -> str:
    return '''plugins {
    alias(libs.plugins.kotlinMultiplatform) apply false
    alias(libs.plugins.androidApplication) apply false
    alias(libs.plugins.androidLibrary) apply false
    alias(libs.plugins.composeMultiplatform) apply false
    alias(libs.plugins.composeCompiler) apply false
    alias(libs.plugins.kotlinSerialization) apply false
}
'''


def gradle_properties() -> str:
    return '''kotlin.code.style=official
android.useAndroidX=true
org.gradle.jvmargs=-Xmx2048M -Dfile.encoding=UTF-8
kotlin.native.ignoreDisabledTargets=true
'''


def libs_versions_toml() -> str:
    s = STACK
    return f'''[versions]
kotlin = "{s.kotlin}"
agp = "{s.agp}"
compose = "{s.compose}"
coroutines = "{s.coroutines}"
ktor = "{s.ktor}"
serialization = "{s.serialization}"
sqldelight = "{s.sqldelight}"
androidCompileSdk = "{s.android_compile_sdk}"
androidMinSdk = "{s.android_min_sdk}"

[libraries]
kotlinx-coroutines-core = {{ module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "coroutines" }}
ktor-client-core = {{ module = "io.ktor:ktor-client-core", version.ref = "ktor" }}
ktor-client-content-negotiation = {{ module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }}
ktor-serialization-json = {{ module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }}
ktor-client-darwin = {{ module = "io.ktor:ktor-client-darwin", version.ref = "ktor" }}
ktor-client-okhttp = {{ module = "io.ktor:ktor-client-okhttp", version.ref = "ktor" }}
kotlinx-serialization-json = {{ module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }}

[plugins]
kotlinMultiplatform = {{ id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }}
kotlinSerialization = {{ id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }}
androidApplication = {{ id = "com.android.application", version.ref = "agp" }}
androidLibrary = {{ id = "com.android.library", version.ref = "agp" }}
composeMultiplatform = {{ id = "org.jetbrains.compose", version.ref = "compose" }}
composeCompiler = {{ id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }}
'''


def shared_build_gradle(pkg_root: str) -> str:
    return f'''import org.jetbrains.kotlin.gradle.ExperimentalKotlinGradlePluginApi
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {{
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidLibrary)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
}}

kotlin {{
    androidTarget {{
        @OptIn(ExperimentalKotlinGradlePluginApi::class)
        compilerOptions {{ jvmTarget.set(JvmTarget.JVM_17) }}
    }}
    listOf(iosX64(), iosArm64(), iosSimulatorArm64()).forEach {{ iosTarget ->
        iosTarget.binaries.framework {{ baseName = "shared"; isStatic = true }}
    }}

    sourceSets {{
        commonMain.dependencies {{
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.json)
            implementation(libs.kotlinx.serialization.json)
            // Compose Multiplatform — the migrate stage fills each RIB's View with @Composable UI.
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.ui)
        }}
        androidMain.dependencies {{ implementation(libs.ktor.client.okhttp) }}
        iosMain.dependencies {{ implementation(libs.ktor.client.darwin) }}
        commonTest.dependencies {{ implementation(kotlin("test")) }}
    }}
}}

android {{
    namespace = "{pkg_root}"
    compileSdk = libs.versions.androidCompileSdk.get().toInt()
    defaultConfig {{ minSdk = libs.versions.androidMinSdk.get().toInt() }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
}}
'''


def android_app_build_gradle(pkg_root: str) -> str:
    return f'''plugins {{
    alias(libs.plugins.androidApplication)
    alias(libs.plugins.kotlinAndroid)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
}}

android {{
    namespace = "{pkg_root}.android"
    compileSdk = libs.versions.androidCompileSdk.get().toInt()
    defaultConfig {{
        applicationId = "{pkg_root}.android"
        minSdk = libs.versions.androidMinSdk.get().toInt()
        targetSdk = libs.versions.androidCompileSdk.get().toInt()
        versionCode = 1
        versionName = "1.0"
    }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
    buildFeatures {{ compose = true }}
}}

dependencies {{
    implementation(project(":shared"))
    implementation(libs.androidx.activity.compose)
    implementation(compose.runtime)
    implementation(compose.material3)
    implementation(compose.ui)
}}
'''


# --------------------------------------------------------------------------- #
# core-ribs runtime (KMP-friendly base classes)
# --------------------------------------------------------------------------- #
def core_ribs(pkg_root: str) -> str:
    return f'''package {pkg_root}.core.ribs

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelChildren

/** Business logic + lifecycle for a RIB. Mirrors Uber RIBs but coroutine-based and multiplatform. */
abstract class Interactor<P : Any>(protected val presenter: P) {{
    protected val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    var isActive: Boolean = false
        private set

    fun activate() {{ if (!isActive) {{ isActive = true; didBecomeActive() }} }}
    fun deactivate() {{
        if (isActive) {{ isActive = false; scope.coroutineContext[kotlinx.coroutines.Job]?.cancelChildren(); willResignActive() }}
    }}

    protected open fun didBecomeActive() {{}}
    protected open fun willResignActive() {{}}
}}

/** Navigation only: owns the child-RIB subtree and attaches/detaches it. */
abstract class Router<I : Interactor<*>>(val interactor: I) {{
    private val children = mutableListOf<Router<*>>()

    fun load() {{ interactor.activate() }}
    fun attachChild(child: Router<*>) {{ if (child !in children) {{ children += child; child.load() }} }}
    fun detachChild(child: Router<*>) {{ if (children.remove(child)) child.detach() }}
    open fun detach() {{ children.toList().forEach {{ detachChild(it) }}; interactor.deactivate() }}
    fun children(): List<Router<*>> = children.toList()
}}

/** Constructs a RIB from its dependency scope. */
abstract class Builder<D>(protected val dependency: D)

/** UI-facing loading state (was BaseViewModel.ViewModelStatus). */
sealed interface LoadState {{
    data object Idle : LoadState
    data object Loading : LoadState
    data class Error(val message: String) : LoadState
}}
'''


def http_client(pkg_root: str) -> str:
    return f'''package {pkg_root}.core.network

import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

/** Replaces the custom Combine NetworkClient / URLSession stack. Engine is supplied per platform. */
expect fun httpClientEngineFactory(): io.ktor.client.engine.HttpClientEngineFactory<*>

fun createHttpClient(): HttpClient = HttpClient(httpClientEngineFactory()) {{
    install(ContentNegotiation) {{
        json(Json {{ ignoreUnknownKeys = true; isLenient = true }})
    }}
}}

/** Was Core/Networking/Utility/APIError.swift */
sealed class ApiException(message: String) : Exception(message) {{
    data class Http(val status: Int) : ApiException("HTTP $status")
    data class Network(val cause: Throwable) : ApiException(cause.message ?: "network error")
    data class Decoding(val cause: Throwable) : ApiException(cause.message ?: "decoding error")
}}
'''


def http_engine_actual(pkg_root: str, platform: str) -> str:
    engine = "OkHttp" if platform == "android" else "Darwin"
    return f'''package {pkg_root}.core.network

import io.ktor.client.engine.HttpClientEngineFactory
import io.ktor.client.engine.{engine.lower()}.{engine}

actual fun httpClientEngineFactory(): HttpClientEngineFactory<*> = {engine}
'''


# --------------------------------------------------------------------------- #
# Domain / data artifact stubs (signatures + TODO bodies for the agent)
# --------------------------------------------------------------------------- #
def domain_model(pkg_root: str, name: str, src: str) -> str:
    return f'''package {pkg_root}.domain.model

import kotlinx.serialization.Serializable

// Ported from {src}  ({TODO} map all Codable properties; Swift optionals -> Kotlin nullables)
@Serializable
data class {name}(
    val id: String = "",
    {TODO} declare the remaining fields from the Swift struct
)
'''


def usecase(pkg_root: str, name: str, src: str) -> str:
    return f'''package {pkg_root}.domain.usecase

// Ported from {src}
// Combine AnyPublisher<T, APIError> -> suspend fun returning T (see combine-to-coroutines.md)
interface {name} {{
    {TODO} declare execute(...) as a suspend fun with the same parameters as the Swift use case
}}

class Default{name}(
    {TODO} inject the repository interface(s) this use case used via DIContainer
) : {name} {{
    {TODO} implement execute(...) by delegating to the repository
}}
'''


def repository(pkg_root: str, name: str, src: str) -> str:
    return f'''package {pkg_root}.data.repository

import {pkg_root}.core.network.ApiException

// Ported from {src}
interface {name} {{
    {TODO} declare the data(...) functions as suspend funs (or Flow for streams/cache)
}}

class Default{name}(
    private val client: io.ktor.client.HttpClient,
) : {name} {{
    {TODO} implement using Ktor requests + kotlinx.serialization; map failures to ApiException
}}
'''


def remote(pkg_root: str, name: str, src: str) -> str:
    return f'''package {pkg_root}.data.remote

// Ported from {src} — endpoint/request definitions (was NetworkTarget). Build Ktor requests here.
object {name} {{
    {TODO} define base path + request builders for each endpoint the Swift remote declared
}}
'''


# --------------------------------------------------------------------------- #
# RIB files
# --------------------------------------------------------------------------- #
def _fq(pkg_root: str, rib: RibPlan) -> str:
    return f"{pkg_root}.{rib.package}"


def rib_dependency(pkg_root: str, rib: RibPlan) -> str:
    deps = "\n".join(f"    val {_lc(d)}: {_dep_type(pkg_root, d)}" for d in rib.dependencies)
    body = deps if deps else f"    {TODO} list the use cases / repositories this RIB needs"
    # A parent RIB's scope must satisfy its children's scopes so it can build them.
    child_deps = [r.child_rib for r in rib.routes if not r.external and r.child_rib]
    supers = ""
    if child_deps:
        supers = " : " + ", ".join(
            f"{pkg_root}.features.{c.lower()}.{c}Dependency" for c in child_deps)
    return f'''package {_fq(pkg_root, rib)}

/** What {rib.name}RIB needs from its parent scope (was constructor injection via DIContainer).
 *  Extends its child RIBs' scopes so {rib.name}Builder can construct them. */
interface {rib.name}Dependency{supers} {{
{body}
}}
'''


def rib_listener(pkg_root: str, rib: RibPlan) -> str:
    """Upward (child -> parent) events. EasyCrypto's Coordinators own their own children, so
    navigation is handled locally by this RIB's Router; the Listener is the seam for reporting
    completion/results to the parent (e.g. a 'finished' delegate). Left minimal by default."""
    return (f"package {_fq(pkg_root, rib)}\n\n"
            f"import {pkg_root}.domain.model.*\n\n"
            f"/** Events {rib.name}RIB reports up to its parent (was a Coordinator/ViewModel\n"
            f" *  delegate). Navigation to owned child screens is handled by {rib.name}Router. */\n"
            f"interface {rib.name}Listener {{\n"
            f"    {TODO} add upward delegate events if the parent must react (none detected)\n"
            f"}}\n")


def rib_presenter(pkg_root: str, rib: RibPlan) -> str:
    fields = "\n".join(f"    val {_lc(s)}: Any? = null,  {TODO} type from @Published {s}"
                       for s in rib.state_fields) or f"    {TODO} fields from the ViewModel's @Published state"
    return f'''package {_fq(pkg_root, rib)}

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import {pkg_root}.core.ribs.LoadState
import {pkg_root}.domain.model.*

/** View-facing state (was {rib.name}ViewModel's @Published properties). */
data class {rib.name}ViewState(
{fields}
)

interface {rib.name}Presentable {{
    val state: StateFlow<{rib.name}ViewState>
    val loadState: StateFlow<LoadState>
    fun render(state: {rib.name}ViewState)
    fun setLoadState(value: LoadState)
}}

class {rib.name}Presenter : {rib.name}Presentable {{
    private val _state = MutableStateFlow({rib.name}ViewState())
    override val state: StateFlow<{rib.name}ViewState> = _state.asStateFlow()
    private val _loadState = MutableStateFlow<LoadState>(LoadState.Idle)
    override val loadState: StateFlow<LoadState> = _loadState.asStateFlow()
    override fun render(state: {rib.name}ViewState) {{ _state.value = state }}
    override fun setLoadState(value: LoadState) {{ _loadState.value = value }}
}}

/** Implemented by the Interactor; the View calls these (was SwiftUI -> ViewModel calls). */
interface {rib.name}PresentableListener {{
    fun onAppear()
{_listener_intents(rib)}
}}
'''


def _listener_intents(rib: RibPlan) -> str:
    out = []
    for r in rib.routes:
        arg = f"arg: {r.arg_type}" if r.arg_type else ""
        out.append(f"    fun {r.listener_method.replace('Requested', 'Tapped')}({arg})")
    return "\n".join(out)


def rib_interactor(pkg_root: str, rib: RibPlan) -> str:
    src = ", ".join(rib.source_files[:3]) or "the feature's ViewModel"
    dep_params = "\n".join(f"    private val {_lc(d)}: {_dep_type(pkg_root, d)},"
                           for d in rib.dependencies)
    child_routes = [r for r in rib.routes if not r.external and r.child_rib]
    router_field = (f"\n    lateinit var router: {rib.name}Router"
                    if child_routes else "")
    intents = []
    for r in rib.routes:
        method = r.listener_method.replace("Requested", "Tapped")
        arg = f"arg: {r.arg_type}" if r.arg_type else ""
        passed = "arg" if r.arg_type else ""
        if r.external:
            body = f"{TODO} open external/url presentation (was {r.source_case})"
        else:
            body = f"router.routeTo{r.child_rib}({passed})  // was {r.source_case} ({r.transition})"
        intents.append(f"    override fun {method}({arg}) {{\n        {body}\n    }}")
    intents_block = "\n".join(intents)
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Interactor
import {pkg_root}.domain.model.*

/** Business logic + lifecycle. Ported from {src}.
 *  Owns navigation to its child screens via {rib.name}Router (the dissolved Coordinator). */
class {rib.name}Interactor(
    presenter: {rib.name}Presentable,
{dep_params}
) : Interactor<{rib.name}Presentable>(presenter), {rib.name}PresentableListener {{

    var listener: {rib.name}Listener? = null{router_field}

    override fun didBecomeActive() {{
        // was {rib.name}ViewModel.apply(.onAppear) — bind state + first load
        {TODO} reproduce the ViewModel's onAppear: collect flows, debounce search, initial fetch
    }}

    override fun onAppear() = activate()

{intents_block}
}}
'''


def rib_router(pkg_root: str, rib: RibPlan) -> str:
    if rib.is_root:
        return _root_router(pkg_root, rib)
    builders = []
    routes = []
    for r in [r for r in rib.routes if not r.external and r.child_rib]:
        child_pkg = f"{pkg_root}.features.{r.child_rib.lower()}"
        builders.append(f"    private val {_lc(r.child_rib)}Builder: {child_pkg}.{r.child_rib}Builder,")
        arg = f"arg: {r.arg_type}" if r.arg_type else ""
        build_call = "arg" if r.arg_type else ""
        note = f"// {r.transition} (was {r.source_case})"
        routes.append(
            f"    fun routeTo{r.child_rib}({arg}) {{  {note}\n"
            f"        attachChild({_lc(r.child_rib)}Builder.build({build_call}))\n    }}")
    builders_block = "\n".join(builders)
    routes_block = "\n".join(routes) or f"    {TODO} no child routes"
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Router
import {pkg_root}.domain.model.*

/** Navigation for {rib.name}RIB (was {rib.name}Coordinator's Destination switch). */
class {rib.name}Router(
    interactor: {rib.name}Interactor,
{builders_block}
) : Router<{rib.name}Interactor>(interactor) {{

{routes_block}
}}
'''


def _root_router(pkg_root: str, rib: RibPlan) -> str:
    entry = rib.children[0] if rib.children else None
    if entry:
        ep = f"{pkg_root}.features.{entry.lower()}"
        attach = (f"    private val {_lc(entry)}Builder: {ep}.{entry}Builder,\n")
        load = f"        attachChild({_lc(entry)}Builder.build())  // entry feature"
    else:
        attach, load = "", f"        {TODO} attach the entry feature RIB"
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Router

/** App root. Attaches the entry feature; implements child Listeners to drive navigation. */
class RootRouter(
    interactor: RootInteractor,
{attach}) : Router<RootInteractor>(interactor) {{
    override fun detach() {{ super.detach() }}
    fun attachEntry() {{
{load}
    }}
}}
'''


def rib_builder(pkg_root: str, rib: RibPlan) -> str:
    if rib.is_root:
        return _root_builder(pkg_root, rib)
    args = ", ".join(rib.build_args)
    child_builders = []
    child_construct = []
    for r in [r for r in rib.routes if not r.external and r.child_rib]:
        child_pkg = f"{pkg_root}.features.{r.child_rib.lower()}"
        child_builders.append(f"        val {_lc(r.child_rib)}Builder = {child_pkg}.{r.child_rib}Builder(dependency)")
        child_construct.append(f"{_lc(r.child_rib)}Builder")
    children_block = "\n".join(child_builders)
    router_children = (", " + ", ".join(child_construct)) if child_construct else ""
    wire_router = ("\n        interactor.router = router" if child_construct else "")
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Builder
import {pkg_root}.domain.model.*

/** Constructs {rib.name}RIB (was {rib.name}Coordinator init + DIContainer wiring). */
class {rib.name}Builder(
    dependency: {rib.name}Dependency,
) : Builder<{rib.name}Dependency>(dependency) {{

    fun build({args}): {rib.name}Router {{
        val presenter = {rib.name}Presenter()
        val interactor = {rib.name}Interactor(
            presenter,
            {_builder_dep_args(rib)}
        )
{children_block}
        val router = {rib.name}Router(interactor{router_children}){wire_router}
        return router
    }}
}}
'''


def _builder_dep_args(rib: RibPlan) -> str:
    if rib.dependencies:
        return ", ".join(f"dependency.{_lc(d)}" for d in rib.dependencies)
    return f"{TODO} pass the use cases this RIB needs"


def _root_builder(pkg_root: str, rib: RibPlan) -> str:
    entry = rib.children[0] if rib.children else None
    line = ""
    pass_arg = ""
    if entry:
        ep = f"{pkg_root}.features.{entry.lower()}"
        line = (f"        val {_lc(entry)}Builder = {ep}.{entry}Builder(component)\n")
        pass_arg = f", {_lc(entry)}Builder"
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Builder

/** Root of the RIB tree. `component` is the app-wide dependency graph (was AppDependencyContainer). */
class RootBuilder(
    private val component: RootComponent,
) : Builder<RootComponent>(component) {{

    fun build(): RootRouter {{
        val interactor = RootInteractor(RootPresenter())
{line}        val router = RootRouter(interactor{pass_arg})
        interactor.router = router
        return router
    }}
}}
'''


def root_interactor(pkg_root: str, rib: RibPlan, child_ribs: list[RibPlan]) -> str:
    # The Root attaches the entry feature; that feature owns its own subtree, so the Root only
    # needs to implement an entry feature's Listener if that feature reports events upward.
    entry = rib.children[0] if rib.children else None
    return f'''package {_fq(pkg_root, rib)}

import {pkg_root}.core.ribs.Interactor

/** Root interactor. Attaches the entry feature ({entry or '—'}RIB) on activation. */
class RootInteractor(
    presenter: RootPresenter,
) : Interactor<RootPresenter>(presenter) {{

    lateinit var router: RootRouter

    override fun didBecomeActive() {{ router.attachEntry() }}
}}

class RootPresenter
'''


def root_component(pkg_root: str, ribs: list[RibPlan]) -> str:
    # the app-wide dependency graph: provides all use cases (was AppDependencyContainer registrations)
    deps: list[str] = []
    for r in ribs:
        for d in r.dependencies:
            if d not in deps:
                deps.append(d)
    fields = "\n\n".join(
        f"    {TODO} provide {d} (was AppDependencyContainer.register/DIContainer)\n"
        f"    override val {_lc(d)}: {_dep_type(pkg_root, d)}\n"
        f'        get() = TODO("wire Default{d} with its dependencies")'
        for d in deps)
    # Implement the entry features' Dependency interfaces; because a parent scope extends its
    # children's scopes, the entry features transitively cover the whole tree.
    root = next((r for r in ribs if r.is_root), None)
    entry = root.children if root else []
    ifaces = [f"{pkg_root}.features.{c.lower()}.{c}Dependency" for c in entry]
    iface_block = (" :\n    " + ",\n    ".join(ifaces)) if ifaces else ""
    return f'''package {_fq(pkg_root, [r for r in ribs if r.is_root][0])}

/** App-wide dependency graph. Replaces DIContainer.shared + AppDependencyContainer registrations.
 *  Implements every feature RIB's Dependency interface (constructor injection, no service locator). */
class RootComponent{iface_block} {{
{fields}
}}
'''


def rib_view(pkg_root: str, rib: RibPlan) -> str:
    return f'''package {_fq(pkg_root, rib)}

/* Compose Multiplatform view for {rib.name}RIB (was the SwiftUI {rib.name}View).
 * Kept framework-light so commonMain compiles without the Compose plugin during scaffolding.
 * {TODO} convert to @Composable: collect presenter.state, render UI, forward intents to the listener. */
class {rib.name}View(
    private val presenter: {rib.name}Presentable,
    private val listener: {rib.name}PresentableListener,
) {{
    {TODO} render {rib.name}ViewState and call listener on user actions
}}
'''


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _lc(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _dep_type(pkg_root: str, dep: str) -> str:
    """Fully-qualify an injected dependency by its role (repository vs use case)."""
    if dep.endswith("Repository"):
        return f"{pkg_root}.data.repository.{dep}"
    return f"{pkg_root}.domain.usecase.{dep}"
