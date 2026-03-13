# AI 短剧剪辑系统 - 整体架构文档

本文档介绍杭州雷鸣 AI 短剧剪辑服务的整体架构，包含完整的模块说明和函数调用关系。

---

## 一、整体流程概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI 短剧剪辑系统                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐ │
│   │   训练流程        │     │   视频理解流程     │     │   渲染流程        │ │
│   │  (Training)      │     │ (Video Understand)│     │   (Rendering)   │ │
│   └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘ │
│            │                         │                         │            │
│            ▼                         ▼                         ▼            │
│   Excel标记 + 视频 ──▶ 技能文件 ──▶ 新剧视频 ──▶ 分析结果 ──▶ 成品剪辑   │
│   (人工标注)              (AI模型)      (输入)        (JSON)      (MP4)    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 三大流程说明

| 流程 | 输入 | 输出 | 目的 |
|-----|------|------|------|
| **训练流程** | Excel人工标记 + 视频 | 技能文件(MD+JSON) | 让AI学会识别高光点和钩子点 |
| **视频理解流程** | 视频 + 技能文件 | 分析结果(JSON) | 自动识别新剧的高光点和钩子点 |
| **渲染流程** | 分析结果 + 视频 | 成品剪辑(MP4) | 渲染出可发布的短视频 |

---

## 二、训练流程详解

### 2.1 流程图

```
Excel人工标记 ──┬──▶ 提取关键帧 ──▶ ASR转录 ──▶ AI分析 ──▶ 技能文件
                │      (FFmpeg)    (Whisper)  (Gemini)      (MD+JSON)
                │
                └──▶ 提取上下文 ──▶ 合并技能
```

### 2.2 核心模块

#### 训练主入口
- **文件**: `scripts/train.py`
- **功能**: 协调整个训练流程
- **主要函数**:
  - `train()`: 主训练函数

#### 数据提取模块
- **文件**: `scripts/extract_keyframes.py`
- **功能**: 使用FFmpeg提取视频关键帧
- **主要函数**:
  - `extract_keyframes(video_path, output_dir, fps=1.0)`: 提取关键帧
  - `detect_video_fps(video_path)`: 检测视频帧率

- **文件**: `scripts/extract_asr.py`
- **功能**: 使用Whisper进行语音转录
- **主要函数**:
  - `extract_asr(video_path, output_path, model='base')`: ASR转录

#### AI分析模块
- **文件**: `scripts/analyze_gemini.py`
- **功能**: 调用Gemini API分析标记点特征
- **主要函数**:
  - `analyze_marking(marking, context_frames, context_asr)`: 分析单个标记点
  - `analyze_batch(markings, context_data)`: 批量分析

#### 技能合并模块
- **文件**: `scripts/merge_skills.py`
- **功能**: 合并多项目技能，自动类型简化
- **主要函数**:
  - `merge_skills(skill_files, output_path)`: 合并技能文件
  - `simplify_types(skills)`: 自动简化类型

---

## 三、视频理解流程详解

### 3.1 流程图

```
新剧视频 ──┬──▶ 提取关键帧+ASR ──▶ 片段提取 ──▶ AI分析 ──▶ 质量筛选 ──▶ 剪辑生成 ──▶ 保存结果
           │      (FFmpeg+Whisper)  (分片段)    (Gemini)   (多维度)    (笛卡尔积)    (JSON)
           │
           └──▶ 片尾检测 (提前到理解阶段)
```

### 3.2 核心模块

#### 主入口模块
- **文件**: `scripts/understand/video_understand.py`
- **功能**: 视频理解主入口，协调整个流程
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `video_understand(project_path, skill_file)` | 主入口函数，协调整个视频理解流程 |
| `load_episode_data(project_path, auto_extract)` | 加载或提取单集数据(关键帧+ASR) |
| `extract_asr_parallel(episode_files, project_name)` | 并行提取多集ASR |
| `detect_project_endings_in_understand_phase(project_path)` | 提前检测片尾(理解阶段) |
| `cleanup_project_cache(project_name, min_age_hours)` | 清理项目缓存 |

#### 技能理解模块
- **文件**: `scripts/understand/understand_skill.py`
- **功能**: 解析技能文件
- **主要函数**:
  - `load_skill(skill_path)`: 加载技能文件(MD+JSON)
  - `parse_skill_framework(skill_text)`: 解析技能框架

#### 片段提取模块
- **文件**: `scripts/understand/extract_segments.py`
- **功能**: 将视频切分为分析片段
- **主要函数**:
  - `extract_segments(video_path, segment_duration=30)`: 提取分析片段

#### AI分析模块
- **文件**: `scripts/understand/analyze_segment.py`
- **功能**: 使用Gemini API分析视频片段
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `smart_select_keyframes(frames, count)` | 智能选择关键帧(场景变化大的优先) |
| `build_analyze_prompt(segment, skill)` | 构建分析Prompt |
| `analyze_segment(segment, skill, video_path)` | 分析单个片段 |
| `analyze_all_segments(segments, skill, video_path)` | 批量分析所有片段 |

