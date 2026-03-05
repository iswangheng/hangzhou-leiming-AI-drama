# 视频包装花字叠加模块

## 功能概述

视频包装花字叠加模块为杭州雷鸣AI短剧项目提供了在最终渲染的剪辑视频上叠加三行花字的功能：

1. **"热门短剧"** - 字体最大，醒目突出
2. **"《剧名》"** - 字体中等，从项目元数据读取
3. **免责声明** - 字体最小，随机预制文案

### 核心特性

- ✅ **10种预制样式**：金色豪华、红色激情、蓝色冷艳等
- ✅ **项目级样式统一**：同一项目自动使用相同样式
- ✅ **智能字体检测**：自动查找系统中文字体
- ✅ **避免遮挡字幕**：位置配置灵活，支持字幕安全区
- ✅ **高质量渲染**：基于FFmpeg drawtext滤镜
- ✅ **批量处理支持**：一键处理整个项目的所有剪辑

## 目录结构

```
scripts/understand/video_overlay/
├── __init__.py              # 模块初始化
├── overlay_styles.py        # 样式配置定义（10种预制样式）
├── video_overlay.py         # 核心功能实现
├── test_overlay.py          # 测试脚本
└── README.md               # 本文档
```

## 快速开始

### 1. 列出所有可用样式

```bash
python scripts/understand/video_overlay/test_overlay.py --list-styles
```

输出示例：
```
📋 可用花字样式列表
======================================================================

1. 金色豪华 (ID: gold_luxury)
   描述: 金色渐变、粗体描边，适合高端短剧

2. 红色激情 (ID: red_passion)
   描述: 鲜红色调、醒目突出，适合爱情/都市剧

...（共10种样式）
```

### 2. 测试单个视频

```bash
python scripts/understand/video_overlay/test_overlay.py \
  --single input.mp4 output.mp4 "多子多福，开局就送绝美老婆" "多子多福"
```

### 3. 指定样式

```bash
python scripts/understand/video_overlay/test_overlay.py \
  --single input.mp4 output.mp4 "项目名" "剧名" \
  --style gold_luxury
```

### 4. 批量处理

```bash
python scripts/understand/video_overlay/test_overlay.py \
  --batch ./clips/input ./clips/output "项目名" "剧名"
```

## 集成到渲染流程

### 方式一：命令行参数

在 `render_clips.py` 中添加 `--add-overlay` 参数：

```bash
# 基础使用（随机样式）
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-overlay \
  --overlay-style gold_luxury

# 完整功能（片尾检测 + 结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-ending \
  --add-overlay
```

### 方式二：Python API

```python
from scripts.understand.render_clips import ClipRenderer

renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/项目名",
    output_dir="clips/项目名",
    add_overlay=True,           # 启用花字叠加
    overlay_style_id="gold_luxury"  # 可选：指定样式
)

output_paths = renderer.render_all_clips()
```

## 样式说明

### 可用样式列表

| 样式ID | 名称 | 描述 | 适用场景 |
|--------|------|------|----------|
| `gold_luxury` | 金色豪华 | 金色渐变、粗体描边 | 高端短剧 |
| `red_passion` | 红色激情 | 鲜红色调、醒目突出 | 爱情/都市剧 |
| `blue_cool` | 蓝色冷艳 | 蓝色系、现代感强 | 悬疑/都市剧 |
| `purple_mystery` | 紫色神秘 | 紫色调、神秘感强 | 玄幻/古装剧 |
| `green_fresh` | 绿色清新 | 绿色系、清新自然 | 青春/校园剧 |
| `orange_vitality` | 橙色活力 | 橙色调、活力十足 | 喜剧/都市剧 |
| `pink_romantic` | 粉色浪漫 | 粉色调、浪漫温馨 | 爱情剧 |
| `silver_elegant` | 银色优雅 | 银色调、优雅大气 | 商务/都市剧 |
| `cyan_tech` | 青色科技 | 青色调、科技感强 | 现代/都市剧 |
| `retro_brown` | 复古棕色 | 棕色调、复古怀旧 | 年代/古装剧 |

### 样式配置

每个样式包含三个文本层的配置：

```python
OverlayStyle(
    hot_drama=TextLayer(
        text="热门短剧",
        font_size=64,           # 字体大小
        font_color="#FFD700",   # 字体颜色
        border_color="#8B4513", # 描边颜色
        border_width=4.0,       # 描边宽度
        x="(w-tw)-30",          # X坐标（右上角）
        y="50"                  # Y坐标
    ),
    drama_title=TextLayer(...),
    disclaimer=TextLayer(...)
)
```

## 免责声明文案库

默认免责声明列表（随机选择）：

1. "本故事纯属虚构请勿模仿"
2. "本剧情纯属虚构如有雷同纯属巧合"
3. "影视效果无不良引导请勿模仿"
4. "纯属虚构请勿模仿"

### 自定义免责声明

在 `overlay_styles.py` 中修改 `DISCLAIMER_TEXTS` 列表：

