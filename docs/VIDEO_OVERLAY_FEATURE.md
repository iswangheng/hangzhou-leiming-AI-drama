# 视频花字叠加功能使用指南 (V15.6)

## 功能概述

视频花字叠加功能（V15.6）为渲染的剪辑素材自动添加三行文本，提升视频的品牌识别度和观看体验。

### 核心特性

- ✅ **完全自动化**：渲染时自动应用，无需手动编辑
- ✅ **项目级统一**：同一项目内所有剪辑使用相同样式
- ✅ **智能布局**：避免遮挡原字幕，优化视觉层次
- ✅ **位置可配置**：支持左上角和右上角位置
- ✅ **动态缩放**：字体大小根据视频分辨率自适应
- ✅ **免责声明扩充**：8种文案随机选择

## 花字内容说明

### 1. 热门短剧（V4.9倾斜角标）

**文本内容**：`热门短剧`

**技术实现**：
- 模块：tilted_label.py（V4.9）
- 样式：45度倾斜，红色条幅（95%不透明度），白色文字
- 性能：PNG预渲染，性能提升100倍+

**位置**：
- 可配置：top-left（左上角）或 top-right（右上角）
- 默认：右上角
- 画布中心：距离角落corner_offset像素

**字体大小**（动态缩放）：
- 360p：22px
- 1080p：68px
- 其他分辨率按比例缩放

**V4.9关键修复**：
- 修复投影计算错误（使用canvas_half=200px）
- 解决360p"过于靠中间"的问题
- 所有分辨率视觉比例一致

### 2. 《剧名》

**文本内容**：`《{剧名}》`（自动替换为实际剧名）

