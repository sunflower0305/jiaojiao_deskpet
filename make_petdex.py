#!/usr/bin/env python3
"""Convert Jiaojiao clawd-on-desk APNGs into a Petdex/Codex pet package."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent
APNG_DIR = ROOT / "apng"
BUILD_DIR = ROOT / "petdex"
FRAMES_DIR = BUILD_DIR / "frames"
FINAL_DIR = BUILD_DIR / "final"
QA_DIR = BUILD_DIR / "qa"
PACKAGE_DIR = ROOT / "jiaojiao-petdex"
PACKAGE_ZIP = ROOT / "jiaojiao-petdex.zip"

COLUMNS = 8
ROWS = 9
CELL_W = 192
CELL_H = 208
ATLAS_W = COLUMNS * CELL_W
ATLAS_H = ROWS * CELL_H

ROW_SPECS = [
    {
        "state": "idle",
        "row": 0,
        "frames": 6,
        "source": "idle.png",
        "mirror": False,
    },
    {
        "state": "running-right",
        "row": 1,
        "frames": 8,
        "source": "dragging.png",
        "mirror": False,
    },
    {
        "state": "running-left",
        "row": 2,
        "frames": 8,
        "source": "dragging.png",
        "mirror": True,
    },
    {
        "state": "waving",
        "row": 3,
        "frames": 4,
        "source": "happy.png",
        "mirror": False,
    },
    {
        "state": "jumping",
        "row": 4,
        "frames": 5,
        "source": "happy.png",
        "mirror": False,
    },
    {
        "state": "failed",
        "row": 5,
        "frames": 8,
        "source": "error.png",
        "mirror": False,
    },
    {
        "state": "waiting",
        "row": 6,
        "frames": 6,
        "source": "notification.png",
        "mirror": False,
    },
    {
        "state": "running",
        "row": 7,
        "frames": 6,
        "source": "working.png",
        "mirror": False,
    },
    {
        "state": "review",
        "row": 8,
        "frames": 6,
        "source": "thinking.png",
        "mirror": False,
    },
]


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index] = 0
            data[index + 1] = 0
            data[index + 2] = 0
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def load_apng(path: Path) -> list[Image.Image]:
    with Image.open(path) as opened:
        frames = [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(opened)]
    if not frames:
        raise ValueError(f"{path} did not contain any frames")
    return frames


def select_frames(frames: list[Image.Image], count: int) -> list[Image.Image]:
    if len(frames) == count:
        return frames
    if len(frames) > count:
        if count == 1:
            return [frames[0]]
        indexes = [round(i * (len(frames) - 1) / (count - 1)) for i in range(count)]
        return [frames[index] for index in indexes]
    return [frames[round(i * (len(frames) - 1) / max(1, count - 1))] for i in range(count)]


def fit_frame(frame: Image.Image, mirror: bool) -> Image.Image:
    image = clear_transparent_rgb(frame)
    if mirror:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    scale = min(CELL_W / image.width, CELL_H / image.height)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)

    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    x = (CELL_W - resized.width) // 2
    y = CELL_H - resized.height
    cell.alpha_composite(resized, (x, y))
    return clear_transparent_rgb(cell)


def write_frames() -> dict[str, object]:
    manifest: dict[str, object] = {"rows": []}
    for spec in ROW_SPECS:
        state = str(spec["state"])
        source_path = APNG_DIR / str(spec["source"])
        frames = select_frames(load_apng(source_path), int(spec["frames"]))
        state_dir = FRAMES_DIR / state
        state_dir.mkdir(parents=True, exist_ok=True)

        row_info = {
            "state": state,
            "row": spec["row"],
            "frame_count": spec["frames"],
            "source": str(source_path.relative_to(ROOT)),
            "mirrored": spec["mirror"],
            "frames": [],
        }
        for index, frame in enumerate(frames):
            cell = fit_frame(frame, bool(spec["mirror"]))
            output = state_dir / f"{index:02d}.png"
            cell.save(output)
            row_info["frames"].append(str(output.relative_to(ROOT)))
        manifest["rows"].append(row_info)
    return manifest


def compose_atlas() -> Image.Image:
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    for spec in ROW_SPECS:
        state = str(spec["state"])
        row = int(spec["row"])
        frame_count = int(spec["frames"])
        for column in range(frame_count):
            with Image.open(FRAMES_DIR / state / f"{column:02d}.png") as opened:
                atlas.alpha_composite(opened.convert("RGBA"), (column * CELL_W, row * CELL_H))
    return clear_transparent_rgb(atlas)


def write_pet_json(path: Path) -> None:
    pet_json = {
        "id": "jiaojiao",
        "displayName": "角角",
        "description": "胖嘟嘟的蓝灰英短角角，爱吃爱睡爱哈气。",
        "spritesheetPath": "spritesheet.webp",
    }
    path.write_text(json.dumps(pet_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_package_zip() -> None:
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(PACKAGE_DIR / "pet.json", "pet.json")
        archive.write(PACKAGE_DIR / "spritesheet.webp", "spritesheet.webp")


def main() -> None:
    clean_dir(FRAMES_DIR)
    clean_dir(FINAL_DIR)
    clean_dir(QA_DIR)
    clean_dir(PACKAGE_DIR)

    manifest = write_frames()
    (BUILD_DIR / "frames-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    atlas = compose_atlas()
    atlas_png = FINAL_DIR / "spritesheet.png"
    atlas_webp = FINAL_DIR / "spritesheet.webp"
    atlas.save(atlas_png)
    atlas.save(atlas_webp, format="WEBP", lossless=True, quality=100, method=6, exact=True)

    shutil.copy2(atlas_webp, PACKAGE_DIR / "spritesheet.webp")
    write_pet_json(PACKAGE_DIR / "pet.json")
    write_package_zip()
    print(f"wrote {atlas_png}")
    print(f"wrote {atlas_webp}")
    print(f"wrote {PACKAGE_DIR / 'pet.json'}")
    print(f"wrote {PACKAGE_DIR / 'spritesheet.webp'}")
    print(f"wrote {PACKAGE_ZIP}")


if __name__ == "__main__":
    main()
