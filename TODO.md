# 项目待办事项

## 🔴 最高优先级 - P0 CRITICAL

### 1. [BUG-V14.10] 片尾拼接帧率不一致导致"有声音无画面" **✅ 已修复**

**状态**: ✅ 已修复并验证 (2026-03-09)
**优先级**: P0 - 最高优先级
**发现日期**: 2026-03-09

**问题描述**:
拼接结尾视频后，出现"只有声音没有画面"的现象：
- 音频正常播放（包括片尾音频）
- 视频画面定格在主剪辑最后一帧
- 片尾视频的画面没有显示出来

**问题根源**:
**帧率不一致！**
- 原剪辑帧率：30 fps
- 结尾视频帧率：24 fps
- 不同帧率的视频拼接时，FFmpeg无法正确处理，导致视频流被截断

**修复方案** (V14.10):
在 `_preprocess_ending_video` 方法中添加帧率转换：

```python
# 1. 获取原剪辑的帧率
cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
       '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', clip_path]
# 解析帧率（如 "30/1" -> 30.0）

# 2. 在预处理结尾视频时转换帧率
cmd = [
    'ffmpeg',
    '-i', ending_video,
    '-vf', f'fps={clip_fps},scale=...',  # 添加fps转换
    '-r', str(clip_fps),  # 明确指定输出帧率
    '-vsync', 'cfr',  # 使用CFR模式确保帧率一致
    ...
]
```

**验证结果** (2026-03-09 烈日重生项目测试):
| 视频 | 修复前差异 | 修复后差异 |
|------|-----------|-----------|
| 第1集0秒_第2集56秒 | 2.58秒 ❌ | 0.02秒 ✅ |
| 第1集0秒_第2集1分43秒 | 2.58秒 ❌ | 0.02秒 ✅ |
| 第1集0秒_第2集2分7秒 | 2.58秒 ❌ | 0.03秒 ✅ |

**相关文件**:
- `scripts/understand/render_clips.py`
  - `_preprocess_ending_video()` 方法（第 957-985 行）- 添加帧率转换逻辑

---

### 2. [BUG-V15.1] 钩子点时间戳不精确 - 话没说完就被截断 **✅ 已实现**

**状态**: ✅ 已实现 (2026-03-09)
**优先级**: P0 - 最高优先级
**发现日期**: 2026-03-09

**问题描述**:
剪辑视频在钩子点结束，但当前这句话还没说完就被截断了：
- 例如："林溪你去物业问问到底怎么回事" 这句话还没说完
- 视频在98秒就结束了，但这句话应该到105秒才说完
- 画面结束得很突然，给人一种"话说到一半"的感觉

**问题根源**:
1. **ASR片段不完整**：Whisper ASR把一句话拆分成多个片段
2. **算法错误**：当前 `adjust_hook_point()` 只是简单地延伸到包含钩子点的第一个ASR片段结尾
3. **精度不足**：使用毫秒级精度，不同帧率视频会导致切割位置不准确
4. **缺乏智能判断**：没有考虑画面稳定性、场景切换等因素

**实测案例**（烈日重生 第1集0秒_第2集1分43秒）:
- 钩子点时间：94.9秒
- 钩子点描述："林溪你去物业问问到底怎么回事"
- ASR识别结果：
  - 95-96秒：林溪
  - 96-97秒：你去物业问问
  - 97-98秒：到底怎么回事
  - 98-99秒：我心中一动
  - 102-103秒：物业处
  - 104-105秒：正热的满头大汗
- 当前代码结果：96.1秒（只延伸到"林溪"片段结尾）
- 正确应该是：98秒（"到底怎么回事"说完）

---

### 3. [FEATURE-V15.2] 智能多维度切割点查找 **✅ 已实现**

**目标**：实现基于帧级精度的智能切割点查找

**设计思路**：

```
┌─────────────────────────────────────────────────────────┐
│                    目标时间点 ~98秒                      │
├─────────────────────────────────────────────────────────┤
│  1️⃣ 时间维度         2️⃣ 画面维度          3️⃣ 音频维度  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐│
│  │ 这句话结束   │    │ 画面是否静止 │    │ 是否有静音  ││
│  │ 于98秒      │    │ /稳定？      │    │ /停顿？     ││
│  │             │    │             │    │             ││
│  │ 下一句话   │    │ 是否有场景   │    │ 音频是否    ││
│  │ 101秒开始  │    │ 切换？       │    │ 刚结束？    ││
│  └─────────────┘    └─────────────┘    └─────────────┘│
│                                                         │
│              📊 综合决策：多维度加权评估                  │
│                                                         │
│    最优切割点 = min(句子结束, 场景切换点, 静音开始点)   │
└─────────────────────────────────────────────────────────┘
```