**样式配置**：
- 字体大小：动态缩放（360p: 18px → 1080p: 52px）
- 字体颜色：白色 (#FFFFFF) 或淡紫色 (#E6E6FA) **随机选择**
- 描边：黑色 (#000000)，宽度1.0（细描边）
- 阴影：黑色，偏移(1,1)

**位置**：
- 水平：居中 `x="(w-tw)/2"`
- 垂直：动态计算（距离底部安全区）

**显示时长**：全程显示

**设计理念**：朴素清晰，细描边让字笔画间的透明区域透出视频内容，营造镂空效果

### 3. 免责声明

**文本内容**（8种随机选择）：
- `本故事纯属虚构 请勿模仿`
- `本剧情纯属虚构 如有雷同 纯属巧合`
- `影视效果无不良引导 请勿模仿`
- `纯属虚构 请勿模仿`
- `剧情纯属虚构  无不良导向`
- `本剧内容虚构 仅供娱乐参考`
- `故事情节虚构 切勿当真模仿`
- `纯属艺术创作 无不良导向`

**样式配置**：
- 字体大小：动态缩放（360p: 16px → 1080p: 46px）
- 字体颜色：白色或浅色系
- 描边：黑色，宽度1.0
- 阴影：黑色，偏移(1,1)

**位置**：
- 水平：居中 `x="(w-tw)/2"`
- 垂直：动态计算（剧名下方）

**显示时长**：全程显示

**V15.6改进**：
- 文案从4条扩充到8条
- 添加空格提高可读性
- 基于现有文案风格裂变生成

## 预制样式列表

### 1. 金色豪华 (gold_luxury)
- **主题**：金色渐变、高端大气
- **适用**：古装、玄幻、权谋剧
- **配色**：金黄色+橙色描边

### 2. 红色激情 (red_passion)
- **主题**：鲜红色调、醒目突出
- **适用**：爱情、都市、情感剧
- **配色**：番茄红+深棕色描边

### 3. 蓝色冷艳 (blue_cool)
- **主题**：蓝色系、现代科技感
- **适用**：悬疑、刑侦、都市剧
- **配色**：深天蓝+深蓝色描边

### 4. 紫色神秘 (purple_mystery)
- **主题**：紫色调、神秘玄幻
- **适用**：玄幻、古装、仙侠剧
- **配色**：紫罗兰+靛青描边

### 5. 绿色清新 (green_fresh)
- **主题**：绿色系、清新自然
- **适用**：青春、校园、生活剧
- **配色**：酸橙绿+深绿色描边

### 6. 橙色活力 (orange_vitality)
- **主题**：橙色调、活力十足
- **适用**：喜剧、都市、轻喜剧
- **配色**：金色+橙色描边

### 7. 粉色浪漫 (pink_romantic)
- **主题**：粉色调、浪漫温馨
- **适用**：爱情、偶像、甜宠剧
- **配色**：深粉色+中紫红色描边

### 8. 银色优雅 (silver_elegant)
- **主题**：银色调、优雅大气
- **适用**：商务、都市、职场剧
- **配色**：浅灰色+灰色描边

### 9. 青色科技 (cyan_tech)
- **主题**：青色调、科技感强
- **适用**：现代、科技、都市剧
- **配色**：浅海绿+青色描边

### 10. 复古棕色 (retro_brown)
- **主题**：棕色调、复古怀旧
- **适用**：年代、历史、古装剧
- **配色**：秘鲁色+赭色描边

## 使用方法

### 基本用法

```bash
# 启用花字叠加（默认参数）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay
```

### 高级用法

```bash
# 指定特定样式
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-style gold_luxury

# 自定义免责声明
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-disclaimer "本故事纯属虚构"

# 使用自定义字体
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-font /path/to/custom/font.ttf
```

### 组合使用

```bash
# 花字叠加 + 结尾视频
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --add-ending

# 花字叠加 + 结尾视频 + 强制重检片尾
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --add-ending \
    --force-detect
```

## 输出文件命名

添加花字叠加后，输出文件名会添加 `_带花字` 标记：

```
原文件：1_去除片尾_带结尾.mp4
带花字：1_带花字.mp4

输出目录：clips/项目名_去除片尾_保守版_带花字/
```

## 样式缓存机制

### 缓存位置
```
data/hangzhou-leiming/.overlay_style_cache/
└── style_{project_hash}.json
```

### 缓存逻辑
1. **首次运行**：随机选择样式并缓存
2. **后续运行**：从缓存读取样式，确保项目内统一
3. **指定样式**：如果使用 `--overlay-style` 参数，优先使用指定样式

### 清除缓存
```bash
# 删除项目样式缓存
rm .overlay_style_cache/style_{project_hash}.json

# 删除所有样式缓存
rm -rf .overlay_style_cache/
```

## 技术实现

### FFmpeg drawtext滤镜

花字叠加使用FFmpeg的drawtext滤镜实现，关键参数：

```bash
# 热门短剧左上角滤镜示例（0-10秒、40-50秒...显示）
drawtext=text='热门短剧':fontsize=24:fontcolor=#FFD700:\
x='20':y='50':borderw=2.0:bordercolor=#FFA500:\
shadowx=2:shadowy=2:shadowcolor=#000000:\
enable='between(t,0,10)+between(t,40,50)+between(t,80,90)'

# 热门短剧右上角滤镜示例（20-30秒、60-70秒...显示）
drawtext=text='热门短剧':fontsize=24:fontcolor=#FFD700:\
x='(w-tw)-20':y='50':borderw=2.0:bordercolor=#FFA500:\
shadowx=2:shadowy=2:shadowcolor=#000000:\
enable='between(t,20,30)+between(t,60,70)+between(t,100,110)'

# 剧名滤镜示例
drawtext=text='《剧名》':fontsize=18:fontcolor=#FFFFFF:\
x='(w-tw)/2':y='h-90':borderw=1.0:bordercolor=#000000:\
shadowx=1:shadowy=1:shadowcolor=#000000

# 免责声明滤镜示例
drawtext=text='免责声明':fontsize=12:fontcolor=#FFFF00:\
x='(w-tw)/2':y='h-50':borderw=2.0:bordercolor=#000000:\
shadowx=1:shadowy=1:shadowcolor=#000000
```

### 坐标系统

FFmpeg使用左上角为原点(0,0)，Y轴向下递增：
- 视频尺寸：360x640（竖屏）
- `x="(w-tw)/2"`：水平居中
- `y="h-100"`：距离底部100像素（Y坐标540）

### 字体检测

自动检测系统字体，优先级：
1. 用户自定义字体（`--overlay-font`参数）
2. 样式中指定的字体
3. 系统中文字体：
   - macOS: Songti.ttc、STHeiti.ttc、PingFang.ttc
   - Linux: wqy-zenhei.ttc、DroidSansFallbackFull.ttf
   - Windows: msyh.ttc、simhei.ttf

## 常见问题

### Q1: 如何修改样式颜色？
A: 编辑 `scripts/understand/video_overlay/overlay_styles.py` 文件中对应样式的颜色配置。

### Q2: 如何调整花字位置？
A: 修改 `overlay_styles.py` 中的 `x` 和 `y` 参数：
- `y="h-100"` 表示距离底部100像素
- `y="50"` 表示距离顶部50像素

### Q3: 为什么中文显示为方框？
A: 字体文件未正确加载。解决方法：
1. 检查系统是否安装中文字体
2. 使用 `--overlay-font` 参数指定字体路径
3. 确保 `scripts/understand/video_overlay/video_overlay.py` 的字体检测路径正确

### Q4: 如何添加新的预制样式？
A: 在 `overlay_styles.py` 中添加新的样式函数：
```python
def _create_style_11_custom() -> OverlayStyle:
    """样式11：自定义样式"""
    return OverlayStyle(
        id="custom_style",
        name="自定义样式",
        description="样式描述",
        # ... 配置参数
    )
```

然后注册到 `STYLE_REGISTRY`。

### Q5: 花字遮挡了原字幕怎么办？
A: 调整 `OverlayConfig` 中的 `subtitle_safe_zone` 参数，增大字幕安全区。

## 性能影响

- **处理速度**：添加花字叠加增加约5-10%的处理时间
- **文件大小**：输出文件大小基本不变（FFmpeg重新编码）
- **质量影响**：使用 `-c:a copy` 保留原始音频质量，视频使用默认编码器

## 版本历史

- **V15.0** (2026-03-05)：初始版本
  - 实现10种预制样式
  - 项目级样式统一缓存
  - 随机化位置和显示时长
  - 中文字体自动检测

## 相关文档

- [README.md](../README.md) - 项目主文档
- [CLAUDE.md](../CLAUDE.md) - 开发指南
- [ENDING_CLIP_FEATURE.md](./ENDING_CLIP_FEATURE.md) - 结尾视频功能
