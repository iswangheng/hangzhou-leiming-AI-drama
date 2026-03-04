# 视频剪辑渲染模块使用指南

## 概述

`render_clips.py` 模块实现了基于FFmpeg的视频剪辑渲染功能，可以将 `result.json` 中的剪辑组合（高光点-钩子点）渲染成实际的视频文件。

## 功能特性

✅ **单集剪辑**：从同一集视频中裁剪片段
✅ **跨集剪辑**：从不同集视频中裁剪片段并自动拼接
✅ **进度显示**：实时显示FFmpeg处理进度
✅ **错误处理**：完善的错误处理和日志输出
✅ **质量控制**：可配置的视频编码参数

## 核心组件

### 1. ClipRenderer

剪辑渲染器，负责：
- 加载result.json
- 发现视频文件
- 计算各集时长
- 渲染单个或所有剪辑

### 2. Clip

剪辑数据类，包含：
- `start`: 起始累积秒（相对于第1集开头）
- `end`: 结束累积秒（相对于第1集开头）
- `duration`: 时长（秒）
- `highlight`: 高光类型
- `hook`: 钩子类型
- `episode`: 起始集数
- `hookEpisode`: 结束集数

### 3. VideoFile

视频文件信息：
- `episode`: 集数
- `path`: 文件路径
- `duration`: 时长（秒）

### 4. ClipSegment

剪辑片段（用于跨集剪辑）：
- `episode`: 集数
- `start`: 开始秒（在该集内）
- `end`: 结束秒（在该集内）
- `video_path`: 视频文件路径

## 使用方法

### 方法1：命令行（推荐）

#### 渲染单个剪辑

```bash
python3 -m scripts.understand.render_clips <项目路径> <输出目录> <视频目录>
```

**示例**：

```bash
python3 -m scripts.understand.render_clips \
  "data/hangzhou-leiming/analysis/百里将就" \
  "data/hangzhou-leiming/analysis/百里将就/clips" \
  "漫剧素材/百里将就"
```

#### 渲染所有剪辑

```bash
python3 -m scripts.understand.render_clips \
  "data/hangzhou-leiming/analysis/百里将就" \
  "data/hangzhou-leiming/analysis/百里将就/clips" \
  "漫剧素材/百里将就"
```

### 方法2：Python API

```python
from scripts.understand.render_clips import ClipRenderer

# 创建渲染器
renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/百里将就",
    output_dir="data/hangzhou-leiming/analysis/百里将就/clips",
    video_dir="漫剧素材/百里将就",
    width=1920,
    height=1080,
    fps=30,
    crf=18,
    preset="fast"
)

# 渲染所有剪辑
def on_progress(current, total, progress):
    """进度回调"""
    percent = progress * 100
    print(f"\r进度: [{current}/{total}] {percent:.1f}%", end='', flush=True)

output_paths = renderer.render_all_clips(on_clip_progress=on_progress)

print(f"\n完成！渲染了 {len(output_paths)} 个剪辑")
```

### 方法3：使用测试脚本

#### 测试单个剪辑

```bash
python3 scripts/understand/test_render.py
```

#### 测试所有剪辑

```bash
python3 scripts/understand/test_render.py --all
```

## 参数说明

### ClipRenderer参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `project_path` | str | **必需** | 项目路径（包含result.json） |
| `output_dir` | str | **必需** | 输出目录 |
| `video_dir` | str | project_path | 视频文件目录 |
| `width` | int | 1920 | 输出视频宽度 |
| `height` | int | 1080 | 输出视频高度 |
| `fps` | int | 30 | 输出帧率 |
| `crf` | int | 18 | CRF质量（18-28，越小质量越高） |
| `preset` | str | "fast" | 编码预设 |

### 编码预设（preset）

从快到慢（质量从低到高）：
- `ultrafast` - 最快，质量最低
- `superfast`
- `veryfast`
- `faster`
- `fast` - **推荐**
- `medium`
- `slow`
- `slower`
- `veryslow` - 最慢，质量最高

### CRF质量参数

| 值 | 质量 | 文件大小 | 适用场景 |
|---|------|----------|----------|
| 18 | 很高 | 很大 | 存储充足，追求质量 |
| 20 | 高 | 大 | **推荐** |
| 23 | 中等 | 中等 | 一般用途 |
| 28 | 低 | 小 | 快速预览 |

## 工作流程

### 单集剪辑流程

```
1. 读取result.json
   ↓
2. 加载剪辑数据
   ↓
3. 转换为视频片段（1个）
   ↓
4. FFmpeg裁剪
   ↓
5. 保存输出文件
```

