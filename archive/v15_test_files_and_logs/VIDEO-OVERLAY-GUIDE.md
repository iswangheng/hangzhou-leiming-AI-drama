# 视频包装花字叠加 - 快速使用指南

## 🎯 功能简介

在剪辑视频上自动叠加三行花字：
1. **"热门短剧"** - 大标题
2. **"《剧名》"** - 中标题
3. **免责声明** - 小标题（随机选择）

## ⚡ 快速开始

### 方法一：集成到渲染流程（推荐）

```bash
# 渲染时自动添加花字（随机样式）
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-overlay \
  --overlay-style gold_luxury
```

### 方法二：独立使用

```bash
# 单个视频
python scripts/understand/video_overlay/test_overlay.py \
  --single input.mp4 output.mp4 "项目名" "剧名"

# 批量处理
python scripts/understand/video_overlay/test_overlay.py \
  --batch ./input_dir ./output_dir "项目名" "剧名"
```

## 🎨 可用样式

| ID | 名称 | 适用场景 |
|----|------|----------|
| `gold_luxury` | 金色豪华 | 高端短剧 |
| `red_passion` | 红色激情 | 爱情/都市剧 |
| `blue_cool` | 蓝色冷艳 | 悬疑/都市剧 |
| `purple_mystery` | 紫色神秘 | 玄幻/古装剧 |
| `green_fresh` | 绿色清新 | 青春/校园剧 |
| `orange_vitality` | 橙色活力 | 喜剧/都市剧 |
| `pink_romantic` | 粉色浪漫 | 爱情剧 |
| `silver_elegant` | 银色优雅 | 商务/都市剧 |
| `cyan_tech` | 青色科技 | 现代/都市剧 |
| `retro_brown` | 复古棕色 | 年代/古装剧 |

### 查看所有样式

```bash
python scripts/understand/video_overlay/test_overlay.py --list-styles
```

## 🔧 配置选项

### 命令行参数

```bash
--add-overlay              # 启用花字叠加
--overlay-style <ID>      # 指定样式ID（可选，默认随机）
```

### Python API

```python
from scripts.understand.render_clips import ClipRenderer

renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/项目名",
    output_dir="clips/项目名",
    add_overlay=True,              # 启用花字叠加
    overlay_style_id="gold_luxury" # 可选：指定样式
)

output_paths = renderer.render_all_clips()
```

## 📋 核心特性

- ✅ **10种预制样式** - 覆盖各种短剧类型
- ✅ **项目级统一** - 同一项目自动使用相同样式
- ✅ **自动字体检测** - 支持系统默认中文字体
- ✅ **避免遮挡字幕** - 智能位置配置
- ✅ **批量处理** - 一键处理整个项目
- ✅ **高质量渲染** - 基于FFmpeg drawtext滤镜

## 🎯 使用场景

### 场景1：新项目渲染

```bash
# 完整流程：片尾检测 + 结尾视频 + 花字叠加
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-ending \
  --add-overlay
```

### 场景2：批量处理现有视频

```bash
python scripts/understand/video_overlay/test_overlay.py \
  --batch ./clips/项目名 ./clips/项目名_带花字 "项目名" "剧名"
```

### 场景3：指定特定样式

```bash
python -m scripts.understand.render_clips \
  data/hangzhou-leiming/analysis/项目名 \
  --add-overlay \
  --overlay-style red_passion  # 使用红色激情样式
```

## 🧪 测试验证

### 快速验证

```bash
# 运行快速测试（无需视频文件）
python scripts/understand/video_overlay/quick_test.py
```

预期输出：
```
✅ 通过: 模块导入
✅ 通过: 样式配置
✅ 通过: 免责声明
✅ 通过: 配置对象
✅ 通过: 渲染器创建
✅ 通过: FFmpeg命令

🎉 所有测试通过！
```

### 完整测试

```bash
# 查看帮助
python scripts/understand/video_overlay/test_overlay.py --help

# 列出样式
python scripts/understand/video_overlay/test_overlay.py --list-styles

# 测试单个视频（需要准备测试视频）
python scripts/understand/video_overlay/test_overlay.py \
  --single test.mp4 test_output.mp4 "测试项目" "测试剧名"
```

## 🔍 故障排除

### 问题1：中文显示为方框

**原因**：FFmpeg未找到中文字体

**解决**：
1. 检查FFmpeg是否启用了freetype：`ffmpeg -version | grep freetype`
2. 确认系统已安装中文字体
3. 手动指定字体路径

### 问题2：花字位置不理想

**解决**：修改样式配置（见 `overlay_styles.py`）

### 问题3：遮挡了原字幕

**解决**：增加字幕安全区配置

## 📁 文件结构

```
scripts/understand/video_overlay/
├── __init__.py           # 模块初始化
├── overlay_styles.py     # 样式配置（10种样式）
├── video_overlay.py      # 核心功能
├── test_overlay.py       # 测试脚本
├── quick_test.py         # 快速验证
└── README.md            # 详细文档

examples/
└── overlay_example.py    # 使用示例
```

## 🚀 下一步

1. 运行快速测试验证环境
2. 选择合适的样式
3. 在测试视频上验证效果
4. 应用到实际项目

## 📖 更多文档

详细文档：`scripts/understand/video_overlay/README.md`

---

**版本**：V1.0
**更新日期**：2025-03-05
**维护者**：杭州雷鸣AI短剧项目