```python
DISCLAIMER_TEXTS = [
    "自定义免责声明1",
    "自定义免责声明2",
    # ... 添加更多
]
```

## 技术实现

### 核心技术

- **FFmpeg drawtext滤镜**：用于文本叠加
- **字体自动检测**：支持macOS/Linux/Windows系统中文字体
- **样式缓存机制**：项目级样式统一，避免重复随机

### 处理流程

```
输入视频
    ↓
检查样式缓存
    ↓
选择样式（缓存/随机/指定）
    ↓
构建FFmpeg drawtext滤镜
    ↓
执行视频处理
    ↓
输出视频（带花字）
```

### FFmpeg滤镜示例

```bash
ffmpeg -i input.mp4 \
  -vf "drawtext=text='热门短剧':fontsize=64:fontcolor=#FFD700:x=(w-tw)-30:y=50:borderw=4:bordercolor=#8B4513" \
  -c:a copy \
  output.mp4
```

## 高级配置

### 字体配置

系统会自动查找以下字体（按优先级）：

**macOS:**
- /System/Library/Fonts/PingFang.ttc
- /System/Library/Fonts/STHeiti Light.ttc

**Linux:**
- /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
- /usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf

**Windows:**
- C:/Windows/Fonts/msyh.ttc
- C:/Windows/Fonts/simhei.ttf

#### 自定义字体

```python
from scripts.understand.video_overlay.video_overlay import apply_overlay_to_video

apply_overlay_to_video(
    input_video="input.mp4",
    output_video="output.mp4",
    project_name="项目名",
    font_path="/path/to/your/font.ttf"  # 自定义字体
)
```

### 位置配置

#### 坐标表达式

- `(w-tw)/2` - 水平居中
- `30` - 距左边30像素
- `(w-tw)-30` - 距右边30像素
- `h-60` - 距底部60像素

#### 字幕安全区

默认字幕安全区：150像素（底部）

修改配置：

```python
config = OverlayConfig(
    enabled=True,
    project_name="项目名",
    subtitle_safe_zone=200  # 增加到200像素
)
```

### 自定义样式

在 `overlay_styles.py` 中添加新样式：

```python
def _create_style_custom() -> OverlayStyle:
    """自定义样式"""
    return OverlayStyle(
        id="custom_style",
        name="自定义样式",
        description="描述",

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=70,
            font_color="#YOUR_COLOR",
            # ... 更多配置
        ),
        # ... 其他文本层
    )

# 注册到STYLE_REGISTRY
STYLE_REGISTRY["custom_style"] = _create_style_custom()
```

## 故障排除

### 问题1：中文显示为方框

**原因**：FFmpeg未找到中文字体

**解决方案**：

1. 确认系统已安装中文字体
2. 检查FFmpeg编译时是否启用了 `--enable-libfreetype`
3. 手动指定字体路径：

```bash
ffmpeg -version | grep freetype
```

### 问题2：花字位置不理想

**解决方案**：调整样式配置中的 `x` 和 `y` 参数

```python
# 调整"热门短剧"位置
hot_drama=TextLayer(
    text="热门短剧",
    x="30",              # 改为左上角
    y="50"               # 调整Y坐标
)
```

### 问题3：遮挡了原字幕

**解决方案**：增加 `subtitle_safe_zone` 参数

```python
config = OverlayConfig(
    enabled=True,
    subtitle_safe_zone=200  # 增加底部安全区
)
```

## 性能优化

### 批量处理建议

1. **项目级样式统一**：同一项目使用相同样式，减少样式选择时间
2. **临时文件管理**：处理完成后自动删除临时文件
3. **FFmpeg预设**：使用 `-preset fast` 平衡速度和质量

### 处理速度参考

- 1080p视频：约 2-5秒/分钟视频
- 主要耗时在视频编码（非花字叠加本身）

## 测试

### 运行测试套件

```bash
# 列出样式
python scripts/understand/video_overlay/test_overlay.py --list-styles

# 测试免责声明
python scripts/understand/video_overlay/test_overlay.py --disclaimers

# 单个视频测试
python scripts/understand/video_overlay/test_overlay.py \
  --single test_input.mp4 test_output.mp4 "测试项目" "测试剧名"

# 批量测试
python scripts/understand/video_overlay/test_overlay.py \
  --batch ./test_input ./test_output "测试项目"
```

## 版本历史

### V1.0 (2025-03-05)
- ✅ 初始版本
- ✅ 10种预制样式
- ✅ 项目级样式统一
- ✅ 自动字体检测
- ✅ 集成到render_clips.py

## 贡献

欢迎提交新样式和改进建议！

### 添加新样式流程

1. 在 `overlay_styles.py` 中创建样式函数
2. 添加到 `STYLE_REGISTRY`
3. 测试样式效果
4. 更新文档

## 许可证

杭州雷鸣AI短剧项目内部使用

## 联系方式

如有问题或建议，请联系项目维护者。
