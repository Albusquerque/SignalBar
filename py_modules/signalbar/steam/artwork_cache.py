"""Read-only discovery of Steam's local Library artwork cache."""

from __future__ import annotations

import base64
import glob
import hashlib
import mimetypes
import os
from pathlib import Path

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
MAX_BYTES = 12 * 1024 * 1024
ARTWORK_SOURCES = {
    "hero": {
        "label": "Library Hero",
        "stems": ("library_hero", "library_hero_2x", "library_hero@2x"),
    },
    "header": {
        "label": "Library Header",
        "stems": ("library_header", "library_header_2x", "header"),
    },
    "capsule": {
        "label": "Library Capsule",
        "stems": ("library_capsule", "library_600x900", "library_600x900_2x"),
    },
}


def steam_roots():
    candidates = []
    for raw in (
        os.environ.get("SIGNALBAR_STEAM_ROOT"),
        os.environ.get("STEAM_COMPAT_CLIENT_INSTALL_PATH"),
        os.environ.get("STEAM_DIR"),
    ):
        if raw:
            candidates.append(Path(raw).expanduser())
    decky_home = os.environ.get("DECKY_USER_HOME")
    if decky_home:
        home = Path(decky_home)
        candidates.extend((home / ".local/share/Steam", home / ".steam/steam"))
    home = Path(os.path.expanduser("~"))
    candidates.extend((home / ".local/share/Steam", home / ".steam/steam"))
    for pattern in ("/home/*/.local/share/Steam", "/home/*/.steam/steam"):
        candidates.extend(Path(value) for value in glob.glob(pattern))

    found, seen = [], set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen and (candidate / "appcache/librarycache").is_dir():
            seen.add(key)
            found.append(candidate)
    return found


def artwork_candidates(cache: Path, appid: int, source="hero"):
    aid = str(int(appid))
    specification = ARTWORK_SOURCES.get(source, ARTWORK_SOURCES["hero"])
    candidates = []
    for extension in IMAGE_EXTENSIONS:
        for name in specification["stems"]:
            candidates.append(cache / aid / f"{name}.{extension}")
            candidates.extend(Path(value) for value in glob.glob(str(cache / aid / "*" / f"{name}.{extension}")))
            candidates.append(cache / f"{aid}_{name}.{extension}")
    return candidates


def find_library_artwork(appid: int, source="hero"):
    try:
        appid = int(appid)
    except (TypeError, ValueError):
        return None
    if appid <= 0:
        return None
    source = source if source in ARTWORK_SOURCES else "hero"
    for root in steam_roots():
        for candidate in artwork_candidates(root / "appcache/librarycache", appid, source):
            try:
                size = candidate.stat().st_size
                if candidate.is_file() and 0 < size <= MAX_BYTES:
                    return candidate
            except OSError:
                continue
    return None


def get_library_artwork(appid: int, source="hero"):
    source = source if source in ARTWORK_SOURCES else "hero"
    path = find_library_artwork(appid, source)
    if path is None:
        return {
            "found": False,
            "appid": int(appid or 0),
            "source": source,
            "source_label": ARTWORK_SOURCES[source]["label"],
        }
    try:
        raw = path.read_bytes()
        stat = path.stat()
    except OSError:
        return {
            "found": False,
            "appid": int(appid or 0),
            "source": source,
            "source_label": ARTWORK_SOURCES[source]["label"],
        }
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    fingerprint = hashlib.sha256(
        f"{stat.st_size}:{stat.st_mtime_ns}:".encode("ascii") + raw[:4096]
    ).hexdigest()[:20]
    return {
        "found": True,
        "appid": int(appid),
        "source": source,
        "source_label": ARTWORK_SOURCES[source]["label"],
        "mime": mime,
        "filename": path.name,
        "fingerprint": fingerprint,
        "data_uri": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}",
    }


def find_library_hero(appid: int):
    return find_library_artwork(appid, "hero")


def get_library_hero(appid: int):
    return get_library_artwork(appid, "hero")
