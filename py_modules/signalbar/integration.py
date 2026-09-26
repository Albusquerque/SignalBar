"""Small, fail-safe coordination signals shared with other LED plugins."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path


LEASE_ENV = "SIGNALBAR_LIGHT_EVENT_LEASE"
DEFAULT_LIGHT_EVENT_LEASE = "/run/decky/signalbar-light-event.json"


class LightEventLease:
    """Publish a short renewable lease while SignalBar renders a Light event."""

    def __init__(self, path=None, clock=time.time, ttl_s=0.75, ack_path=None):
        self.path = Path(path or os.environ.get(LEASE_ENV, DEFAULT_LIGHT_EVENT_LEASE))
        self.ack_path = Path(ack_path) if ack_path else self.path.with_name(self.path.stem + ".ack.json")
        self.clock = clock
        self.ttl_s = max(0.25, float(ttl_s))
        self.token = f"{os.getpid()}-{uuid.uuid4().hex}"
        self._last_write_at = 0.0

    def refresh(self, event=""):
        now = self.clock()
        if now - self._last_write_at < min(0.20, self.ttl_s / 3):
            return True
        temporary = self.path.with_name(f".{self.path.name}.{self.token}.tmp")
        payload = {
            "protocol": 1,
            "owner": "SignalBar",
            "purpose": "light-event",
            "event": str(event or "")[:80],
            "token": self.token,
            "expires_at": now + self.ttl_s,
        }
        try:
            self.path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
            os.chmod(temporary, 0o644)
            os.replace(temporary, self.path)
            self._last_write_at = now
            return True
        except OSError:
            try:
                temporary.unlink()
            except OSError:
                pass
            return False

    def acknowledged(self):
        try:
            if self.ack_path.stat().st_size > 4096:
                return False
            data = json.loads(self.ack_path.read_text(encoding="utf-8"))
            return (
                data.get("protocol") == 1
                and data.get("owner") == "StripMine"
                and data.get("token") == self.token
                and float(data.get("expires_at", 0)) > self.clock()
            )
        except (OSError, ValueError, TypeError, OverflowError):
            return False

    def release(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("token") == self.token:
                self.path.unlink()
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        try:
            data = json.loads(self.ack_path.read_text(encoding="utf-8"))
            if data.get("token") == self.token:
                self.ack_path.unlink()
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self._last_write_at = 0.0
