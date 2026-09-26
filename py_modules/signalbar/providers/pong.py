"""PongBar's one-dimensional game and 17-pixel LED presentation."""

from __future__ import annotations

import time

from signalbar.models import LED_COUNT, ProviderOutput, normalize_frame

BLACK = (0, 0, 0)
WHITE = (245, 245, 235)
LEFT = (0, 175, 215)
RIGHT = (235, 65, 135)
LEVELS = ((0, 80, 95), (30, 65, 160), (100, 55, 165), (180, 85, 10), (190, 28, 25))


def _dim(colour, scale):
    return tuple(round(channel * scale) for channel in colour)


class PongGame:
    """Mutation is serialized by Engine's lock; time always uses one clock domain."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.session_id = 0
        self.best_streak = 0
        self.stop()

    def start(self, mode, gamepad_indices=(), best_streak=0,
              input_source=None, action_button=0):
        if mode not in {"solo", "duel"}:
            raise ValueError("PongBar mode must be solo or duel")
        indices = tuple(gamepad_indices)
        if input_source is None:
            input_source = "browser" if indices else "touch"
        if input_source not in {"touch", "browser", "steam"}:
            raise ValueError("Invalid PongBar input source")
        expected = 0 if input_source == "touch" else 1 if mode == "solo" else 2
        if len(indices) != expected:
            raise ValueError("Select one controller for solo or two for duel")
        if len(indices) != len(set(indices)) or any(
            not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < 0xffffffff
            for index in indices
        ):
            raise ValueError("Invalid controller selection")
        if input_source == "steam" and action_button not in {0, 2, 29, 41}:
            raise ValueError("Invalid PongBar button")
        now = self.clock()
        self.session_id += 1
        self.mode = mode
        self.input_source = input_source
        self.action_button = action_button if input_source == "steam" else 0
        self.gamepad_indices = indices
        self.active = True
        self.phase = "ready"
        self.phase_started = now
        self.last_tick = now
        self.paused_at = None
        self.pause_reason = ""
        self.ball = 8.0
        self.direction = 1
        self.server = 0
        self.scores = [0, 0]
        self.lives = 3
        self.streak = 0
        self.returns = 0
        self.best_streak = max(0, int(best_streak))
        self.hit_at = 0.0
        self.hit_player = -1
        self.hit_quality = ""
        self.feedback_seq = 0
        self.feedback_player = -1
        self.feedback_kind = ""
        self.winner = -1
        return self.status()

    def stop(self, reason=""):
        self.active = False
        self.phase = "idle"
        self.mode = ""
        self.input_source = "touch"
        self.action_button = 0
        self.gamepad_indices = ()
        self.scores = [0, 0]
        self.lives = 3
        self.streak = 0
        self.returns = 0
        self.ball = 8.0
        self.direction = 1
        self.server = 0
        self.phase_started = self.clock()
        self.last_tick = self.phase_started
        self.paused_at = None
        self.pause_reason = str(reason or "")
        self.hit_at = 0.0
        self.hit_player = -1
        self.hit_quality = ""
        self.feedback_seq = 0
        self.feedback_player = -1
        self.feedback_kind = ""
        self.winner = -1

    def _feedback(self, player, kind):
        self.feedback_seq += 1
        self.feedback_player = player
        self.feedback_kind = kind

    @property
    def level(self):
        return min(4, self.returns // 5)

    @property
    def seconds_per_led(self):
        return (0.25, 0.23, 0.21, 0.19, 0.17)[self.level]

    def press(self, player, session_id):
        now = self.clock()
        if not self.active or self.phase != "rally" or self.paused_at is not None:
            return False
        if session_id != self.session_id or player not in (0, 1):
            return False
        if self.mode == "solo" and player != 0:
            return False
        target = 0 if self.direction < 0 else 1
        if player != target:
            return False
        # Account for elapsed time between render ticks without trusting a
        # timestamp supplied by the frontend or another process clock.
        self._move(now)
        if self.phase != "rally":
            return False
        distance = self.ball - 1 if player == 0 else 15 - self.ball
        if not 0 <= distance <= 1.8:
            return False
        self.direction *= -1
        self.streak += 1
        self.returns += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.hit_at = now
        self.hit_player = player
        self.hit_quality = "perfect" if distance <= 0.55 else "hit"
        self._feedback(player, self.hit_quality)
        if self.returns % 5 == 0:
            self.phase = "level"
            self.phase_started = now
            self._feedback(player, "level")
        return True

    def _point(self, scorer, now):
        self._feedback(0 if self.mode == "solo" else scorer,
                       "loss" if self.mode == "solo" else "point")
        if self.mode == "solo":
            self.lives -= 1
            if self.lives <= 0:
                self.winner = 1
        else:
            self.scores[scorer] += 1
            if self.scores[scorer] >= 5:
                self.winner = scorer
        self.streak = 0
        self.server = 1 - self.server
        self.phase = "finished" if self.winner >= 0 else "point"
        self.phase_started = now

    def _move(self, now):
        if self.phase != "rally":
            self.last_tick = now
            return
        elapsed = max(0.0, min(0.5, now - self.last_tick))
        self.last_tick = now
        self.ball += self.direction * elapsed / self.seconds_per_led
        if self.mode == "solo" and self.direction > 0 and self.ball >= 15:
            self.ball = 15 - (self.ball - 15)
            self.direction = -1
            self._feedback(1, "bot")
        elif self.ball <= 1:
            self.ball = 1
            self._point(1, now)
        elif self.ball >= 15:
            self.ball = 15
            self._point(0, now)

    def advance(self, visible=True, reason=""):
        now = self.clock()
        if not self.active:
            return
        if not visible:
            if self.paused_at is None:
                self.paused_at = now
            self.pause_reason = str(reason or "Another signal has the bar")
            return
        if self.paused_at is not None:
            pause = now - self.paused_at
            self.phase_started += pause
            self.last_tick = now
            self.paused_at = None
            self.pause_reason = ""
        if self.phase == "ready" and now - self.phase_started >= 1.5:
            self.phase = "rally"
            self.phase_started = now
            self.last_tick = now
            self.ball = 8.0
            self.direction = 1 if self.server == 0 else -1
        elif self.phase == "point" and now - self.phase_started >= 0.9:
            self.phase = "ready"
            self.phase_started = now
        elif self.phase == "level" and now - self.phase_started >= 0.55:
            self.phase = "rally"
            self.phase_started = now
            self.last_tick = now
        elif self.phase == "finished" and now - self.phase_started >= 3.0:
            self.active = False
        else:
            self._move(now)

    def frame(self):
        pixels = [BLACK] * LED_COUNT
        if not self.active:
            return normalize_frame(pixels)
        now = self.paused_at if self.paused_at is not None else self.clock()
        level_colour = LEVELS[self.level]
        for index in range(2, 15):
            pixels[index] = _dim(level_colour, 0.5)
        pixels[0], pixels[1] = LEFT, _dim(LEFT, 0.48)
        pixels[15], pixels[16] = _dim(RIGHT, 0.48), RIGHT
        if self.phase == "rally":
            pixels[max(1, min(15, round(self.ball)))] = WHITE
            if now - self.hit_at < 0.18:
                edge = 0 if self.hit_player == 0 else 16
                pixels[edge] = WHITE if self.hit_quality == "perfect" else LEVELS[self.level]
        elif self.phase == "ready":
            elapsed = now - self.phase_started
            for index in range(max(0, 3 - int(elapsed / 0.5))):
                pixels[7 + index] = WHITE
        elif self.phase == "point":
            colour = LEFT if self.server == 0 else RIGHT
            span = int((now - self.phase_started) / 0.15) % 5 + 1
            for index in range(span):
                pixels[index if self.server == 0 else 16 - index] = colour
        elif self.phase == "level":
            reach = min(16, int((now - self.phase_started) / 0.55 * 17))
            for index in range(reach + 1):
                pixels[index] = level_colour
            pixels[max(1, min(15, round(self.ball)))] = WHITE
        elif self.phase == "finished":
            wave = int((now - self.phase_started) / 0.12)
            colour = LEFT if self.winner == 0 else RIGHT
            for index in range(17):
                pixels[index] = colour if abs(index - wave % 17) <= 2 else _dim(colour, 0.18)
        return normalize_frame(pixels)

    def output(self):
        return ProviderOutput("pongbar", self.frame() if self.active else None, self.phase)

    def status(self):
        return {
            "active": self.active,
            "session_id": self.session_id,
            "phase": self.phase,
            "mode": self.mode,
            "input_source": self.input_source,
            "action_button": self.action_button,
            "gamepad_indices": list(self.gamepad_indices),
            "scores": list(self.scores),
            "lives": self.lives,
            "streak": self.streak,
            "returns": self.returns,
            "best_streak": self.best_streak,
            "level": self.level + 1,
            "winner": self.winner,
            "paused": self.paused_at is not None,
            "pause_reason": self.pause_reason,
            "feedback_seq": self.feedback_seq,
            "feedback_player": self.feedback_player,
            "feedback_kind": self.feedback_kind,
            "colors": [list(pixel) for pixel in self.frame()],
        }