### 跨集剪辑流程

```
1. 读取result.json
   ↓
2. 加载剪辑数据
   ↓
3. 转换为视频片段（多个）
   - 第1集片段
   - 第2集片段
   - 第3集片段
   - ...
   ↓
4. FFmpeg分别裁剪每个片段
   ↓
5. 创建concat列表文件
   ↓
6. FFmpeg拼接片段
   ↓
7. 保存输出文件
   ↓
8. 删除临时文件
```

## 输出文件命名

### 同集剪辑

```
clip_ep{集数}_{起始时间}-{结束时间}_{类型}.mp4
```

示例：
```
clip_ep1_0-204_开篇高光-秘密揭露或真相揭示.mp4
clip_ep1_75-301_开篇高光-关键信息被截断.mp4
```

### 跨集剪辑

```
clip_ep{起始集}-ep{结束集}_{类型}.mp4
```

示例：
```
clip_ep2-ep3_开篇高光-关键信息被截断.mp4
clip_ep2-ep4_开篇高光-情感爆发顶点.mp4
```

## 测试结果（百里将就）

### 成功渲染的剪辑

| # | 文件名 | 时长 | 大小 | 类型 |
|---|--------|------|------|------|
| 1 | clip_ep1_0-204_*.mp4 | 204秒 | 87.91 MB | 同集 |

### 待测试功能

- ✅ 单集剪辑
- ⏳ 跨集剪辑（3个）
- ⏳ 批量渲染（11个剪辑）

## 常见问题

### Q1: 找不到视频文件？

**错误信息**：
```
找不到第X集视频文件
```

**解决方案**：
1. 检查`video_dir`参数是否正确
2. 确认视频文件命名格式：`1.mp4`, `2.mp4`, ...
3. 支持的命名格式：
   - `第1集.mp4`
   - `EP01.mp4`
   - `E01.mp4`
   - `01.mp4`
   - `1.mp4`

### Q2: FFmpeg裁剪失败？

**错误信息**：
```
FFmpeg裁剪失败 (返回码: 1)
```

**解决方案**：
1. 检查FFmpeg是否已安装：`ffmpeg -version`
2. 检查视频文件是否损坏
3. 尝试降低质量参数（增加crf值）
4. 检查磁盘空间是否充足

### Q3: 跨集剪辑拼接失败？

**错误信息**：
```
FFmpeg拼接失败
```

**解决方案**：
1. 检查临时片段是否都成功生成
2. 确认所有片段的编码参数一致
3. 检查concat列表文件格式

### Q4: 输出视频质量不佳？

**解决方案**：
1. 降低CRF值（18→20→23）
2. 使用更慢的preset（fast→medium→slow）
3. 增加分辨率（width/height）

### Q5: 渲染速度太慢？

**解决方案**：
1. 使用更快的preset（fast→faster→veryfast）
2. 提高CRF值（18→23→28）
3. 降低分辨率（1920x1080→1280x720）
4. 降低帧率（30fps→24fps）

## 性能优化建议

### 快速预览（质量较低）

```python
renderer = ClipRenderer(
    ...
    crf=28,  # 较低质量
    preset="veryfast",  # 快速编码
    fps=24,  # 较低帧率
    width=1280,  # 较低分辨率
    height=720
)
```

### 标准质量（推荐）

```python
renderer = ClipRenderer(
    ...
    crf=20,  # 标准
    preset="fast",  # 平衡
    fps=30,
    width=1920,
    height=1080
)
```

### 高质量（文件较大）

```python
renderer = ClipRenderer(
    ...
    crf=18,  # 高质量
    preset="medium",  # 较慢编码
    fps=30,
    width=1920,
    height=1080
)
```

## 后续优化方向

1. **并行渲染**：使用多进程/多线程同时渲染多个剪辑
2. **GPU加速**：使用NVENC/QuickSync等硬件编码器
3. **智能裁剪**：使用关键帧检测，在关键帧处裁剪
4. **增量渲染**：只重新渲染修改过的剪辑
5. **批量优化**：智能调整编码参数，平衡质量和速度

## 相关文件

- `scripts/understand/render_clips.py` - 主模块
- `scripts/understand/test_render.py` - 测试脚本
- `scripts/understand/generate_clips.py` - 生成剪辑组合
- `scripts/understand/video_understand.py` - 视频理解主流程

---

**版本**: 1.0.0
**最后更新**: 2026-03-03
**作者**: Claude Code + Happy
