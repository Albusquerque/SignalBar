from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from signalbar.arbiter import Arbiter
from signalbar.models import GameState, ProviderOutput, normalize_frame
from signalbar.providers.controller import ControllerProvider, DURATIONS, VARIANTS, controller_frame
from signalbar.settings import SettingsStore


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def controller(percent=74, identifier="one", charging=False):
    return {"id": identifier, "name": identifier, "percent": percent, "level": None, "charging": charging}


class ControllerTests(unittest.TestCase):
    def test_fifteen_mockup_variants_render_bounded_frames(self):
        for kind, variants in VARIANTS.items():
            for variant in variants:
                with self.subTest(kind=kind, variant=variant):
                    for step in range(1, 12):
                        elapsed = DURATIONS.get(kind, 3) * step / 12
                        frame = controller_frame(kind, variant, elapsed, 74, 25, intro_age=elapsed)
                        self.assertEqual(len(frame), 17)
                        self.assertTrue(all(0 <= channel <= 255 for pixel in frame for channel in pixel))
                    if kind in {"connect", "low", "charging"}:
                        self.assertEqual(controller_frame(kind, variant, DURATIONS[kind]),
                                         normalize_frame([(0, 0, 0)] * 17))
                    if kind == "duo":
                        self.assertEqual(controller_frame(kind, variant, 2.5, 74, 25)[8], (0, 0, 0))

    def test_settings_persist_validate_and_default_to_opt_in_gauge(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "settings.json")
            store = SettingsStore(path)
            self.assertEqual(store.all()["controller_battery_display"], "off")
            self.assertEqual(store.all()["controller_alert_context"], "both")
            store.update({"controller_battery_display": "home", "controller_connect_variant": "orbit"})
            restored = SettingsStore(path)
            self.assertEqual(restored.all()["controller_connect_variant"], "orbit")
            self.assertEqual(restored.all()["controller_battery_display"], "home")
            restored.update({"controller_connect_variant": "invalid", "controller_alert_context": [],
                             "controller_low_threshold": 999})
            self.assertEqual(restored.all()["controller_connect_variant"], "welcome")
            self.assertEqual(restored.all()["controller_alert_context"], "both")
            self.assertEqual(restored.all()["controller_low_threshold"], 30)

    def test_alerts_do_not_require_persistent_gauge_and_context_is_enforced(self):
        clock = Clock()
        provider = ControllerProvider(clock=clock)
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        provider.update([], values, False)
        provider.update([controller()], values, False)
        self.assertEqual(provider.event_output().provider, "controller:connect")
        self.assertIsNone(provider.persistent_output(values, False).frame)
        provider.clear_transients()
        provider.update([], values, False)
        values["controller_alert_context"] = "game"
        provider.update([controller(identifier="two")], values, False)
        self.assertIsNone(provider.event_output().frame)
        provider.update([], values, True)
        provider.update([controller(identifier="three")], values, True)
        self.assertEqual(provider.event_output().provider, "controller:connect")
        values["controller_alert_context"] = "home"
        provider.cancel_for_settings(values, game_running=True)
        self.assertIsNone(provider.event_output().frame)

    def test_low_battery_fires_once_on_crossing_and_rearms_after_recharge(self):
        clock = Clock()
        provider = ControllerProvider(clock=clock)
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        provider.update([controller(30)], values)
        provider.update([controller(19)], values)
        self.assertEqual(provider.event_output().provider, "controller:low")
        provider.clear_transients()
        provider.update([controller(18)], values)
        self.assertIsNone(provider.event_output().frame)
        provider.update([controller(26)], values)
        provider.update([controller(20)], values)
        self.assertEqual(provider.event_output().provider, "controller:low")
        provider.clear_transients()
        provider.update([controller(None)], values)
        self.assertIsNone(provider.event_output().frame)

    def test_home_gauge_replaces_base_but_never_countdown_or_critical_warning(self):
        clock = Clock()
        provider = ControllerProvider(clock=clock)
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        provider.update([controller()], values)
        values["controller_battery_display"] = "home"
        gauge = provider.persistent_output(values, False)
        self.assertEqual(gauge.provider, "controller-battery")
        self.assertIsNotNone(gauge.frame)
        self.assertIsNone(provider.persistent_output(values, True).frame)
        arbiter = Arbiter()
        base = ProviderOutput("performance", normalize_frame([(10, 20, 30)] * 17), "")
        timer = ProviderOutput("countdown", normalize_frame([(30, 20, 10)] * 17), "")
        kwargs = dict(mode="performance", guard_allows=True, game=GameState(),
                      performance=base, artwork=base, idle=ProviderOutput("idle", None, ""),
                      signal=ProviderOutput("countdown", None, ""), controller_base=gauge)
        self.assertEqual(arbiter.choose(**kwargs).provider, "controller-battery")
        self.assertEqual(arbiter.choose(**{**kwargs, "signal": timer}).provider, "countdown")
        self.assertEqual(arbiter.choose(**{**kwargs, "signal": timer, "signal_critical": True}).provider,
                         "countdown")
        self.assertEqual(arbiter.choose(**{**kwargs, "mode": "disabled"}).provider, "none")

    def test_two_controller_gauge_has_dark_centre_and_unknown_is_not_fake_percent(self):
        provider = ControllerProvider(clock=Clock())
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        values["controller_battery_display"] = "everywhere"
        provider.update([controller(74), controller(25, "two")], values)
        frame = provider.persistent_output(values, True).frame
        self.assertEqual(frame[8], (0, 0, 0))
        self.assertGreater(sum(pixel != (0, 0, 0) for pixel in frame[:8]),
                           sum(pixel != (0, 0, 0) for pixel in frame[9:]))
        provider.update([controller(None)], values)
        self.assertIsNone(provider.persistent_output(values, True).frame)

    def test_second_connection_uses_selected_duo_alert(self):
        provider = ControllerProvider(clock=Clock())
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        values["controller_duo_variant"] = "double-welcome"
        provider.update([controller()], values)
        provider.update([controller(), controller(25, "two")], values)
        active = provider.status(values)
        self.assertEqual(active["kind"], "duo")
        self.assertEqual(active["variant"], "double-welcome")
        self.assertEqual(active["colors"][8], [0, 0, 0])

    def test_coarse_battery_level_can_render_and_warn_without_claiming_percent(self):
        provider = ControllerProvider(clock=Clock())
        values = SettingsStore("/nonexistent/signalbar-settings.json").all()
        values["controller_battery_display"] = "everywhere"
        first = {**controller(None), "level": 2}
        provider.update([first], values)
        self.assertEqual(provider.status(values)["controllers"][0]["percent"], None)
        self.assertIsNotNone(provider.persistent_output(values).frame)
        provider.update([{**first, "level": 1}], values)
        self.assertEqual(provider.event_output().provider, "controller:low")


if __name__ == "__main__":
    unittest.main()
