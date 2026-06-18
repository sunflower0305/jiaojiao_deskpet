# 角角桌宠素材包

[clawd-on-desk](https://github.com/KakaJi/clawd-on-desk) jiaojiao 主题的动图素材，包含 8 种状态的 APNG 动图和静态 GIF。

## 目录结构

```
角角桌宠/
  source_sprites/   # AI 生成的原始精灵图（横向拼帧，单行）
  sprites/          # 静态单帧图（供 make_gif.py 使用）
  apng/             # 输出：APNG 动图（clawd-on-desk 用）
  gifs/             # 输出：GIF 动图（通用预览）
  theme.json        # clawd-on-desk 主题配置
  make_apng.py      # 精灵图 → APNG 脚本
  make_gif.py       # 静态图 → GIF 脚本
  requirements.txt
```

## 快速使用（安装到 clawd-on-desk）

1. 在 clawd-on-desk 主题目录下新建文件夹 `jiaojiao/`
   - Windows: `%APPDATA%\clawd-on-desk\themes\jiaojiao\`
   - macOS: `~/Library/Application Support/clawd-on-desk/themes/jiaojiao/`
2. 将 `theme.json` 复制到该目录
3. 新建子目录 `assets/`，将 `apng/` 下所有 `.png` 复制进去
4. 重启 clawd-on-desk，在设置里切换到「角角」主题

## 重新生成动图

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 生成 APNG（clawd-on-desk 用）

```bash
python make_apng.py
```

输出到 `apng/`。如需自动部署到 clawd-on-desk，设置环境变量：

```bash
# Windows
set THEME_ASSETS=C:\Users\<你的用户名>\AppData\Roaming\clawd-on-desk\themes\jiaojiao\assets
python make_apng.py

# macOS / Linux
THEME_ASSETS=/path/to/themes/jiaojiao/assets python make_apng.py
```

### 3. 生成 GIF（通用预览）

```bash
python make_gif.py
```

输入 `sprites/` 下的静态 PNG，输出到 `gifs/`。

---

## 如何生成新的精灵图

精灵图通过 ZenMux 的 `gpt-image-2` 模型批量生成，每张图为**横向拼帧的单行精灵图**。

### 生成要求

向 AI 描述角色和动作，并明确以下参数：

| 参数 | idle | 其他状态 |
|------|------|---------|
| 列数（帧数）| 4 | 8 |
| 图像尺寸 | 1024×640 | 2048×768 |
| 每帧尺寸 | 256×640 | 256×768 |
| 排列方式 | 单行横向 | 单行横向 |

示例 prompt：

> 生成一张像素风格的英国短毛猫精灵图，横向单行排列 8 帧，图像总尺寸 2048×768，每帧 256×768，猫咪处于「开心」状态，动作依次为：坐姿微摇→尾巴上翘→耳朵抖动→眼睛弯曲，循环 2 遍。白色或浅灰色纯色背景。

### 生成后注意事项

**⚠️ 必须遵守，否则动图会有问题：**

1. **单行排列，不要分行**
   脚本读取时 `rows=1`，整张图高作为单帧高。如果 AI 生成了多行（如 4×2 网格），猫体会被从中间切断，只显示上半身。

2. **背景用纯白或浅灰，不要渐变/纹理**
   脚本用 BFS 从四角采样背景色并去除。复杂背景会导致去背失败，猫体周围留有杂色。

3. **猫体不要贴近帧的左右边缘**
   相邻帧的猫体之间需要有明显间隙（至少 10px）。帧边缘有猫体像素时，去背后会残留邻帧的猫身碎片（脚本会自动保留最大连通域来过滤，但源图间距太小时可能失效）。

4. **猫体不要太小**
   单帧里猫体最好占到帧宽的 60% 以上，否则缩放到 256×320 画布后猫会显得很小。

5. **每帧猫的姿势变化要连贯**
   pingpong 动画会把帧序列做正反播放，所以首帧和末帧应该是同一个「静止」姿势，中间帧是动作高潮。

### 生成后替换精灵图

把新图命名为对应状态名（如 `happy.png`），放到 `source_sprites/` 目录，然后重新运行：

```bash
python make_apng.py
```

如果新图的帧数与原来不同，同步修改 `make_apng.py` 里对应状态的 `cols` 和 `n_frames`。

---

## 状态说明

| 状态 | 含义 | 帧数 | 播放模式 |
|------|------|------|---------|
| idle | 空闲/待机 | 4 | pingpong |
| sleeping | 睡眠 | 8 | pingpong |
| thinking | 思考中 | 8 | pingpong |
| working | 工作中 | 8 | 循环 |
| happy | 开心/完成 | 8 | pingpong |
| error | 报错 | 8 | pingpong |
| notification | 通知 | 8 | 循环 |
| waking | 唤醒 | 8 | 循环 |
