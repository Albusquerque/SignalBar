from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from signalbar.arbiter import Arbiter
from signalbar.arbiter.guard import ManualClock
from signalbar.backend import Engine
from signalbar.models import GameState, ProviderOutput, normalize_frame
from signalbar.providers.pong import PongGame
from signalbar.settings import SettingsStore


def step(game, clock, seconds):
    for _ in range(round(seconds / 0.05)):
        clock.advance(0.05)
        game.advance()


class PongTests(unittest.TestCase):
    def test_engine_pong_reaches_renderer_and_returns_to_base(self):
        class Hardware:
            device_path = "/fake/valve-leds"
            reverse = False

            def __init__(self):
                self.frame = normalize_frame([(0, 0, 0)] * 17)

            def set_reverse(self, reverse):
                self.reverse = bool(reverse)

            def read_frame(self):
                return self.frame

            def read_signature(self):
                return self.frame

            def write_frame(self, frame):
                self.frame = normalize_frame(frame)

            def try_restore(self, frame):
                self.write_frame(frame)

        with tempfile.TemporaryDirectory() as folder:
            settings = SettingsStore(str(Path(folder) / "settings.json"))
            settings.update({"guard_stable_s": 0.5, "guard_cooldown_s": 1})
            hardware = Hardware()
            engine = Engine(settings, str(Path(folder) / "artwork.json"), hardware_factory=lambda: hardware)
            engine.start()
            try:
                engine.start_pong("solo", [])
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and engine.status()["provider"] != "pongbar":
                    time.sleep(0.02)
                self.assertEqual(engine.status()["provider"], "pongbar")
                self.assertNotEqual(hardware.frame[0], (0, 0, 0))
                engine.stop_pong()
                deadline = time.monotonic() + 1.0
                while time.monotonic() < deadline and engine.status()["provider"] == "pongbar":
                    time.sleep(0.02)
                self.assertNotEqual(engine.status()["provider"], "pongbar")
            finally:
                engine.stop()

    def test_solo_returns_progress_to_new_colour_and_record(self):
        clock = ManualClock(100)
        game = PongGame(clock)
        game.start("solo", [0])
        step(game, clock, 1.55)
        self.assertEqual(game.phase, "rally")
        for expected in range(1, 6):
            for _ in range(250):
                if game.phase == "rally" and game.direction < 0 and game.ball <= 2.7:
                    break
                step(game, clock, 0.05)
            else:
                self.fail("Ball never reached the left return window")
            self.assertFalse(game.press(1, game.session_id))
            self.assertFalse(game.press(0, game.session_id - 1))
            self.assertTrue(game.press(0, game.session_id))
            self.assertEqual(game.streak, expected)
        self.assertEqual(game.level, 1)
        self.assertEqual(game.best_streak, 5)
        self.assertEqual(game.phase, "level")
        self.assertEqual(len(game.output().frame), 17)
        self.assertEqual(game.status()["level"], 2)
        step(game, clock, 0.6)
        self.assertEqual(game.phase, "rally")
        for _ in range(200):
            if game.phase == "point":
                break
            step(game, clock, 0.05)
        self.assertEqual(game.streak, 0)
        self.assertEqual(game.returns, 5)
        self.assertEqual(game.status()["level"], 2)
        self.assertEqual(game.status()["feedback_player"], 0)
        self.assertEqual(game.status()["feedback_kind"], "loss")

    def test_duel_score_pause_and_finished_return_to_base(self):
        clock = ManualClock(100)
        game = PongGame(clock)
        game.start("duel", [2, 5])
        step(game, clock, 1.55)
        self.assertFalse(game.press(0, game.session_id))
        step(game, clock, 1.35)
        self.assertTrue(game.press(1, game.session_id))
        before = game.ball
        game.advance(False, "Steam alert")
        clock.advance(8)
        game.advance(False, "Steam alert")
        self.assertTrue(game.status()["paused"])
        self.assertFalse(game.press(0, game.session_id))
        game.advance(True)
        self.assertAlmostEqual(game.ball, before)
        step(game, clock, 4)
        self.assertEqual(game.scores, [0, 1])
        self.assertEqual(game.phase, "point")
        game.scores[1] = 4
        step(game, clock, 2.5)
        step(game, clock, 4)
        self.assertEqual(game.phase, "finished")
        self.assertEqual(game.winner, 1)
        step(game, clock, 3.1)
        self.assertFalse(game.active)
        self.assertIsNone(game.output().frame)

    def test_arbiter_gives_alerts_and_steam_priority_over_pong(self):
        frame = normalize_frame([(30, 20, 10)] * 17)
        pong = ProviderOutput("pongbar", frame, "rally")
        event = ProviderOutput("event:notification", frame, "notification")
        base = ProviderOutput("idle", frame, "idle")
        choose = dict(mode="performance", game=GameState(), performance=base,
                      artwork=base, idle=base, pong=pong)
        self.assertEqual(Arbiter().choose(guard_allows=True, **choose).provider, "pongbar")
        self.assertEqual(Arbiter().choose(guard_allows=True, event=event, **choose).provider, "event:notification")
        self.assertEqual(Arbiter().choose(guard_allows=False, **choose).provider, "valve")

    def test_engine_rejects_game_session_and_persists_solo_record(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = SettingsStore(str(Path(folder) / "settings.json"))
            engine = Engine(settings, str(Path(folder) / "artwork.json"))
            status = engine.start_pong("solo", [])
            self.assertTrue(status["pong"]["active"])
            with engine._lock:
                engine.pong.phase = "rally"
                engine.pong.ball = 2.0
                engine.pong.direction = -1
            engine.press_pong(status["pong"]["session_id"], 0)
            self.assertEqual(SettingsStore(settings.path).all()["pong_best_streak"], 1)
            engine.set_game(123, "Other game")
            self.assertFalse(engine.pong_status()["active"])
            with self.assertRaisesRegex(ValueError, "Steam Home"):
                engine.start_pong("duel", [0, 1])


if __name__ == "__main__":
    unittest.main()