**实现方案**：

```python
def find_optimal_cut_point(
    hook_timestamp,      # 原始钩子点（如94.9秒）
    asr_segments,      # ASR数据
    video_path,         # 视频文件路径
    video_fps,          # 视频实际帧率（24/30/50/60 fps）
    search_window=2.0   # 搜索窗口（秒）
):
    """
    智能多维度切割点查找（帧级精度）

    返回：最佳切割时间（秒，精确到帧）
    """

    # Step 1: 找到目标句子
    # - 找到包含钩子点的那句话
    # - 返回该句话最后一个ASR片段的结束时间
    sentence_end = find_sentence_end(hook_timestamp, asr_segments)  # 如98秒

    # Step 2: 多维度分析（搜索窗口：97.5s - 99s）

    # 2.1 画面分析 - 检测场景切换点
    scene_change_frames = detect_scene_changes(
        video_path, search_start, search_end, video_fps
    )

    # 2.2 画面分析 - 分析帧稳定性（避免切在运动画面）
    stability_scores = analyze_frame_stability(
        video_path, sentence_end - 1.0, sentence_end + 0.5, video_fps
    )

    # 2.3 音频分析 - 检测静音区域
    silence_segments = detect_silence(
        video_path, search_start, search_end, threshold_db=-40
    )

    # Step 3: 综合决策
    # 优先级：1. 避免场景切换 2. 画面稳定 3. 静音区域
    optimal_point = make_decision(
        sentence_end=sentence_end,
        scene_change_frames=scene_change_frames,
        stability_scores=stability_scores,
        silence_segments=silence_segments,
        video_fps=video_fps
    )

    return optimal_point  # 返回帧级精度的时间点
```

**关键改进点**：

| 改进项 | 当前方案 | 优化后方案 |
|-------|---------|-----------|
| 时间精度 | 毫秒 | 精确到帧 |
| 句子判断 | 第一个ASR片段 | 同一句话的所有片段 |
| 画面判断 | 无 | 场景切换 + 帧稳定性 |
| 音频判断 | 固定100ms缓冲 | 静音区域检测 |
| 决策逻辑 | 简单延伸 | 多维度加权 |

**文件位置（已实现）**：
- ✅ `scripts/understand/smart_cut_finder.py` - 智能切割点查找模块
- ✅ `scripts/understand/timestamp_optimizer.py` - 集成智能切割算法
- ✅ `scripts/understand/generate_clips.py` - 传递视频路径和帧率
- ✅ `scripts/understand/video_understand.py` - 自动获取视频帧率

**实现细节 (2026-03-09)**:
- 创建 `SmartCutFinder` 类，实现多维度智能切割
- `find_sentence_end()`: 找到包含钩子点的整句话结束时间（间隔<0.5秒视为连续）
- `detect_silence_regions()`: 使用 FFmpeg silencedetect 检测静音区域
- `find_optimal_cut_point()`: 综合决策，优先选择静音区域开始点
- 帧级精度：基于实际帧率转换切割时间

---

### 4. [FEATURE-V15.3] 高光点帧级精度优化 **✅ 已实现**

**状态**: ✅ 已实现 (2026-03-10)
**优先级**: P0 - 最高优先级

**问题描述**:
高光点之前使用毫秒级精度，没有考虑视频帧率，可能导致：
- 剪辑起点不在关键帧上
- 不同帧率视频精度不一致

**解决方案**:
- 为高光点添加智能算法，找到包含高光点的那句话的**开始时间**
- 使用帧级精度：基于实际视频帧率转换时间戳
- 与钩子点使用相同的ASR句子边界检测逻辑

**实现细节**:
- 在 `SmartCutFinder` 中添加 `find_sentence_start()` 方法
- 添加 `smart_adjust_highlight_point()` 智能调整函数
- 修改 `adjust_highlight_point()` 接收视频路径和帧率参数

**对比**:
| 特性 | 优化前 | 优化后 |
|-----|-------|-------|
| 精度 | 毫秒级 | 帧级 |
| 句子判断 | 第一个ASR片段 | 整句话开始 |
| 帧率考虑 | 无 | 基于实际FPS |

