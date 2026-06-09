"""Stage 5 — verify (the gate).

If a Gradle/JDK toolchain is available the verifier runs a real compile; otherwise it falls back to
a static gate that checks the generated tree the way `build_check.sh` does for the Swift harness:
structure completeness, Kotlin brace/paren balance (across all source sets), package declarations,
RIB wiring integrity, and absence of iOS-only symbols in `commonMain`.

Because there is usually no Kotlin compiler in this environment, the static gate also runs a set of
cheap, compiler-free *semantic* checks that catch the failure classes a brace-count cannot:
  - JVM-only APIs in `commonMain` (`String.format`, `import java.*`) — won't compile for KMP;
  - Compose UI in `commonMain` without the Compose plugin applied to `shared`;
  - imports of project types (`<pkg>.domain.model.X`, `<pkg>.features.…`, …) that are never declared;
  - `expect` declarations in `commonMain` with no matching `actual` in androidMain AND iosMain.
Returns GREEN / YELLOW / RED.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

from .models import MigrationPlan

_FORBIDDEN_IN_COMMON = [
    (r"\bimport Combine\b", "Combine import"),
    (r"\bimport SwiftUI\b", "SwiftUI import"),
    (r"\bDIContainer\b", "DIContainer service locator"),
    (r"@Published\b", "@Published"),
    (r"AnyPublisher<", "Combine AnyPublisher"),
]

# JVM-only constructs that do not exist in a multiplatform `commonMain` source set.
_JVM_ONLY_IN_COMMON = [
    (r'"[^"\n]*"\.format\(', "JVM-only String.format (no java.* in commonMain — use kotlin stdlib)"),
    (r"\bString\.format\(", "JVM-only String.format (no java.* in commonMain)"),
    (r"^\s*import\s+java\.", "java.* import in commonMain"),
    (r"^\s*import\s+javax\.", "javax.* import in commonMain"),
]

_TYPE_DECL_RE = re.compile(
    r"\b(?:data\s+|sealed\s+|open\s+|abstract\s+|final\s+|inner\s+|value\s+|enum\s+|annotation\s+)*"
    r"(?:class|interface|object)\s+([A-Za-z_]\w*)")
_TYPEALIAS_RE = re.compile(r"\btypealias\s+([A-Za-z_]\w*)")
_IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+)(?:\s+as\s+\w+)?", re.M)
_EXPECT_RE = re.compile(r"\bexpect\s+(?:fun|class|object|interface|val|var)\s+([A-Za-z_]\w*)")
_ACTUAL_RE = re.compile(r"\bactual\s+(?:fun|class|object|interface|val|var)\s+([A-Za-z_]\w*)")


def _kotlin_files(root: str) -> list[str]:
    out = []
    for dp, _dns, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".kt"):
                out.append(os.path.join(dp, fn))
    return out


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _strip_comments(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def _balanced(text: str) -> bool:
    # strip strings/comments crudely before counting braces
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    text = _strip_comments(text)
    return text.count("{") == text.count("}") and text.count("(") == text.count(")")


def verify(plan: MigrationPlan, run_gradle: bool = True) -> dict:
    out = os.path.abspath(plan.output_dir)
    findings: list[str] = []
    errors: list[str] = []

    # 1. structure completeness ------------------------------------------------
    required = ["settings.gradle.kts", "build.gradle.kts", "gradle/libs.versions.toml",
                "shared/build.gradle.kts"]
    for rel in required:
        if not os.path.exists(os.path.join(out, rel)):
            errors.append(f"missing build file: {rel}")

    src_root = os.path.join(out, "shared", "src")
    common = os.path.join(src_root, "commonMain", "kotlin")
    android = os.path.join(src_root, "androidMain", "kotlin")
    ios = os.path.join(src_root, "iosMain", "kotlin")

    common_files = _kotlin_files(common)
    all_files = _kotlin_files(src_root)
    if not common_files:
        errors.append("no Kotlin sources generated under commonMain")

    # whether the Compose plugin is applied to :shared (needed for androidx.compose in commonMain)
    shared_build = _read(os.path.join(out, "shared", "build.gradle.kts"))
    compose_enabled = ("composeMultiplatform" in shared_build
                       or "org.jetbrains.compose" in shared_build)

    # declared top-level types across commonMain — used to resolve project imports
    common_text: dict[str, str] = {}
    declared: set[str] = set()
    for path in common_files:
        text = _read(path)
        common_text[path] = text
        declared |= set(_TYPE_DECL_RE.findall(text))
        declared |= set(_TYPEALIAS_RE.findall(text))

    # 2. brace/package sanity across ALL source sets, todo count ---------------
    todo_count = 0
    for path in all_files:
        rel = os.path.relpath(path, out)
        text = common_text.get(path) or _read(path)
        if not re.search(r"^\s*package\s+[\w.]+", text, re.M):
            errors.append(f"{rel}: missing package declaration")
        if not _balanced(text):
            errors.append(f"{rel}: unbalanced braces/parens")
        todo_count += text.count("TODO(ios2ribs)")

    # 3. commonMain-only checks: forbidden / JVM-only / Compose / import resolution
    pkg_prefix = plan.package_root + "."
    for path in common_files:
        rel = os.path.relpath(path, out)
        text = common_text[path]
        stripped = _strip_comments(text)
        for pat, label in _FORBIDDEN_IN_COMMON:
            if re.search(pat, stripped):
                errors.append(f"{rel}: forbidden in commonMain — {label}")
        for pat, label in _JVM_ONLY_IN_COMMON:
            if re.search(pat, stripped, re.M):
                errors.append(f"{rel}: {label}")
        if not compose_enabled and re.search(r"\bandroidx\.compose\.", stripped):
            errors.append(f"{rel}: uses androidx.compose but :shared does not apply the Compose plugin")
        # imports of project types that were never declared anywhere in commonMain
        for fqn in _IMPORT_RE.findall(text):
            if not fqn.startswith(pkg_prefix):
                continue
            sym = fqn.rsplit(".", 1)[-1]
            if not sym or not sym[0].isupper():   # skip wildcards + top-level fun/val imports
                continue
            if sym not in declared:
                errors.append(f"{rel}: import of undeclared project type '{sym}' ({fqn})")

    # 4. expect/actual pairing -------------------------------------------------
    android_actuals = set()
    ios_actuals = set()
    for p in _kotlin_files(android):
        android_actuals |= set(_ACTUAL_RE.findall(_read(p)))
    for p in _kotlin_files(ios):
        ios_actuals |= set(_ACTUAL_RE.findall(_read(p)))
    for path in common_files:
        for name in _EXPECT_RE.findall(common_text[path]):
            if name not in android_actuals:
                errors.append(f"expect '{name}' has no matching actual in androidMain")
            if name not in ios_actuals:
                errors.append(f"expect '{name}' has no matching actual in iosMain")

    # 5. RIB wiring integrity --------------------------------------------------
    rib_names = {r.name for r in plan.ribs}
    for rib in plan.ribs:
        for r in rib.routes:
            if r.external:
                continue  # .url / system presentation — no child RIB by design
            if r.child_rib not in rib_names and not rib.is_root:
                findings.append(f"{rib.name}Router routes to unknown child '{r.child_rib}'")
    # every feature RIB has its 7 files
    for rib in plan.ribs:
        if rib.is_root:
            continue
        rdir = os.path.join(common, *plan.package_root.split("."), *rib.package.split("."))
        for suffix in ("Dependency", "Listener", "Presenter", "Interactor", "Router",
                       "Builder", "View"):
            if not os.path.exists(os.path.join(rdir, f"{rib.name}{suffix}.kt")):
                errors.append(f"{rib.name}: missing {rib.name}{suffix}.kt")

    # 6. optional real compile -------------------------------------------------
    gradle_result = None
    if run_gradle:
        gradlew = os.path.join(out, "gradlew")
        gradle_bin = gradlew if os.path.exists(gradlew) else shutil.which("gradle")
        if gradle_bin and shutil.which("java"):
            try:
                proc = subprocess.run(
                    [gradle_bin, "compileKotlinMetadata", "--offline", "-q"],
                    cwd=out, capture_output=True, text=True, timeout=900)
                gradle_result = {"ran": True, "returncode": proc.returncode,
                                 "tail": (proc.stdout + proc.stderr)[-1500:]}
                if proc.returncode != 0:
                    errors.append("gradle compile failed (see tail)")
            except (OSError, subprocess.SubprocessError) as exc:
                gradle_result = {"ran": False, "reason": str(exc)}
        else:
            gradle_result = {"ran": False, "reason": "no gradle/jdk toolchain available"}

    # status
    if errors:
        status = "RED"
    elif todo_count > 0 or (gradle_result and not gradle_result.get("ran")):
        status = "YELLOW"   # structurally sound; logic bodies (TODOs) still to be filled by agent
    else:
        status = "GREEN"

    return {
        "status": status,
        "kotlin_files": len(common_files),
        "open_todos": todo_count,
        "errors": errors,
        "findings": findings,
        "gradle": gradle_result,
        "compiled": bool(gradle_result and gradle_result.get("ran")
                         and gradle_result.get("returncode") == 0),
    }
