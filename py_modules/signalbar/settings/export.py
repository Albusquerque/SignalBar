"""Human-retrievable exports of SignalBar's saved configuration."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path


EXPORT_FILENAME = "SignalBar-configuration.json"


def configuration_export_path(settings_directory: str, user_home: str | None = None) -> Path:
    """Prefer the Steam user's Documents folder, with a safe settings fallback."""
    if user_home:
        home = Path(user_home).expanduser()
        if home.is_absolute():
            return home / "Documents" / EXPORT_FILENAME

    settings = Path(settings_directory).expanduser()
    if not settings.is_absolute():
        settings = Path.cwd() / settings
    for parent in (settings, *settings.parents):
        if parent.name == "homebrew" and parent.parent != parent:
            return parent.parent / "Documents" / EXPORT_FILENAME
    return settings / EXPORT_FILENAME


def build_configuration_export(settings, version: str, current_game=None, generated_at=None):
    """Build a stable, controller-ID-free document from persisted choices."""
    values = deepcopy(settings.all())
    display_profiles = values.pop("display_profiles", {})
    artwork_profiles = values.pop("artwork_profiles", {})

    game = None
    raw_game = current_game if isinstance(current_game, dict) else {}
    try:
        appid = int(raw_game.get("appid", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        appid = 0
    if appid > 0:
        game = {
            "appid": appid,
            "title": str(raw_game.get("title", "")),
            "display": settings.display_for(appid),
            "artwork": settings.artwork_for(appid),
        }

    timestamp = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "signalbar_version": version,
        "exported_at": timestamp,
        "configuration": {
            "global": values,
            "profiles": {
                "display_by_appid": display_profiles,
                "artwork_by_appid": artwork_profiles,
            },
            "current_game": game,
        },
    }


def write_configuration_export(settings, path: Path, version: str, current_game=None):
    """Atomically write the export and return UI-ready metadata."""
    target = Path(path)
    parent_existed = target.parent.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed and hasattr(os, "geteuid") and os.geteuid() == 0:
        owner = target.parent.parent.stat()
        os.chown(target.parent, owner.st_uid, owner.st_gid)
    payload = build_configuration_export(settings, version, current_game)
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            owner = target.parent.stat()
            os.chown(target, owner.st_uid, owner.st_gid)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return {"path": str(target), "exported_at": payload["exported_at"]}