**文件位置**:
- ✅ `scripts/understand/smart_cut_finder.py` - 添加 find_sentence_start 和 smart_adjust_highlight_point
- ✅ `scripts/understand/timestamp_optimizer.py` - 修改 adjust_highlight_point 使用智能算法

---

## 🔄 高优先级

### 2. 自动清理缓存机制 [CRITICAL]

**问题描述**：
缓存文件占用大量空间（当前约1.7GB）：
- `cache/keyframes/`: ~1.4GB（关键帧图片）
- `cache/audio/`: ~335MB（提取的音频文件）
- `cache/asr/`: ~4.6MB（ASR转录文本，很小）

**需求**：
- 实现自动清理机制
- 清理过期的关键帧和音频文件
- 保留ASR文本（很小且有用）

**实现建议**：

1. **基于时间的清理策略**
   ```python
   # 示例配置
   CACHE_RETENTION_DAYS = {
       'keyframes': 7,      # 关键帧保留7天
       'audio': 7,          # 音频保留7天
       'asr': -1,           # ASR文本永久保留（-1表示不删除）
   }
   ```

2. **实现位置**
   - 创建 `scripts/cache_cleaner.py`
   - 集成到 `video_understand.py` 流程末尾
   - 或作为独立的定时任务

3. **清理逻辑**
   ```bash
   # 示例命令
   python -m scripts.cache_cleaner --days 7 --dry-run
   python -m scripts.cache_cleaner --days 7 --execute
   ```

4. **安全性考虑**
   - 清理前检查是否有项目正在使用这些缓存
   - 提供 `--dry-run` 选项预览要删除的文件
   - 记录清理日志

**文件位置**：
- 待创建：`scripts/cache_cleaner.py`
- 待修改：`scripts/understand/video_understand.py`（集成清理调用）

---

## 📋 中优先级

### 3. 集成视频包装花字模块到默认渲染流程

**问题描述**：
视频包装花字模块已实现（V15功能），但还没有集成到默认渲染流程中。

**当前状态**：
- ✅ 花字模块已实现：`scripts/understand/video_overlay/video_overlay.py`
- ✅ 已集成到render_clips.py：可以使用`--add-overlay`参数启用
- ❌ 默认渲染流程未启用：需要手动添加`--add-overlay`参数

**功能说明**：
- **三层花字叠加**：
  1. **热门短剧**（24pt字体）：随机位置（左上/右上)，随机显示3-8秒
  2. **剧名**（16pt字体）：底部居中，全时长显示
  3. **免责声明**（12pt字体）：底部居中，剧名下方40px，全时长显示
- **10种预设样式**：gold_luxury, red_passion, blue_cool, purple_mystery等
- **项目级样式统一**：同一项目的所有剪辑使用相同样式（基于项目名hash缓存）
- **自动字体检测**：优先使用Songti.ttc（macOS），fallback到系统字体

**使用方法**（当前需要手动指定参数）：
```bash
# 基础使用（启用花字叠加）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-style-id gold_luxury

# 完整示例（结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending \
    --add-overlay
```

**待办事项**：
- [ ] 评估是否应该在默认渲染流程中启用花字叠加
  - 优点：增加视频吸引力，符合短视频平台习惯
  - 缺点：渲染时间稍长（需要额外的FFmpeg处理）
  - 决策：用户手动启用 OR 默认启用添加配置项控制
- [ ] 更新CLAUDE.md文档，添加`--add-overlay`参数说明
- [ ] 创建花字样式预览脚本（查看不同样式的效果）
- [ ] 测试花字叠加在不同分辨率视频下的表现
- [ ] 验证字幕安全区设置是否合理（当前150px）

**文件位置**：
- 核心模块：`scripts/understand/video_overlay/video_overlay.py`
- 样式定义：`scripts/understand/video_overlay/overlay_styles.py`
- 已集成到：`scripts/understand/render_clips.py`
- 测试脚本：`scripts/understand/video_overlay/test_overlay.py`

---

### 4. 添加标准结尾帧视频功能

**问题描述**：
生成的剪辑没有自动添加标准结尾帧视频

**需求**：
- 在每个剪辑末尾添加标准结尾帧视频
- 使用 `标准结尾帧视频素材/` 目录下的标准结尾

