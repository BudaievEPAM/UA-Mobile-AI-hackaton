"""Stage 5 (verify) — the gate must pass a clean scaffold and fail broken / non-portable trees.

Each test scaffolds a fresh EasyCrypto project into a temp dir, mutates it, and asserts the gate's
verdict. Covers the structural checks and the semantic checks that a brace-count cannot catch.
"""
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


@unittest.skipUnless(os.path.isdir(EASYCRYPTO), "EasyCrypto fixture not present")
class VerifierGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ios2ribs-verify-")
        self.plan = planner.plan(analyzer.analyze(EASYCRYPTO), output_dir=self.tmp)
        scaffolder.scaffold(self.plan)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- path helpers ------------------------------------------------------- #
    def _common(self, *rel):
        return os.path.join(self.tmp, "shared", "src", "commonMain", "kotlin",
                            *self.plan.package_root.split("."), *rel)

    def _ios(self, *rel):
        return os.path.join(self.tmp, "shared", "src", "iosMain", "kotlin",
                            *self.plan.package_root.split("."), *rel)

    @staticmethod
    def _append(path, text):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n" + text + "\n")

    @staticmethod
    def _rewrite(path, fn):
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn(src))

    def _verify(self):
        return verifier.verify(self.plan, run_gradle=False)

    def _assert_red(self, res, needle):
        self.assertEqual(res["status"], "RED", res)
        self.assertTrue(any(needle in e for e in res["errors"]),
                        f"expected an error containing {needle!r}; got {res['errors']}")

    # --- baseline ----------------------------------------------------------- #
    def test_fresh_scaffold_is_yellow_no_errors(self):
        res = self._verify()
        self.assertEqual(res["errors"], [], res["errors"])
        self.assertEqual(res["status"], "YELLOW")   # TODO bodies still to be filled
        self.assertGreater(res["open_todos"], 0)

    # --- structural RED cases ---------------------------------------------- #
    def test_missing_package_is_red(self):
        self._rewrite(self._common("core", "ribs", "Ribs.kt"),
                      lambda s: s.replace("package ", "// package ", 1))
        self._assert_red(self._verify(), "missing package declaration")

    def test_unbalanced_braces_is_red(self):
        self._append(self._common("core", "ribs", "Ribs.kt"), "fun broken() {")
        self._assert_red(self._verify(), "unbalanced")

    def test_missing_rib_file_is_red(self):
        os.remove(self._common("features", "main", "MainView.kt"))
        self._assert_red(self._verify(), "missing MainView.kt")

    def test_combine_import_in_common_is_red(self):
        self._append(self._common("core", "ribs", "Ribs.kt"), "import Combine")
        self._assert_red(self._verify(), "Combine")

    # --- semantic RED cases (the bugs a brace-count misses) ----------------- #
    def test_string_format_in_common_is_red(self):
        self._append(self._common("core", "ribs", "Ribs.kt"),
                     'val pct = "%.2f".format(1.0)')
        self._assert_red(self._verify(), "String.format")

    def test_java_import_in_common_is_red(self):
        self._append(self._common("core", "ribs", "Ribs.kt"), "import java.text.DecimalFormat")
        self._assert_red(self._verify(), "java.* import")

    def test_compose_without_plugin_is_red(self):
        # drop the Compose plugin from :shared, then use Compose in commonMain
        self._rewrite(os.path.join(self.tmp, "shared", "build.gradle.kts"),
                      lambda s: "\n".join(l for l in s.splitlines()
                                          if "compose" not in l.lower()))
        self._append(self._common("core", "ribs", "Ribs.kt"),
                     "import androidx.compose.runtime.Composable")
        self._assert_red(self._verify(), "Compose plugin")

    def test_unresolved_project_import_is_red(self):
        self._append(self._common("core", "ribs", "Ribs.kt"),
                     f"import {self.plan.package_root}.domain.model.NoSuchType")
        self._assert_red(self._verify(), "NoSuchType")

    def test_missing_ios_actual_is_red(self):
        # remove the iosMain actual for the expect httpClientEngineFactory
        os.remove(self._ios("core", "network", "HttpClient.ios.kt"))
        self._assert_red(self._verify(), "no matching actual in iosMain")


if __name__ == "__main__":
    unittest.main()
