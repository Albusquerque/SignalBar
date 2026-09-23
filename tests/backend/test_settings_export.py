import json
from pathlib import Path
import tempfile
import unittest

from signalbar.settings import SettingsStore
from signalbar.settings.export import (
    build_configuration_export,
    configuration_export_path,
    write_configuration_export,
)


class SettingsExportTests(unittest.TestCase):
    def test_export_groups_global_profiles_and_current_game(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(str(Path(directory) / "config.json"))
            store.update_display(42, "artwork")
            store.update_artwork(42, {"source": "header", "mode": "manual", "manual_y": 0.83})

            payload = build_configuration_export(
                store,
                "0.5.1",
                {"appid": 42, "title": "Example Game"},
                "2026-09-23T10:00:00Z",
            )

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["configuration"]["global"]["mode"], "performance")
            self.assertNotIn("display_profiles", payload["configuration"]["global"])
            self.assertEqual(payload["configuration"]["profiles"]["display_by_appid"], {"42": "artwork"})
            self.assertEqual(payload["configuration"]["current_game"]["display"]["mode"], "artwork")
            self.assertEqual(payload["configuration"]["current_game"]["artwork"]["manual_y"], 0.83)
            self.assertNotIn("controllers", payload["configuration"])

    def test_write_is_readable_and_reports_exact_path(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Documents" / "SignalBar-configuration.json"
            result = write_configuration_export(
                SettingsStore(str(Path(directory) / "config.json")),
                target,
                "0.5.1",
            )
            self.assertEqual(result["path"], str(target))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["signalbar_version"], "0.5.1")
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_path_prefers_documents_and_falls_back_to_settings(self):
        self.assertEqual(
            configuration_export_path("/tmp/settings", "/home/deck"),
            Path("/home/deck/Documents/SignalBar-configuration.json"),
        )
        self.assertEqual(
            configuration_export_path("/home/deck/homebrew/settings/SignalBar"),
            Path("/home/deck/Documents/SignalBar-configuration.json"),
        )
        self.assertEqual(
            configuration_export_path("/tmp/settings"),
            Path("/tmp/settings/SignalBar-configuration.json"),
        )


if __name__ == "__main__":
    unittest.main()
