"""Create the installable Decky ZIP with a single SignalBar/ root."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "out" / f"SignalBar-v{PACKAGE['version']}.zip"
FILES = [
    "main.py", "plugin.json", "package.json", "LICENSE", "README.md",
    "ARCHITECTURE.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "dist/index.js",
    "assets/signalbar-decky-showcase-v3.png",
]


def iter_files():
    for relative in FILES:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"required release file is missing: {relative}")
        yield path
    for path in sorted((ROOT / "py_modules" / "signalbar").rglob("*.py")):
        yield path


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for path in iter_files():
            relative = path.relative_to(ROOT)
            archive.write(path, Path("SignalBar") / relative)
    print(OUTPUT)


if __name__ == "__main__":
    main()
