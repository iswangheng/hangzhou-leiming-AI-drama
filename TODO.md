# 项目待办事项

## 🔴 最高优先级 - P0 CRITICAL

### 1. [FEATURE-V16/17] OCR精确字级马赛克遮盖 **✅ 已完成**

**状态**: ✅ 已完成且彻底修复 (2026-03-13)
**优先级**: P0 - 最高优先级
**发现日期**: 2026-03-11

**功能描述**:
通过OCR识别视频字幕，检测敏感词并自动应用马赛克遮盖

**技术方案**：
1. **OCR识别**：使用PaddleOCR 3.x识别视频帧中的字幕文字
2. **字幕区域检测**：使用像素变化法自动检测字幕位置
3. **OCR+ASR结合**：
   - OCR识别到敏感词句子
   - 用OCR时间点在ASR中找对应片段
   - 模糊匹配（相似度>60%）处理OCR/ASR识别误差
   - 词组匹配（如"热死"），不拆分单个字符
4. **马赛克遮盖**：根据检测到的时间段应用马赛克

**关键实现**：
```python
# OCR+ASR结合检测流程
1. OCR扫描视频帧，识别字幕文字
2. 检测到敏感词时记录该帧时间点
3. 用OCR时间点在ASR中查找对应片段
4. 模糊匹配：相似度>60% + 包含敏感词
5. 返回ASR片段的精确时间范围
```

**测试结果**（烈日重生第1集）：
- OCR识别句子: "我不是已经在70度的高温里活活热死吗"
- ASR合并: "我不是已经在70度的高温率活活热死了"
- 相似度: 78.9%
- 时间段: 0.00s - 4.56s (ASR片段0-1)
- 马赛克遮盖效果: ✅ 正常

**相关文件**：
- `scripts/preprocess/ocr_subtitle.py` - OCR字幕识别模块
- `scripts/preprocess/sensitive_detector.py` - 敏感词检测模块（添加模糊匹配）
- `scripts/preprocess/subtitle_detector.py` - 字幕区域检测
- `scripts/preprocess/video_cleaner.py` - 视频马赛克处理
- `config/sensitive_words.txt` - 敏感词列表（添加"热死"）

---

### 2. [BUG-V14.10] 片尾拼接帧率不一致导致"有声音无画面" **✅ 已修复**

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

### 2. 自动清理缓存机制 [CRITICAL] **✅ 已完成 (V15.8)**

**状态**: ✅ 已完成 (2026-03-11)

**问题描述**：
缓存文件占用大量空间（当前约1.7GB），且原来的清理机制在分析/渲染完成后立即删除，太着急了。

**解决方案 (V15.8)**：
- 修改 `cleanup_project_cache()` 函数，添加 `min_age_hours` 参数（默认3.0小时）
- 基于文件 mtime 判断，只清理超过指定小时数的缓存
- 添加日志显示跳过了多少文件

**修改文件**：
- `scripts/understand/video_understand.py` - cleanup_project_cache()
- `scripts/understand/render_clips.py` - cleanup_project_cache()
- `scripts/train.py` - cleanup_project_cache()
- `test/test_cache_cleanup_with_age.py` - 测试脚本

**日志示例**：
```
清理项目 项目名 的中间缓存（仅清理超过3小时的缓存）...
  已清理: 关键帧=1, 音频=1, ASR=1
  ⏭️  跳过（未到3小时）: 5 个文件
  释放空间: 123.45 MB
```

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
    data/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
    data/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-style-id gold_luxury

# 完整示例（结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \
    data/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending \
    --add-overlay
```

**待办事项**：
- [x] 评估是否应该在默认渲染流程中启用花字叠加 ✅ (V17已默认启用)
- [x] 更新CLAUDE.md文档，添加`--add-overlay`参数说明 ✅ (V17已完成)
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
    data/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending
```

**待办事项**：
- [x] 验证标准结尾帧视频素材是否存在 ✅
- [x] 测试--add-ending功能是否正常工作 ✅ (2026-03-09)
- [x] 确认结尾帧拼接的准确性 ✅ (已修复帧率问题)
- [x] 默认启用片尾视频 ✅ (V17已完成)