**实现方法**：
V14版本已实现此功能，使用 `--add-ending` 参数：
```bash
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending
```

**待办事项**：
- [x] 验证标准结尾帧视频素材是否存在 ✅
- [x] 测试--add-ending功能是否正常工作 ✅ (2026-03-09)
- [x] 确认结尾帧拼接的准确性 ✅ (已修复帧率问题)

**文件位置**：
- 功能已实现：`scripts/understand/render_clips.py`
- 素材目录：`标准结尾帧视频素材/`

---

### 5. 性能优化
- [ ] 并行处理多个项目（当前是串行）
- [ ] 关键帧提取进度显示（当前没有进度条）
- [ ] ASR转录速度优化（考虑使用更快的模型）

### 6. 质量改进
- [ ] 优化AI分析prompt提高准确率
- [ ] 增加更多质量过滤器
- [ ] 支持人工审核和修正AI标记

---

## 💡 低优先级

### 7. 功能增强
- [ ] 支持批量项目管理（一次性处理多个项目）
- [ ] Web界面可视化查看分析结果
- [ ] 导出分析报告为PDF/Excel

### 8. 文档完善
- [ ] 添加更多示例到文档
- [ ] 录制视频教程
- [ ] 编写故障排查指南

---

## 🔬 技术难点 / 后续优化

### 1. [FEATURE-V15.8] 字幕与剪辑时间点同步优化

**状态**: 📋 待处理
**优先级**: P1 - 高优先级
**发现日期**: 2026-03-10

**问题描述**：

**核心矛盾**：一个字幕(subtitle)可能由多个 ASR segment 组成，导致剪辑时间点与字幕显示范围不一致

**场景示例**：

```
ASR segments:
├── segment 1 [10.0-12.0s]: "今天天气"
├── segment 2 [12.0-14.0s]: "真不错"
└── segment 3 [14.0-16.0s]: "我们去公园吧"

实际字幕显示: "今天天气真不错我们去公园吧" (完整一条字幕)
```

**剪辑问题**：

1. **高光点问题**
   - 假设高光点在 12.0s (segment 2 开始)
   - ✅ V15.7 时间戳优化正确：落在 segment 边界
   - ❌ 字幕显示问题：字幕从"今天天气"开始，高光点跳过了 segment 1
   - **用户观感**：字幕从"话的一半"开始，感觉突兀

2. **钩子点问题**
   - 假设钩子点在 14.0s (segment 2 结束)
   - ✅ V15.7 时间戳优化正确：落在 segment 边界
   - ❌ 字幕显示问题：字幕还有"我们去公园吧"没说完
   - **用户观感**：字幕话没说完就被截断，感觉不完整

**问题根源**：

| 层级 | V15.7 当前处理 | 实际情况 |
|-----|---------------|---------|
| ASR segment | ✅ 时间戳对齐到边界 | 一个字幕 = 多个 segment |
| 字幕显示 | ❌ 显示完整字幕文本 | 需要按时间截取 |

**解决方案**：

1. **字幕聚合** - 先合并时间间隔小的连续 segment 成一个"字幕单元"
   ```python
   # 示例逻辑
   subtitle_units = merge_segments_by_gap(asr_segments, max_gap=0.5)
   # 结果: [字幕1: seg1+seg2+seg3], [字幕2: seg4+seg5], ...
   ```

2. **剪辑点优化** - 让剪辑时间戳对齐到"字幕单元"边界，而非单个 segment 边界
   ```python
   # 高光点 → 字幕单元开始时间
   # 钩子点 → 字幕单元结束时间
   ```

3. **字幕截取** - 如果必须从字幕中间剪辑，按时间范围截取字幕文本
   ```python
   # 方案A: 截取字幕文本
   subtitle_text = get_subtitle_in_range(subtitle_units, start_time, end_time)

   # 方案B: 生成 SRT 字幕文件
   generate_srt_for_clip(subtitle_units, start_time, end_time, output_path)
   ```

**相关文件**：
- `scripts/understand/smart_cut_finder.py` - V15.7 时间戳优化（需修改）
- `scripts/understand/video_overlay/video_overlay.py` - 字幕渲染（需修改）
- `scripts/understand/render_clips.py` - 剪辑渲染主流程（需修改）
- `scripts/extract_asr.py` - ASR 提取（可能需要输出字幕聚合信息）