#### 质量筛选模块
- **文件**: `scripts/understand/quality_filter.py`
- **功能**: 多维度质量筛选
- **主要函数**:
  - `filter_by_confidence(analysis_results, threshold=7.0)`: 置信度筛选
  - `filter_by_dedup(analysis_results, window=10)`: 去重筛选
  - `filter_by_count_per_episode(analysis_results, max_per_episode=2)`: 集内数量控制

#### 剪辑生成模块
- **文件**: `scripts/understand/generate_clips.py`
- **功能**: 生成高光×钩子剪辑组合
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `generate_clips(highlights, hooks)` | 生成笛卡尔积剪辑组合 |
| `deduplicate_highlights(highlights, window)` | 高光点去重 |
| `deduplicate_hooks(hooks, window)` | 钩子点去重 |
| `save_clips(clips, output_path)` | 保存剪辑结果到JSON |
| `sort_and_filter_clips(clips, top_n)` | 排序+筛选Top N |

#### 时间戳优化模块
- **文件**: `scripts/understand/timestamp_optimizer.py`
- **功能**: 优化高光点和钩子点的时间戳
- **主要函数**:
  - `adjust_highlight_point(timestamp, asr_segments)`: 调整高光点到句子开始
  - `adjust_hook_point(timestamp, asr_segments)`: 调整钩子点到句子结束

#### 智能切割点查找模块
- **文件**: `scripts/understand/smart_cut_finder.py`
- **功能**: 多维度智能切割点查找
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `find_sentence_end(timestamp, asr_segments)` | 找到包含时间点的整句话结束时间 |
| `find_sentence_start(timestamp, asr_segments)` | 找到包含时间点的整句话开始时间 |
| `detect_silence_regions(video_path, start, end)` | 检测静音区域 |
| `find_optimal_cut_point(hook_timestamp, asr, video_path, fps)` | 综合决策最优切割点 |

---

## 四、渲染流程详解

### 4.1 流程图

```
分析结果(JSON) ──┬──▶ 加载视频 ──▶ 智能切割点 ──▶ 裁剪片段 ──▶ 拼接片段 ──▶ 添加片尾 ──▶ 添加花字 ──▶ 输出MP4
                 │    (VideoFile)   (优化时间戳)   (FFmpeg)    (FFmpeg)    (FFmpeg)    (FFmpeg)
                 │
                 └──▶ 片尾检测 (如缓存不存在)
```

### 4.2 核心模块

#### 渲染主入口
- **文件**: `scripts/understand/render_clips.py`
- **功能**: 视频渲染主入口
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `ClipRenderer.__init__()` | 初始化渲染器 |
| `ClipRenderer.render_all_clips()` | 渲染所有剪辑(支持并行) |
| `ClipRenderer.render_all_clips_parallel()` | 多进程并行渲染 |
| `render_single_clip_standalone()` | 独立渲染单个剪辑(支持并行) |

#### 统一渲染函数
- **文件**: `scripts/understand/render_clips.py`
- **功能**: 统一的渲染逻辑(单次编码优化)
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `_render_clip_unified_standalone()` | 统一渲染入口 |
| `_clip_to_segments_standalone()` | 将跨集剪辑拆分为片段 |
| `_trim_segment_standalone()` | 裁剪单个片段 |
| `_concat_segments_standalone()` | 拼接片段 |
| `_preprocess_ending_video_standalone()` | 预处理结尾视频(帧率转换) |
| `_concat_videos_standalone()` | 拼接多个视频 |

#### 片尾处理
- **文件**: `scripts/understand/render_clips.py`
- **功能**: 片尾检测和拼接
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `_auto_detect_ending_credits()` | 自动检测片尾(渲染阶段) |
| `_append_ending_video_standalone()` | 追加结尾视频 |
| `detect_ending_credits()` | 独立片尾检测脚本 |

- **文件**: `scripts/detect_ending_credits.py`
- **功能**: 独立片尾检测脚本(双层检测)
- **主要函数**:
  - `detect_ending_credits(video_path)`: 检测片尾时间点

- **文件**: `scripts/asr_analyzer.py`
- **功能**: ASR分析(片尾检测用)
- **主要函数**:
  - `analyze_ending_asr(asr_path)`: 分析ASR找片尾关键词

#### 花字叠加模块
- **文件**: `scripts/understand/video_overlay/video_overlay.py`
- **功能**: 视频花字叠加(热门短剧+剧名+免责声明)
- **主要函数**:

| 函数名 | 功能说明 |
|--------|----------|
| `VideoOverlayRenderer.apply_overlay()` | 应用花字叠加 |
| `_build_drawtext_filter()` | 构建drawtext滤镜 |