**文件位置**：
- 功能已实现：`scripts/understand/render_clips.py`
- 素材目录：`标准结尾帧视频素材/`

---

### 5. 性能优化
- [ ] 并行处理多个项目（当前是串行）
- [ ] 关键帧提取进度显示（当前没有进度条）
- [x] ASR转录速度优化 ✅ (V15.9已实现并行提取)

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

### 1. [FEATURE-V16] 字幕与剪辑时间点同步优化 **✅ 已完成**

**状态**: ✅ 已完成 (2026-03-11)
**优先级**: P1 - 高优先级
**完成日期**: 2026-03-11

**解决方案**：
通过OCR+ASR结合的方式解决"ASR多segment组成一句字幕"的问题：

1. **OCR识别完整句子** - "我不是已经在70度的高温里活活热死吗"
2. **用OCR时间点在ASR中找对应片段** - 找到片段0和片段1
3. **模糊匹配确定精确时间段** - 相似度>60%，确定时间范围0.00s-4.56s

**相关文件**：
- `scripts/preprocess/sensitive_detector.py` - detect_sensitive_segments_with_ocr_asr()

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

- **2026-03-11**: ✅ V16 - OCR+ASR敏感词检测与马赛克遮盖模块完成
- **2026-03-11**: ✅ V16.2 - GPU加速跨平台支持 + 性能优化完成
- **2026-03-11**: ✅ V16.1 - 修复并行渲染文件命名Bug + 添加合并渲染函数
- **2026-03-11**: ✅ V15.9 - ASR并行提取和缓存复用优化完成
- **2026-03-11**: ✅ V15.8 - 缓存清理3小时保留策略完成
- **2026-03-11**: ✅ V15.7 - 时间戳优化修复完成
- **2026-03-10**: 📋 记录 V15.8 技术难点 - 字幕与剪辑时间点同步优化
- **2026-03-09**: ✅ 已修复V14.10 BUG - 片尾拼接帧率不一致问题（真正根因：帧率24fps vs 30fps）
- **2026-03-08**: 新增P0最高优先级BUG - 片尾拼接视频流截断问题（V14.9未修复）
- **2026-03-05**: 创建待办事项列表，标记缓存清理为高优先级

---

## 🚀 V16 已完成功能汇总 (2026-03-11)

### 已完成的V16功能：

| 功能 | 状态 | 描述 |
|-----|------|------|
| OCR+ASR敏感词检测 | ✅ | PaddleOCR 3.x + 模糊匹配 + 马赛克遮盖 |
| 字幕与剪辑时间点同步 | ✅ | OCR+ASR结合解决ASR多segment问题 |
| GPU加速跨平台 | ✅ | Windows/macOS/Linux GPU支持 |
| 多项目串行处理 | ✅ | 一次性处理多个项目 |
| 完全合并编码优化 | ✅ | 单次FFmpeg调用完成所有操作 |
| 并行渲染优化 | ✅ | ProcessPoolExecutor多进程 |
| ASR并行提取 | ✅ | ThreadPoolExecutor + 缓存复用 |
| 缓存3小时保留 | ✅ | min_age_hours参数 |

### V16 待优化功能：

| 功能 | 状态 | 描述 |
|-----|------|------|
| 剪辑组合排序与智能筛选 | ✅ 已完成 | V17 实现 Top N 精选，按高光×钩子组合质量排序 |
| 片尾检测优化 | ✅ 已完成 | 在video_understand阶段检测，结果缓存到data/ending_credits/ |
| 硬盘空间管理 | 📋 待处理 | 空间检查、预警、断点续传 |
| 视频大小控制 | 📋 待处理 | 压缩到目标大小（如100MB） |
| 字幕与剪辑时间点同步 | ✅ 已完成 | OCR+ASR结合解决ASR多segment问题 |

### 1. 剪辑组合排序与智能筛选 **✅ 已完成 (V17)**

**状态**: ✅ 已完成 (2026-03-12)

