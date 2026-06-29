# 如何制作角角的 GIF 动图

> 角角是跑在 clawd-on-desk 上的桌宠，所有动画素材都是用 Python 脚本从 AI 生成的精灵图中自动加工出来的。这篇教程记录整个制作流程。

---

## 整体思路

制作角角的 GIF 分两条路：

| 路线 | 输入 | 输出 | 适用场景 |
|------|------|------|----------|
| **精灵图 → APNG**（`make_apng.py`） | AI 生成的多帧横向拼图 | 透明背景 APNG | 桌宠内嵌动画 |
| **静态图 → GIF**（`make_gif.py`） | 单帧 PNG | 带呼吸/抖动的 GIF | 公众号配图、预览 |

两条路都依赖 Python + Pillow，产出可以直接用在桌宠或发公众号。

---

## 环境准备

```bash
pip install pillow numpy scipy
```

---

## 路线一：精灵图 → APNG（桌宠用）

### 第一步：准备精灵图

让 AI（MidJourney / DALL·E / ComfyUI）生成**横向单行排列**的多帧精灵图，放到 `source_sprites/` 目录下，文件按状态命名：

```
source_sprites/
├── idle.png        # 4 帧，待机
├── sleeping.png    # 8 帧，睡觉
├── working.png     # 8 帧，工作
├── happy.png       # 8 帧，开心
├── error.png       # 8 帧，报错
└── ...
```

精灵图长这样——每帧横向拼排，猫体在同一行：

```
[帧1][帧2][帧3][帧4][帧5][帧6][帧7][帧8]
```

### 第二步：配置状态参数

在 `make_apng.py` 的 `STATES` 字典里按需调整每个状态：

```python
STATES = {
    "idle": {
        "file": "idle.png",
        "cols": 4,          # 精灵图列数（帧数）
        "rows": 1,          # 行数（单行写 1）
        "n_frames": 4,      # 实际使用的帧数
        "ms": 260,          # 每帧毫秒
        "pingpong": True,   # True = 正放+倒放，False = 正循环
    },
    "working": {
        "file": "working.png",
        "cols": 8, "rows": 1,
        "n_frames": 8,
        "ms": 180, "pingpong": False,  # 工作状态不倒放，快速循环
    },
    # ...
}
```

**pingpong 说明**：`True` 时输出帧序列为 1→2→3→4→3→2，适合呼吸类动画；`False` 时是 1→2→3→4→1，适合有方向的动作。

### 第三步：运行脚本

```bash
python make_apng.py
```

脚本自动完成 4 步处理：

```
精灵图切帧
    ↓
BFS 去背景（从四角采样背景色，容差 35）
    ↓
保留最大连通域（去掉邻帧残留碎片）
    ↓
裁到猫体 → 缩放贴到 256×320 画布（猫底部对齐 y=305）
    ↓
输出 apng/<state>.png
```

如果设置了 `THEME_ASSETS` 环境变量，脚本还会自动把 APNG 复制到 clawd-on-desk 的主题目录：

```bash
THEME_ASSETS="C:\...\clawd-on-desk\themes\jiaojiao\assets" python make_apng.py
```

---

## 路线二：静态图 → 呼吸 GIF（公众号用）

这条路适合把单帧的角角静态图做成有动感的 GIF。

### 第一步：准备静态图

把各状态的单帧 PNG 放到 `sprites/` 目录：

```
sprites/
├── idle.png
├── sleeping.png
├── working.png
└── ...
```

### 第二步：了解 5 种动画风格

脚本内置 5 种风格，根据角角的情绪自动匹配：

| 风格 | 效果 | 适用状态 |
|------|------|----------|
| `breathe` | 正弦上下浮动 + 轻微缩放 | idle、sleeping、working |
| `sway` | 左右摇晃 + 小幅浮动 | thinking |
| `bounce` | 离地蹦跳、落地轻微压扁 | happy |
| `shake` | 小幅颤抖（横向为主） | error |
| `pulse` | 呼吸 + 脉冲放大 | notification |

### 第三步：调整动画参数（可选）

在 `STATE_PARAMS` 里按需修改：

```python
STATE_PARAMS = {
    "idle":     {"n": 24, "ms": 80,  "bob": 4, "scale": 0.012, "style": "breathe"},
    "happy":    {"n": 20, "ms": 55,  "bob": 7, "scale": 0.018, "style": "bounce"},
    "error":    {"n": 18, "ms": 55,  "bob": 2, "scale": 0.008, "style": "shake"},
}
```

参数含义：
- `n`：帧数（越多越流畅，文件越大）
- `ms`：每帧毫秒（越小越快）
- `bob`：上下浮动像素（越大动作越大）
- `scale`：呼吸缩放幅度（0.01 = 1%）

### 第四步：运行脚本

```bash
python make_gif.py
```

输出在 `gifs/` 目录，每个状态一个 GIF：

```
gifs/
├── idle.gif
├── sleeping.gif
├── happy.gif
└── ...
```

GIF 背景透明，可以直接插入公众号文章（公众号会自动处理透明背景，显示为白底）。

---

## 目录结构总览

```
角角桌宠/
├── source_sprites/     # 输入：AI 生成的精灵图（多帧拼排）
├── sprites/            # 输入：静态单帧图
├── apng/               # 输出：APNG（桌宠嵌入用）
├── gifs/               # 输出：GIF（公众号、预览用）
├── make_apng.py        # 精灵图 → APNG
├── make_gif.py         # 静态图 → 呼吸 GIF
└── theme.json          # clawd-on-desk 主题配置
```

---

## 几个踩坑经验

**去背景容差要调**：AI 生成的精灵图背景色不总是纯白，`tolerance=35` 适合大多数情况，如果切出来边缘有白边或猫体被切掉，可以把这个值调小（15~20）。

**连通域过滤救了很多次**：AI 生成的相邻帧之间常常有半透明残影，`keep_largest_component` 用 scipy 的连通域标记自动去掉，省去手动 PS。

**pingpong vs 正循环**：带方向的动作（eating、working、notification）不能倒放，会穿帮；呼吸类（idle、sleeping）用 pingpong 更自然。

**GIF 透明的坑**：GIF 格式的透明是单色透明（palette transparency），不支持半透明。脚本里用第 255 号调色板槽作为透明色，alpha < 128 的像素统一设成透明，边缘会有轻微锯齿，这是 GIF 格式的固有限制。

---

## 完整流程一句话

> AI 生成精灵图 → `make_apng.py` 自动切帧去背景 → 贴 256×320 画布 → APNG 给桌宠用；单帧静态图 → `make_gif.py` 加呼吸动画 → GIF 给公众号用。
