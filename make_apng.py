#!/usr/bin/env python3
"""
从精灵图切帧 → 去背景 → 裁到猫体 → 贴到统一 256×320 画布 → 输出 APNG。

用法:
  python make_apng.py

输入: ./source_sprites/<state>.png  （AI 生成的精灵图，横向拼帧，单行）
输出: ./apng/<state>.png            （APNG，透明背景，256×320）

如果设置了 THEME_ASSETS 环境变量，或系统存在对应路径，
会同时把结果复制到 clawd-on-desk 主题目录。
"""

import os
import shutil
from collections import deque
from PIL import Image
import numpy as np
from scipy.ndimage import label

_HERE = os.path.dirname(os.path.abspath(__file__))

SOURCE_SPRITES = os.path.join(_HERE, "source_sprites")

# 如需自动部署到 clawd-on-desk，把下面路径改成你自己的主题 assets 目录，
# 或设置环境变量 THEME_ASSETS=<path>。留空则跳过复制。
THEME_ASSETS = os.environ.get(
    "THEME_ASSETS",
    r"C:\Users\valeria_zhang\AppData\Roaming\clawd-on-desk\themes\jiaojiao\assets",
)

# 画布尺寸与 theme.json viewBox 一致
CANVAS_W = 256
CANVAS_H = 320
# 猫的底部落在画布的 y=305（= theme baselineY）
CAT_BASELINE_Y = 305
# 猫体宽度不超过画布的这个比例（留左右边距）
CAT_MAX_WIDTH_RATIO = 0.90

# 每种状态：精灵图文件名（在 source_sprites/ 下）、列数、动画参数
# rows=1 表示精灵图为单行，每帧占完整图高（AI 生成时猫体可能跨越半高边界）
STATES = {
    "idle": {
        "file": "idle.png",
        "cols": 4, "rows": 1,
        "n_frames": 4,
        "ms": 260, "pingpong": True,
    },
    "sleeping": {
        "file": "sleeping.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 350, "pingpong": True,
    },
    "thinking": {
        "file": "thinking.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 260, "pingpong": True,
    },
    "working": {
        "file": "working.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 180, "pingpong": False,
    },
    "happy": {
        "file": "happy.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 160, "pingpong": True,
    },
    "error": {
        "file": "error.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 140, "pingpong": True,
    },
    "notification": {
        "file": "notification.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 220, "pingpong": False,
    },
    "waking": {
        "file": "waking.png",
        "cols": 4, "rows": 1,
        "n_frames": 4,
        "ms": 280, "pingpong": True,
    },
}


def remove_bg(img, tolerance=35):
    """BFS 从四边出发去除背景色，自动从亮角采样背景颜色。"""
    rgb = np.array(img.convert("RGB")).astype(int)
    h, w = rgb.shape[:2]

    corners = [rgb[0, 0], rgb[0, w-1], rgb[h-1, 0], rgb[h-1, w-1]]
    light = [c for c in corners if float(np.mean(c)) > 150]
    bg = np.mean(light if light else corners, axis=0)

    diff = np.max(np.abs(rgb - bg), axis=2)
    is_bg = diff <= tolerance

    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    def seed(y, x):
        if is_bg[y, x] and not visited[y, x]:
            visited[y, x] = True
            q.append((y, x))

    for x in range(w):
        seed(0, x); seed(h-1, x)
    for y in range(h):
        seed(y, 0); seed(y, w-1)

    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < h and 0 <= nx < w:
                seed(ny, nx)

    rgba = np.array(img.convert("RGBA"))
    rgba[visited, 3] = 0
    return Image.fromarray(rgba)


def keep_largest_component(img):
    """去除 remove_bg 后残留的邻帧像素碎片，只保留面积最大的连通域。"""
    arr = np.array(img)
    mask = arr[:, :, 3] > 10
    labeled, n = label(mask)
    if n <= 1:
        return img
    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0  # ignore background label
    largest = sizes.argmax()
    keep = labeled == largest
    arr[~keep, 3] = 0
    return Image.fromarray(arr)


