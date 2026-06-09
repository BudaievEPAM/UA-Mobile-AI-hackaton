"""Dataclasses shared across the pipeline stages.

Everything is JSON-serialisable via :func:`to_dict` so each stage can persist its
output (analysis.json, plan.json) and the next stage / the agent can read it back.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Source-side (iOS) inventory
# --------------------------------------------------------------------------- #
class Kind(str, Enum):
    """Classified role of a Swift source file (by filename / content heuristics)."""

    VIEW = "view"
    VIEWMODEL = "viewmodel"
    COORDINATOR = "coordinator"
    PRESENTER = "presenter"
    INTERACTOR = "interactor"
    ROUTER = "router"
    BUILDER = "builder"
    USECASE = "usecase"
    REPOSITORY = "repository"
    REMOTE = "remote"
    ENTITY = "entity"
    DTO = "dto"
    MAPPER = "mapper"
    DI = "di"
    NETWORK = "network"
    PERSISTENCE = "persistence"
    EXTENSION = "extension"
    COMPONENT = "component"
    OTHER = "other"


@dataclass
class SwiftFile:
    rel_path: str
    kind: str = Kind.OTHER.value
    lines: int = 0
    types: list[str] = field(default_factory=list)        # declared type names
    imports: list[str] = field(default_factory=list)
    publishes: list[str] = field(default_factory=list)    # @Published / Subject names
    routes: list[str] = field(default_factory=list)       # navigation route cases found

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class FeatureModule:
    """A candidate feature (a Presentation/<Feature> folder or a Domain/Data group)."""

    name: str
    path: str
    kinds: dict[str, int] = field(default_factory=dict)   # kind -> count
    files: list[str] = field(default_factory=list)        # rel paths
    routes: list[str] = field(default_factory=list)       # navigation cases this feature emits
    is_ui_feature: bool = False                            # has View+ViewModel(+Coordinator)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class Analysis:
    repo: str
    app_name: str
    summary: dict[str, int] = field(default_factory=dict)
    architecture: dict[str, Any] = field(default_factory=dict)
    stack: dict[str, list[str]] = field(default_factory=dict)
    features: list[FeatureModule] = field(default_factory=list)
    files: list[SwiftFile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        return d


# --------------------------------------------------------------------------- #
# Target-side (RIBs / KMP) plan
# --------------------------------------------------------------------------- #
class Transition(str, Enum):
    PUSH = "push"
    SHEET = "bottomSheet"
    URL = "url"
    ROOT = "root"


@dataclass
class RibRoute:
    """A navigation edge of a RIB: parent attaches a child RIB."""

    listener_method: str          # e.g. "coinDetailRequested"
    child_rib: str                # e.g. "CoinDetail"
    transition: str = Transition.PUSH.value
    arg_type: Optional[str] = None  # payload carried to the child (e.g. "String", "MarketsPrice")
    source_case: Optional[str] = None  # original Swift route case
    external: bool = False        # true for .url / system presentations (no child RIB attached)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class RibPlan:
    """One RIB to generate."""

    name: str                       # e.g. "Main", "CoinDetail", "Root"
    package: str                    # e.g. "features.main"
    source_feature: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)   # UseCase / repository interfaces it needs
    state_fields: list[str] = field(default_factory=list)   # ViewState fields (from @Published)
    build_args: list[str] = field(default_factory=list)     # inputs Builder.build(...) takes
    routes: list[RibRoute] = field(default_factory=list)    # children it can attach
    children: list[str] = field(default_factory=list)       # child RIB names
    is_root: bool = False
    source_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["routes"] = [r if isinstance(r, dict) else r.to_dict() for r in self.routes]
        return d


@dataclass
class KotlinArtifact:
    """A domain/data/network Kotlin file to generate (non-RIB)."""

    rel_path: str                   # under shared/src/commonMain/kotlin/<pkg>/
    kind: str                       # model | usecase | repository | remote | network
    source_files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class MigrationPlan:
    app_name: str
    package_root: str               # e.g. "com.easycrypto"
    output_dir: str
    ribs: list[RibPlan] = field(default_factory=list)
    artifacts: list[KotlinArtifact] = field(default_factory=list)
    build_order: list[str] = field(default_factory=list)   # ordered list of step ids
    stack_substitutions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "package_root": self.package_root,
            "output_dir": self.output_dir,
            "ribs": [r.to_dict() for r in self.ribs],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "build_order": self.build_order,
            "stack_substitutions": self.stack_substitutions,
        }
