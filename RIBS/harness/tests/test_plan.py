"""Stage 2 (plan) — RIB tree + build order derived from EasyCrypto."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from harness import analyzer, planner  # noqa: E402

_RIBS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_INPUT = os.path.join(os.path.dirname(_RIBS), "workspace", "input")
EASYCRYPTO = os.path.join(_INPUT, "EasyCrypto")


@unittest.skipUnless(os.path.isdir(EASYCRYPTO), "EasyCrypto fixture not present")
class PlanEasyCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = planner.plan(analyzer.analyze(EASYCRYPTO), output_dir="/tmp/ios2ribs-plan-unused")

    def test_package_root(self):
        self.assertEqual(self.p.package_root, "com.easycrypto")

    def test_rib_set(self):
        names = {r.name for r in self.p.ribs}
        self.assertSetEqual(names, {"Root", "Main", "Detail", "CoinDetail"})

    def test_root_is_root(self):
        root = next(r for r in self.p.ribs if r.is_root)
        self.assertEqual(root.name, "Root")
        self.assertIn("Main", root.children)

    def test_main_children(self):
        main = next(r for r in self.p.ribs if r.name == "Main")
        self.assertSetEqual(set(main.children), {"Detail", "CoinDetail"})
        self.assertTrue(main.routes)

    def test_build_order_tail(self):
        self.assertEqual(self.p.build_order[-3:], ["rib:Root", "app", "verify"])

    def test_artifacts_present(self):
        kinds = {a.kind for a in self.p.artifacts}
        # use cases + repositories are reliably planned from EasyCrypto's Clean layer
        self.assertTrue({"usecase", "repository"} <= kinds, kinds)


if __name__ == "__main__":
    unittest.main()