**实现方案**：
- 高光按综合质量取 Top 10，钩子按综合质量取 Top 10
- 生成组合后按组合质量分数排序（高光×钩子质量乘积）
- 取 Top 20，兼顾类型和集数多样性

**多维度评分**：
- 置信度权重 40%：AI返回的置信度分数
- 类型权重 30%：反转 > 冲突 > 情感 > 日常
- 时机权重 20%：高光在集前、钩子在集末加分
- 描述权重 10%：描述越详细越可信

**组合质量计算**：
- 高光分数 = 置信度×0.4 + 类型×0.3 + 时机×0.2 + 描述×0.1
- 钩子分数 = 置信度×0.4 + 类型×0.3 + 时机×0.2 + 描述×0.1
- 组合分数 = 高光分数×0.4 + 钩子分数×0.6（钩子权重更高）

**实现位置**：
- `scripts/understand/generate_clips.py` - 新增 `sort_and_filter_clips()` 函数
- `scripts/understand/video_understand.py` - 在 generate_clips 后调用排序筛选

---

### 2. 片尾检测优化 **✅ 已完成 (V17)**

**状态**: ✅ 部分完成 (2026-03-11)

**已完成**：
- ASR并行提取 ✅ (使用ThreadPoolExecutor)
- 片尾检测缓存复用 ✅ (V15.9)
- **片尾检测提前到AI分析阶段完成 ✅ (V17)** - 在video_understand阶段检测，结果缓存到data/ending_credits/目录

**问题描述**：
- 片尾检测在渲染阶段进行，需要对每集进行ASR转录
- 耗时较长，影响整体效率

**优化方案**：
- 方案A：片尾检测提前到AI分析阶段完成，渲染时直接使用缓存结果 ✅ (已完成)
- 方案B：优化ASR转录速度（使用更快的模型、并行转录多集） ✅ (已完成)
- 方案C：简化检测算法，减少转录次数

**实现说明**：
- 在 `video_understand.py` 中调用 `detect_project_endings_in_understand_phase()` 完成检测
- 缓存保存在 `data/ending_credits/{project}_ending_credits.json`
- render阶段优先加载缓存，缓存不存在时自动回退到实时检测（使用ASR缓存加速）

---

### 3. 渲染多线程并行 **✅ 已完成 (V16)**

**状态**: ✅ 已完成 (2026-03-11)

**问题描述**：
- 当前渲染是串行的，每个剪辑逐一处理
- 多个剪辑渲染耗时过长（10个剪辑约5分钟）

**实现方案** (V16):
- 使用 `concurrent.futures.ProcessPoolExecutor` 实现多进程并行
- 默认4个worker，可通过 `--parallel` 参数调整
- 设为1禁用并行（调试用）

**修改文件**：
- `scripts/understand/render_clips.py`
  - 添加 `render_all_clips_parallel()` 方法
  - 添加独立渲染函数 `render_single_clip_standalone()` 及辅助函数
  - 添加 `--parallel` 命令行参数

**使用方法**：
```bash
# 默认4个并行worker
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名

# 指定8个并行worker
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名 --parallel 8

# 串行模式（调试用）
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名 --parallel 1
```

**预期效果**：
- 渲染时间：5分钟 → 1.5分钟（4个worker）
- 节省：约3.5分钟/项目

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

### 9. 全局Timeout配置排查与处理 **📋 待处理**

**问题描述**：
项目中存在多处timeout设置，超时后的处理逻辑不一致，需要统一排查和规范。

**当前已发现的Timeout配置**：