**验证数据**（烈日重生项目）：
- 高光点匹配率: 1/4 (25%)
- 钩子点匹配率: 10/20 (50%)
- 未匹配的时间戳不在任何 ASR segment 内

---

---

## 📝 更新日志

- **2026-03-10**: 📋 记录 V15.8 技术难点 - 字幕与剪辑时间点同步优化
- **2026-03-09**: ✅ 已修复V14.10 BUG - 片尾拼接帧率不一致问题（真正根因：帧率24fps vs 30fps）
- **2026-03-08**: 新增P0最高优先级BUG - 片尾拼接视频流截断问题（V14.9未修复）
- **2026-03-05**: 创建待办事项列表，标记缓存清理为高优先级

---

## 🚀 V16 待优化功能 (2026-03-10)

### 1. 剪辑组合排序与智能筛选

**问题描述**：
- 当前从AI分析会产生大量剪辑组合（如299个），但实际只需要10-20个
- 需要按一定规则排序，挑选最合适的剪辑组合

**需求**：
- 支持按多种方式排序：时长、类型、置信度、跨集数等
- 智能筛选：去除重复、保留多样性
- 最终输出控制在10-20个精选组合

**实现建议**：
- 在 `generate_clips.py` 或 `quality_filter.py` 中添加排序逻辑
- 支持多维度加权排序

---

### 2. 片尾检测优化

**问题描述**：
- 片尾检测在渲染阶段进行，需要对每集进行ASR转录
- 耗时较长，影响整体效率

**优化方案**：
- 方案A：将片尾检测提前到AI分析阶段完成，渲染时直接使用缓存结果
- 方案B：优化ASR转录速度（使用更快的模型、并行转录多集）
- 方案C：简化检测算法，减少转录次数

**实现建议**：
- 创建 `scripts/preprocess/ending_detector.py`，在视频理解阶段提前检测
- 使用缓存机制，避免重复检测

---

### 3. 渲染多线程并行

**问题描述**：
- 当前渲染是串行的，每个剪辑逐一处理
- 多个剪辑渲染耗时过长

**优化方案**：
- 支持多进程并行渲染多个剪辑
- 支持项目内剪辑并行、项目间也并行

**实现建议**：
- 修改 `render_clips.py`，支持 `--parallel` 参数
- 使用 `concurrent.futures.ProcessPoolExecutor` 实现多进程

---

### 4. 硬盘空间管理与边界情况

**问题描述**：
- 需要考虑硬盘空间不足的各种边界情况
- 当前没有空间检查和预警

**需求**：
- 在开始前检查可用空间
- 空间不足时给出警告或自动清理策略
- 增量渲染：支持断点续传

**实现建议**：
- 在关键步骤前检查空间：`df -h`
- 空间不足时提示用户
- 支持 `--resume` 参数，从中断处继续

---

### 5. 其他边界情况处理

**待处理边界情况**：
- [ ] 视频文件损坏/无法读取
- [ ] ASR转录失败
- [ ] AI分析超时
- [ ] 渲染中断后的临时文件清理
- [ ] 网络问题导致API调用失败
- [ ] 磁盘写满时的异常处理

---

### 6. 整体流程提效

**当前耗时分析**（示例：2个项目各5个剪辑）：
- AI分析：约20分钟
- 片尾检测：约15分钟
- 渲染：约20分钟
- 总计：约55分钟

**提效方案**：
- 片尾检测提前到分析阶段（节省15分钟）
- 渲染多线程并行（节省15分钟）
- 使用更快的ASR模型
- 缓存复用：避免重复检测

---

### 7. 视频大小控制

**问题描述**：
- 当前渲染的视频通常几百MB，广告投放素材一般不超过100MB
- 需要控制输出视频大小

**当前状态**：
- ✅ 已实现压缩脚本（CRF 28，约1/5大小）

**优化方案**：
- 渲染时自动压缩：添加 `--compress` 参数
- 默认压缩到目标大小（如100MB以内）
- 支持多种质量档位：低(50MB)、中(100MB)、高(200MB)

**实现建议**：
- 修改 `render_clips.py`，添加压缩参数
- 计算合理比特率：`target_bitrate = target_size_bytes * 8 / duration_seconds`
- 使用Two-Pass编码提高压缩质量

---

## 📝 更新日志

- **2026-03-10**: 📋 记录V16待优化功能 - 剪辑筛选、片尾检测优化、渲染并行、空间管理、视频压缩等
