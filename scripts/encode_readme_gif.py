"""Encode captured browser frames as a compact, GitHub-compatible GIF."""

from pathlib import Path
import sys

from PIL import Image, ImageChops


def main() -> None:
    folder = Path(sys.argv[1])
    output = Path(sys.argv[2])
    duration = int(sys.argv[3])
    files = sorted(folder.glob("*.png"))
    if not files:
        raise SystemExit(f"No captured frames in {folder}")

    frames = []
    durations = []
    previous = None
    for file in files:
        with Image.open(file) as image:
            frame = image.convert("RGB")
            if frame.width > 500:
                frame.thumbnail((500, 700), Image.Resampling.LANCZOS)
            if previous is not None and ImageChops.difference(frame, previous).getbbox() is None:
                durations[-1] += duration
                continue
            frames.append(frame.quantize(colors=96, method=Image.Quantize.FASTOCTREE))
            durations.append(duration)
            previous = frame

    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    main()