- **文件**: `scripts/understand/video_overlay/tilted_label.py`
- **功能**: 倾斜角标生成
- **主要函数**:
  - `TiltedLabelRenderer.render()`: 渲染倾斜角标PNG

- **文件**: `scripts/understand/video_overlay/overlay_styles.py`
- **功能**: 样式定义(10种预设样式)
- **主要类**:
  - `OverlayStyle`: 样式数据结构
  - `get_style_by_id(style_id)`: 获取样式
  - `get_random_style()`: 随机样式

---

## 五、数据结构说明

### 5.1 核心数据结构

#### 高光点/钩子点 (SegmentAnalysis)
```python
@dataclass
class SegmentAnalysis:
    episode: int           # 集数
    start: float          # 开始时间(秒)
    end: float            # 结束时间(秒)
    type: str             # 类型: highlight/hook
    sub_type: str         # 子类型
    confidence: float     # 置信度(0-10)
    description: str     # 描述
```

#### 剪辑组合 (Clip)
```python
@dataclass
class Clip:
    highlight: SegmentAnalysis  # 高光点
    hook: SegmentAnalysis      # 钩子点
    hookEpisode: int           # 钩子点所在集数
    duration: float            # 预期时长
```

#### 分析结果 (VideoAnalysis)
```python
@dataclass
class VideoAnalysis:
    project_name: str
    highlights: List[SegmentAnalysis]
    hooks: List[SegmentAnalysis]
    clips: List[Clip]
```

---

## 六、关键配置文件

### 6.1 项目配置
- **文件**: `scripts/config.py`
- **内容**: 项目路径、API配置等

### 6.2 敏感词配置
- **文件**: `config/sensitive_words.txt`
- **内容**: 敏感词列表(用于OCR+ASR检测)

### 6.3 技能文件
- **位置**: `data/skills/`
- **内容**: AI分析用的技能框架(MD+JSON)

---

## 七、缓存机制

### 7.1 缓存目录

```
data/cache/
├── keyframes/          # 关键帧缓存
│   └── 项目名/
│       └── 集数/
├── asr/                # ASR转录缓存
│   └── 项目名/
│       └── 集数.json
└── audio/              # 音频缓存
    └── 项目名/
        └── 集数.mp4
```

### 7.2 片尾缓存
```
data/ending_credits/
└── 项目名_ending_credits.json
```

### 7.3 花字样式缓存
```
.overlay_style_cache/
└── style_{project_hash}.json
```

---

## 八、命令行接口

### 8.1 视频理解
```bash
python -m scripts.understand.video_understand "漫剧素材/项目名"
```

### 8.2 渲染剪辑
```bash
# 基础渲染（V17: 默认启用花字叠加）
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名

# 添加片尾
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名 --add-ending

# 禁用花字（V17新增）
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名 --no-overlay

# 完整参数
python -m scripts.understand.render_clips data/analysis/项目名 漫剧素材/项目名 \
    --add-ending --parallel 4
```

### 8.3 片尾检测
```bash
python -m scripts.detect_ending_credits "视频路径.mp4"
```

---

## 九、版本历史

| 版本 | 日期 | 主要变更 |
|-----|------|----------|
| V17.8 | 2026-03-13 | 修复第1集第0秒重复高光点问题 |
| V17.7 | 2026-03-13 | 渲染分辨率优化：360p/480p保持原分辨率，720p及以上统一720p |
| V17.6 | 2026-03-12 | 渲染性能优化：CRF=23，花字叠加默认启用 |
| V17.5 | 2026-03-12 | 修复跨集剪辑渲染问题 |
| V17 | 2026-03-12 | 剪辑组合排序与智能筛选 |
| V16 | 2026-03-11 | OCR+ASR敏感词检测、渲染多线程并行 |
| V15 | 2026-03-05 | 视频花字叠加功能 |
| V14 | 2026-03-05 | 片尾视频拼接功能 |
| V13 | 2026-03-05 | 片尾检测双层架构 |
| V12 | 2026-03-03 | 笛卡尔积剪辑生成 |

---

## 十、维护指南

### 10.1 添加新功能

1. **确定模块位置**: 根据功能选择合适模块
2. **实现函数**: 在对应模块中添加函数
3. **更新入口**: 在主入口函数中调用新功能
4. **更新文档**: 更新本文档和CHANGELOG

### 10.2 调试技巧

1. 使用 `--parallel 1` 禁用并行，查看单线程日志
2. 使用 `--no-cleanup` 保留中间缓存
3. 查看 `clips/` 目录的中间文件

### 10.3 性能优化

1. **并行渲染**: 使用 `--parallel 4` 启用多进程
2. **缓存复用**: 避免重复提取关键帧和ASR
3. **单次编码**: V17.1+ 使用单次编码优化

---

*本文档最后更新: 2026-03-12*
