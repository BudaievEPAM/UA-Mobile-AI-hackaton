"""Stage 3 (scaffold) — every RIB gets its 7 files + build skeleton; other samples don't crash."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from harness import analyzer, planner, scaffolder, verifier  # noqa: E402

_RIBS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_INPUT = os.path.join(os.path.dirname(_RIBS), "workspace", "input")
EASYCRYPTO = os.path.join(_INPUT, "EasyCrypto")
_RIB_SUFFIXES = ("Dependency", "Listener", "Presenter", "Interactor", "Router", "Builder", "View")


@unittest.skipUnless(os.path.isdir(EASYCRYPTO), "EasyCrypto fixture not present")
class ScaffoldEasyCryptoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ios2ribs-scaffold-")
        self.plan = planner.plan(analyzer.analyze(EASYCRYPTO), output_dir=self.tmp)
        self.files = scaffolder.scaffold(self.plan)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_skeleton_written(self):
        for rel in ("settings.gradle.kts", "build.gradle.kts", "gradle/libs.versions.toml",
                    "shared/build.gradle.kts"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, rel)), rel)

    def test_seven_files_per_feature_rib(self):
        common = os.path.join(self.tmp, "shared", "src", "commonMain", "kotlin",
                              *self.plan.package_root.split("."))
        for rib in (r for r in self.plan.ribs if not r.is_root):
            rdir = os.path.join(common, *rib.package.split("."))
            for suffix in _RIB_SUFFIXES:
                self.assertTrue(os.path.exists(os.path.join(rdir, f"{rib.name}{suffix}.kt")),
                                f"{rib.name}{suffix}.kt")

    def test_scaffold_generates_compose_capable_build(self):
        # the migrate stage fills Views with Compose, so the scaffold must enable the plugin
        with open(os.path.join(self.tmp, "shared", "build.gradle.kts"), encoding="utf-8") as fh:
            shared = fh.read()
        self.assertIn("composeMultiplatform", shared)
        self.assertIn("composeCompiler", shared)
        self.assertIn("compose.runtime", shared)


@unittest.skipUnless(os.path.isdir(_INPUT), "workspace/input not present")
class OtherSamplesSmokeTests(unittest.TestCase):
    """analyze -> plan -> scaffold -> verify must complete (no crash) on every bundled sample."""

    def test_all_samples_complete_without_crashing(self):
        samples = [d for d in sorted(os.listdir(_INPUT))
                   if os.path.isdir(os.path.join(_INPUT, d))]
        self.assertTrue(samples, "no input samples found")
        for name in samples:
            with self.subTest(sample=name):
                tmp = tempfile.mkdtemp(prefix=f"ios2ribs-{name}-")
                try:
                    a = analyzer.analyze(os.path.join(_INPUT, name))
                    p = planner.plan(a, output_dir=tmp)
                    scaffolder.scaffold(p)
                    res = verifier.verify(p, run_gradle=False)
                    # always produces a Root RIB and a defensible status
                    self.assertTrue(any(r.is_root for r in p.ribs), f"{name}: no Root RIB")
                    self.assertIn(res["status"], {"GREEN", "YELLOW", "RED"})
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