| 位置 | Timeout值 | 超时处理方式 | 问题 |
|------|-----------|-------------|------|
| `scripts/config.py` - TrainingConfig.REQUEST_TIMEOUT | 120秒 | 抛出异常 | AI分析请求超时 |
| `scripts/analyze_gemini.py:177` | REQUEST_TIMEOUT | 抛出异常 | 同上 |
| `scripts/analyze_gemini.py:278` | REQUEST_TIMEOUT+60 | 抛出异常 | 异步分析结果超时 |
| `scripts/understand/understand_skill.py:151` | 60秒 | 抛出异常 | 技能加载请求超时 |
| `scripts/understand/analyze_segment.py:719` | 60秒 | 抛出异常 | 片段分析请求超时 |
| `scripts/understand/smart_cut_finder.py:156` | 60秒 | 抛出异常 | 静音检测FFmpeg超时 |
| `scripts/understand/render_clips.py:1708` | 600秒(10分钟) | 返回原文件 | 视频压缩超时 |
| `scripts/understand/render_clips.py:1731` | 600秒(10分钟) | 返回原文件 | 二次压缩超时 |
| `scripts/understand/render_clips.py:1780` | 30秒 | 抛出异常 | 其他FFmpeg操作超时 |
| `scripts/understand/video_understand.py:729` | 10秒 | 打印错误 | 清理命令超时 |
| `scripts/asr_transcriber.py:84` | 30秒 | 抛出异常 | ASR转录超时 |
| `scripts/setup_gpu_accel.py` | 5-10秒 | 打印警告 | GPU设置命令超时 |

**需要添加Timeout的模块**（当前无超时保护）：
- ❌ `scripts/preprocess/sensitive_detector.py` - 敏感词检测（OCR+ASR）
- ❌ `scripts/preprocess/ocr_subtitle.py` - OCR字幕识别
- ❌ `scripts/preprocess/subtitle_detector.py` - 字幕区域检测
- ❌ `scripts/preprocess/video_cleaner.py` - 视频马赛克处理
- ❌ `scripts/detect_ending_credits.py` - 片尾检测
- ❌ `scripts/asr_analyzer.py` - ASR分析

**待处理任务**：
- [ ] 排查所有timeout设置点
- [ ] 敏感词检测模块添加timeout（OCR、FFmpeg操作）
- [ ] 片尾检测模块添加timeout
- [ ] 统一超时处理策略（重试？降级？告警？）
- [ ] 添加超时配置化（支持命令行参数）
- [ ] 添加超时监控和日志
- [ ] 实现断点续传（超时后能从中断处继续）

**建议的超时处理策略**：
1. **AI分析请求**（120秒）：增加重试机制（当前已有MAX_RETRIES=3）
2. **FFmpeg操作**（600秒）：返回原文件或中间结果，记录日志
3. **网络请求**（60秒）：增加重试和降级策略
4. **清理操作**（10秒）：打印警告，不阻塞主流程
5. **OCR/视频处理**：添加120-300秒超时，返回空结果或跳过

**实现建议**：
```python
# 统一的超时处理装饰器
def timeout_handler(timeout_seconds, fallback_value=None, max_retries=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except TimeoutError:
                    if attempt == max_retries - 1:
                        if fallback_value is not None:
                            return fallback_value
                        raise
                    print(f"  ⚠️ 超时，重试 {attempt+1}/{max_retries}...")
            return None
        return wrapper
    return decorator
```

---

### 6. 整体流程提效

**当前耗时分析**（示例：2个项目各5个剪辑）：
- AI分析：约20分钟
- 片尾检测：约15分钟
- 渲染：约20分钟
- 总计：约55分钟

**提效方案**：
- 片尾检测提前到分析阶段（已完成 ✅）
- 渲染多线程并行（已完成 ✅）
- 使用更快的ASR模型
- 缓存复用：避免重复检测

---

### 7. 视频大小控制

**问题描述**：
- 当前渲染的视频通常几百MB，广告投放素材一般不超过100MB
- 需要控制输出视频大小

**当前状态**：
- ✅ 已实现压缩脚本（CRF 28，约1/5大小）
- ✅ V17已实现 `--compress` 和 `--compress-target` 参数

**优化方案**：
- 渲染时自动压缩：添加 `--compress` 参数
- 默认压缩到目标大小（如100MB以内）
- 支持多种质量档位：低(50MB)、中(100MB)、高(200MB)

**实现建议**：
- 修改 `render_clips.py`，添加压缩参数
- 计算合理比特率：`target_bitrate = target_size_bytes * 8 / duration_seconds`
- 使用Two-Pass编码提高压缩质量

---

### 8. ASR 并行提取和缓存复用 **✅ 已完成 (V15.9)**

