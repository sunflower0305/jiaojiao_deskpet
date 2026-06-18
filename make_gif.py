#!/usr/bin/env python3
"""
对静态桌宠精灵图生成呼吸/动态 GIF。
用法: python make_gif.py
输出: ./gifs/*.gif
"""

import os
import math
from PIL import Image

# 每个状态的动画参数
#   n_frames: 帧数（越多越流畅，文件越大）
#   duration: 每帧毫秒（越小越快）
#   bob:      上下浮动像素
#   scale:    呼吸缩放幅度（0.01 = 1%）
#   style:    动画风格
STATE_PARAMS = {
    "idle":         {"n": 24, "ms": 80,  "bob": 4, "scale": 0.012, "style": "breathe"},
    "sleeping":     {"n": 32, "ms": 110, "bob": 3, "scale": 0.007, "style": "breathe"},
    "thinking":     {"n": 24, "ms": 80,  "bob": 3, "scale": 0.010, "style": "sway"},
    "working":      {"n": 20, "ms": 55,  "bob": 5, "scale": 0.015, "style": "breathe"},
    "happy":        {"n": 20, "ms": 55,  "bob": 7, "scale": 0.018, "style": "bounce"},
    "error":        {"n": 18, "ms": 55,  "bob": 2, "scale": 0.008, "style": "shake"},
    "notification": {"n": 20, "ms": 65,  "bob": 4, "scale": 0.016, "style": "pulse"},
    "waking":       {"n": 28, "ms": 95,  "bob": 4, "scale": 0.010, "style": "breathe"},
}

DEFAULT = {"n": 24, "ms": 80, "bob": 4, "scale": 0.012, "style": "breathe"}


def build_frame(src: Image.Image, canvas_wh: tuple, dx: float, dy: float, sc: float) -> Image.Image:
    cw, ch = canvas_wh
    nw = max(1, int(src.width * sc))
    nh = max(1, int(src.height * sc))
    scaled = src.resize((nw, nh), Image.LANCZOS)
    x = (cw - nw) // 2 + int(dx)
    y = (ch - nh) // 2 + int(dy)
    canvas = Image.new("RGBA", canvas_wh, (0, 0, 0, 0))
    canvas.paste(scaled, (x, y), scaled)
    return canvas


def to_gif_frame(frame_rgba: Image.Image) -> Image.Image:
    """RGBA → 调色板模式（含透明），用于写入 GIF。"""
    # 白底合成用于色彩量化（透明区域量化后不影响颜色精度）
    bg = Image.new("RGB", frame_rgba.size, (255, 255, 255))
    bg.paste(frame_rgba, mask=frame_rgba.split()[3])
    p = bg.quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=0)

    # 第 255 号调色板槽留给透明色
    pal = p.getpalette()
    pal = pal[: 255 * 3] + [0, 0, 0]
    p.putpalette(pal)

    alpha = frame_rgba.getchannel("A")
    px = p.load()
    ax = alpha.load()
    for y in range(frame_rgba.height):
        for x in range(frame_rgba.width):
            if ax[x, y] < 128:
                px[x, y] = 255

    p.info["transparency"] = 255
    return p


def make_gif(src_path: str, dst_path: str, p: dict):
    img = Image.open(src_path).convert("RGBA")
    w, h = img.size
    pad = p["bob"] + 10
    canvas = (w, h + pad * 2)
    n, style, bob, scale_amp = p["n"], p["style"], p["bob"], p["scale"]

    frames = []
    for i in range(n):
        t = i / n
        phase = 2 * math.pi * t

        if style == "breathe":
            dy = -math.sin(phase) * bob
            dx = 0.0
            sc = 1.0 + math.sin(phase) * scale_amp

        elif style == "sway":
            # 轻微左右摇晃 + 小幅浮动
            dy = -abs(math.sin(phase)) * bob * 0.6
            dx = math.sin(phase) * 2.5
            sc = 1.0 + abs(math.sin(phase)) * scale_amp

        elif style == "bounce":
            # 开心蹦跳：离地后快速落回
            raw = abs(math.sin(phase))
            dy = -raw * bob
            sc = 1.0 + raw * scale_amp
            # 落地时轻微压扁
            if raw < 0.15:
                sc = 1.0 - scale_amp * 0.5
            dx = 0.0

        elif style == "shake":
            # 小幅颤抖
            dy = math.sin(phase * 2) * bob * 0.4
            dx = math.sin(phase * 3 + 0.5) * 2.5
            sc = 1.0

        elif style == "pulse":
            # 呼吸 + 轻微放大脉冲
            sc = 1.0 + math.sin(phase) * scale_amp * 1.4
            dy = -math.sin(phase) * bob * 0.8
            dx = 0.0

        else:
            dy = dx = 0.0
            sc = 1.0

        frames.append(build_frame(img, canvas, dx, dy, sc))

    gif_frames = [to_gif_frame(f) for f in frames]
    gif_frames[0].save(
        dst_path,
        save_all=True,
        append_images=gif_frames[1:],
        loop=0,
        duration=p["ms"],
        disposal=2,
        optimize=False,
    )
    print(f"  {os.path.basename(dst_path)}: {n} 帧 × {p['ms']} ms  [{style}]")


def main():
    sprite_dir = os.path.join(os.path.dirname(__file__), "sprites")
    out_dir = os.path.join(os.path.dirname(__file__), "gifs")
    os.makedirs(out_dir, exist_ok=True)

    pngs = [f for f in os.listdir(sprite_dir) if f.lower().endswith(".png")]
    if not pngs:
        print("sprites/ 目录下没有找到 PNG 文件")
        return

    print(f"找到 {len(pngs)} 张精灵图，开始生成…\n")
    for fname in sorted(pngs):
        name = os.path.splitext(fname)[0]
        params = STATE_PARAMS.get(name, DEFAULT)
        src = os.path.join(sprite_dir, fname)
        dst = os.path.join(out_dir, name + ".gif")
        print(f"处理 {fname}…", end="  ")
        make_gif(src, dst, params)

    print(f"\n完成！GIF 保存在 {out_dir}")


if __name__ == "__main__":
    main()
