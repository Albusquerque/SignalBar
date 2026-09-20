from pathlib import Path
import unittest


class PackagingTests(unittest.TestCase):
    def test_required_decky_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("main.py", "plugin.json", "package.json", "LICENSE", "scripts/package_plugin.py"):
            self.assertTrue((root / relative).is_file(), relative)
        self.assertTrue((root / "py_modules/signalbar/backend/engine.py").is_file())

    def test_panel_order_and_lifecycle_guards(self):
        root = Path(__file__).resolve().parents[2]
        panel = (root / "src/index.tsx").read_text(encoding="utf-8")
        content = panel.index("function Content")
        artwork = panel.index('<PanelSection title="Artwork">', content)
        performance = panel.index('<PanelSection title="Performance">', content)
        countdown = panel.index("<CountdownPanel status=", content)
        debug = panel.index('<PanelSection title="Debug">', content)
        self.assertLess(artwork, performance)
        self.assertLess(performance, countdown)
        self.assertLess(countdown, debug)

        runtime = (root / "src/runtime.ts").read_text(encoding="utf-8")
        self.assertIn('this.observeRunningApp("startup");', runtime)
        self.assertIn('window.setInterval(() => this.observeRunningApp("poll fallback")', runtime)
        self.assertIn("RegisterForAppLifetimeNotifications", runtime)
        self.assertIn("RegisterForOnResumeFromSuspend", runtime)
        self.assertIn("RegisterForDownloadOverview", runtime)
        self.assertIn("RegisterForParentalPlaytimeWarnings", runtime)
        self.assertIn("suppressedStaleAppId", runtime)
        self.assertIn("background game sync failed; retrying", runtime)
        self.assertIn("syncArtwork", runtime)
        game_sync = runtime.index("const status = await gameChanged")
        parental_registration = runtime.index("this.registerParentalSignal(current.appid)", game_sync)
        self.assertLess(game_sync, parental_registration)

        initializer = panel.index("export default definePlugin")
        runtime_start = panel.index("const runtime = startSignalBarRuntime()", initializer)
        returned_plugin = panel.index("return {", runtime_start)
        self.assertLess(runtime_start, returned_plugin)
        self.assertNotIn("useSteamState", panel)
        self.assertNotIn("useCountdownSignals", panel)
        self.assertIn('label="Extra dark LEDs"', panel)
        self.assertIn('setSetting("countdown_dark_edge_compensation", value)', panel)
        self.assertIn('label="Full bar scale"', panel)
        self.assertIn('setSetting("countdown_full_bar_minutes", Number(option.data))', panel)
        self.assertIn("Steam Families callback:", panel)
        self.assertIn("Game detection:", panel)


if __name__ == "__main__":
    unittest.main()
