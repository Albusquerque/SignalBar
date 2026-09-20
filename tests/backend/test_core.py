from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalbar.arbiter import Arbiter
from signalbar.arbiter.guard import ManualClock, VanillaGuard
from signalbar.hardware import ValveLedHardware
from signalbar.models import GameState, PerformanceSample, ProviderOutput, normalize_frame
from signalbar.providers import ArtworkProvider, mixed_performance_frame, performance_frame, temperature_color
from signalbar.renderer import Renderer
from signalbar.settings import SettingsStore
from signalbar.steam import find_library_artwork, get_library_artwork


BLACK = normalize_frame([(0, 0, 0)] * 17)
RED = normalize_frame([(255, 0, 0)] * 17)
BLUE = normalize_frame([(0, 0, 255)] * 17)


class FakeHardware:
    device_path = "/fake/valve-leds"

    def __init__(self):
        self.frame = BLACK
        self.write_calls = []

    def read_frame(self):
        return self.frame

    def read_signature(self):
        return tuple((f"{r} {g} {b}", "255") for r, g, b in self.frame)

    def write_frame(self, frame):
        self.frame = normalize_frame(frame)
        self.write_calls.append(self.frame)

    def try_restore(self, frame):
        self.write_frame(frame)


class CoreTests(unittest.TestCase):
    def test_performance_mapping_zero_to_seventeen(self):
        self.assertEqual(sum(pixel != (0, 0, 0) for pixel in performance_frame(0, 60)), 0)
        self.assertEqual(sum(pixel != (0, 0, 0) for pixel in performance_frame(70, 60)), 12)
        self.assertEqual(sum(pixel != (0, 0, 0) for pixel in performance_frame(100, 60)), 17)

    def test_mixed_performance_uses_eight_plus_separator_plus_eight(self):
        sample = PerformanceSample(
            gpu_load=50, gpu_temp_c=70, cpu_load=25, cpu_temp_c=60, sampled_at=1,
        )
        frame = mixed_performance_frame(sample)
        self.assertEqual(len(frame), 17)
        self.assertEqual(frame[8], (0, 0, 0))
        self.assertEqual(sum(pixel != (0, 0, 0) for pixel in frame[:8]), 2)
        self.assertEqual(sum(pixel != (0, 0, 0) for pixel in frame[9:]), 4)
        self.assertNotEqual(frame[0], (0, 0, 0))
        self.assertNotEqual(frame[-1], (0, 0, 0))

        same_direction = mixed_performance_frame(sample, direction="same")
        self.assertNotEqual(same_direction[9], (0, 0, 0))
        self.assertEqual(same_direction[-1], (0, 0, 0))

    def test_temperature_thresholds_and_palette_are_explicit(self):
        self.assertEqual(temperature_color(50, 50, 90, "classic"), (35, 205, 95))
        self.assertEqual(temperature_color(90, 50, 90, "classic"), (235, 45, 55))

    def test_renderer_coalesces_and_rate_limits(self):
        clock = ManualClock(100)
        hardware = FakeHardware()
        renderer = Renderer(hardware, min_interval_s=0.05, clock=clock)
        self.assertTrue(renderer.render(RED))
        self.assertFalse(renderer.render(RED))
        self.assertFalse(renderer.render(BLUE))
        self.assertEqual(len(hardware.write_calls), 1)
        clock.advance(0.051)
        self.assertTrue(renderer.render(BLUE))
        self.assertEqual(len(hardware.write_calls), 2)

    def test_renderer_restores_only_while_still_owner(self):
        clock = ManualClock(100)
        hardware = FakeHardware()
        renderer = Renderer(hardware, clock=clock)
        renderer.render(RED)
        self.assertTrue(renderer.relinquish(True))
        self.assertEqual(hardware.frame, BLACK)

        renderer.render(RED)
        hardware.frame = BLUE  # Valve/external actor changed the bar.
        self.assertFalse(renderer.relinquish(True))
        self.assertEqual(hardware.frame, BLUE)

    def test_guard_external_takeover_and_cooldown(self):
        clock = ManualClock()
        guard = VanillaGuard(cooldown_s=5, stable_s=2, clock=clock)
        guard.observe("native-a")
        clock.advance(2.1)
        self.assertTrue(guard.observe("native-a"))
        self.assertFalse(guard.observe("native-b", expected_signature="signalbar"))
        self.assertEqual(guard.reason, "external LED change detected")
        clock.advance(4.9)
        self.assertFalse(guard.observe("native-b"))
        clock.advance(0.2)
        self.assertTrue(guard.observe("native-b"))

    def test_arbiter_transitions(self):
        arbiter = Arbiter()
        game = GameState(10, "Test")
        performance = ProviderOutput("performance", RED, "metrics")
        artwork = ProviderOutput("artwork", BLUE, "hero")
        idle = ProviderOutput("idle", None, "Vanilla")
        self.assertEqual(arbiter.choose(mode="artwork", guard_allows=False, game=game, performance=performance, artwork=artwork, idle=idle).provider, "valve")
        self.assertEqual(arbiter.choose(mode="performance", guard_allows=True, game=game, performance=performance, artwork=artwork, idle=idle).provider, "performance")
        unavailable = ProviderOutput("performance", None, "missing")
        self.assertEqual(arbiter.choose(mode="artwork", guard_allows=True, game=game, performance=unavailable, artwork=artwork, idle=idle).provider, "artwork")
        self.assertIsNone(arbiter.choose(mode="disabled", guard_allows=True, game=game, performance=performance, artwork=artwork, idle=idle).frame)


