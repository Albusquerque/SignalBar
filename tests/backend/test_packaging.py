from pathlib import Path
import unittest


class PackagingTests(unittest.TestCase):
    def test_required_decky_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("main.py", "plugin.json", "package.json", "LICENSE", "scripts/package_plugin.py"):
            self.assertTrue((root / relative).is_file(), relative)
        self.assertTrue((root / "py_modules/signalbar/backend/engine.py").is_file())


if __name__ == "__main__":
    unittest.main()