**状态**: ✅ 已完成 (2026-03-11)

**问题描述**：
- 当前 `load_episode_data()` 中的 ASR 提取是串行的，每集 30-60秒
- 片尾检测阶段 `_auto_detect_ending_credits()` 又重新做 ASR - 重复工作！
- 10集项目 ASR 耗时 ~8分钟

**解决方案 (V15.9)**：
1. **ASR 并行提取**：
   - 使用 `ThreadPoolExecutor` 并行提取多集 ASR
   - `max_workers=4`（建议不超过4，避免内存不足）
   - 自动检测缓存，跳过已存在的 ASR

2. **片尾检测缓存复用**：
   - 修改 `_auto_detect_ending_credits()` 方法
   - 先检查 ASR 缓存是否存在
   - 如果存在，直接使用缓存，不做重复转录

3. **命令行支持**：
   - `detect_ending_credits.py` 添加 `--use-cached-asr` 参数

**预期效果**：
- ASR 提取时间：8分钟 → 2分钟（4个worker，75% 提升）
- 片尾检测时间：3分钟 → 瞬间（使用缓存，97% 提升）
- 总节省：约 9 分钟/项目

**修改文件**：
- `scripts/understand/video_understand.py`
  - 新增 `extract_asr_parallel()` 函数
  - 新增 `_extract_single_episode_asr()` 辅助函数
  - 修改 `load_episode_data()` 支持并行 ASR 提取
- `scripts/understand/render_clips.py`
  - 修改 `_auto_detect_ending_credits()` 复用 ASR 缓存
- `scripts/detect_ending_credits.py`
  - 添加 `--use-cached-asr` 参数
- `test/test_asr_parallel_and_cache.py` - 测试脚本

**使用方法**：
```bash
# 1. ASR 并行提取（默认启用，4个worker）
python -m scripts.understand.video_understand "漫剧素材/项目名"

# 2. 片尾检测缓存复用（自动启用）
python -m scripts.understand.render_clips data/.../项目名 漫剧素材/项目名

# 3. 独立片尾检测（使用缓存）
python -m scripts.detect_ending_credits 漫剧素材/项目名 --use-cached-asr
```

---

## 📝 未来规划与架构设计

### 1. [FEATURE-FUTURE] 视频画面内容审核与马赛克遮盖

**状态**: 📋 调研阶段
**优先级**: P2 - 中优先级
**调研日期**: 2026-03-12
**调研文档**: `docs/video_censor_research.md`

**需求背景**:
- 当前V16已实现**字幕敏感词检测**（文字层面）
- 新需求：**画面层面的违规内容检测**（色情、血腥等）
- 不同于字幕检测，画面检测需要AI视觉识别

**技术方案对比**:

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| 商业API（阿里云/腾讯云） | 识别准确率99%+，稳定 | 付费（¥0.03/分钟） | ⭐⭐⭐⭐⭐ |
| 开源模型（YOLOv8+NSFW） | 免费，可定制 | 精度较低，需训练 | ⭐⭐⭐ |
| 混合方案 | 成本与效果平衡 | 实现复杂 | ⭐⭐⭐⭐ |

**推荐实施路径**:

```
Phase 1（1-2周）: 人脸马赛克
  └── 技术成熟，实现简单
  └── 适用于：演员遮盖、隐私保护

Phase 2（2-3周）: 接入商业API
  └── 覆盖全面：色情、暴恐、政治敏感
  └── 适用于：全面内容审核

Phase 3（可选4-8周）: 自建模型
  └── 降低成本，长期可控
  └── 适用于：大流量场景
```

**待办事项**:
- [ ] 评估商业API成本与预算
- [ ] Phase 1: 实现人脸马赛克功能
- [ ] Phase 2: 接入视频审核API
- [ ] 测试不同方案的识别准确率
- [ ] 与现有V16字幕审核模块整合

---

### 2. [ARCH-FUTURE] OpenClaw客户端架构与远程维护

**状态**: 📋 架构规划阶段
**优先级**: P1 - 高优先级
**规划日期**: 2026-03-12