class PersistenceTests(unittest.TestCase):
    def test_artwork_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "art.json")
            provider = ArtworkProvider(path)
            provider.submit(42, "fingerprint", "auto", 0.72, RED, 0.65, "library_hero.jpg")
            reloaded = ArtworkProvider(path)
            self.assertTrue(reloaded.activate_cached(42, "fingerprint", "auto", 0.72))
            self.assertEqual(reloaded.output(42).frame, RED)
            self.assertFalse(reloaded.activate_cached(42, "changed", "auto", 0.72))

    def test_settings_persist_and_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "config.json")
            store = SettingsStore(path)
            store.update({"mode": "artwork", "artwork_manual_y": 5})
            loaded = SettingsStore(path).all()
            self.assertEqual(loaded["mode"], "artwork")
            self.assertEqual(loaded["artwork_manual_y"], 0.90)
            self.assertEqual(json.loads(Path(path).read_text())["mode"], "artwork")

    def test_artwork_settings_are_persisted_per_game(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "config.json")
            store = SettingsStore(path)
            store.update_artwork(2379780, {"mode": "manual", "manual_y": 0.83, "source": "header"})
            self.assertEqual(store.artwork_for(2379780)["manual_y"], 0.83)
            self.assertTrue(store.artwork_for(2379780)["custom"])
            self.assertEqual(store.artwork_for(2379780)["source"], "header")
            self.assertEqual(store.artwork_for(620)["mode"], "auto")
            self.assertFalse(store.artwork_for(620)["custom"])

            reloaded = SettingsStore(path)
            self.assertEqual(reloaded.artwork_for(2379780)["mode"], "manual")
            self.assertEqual(reloaded.artwork_for(2379780)["manual_y"], 0.83)

    def test_automatic_settings_migrate_to_an_explicit_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"mode": "automatic", "performance_enabled": False}))
            self.assertEqual(SettingsStore(str(path)).all()["mode"], "artwork")
            path.write_text(json.dumps({"mode": "automatic", "performance_enabled": True}))
            self.assertEqual(SettingsStore(str(path)).all()["mode"], "performance")

    def test_discovers_hero_header_and_capsule_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Steam"
            cache = root / "appcache/librarycache/42"
            cache.mkdir(parents=True)
            (cache / "library_hero.jpg").write_bytes(b"hero")
            (cache / "header.jpg").write_bytes(b"header")
            (cache / "library_600x900.jpg").write_bytes(b"capsule")
            with patch.dict("os.environ", {"SIGNALBAR_STEAM_ROOT": str(root)}):
                self.assertEqual(find_library_artwork(42, "hero").name, "library_hero.jpg")
                self.assertEqual(find_library_artwork(42, "header").name, "header.jpg")
                self.assertEqual(find_library_artwork(42, "capsule").name, "library_600x900.jpg")
                payload = get_library_artwork(42, "header")
                self.assertEqual(payload["source_label"], "Library Header")

    def test_hardware_reverse_maps_logical_left_to_physical_right(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(17):
                path = Path(directory) / f"valve-leds[{index}]"
                path.mkdir()
                (path / "multi_intensity").write_text("0 0 0")
                (path / "brightness").write_text("255")
                paths.append(str(path))
            hardware = ValveLedHardware(paths)
            hardware.set_reverse(True)
            frame = normalize_frame([(index, 0, 0) for index in range(17)])
            hardware.write_frame(frame)
            self.assertEqual((Path(paths[0]) / "multi_intensity").read_text(), "16 0 0")
            self.assertEqual((Path(paths[-1]) / "multi_intensity").read_text(), "0 0 0")
            self.assertEqual(hardware.read_frame(), frame)


if __name__ == "__main__":
    unittest.main()