def crop_to_cat(img, margin=4):
    """裁切到不透明像素的边界框，加少量边距。"""
    arr = np.array(img)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 10)
    if len(ys) == 0:
        return img
    y1, y2 = max(0, int(ys.min()) - margin), min(img.height, int(ys.max()) + margin + 1)
    x1, x2 = max(0, int(xs.min()) - margin), min(img.width, int(xs.max()) + margin + 1)
    return img.crop((x1, y1, x2, y2))


def place_on_canvas(cat_img):
    """
    把猫缩放后贴到 CANVAS_W × CANVAS_H 的透明画布上，
    猫底部对齐 CAT_BASELINE_Y，水平居中。
    """
    max_w = int(CANVAS_W * CAT_MAX_WIDTH_RATIO)
    max_h = CAT_BASELINE_Y - 20  # 顶部至少留 20px

    cw, ch = cat_img.width, cat_img.height
    scale = min(max_w / cw, max_h / ch)
    nw = max(1, int(cw * scale))
    nh = max(1, int(ch * scale))

    resized = cat_img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    x = (CANVAS_W - nw) // 2
    y = CAT_BASELINE_Y - nh
    canvas.paste(resized, (x, y), resized)
    return canvas


def slice_sprite(path, cols, rows, n_frames):
    """切精灵图，返回前 n_frames 帧。"""
    sheet = Image.open(path).convert("RGBA")
    fw = sheet.width // cols
    fh = sheet.height // rows
    frames = []
    for r in range(rows):
        for c in range(cols):
            if len(frames) >= n_frames:
                break
            box = (c * fw, r * fh, (c+1) * fw, (r+1) * fh)
            frames.append(sheet.crop(box))
        if len(frames) >= n_frames:
            break
    return frames


def make_apng(name, cfg, out_dir):
    src = os.path.join(SOURCE_SPRITES, cfg["file"])
    if not os.path.exists(src):
        print(f"  [{name}] missing: {src}")
        return None

    raw = slice_sprite(src, cfg["cols"], cfg["rows"], cfg["n_frames"])
    print(f"  [{name}] {len(raw)} frames", end="")

    canvased = []
    for f in raw:
        clean = remove_bg(f)
        clean = keep_largest_component(clean)
        cropped = crop_to_cat(clean)
        canvased.append(place_on_canvas(cropped))

    if cfg.get("pingpong"):
        seq = canvased + canvased[-2:0:-1]
    else:
        seq = canvased

    dst = os.path.join(out_dir, f"{name}.png")
    seq[0].save(
        dst, format="PNG", save_all=True,
        append_images=seq[1:], loop=0, duration=cfg["ms"],
        disposal=1,
        blend=0,
    )
    print(f" -> {len(seq)} anim frames at {CANVAS_W}x{CANVAS_H}, {cfg['ms']}ms")
    return dst


def main():
    out_dir = os.path.join(_HERE, "apng")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output: {out_dir}\n")

    generated = []
    for name, cfg in STATES.items():
        result = make_apng(name, cfg, out_dir)
        if result:
            generated.append((name, result))

    if THEME_ASSETS and os.path.isdir(THEME_ASSETS):
        print(f"\nCopying to theme: {THEME_ASSETS}")
        for name, src in generated:
            dst = os.path.join(THEME_ASSETS, f"{name}.png")
            shutil.copy2(src, dst)
            print(f"  {name}.png")
        print("\nDone. Restart clawd-on-desk.")
    else:
        print(f"\nDone. (THEME_ASSETS 路径不存在，跳过复制)")
        print(f"如需部署，请手动将 apng/ 下的文件复制到 clawd-on-desk 主题目录，")
        print(f"或设置环境变量 THEME_ASSETS=<your-path> 后重新运行。")


if __name__ == "__main__":
    main()