**背景**:
项目未来将通过 **OpenClaw** 作为客户端本地运行，需要考虑：
1. 远程维护与升级机制
2. 多客户部署与管理
3. 状态监控与日志收集

**核心功能需求**:

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 远程升级 | 客户端自动更新到最新版本 | P0 |
| 版本管理 | 支持多版本并存，可回滚 | P0 |
| 配置管理 | 远程推送配置、敏感词库更新 | P1 |
| 状态监控 | 实时监控客户端运行状态 | P1 |
| 日志收集 | 远程收集客户端日志 | P2 |
| 任务调度 | 远程下发任务、查看进度 | P1 |

**远程升级方案**:

| 方案 | 实现方式 | 优点 | 缺点 |
|------|---------|------|------|
| Git仓库拉取 | 客户端定时git pull | 简单 | 需要暴露git仓库 |
| HTTP分发 | 服务端提供版本文件下载 | 灵活 | 需要实现下载逻辑 |
| Docker镜像 | 镜像版本管理 | 一致性好 | 需要Docker环境 |

**待办事项**:
- [ ] 设计服务端API（版本管理、配置推送）
- [ ] 客户端自动更新机制实现
- [ ] 配置远程推送功能
- [ ] 状态监控上报功能
- [ ] 日志收集与查看功能

---

### 3. [ARCH-FUTURE] 多客户缓存共享机制

**状态**: 📋 架构规划阶段
**优先级**: P1 - 高优先级
**规划日期**: 2026-03-12

**需求背景**:
- 未来系统可能卖给多个短剧客户
- 不同客户可能处理**同一部剧**（如热门短剧）
- 第一次分析需要调用AI API（付费）
- 后续可直接使用缓存，**零成本**

**缓存共享架构设计**:

| 缓存类型 | 可共享 | 安全性 |
|---------|-------|--------|
| 关键帧 (keyframes) | ✅ 可共享 | 高（原始素材） |
| 音频 (audio) | ✅ 可共享 | 高（原始素材） |
| ASR转录 | ✅ 可共享 | 高（原始素材） |
| AI分析结果 | ✅ 可共享 | 高（通用知识） |
| 渲染成品 (clips) | ❌ 不共享 | 商业价值 |
| 技能文件 (skills) | ✅ 可共享 | 高（通用知识） |

**实现方案**:

```python
# 缓存命名规则
cache_key = f"{md5(video_file_path)}"  # 基于视频内容hash

# 示例
# 客户A处理 "漫剧素材/热门短剧/1.mp4" → hash=abc123
# 客户B处理 "漫剧素材/热门短剧/1.mp4" → hash=abc123
# → 自动命中缓存，无需重复AI分析
```

**待办事项**:
- [ ] 设计缓存目录结构（共享/私有分离）
- [ ] 实现基于内容hash的缓存键
- [ ] 实现缓存访问控制（隔离机制）
- [ ] 实现缓存预热（客户A分析后，客户B可直接使用）
- [ ] 设计缓存清理策略（共享缓存定期清理）
- [ ] 考虑商业授权：哪些缓存可共享，哪些需要授权

---

### 4. [FEATURE-FUTURE] 敏感词库远程更新

**状态**: 📋 规划阶段
**优先级**: P1 - 高优先级
**规划日期**: 2026-03-12

**需求**:
- 敏感词库需要远程更新（云端统一管理）
- 不同客户可能有不同的敏感词要求
- 支持热更新，无需重启服务

**待办事项**:
- [ ] 云端敏感词库管理API
- [ ] 客户端定期检查更新机制
- [ ] 支持热更新（不中断服务）
- [ ] 版本回滚能力
- [ ] 客户自定义敏感词（叠加在全局词库上）

---

## 📝 更新日志

- **2026-03-12**: 📋 记录未来规划 - 画面审核模块、OpenClaw远程维护、多客户缓存共享机制
- **2026-03-11**: ✅ V15.9 - ASR 并行提取和缓存复用优化完成
- **2026-03-10**: 📋 记录V16待优化功能 - 剪辑筛选、片尾检测优化、渲染并行、空间管理、视频压缩等
