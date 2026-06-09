"""Stage 1 (analyze) — invariants on the bundled EasyCrypto fixture."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from harness import analyzer  # noqa: E402

_RIBS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_INPUT = os.path.join(os.path.dirname(_RIBS), "workspace", "input")
EASYCRYPTO = os.path.join(_INPUT, "EasyCrypto")


@unittest.skipUnless(os.path.isdir(EASYCRYPTO), "EasyCrypto fixture not present")
class AnalyzeEasyCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analyzer.analyze(EASYCRYPTO)

    def test_app_name(self):
        self.assertEqual(self.a.app_name, "EasyCrypto")

    def test_detects_coordinator_architecture(self):
        self.assertIn("coordinator", self.a.architecture["detected"])

    def test_three_ui_features(self):
        self.assertEqual(self.a.summary["uiFeatures"], 3)

    def test_feature_names(self):
        ui = {f.name for f in self.a.features if f.is_ui_feature}
        self.assertSetEqual(ui, {"Main", "Detail", "CoinDetail"})

    def test_main_has_routes(self):
        main = next(f for f in self.a.features if f.name == "Main")
        self.assertTrue(main.routes, "Main feature should emit navigation routes")


if __name__ == "__main__":
    unittest.main()
