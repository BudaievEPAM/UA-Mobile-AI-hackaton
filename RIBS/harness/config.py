"""Static configuration: paths, the pinned KMP stack, and filename->kind heuristics.

Kept declarative so the knowledge base (knowledge/kmp-stack.md) and this file stay in sync.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
RIBS_ROOT = os.path.dirname(HARNESS_DIR)              # the RIBS/ directory
KNOWLEDGE_DIR = os.path.join(RIBS_ROOT, "knowledge")
PROMPTS_DIR = os.path.join(HARNESS_DIR, "prompts")
DEFAULT_OUTPUT = os.path.join(RIBS_ROOT, "output")

# Directories never worth scanning in a Swift repo.
SKIP_DIRS = {
    "Pods", "Carthage", ".build", "DerivedData", "build", ".git", "vendor",
    "Vendor", "fastlane", ".swiftpm", "xcuserdata", "Assets.xcassets",
}

# filename-suffix (before .swift) -> source Kind value
SUFFIX_KIND = {
    "Coordinator": "coordinator",
    "FlowCoordinator": "coordinator",
    "Router": "router",
    "Wireframe": "router",
    "Presenter": "presenter",
    "Interactor": "interactor",
    "Builder": "builder",
    "Configurator": "builder",
    "ViewModel": "viewmodel",
    "ViewController": "view",
    "View": "view",
    "UseCase": "usecase",
    "Usecase": "usecase",
    "Repository": "repository",
    "RepositoryImpl": "repository",
    "Remote": "remote",
    "DataSource": "remote",
    "Entity": "entity",
    "DTO": "dto",
    "Mapper": "mapper",
    "DIContainer": "di",
    "DependencyContainer": "di",
    "Component": "component",
    "Client": "network",
    "NetworkClient": "network",
}

# regex -> (stack-category, tag) for tech-stack detection
STACK_SIGNALS = {
    r"\bAlamofire\b": ("networking", "Alamofire"),
    r"\bURLSession\b": ("networking", "URLSession"),
    r"\bMoya\b": ("networking", "Moya"),
    r"\bCoreData\b|NSManagedObject": ("persistence", "CoreData"),
    r"\bRealm\b": ("persistence", "Realm"),
    r"\bUserDefaults\b": ("persistence", "UserDefaults"),
    r"\bSwinject\b": ("di", "Swinject"),
    r"DIContainer": ("di", "DIContainer"),
    r"\bUINavigationController\b|pushViewController": ("navigation", "UIKitNav"),
    r"\bCoordinator\b|navigateSubject": ("navigation", "Coordinator"),
    r"import SwiftUI": ("ui", "SwiftUI"),
    r"import UIKit": ("ui", "UIKit"),
    r"\bCombine\b|@Published": ("reactive", "Combine"),
    r"\bRxSwift\b|Observable<": ("reactive", "RxSwift"),
}

# How the architecture detector scores signals.
ARCH_DIR_SIGNALS = {"domain": "clean", "data": "clean", "presentation": "clean",
                    "infrastructure": "clean", "persistance": "clean", "persistence": "clean"}


@dataclass(frozen=True)
class KmpStack:
    """The pinned target stack — mirrors knowledge/kmp-stack.md."""

    kotlin: str = "2.0.21"
    gradle: str = "8.9"
    agp: str = "8.5.2"
    compose: str = "1.7.1"
    coroutines: str = "1.9.0"
    ktor: str = "3.0.1"
    serialization: str = "1.7.3"
    sqldelight: str = "2.0.2"
    android_compile_sdk: int = 35
    android_min_sdk: int = 24

    substitutions: dict[str, str] = field(default_factory=lambda: {
        "Combine": "kotlinx.coroutines (Flow/StateFlow/suspend)",
        "URLSession / custom NetworkClient": "Ktor HttpClient",
        "Codable": "kotlinx.serialization (@Serializable)",
        "CoreData": "SQLDelight",
        "DIContainer (service locator)": "RIB Component (constructor injection)",
        "SwiftUI": "Compose Multiplatform",
        "GCD / WorkScheduler": "Dispatchers.IO / Dispatchers.Main",
    })


STACK = KmpStack()

KNOWLEDGE_FILES = [
    "ribs-patterns.md",
    "mvvm-coordinator-to-ribs.md",
    "clean-to-kmp.md",
    "combine-to-coroutines.md",
    "kmp-stack.md",
]
