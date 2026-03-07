# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

杭州雷鸣 AI 短剧剪辑服务 - An AI-powered video editing service that automatically identifies "highlights" (高光点) and "hooks" (钩子点) in short drama series to create engaging clips for social media.

**Core Business Model**: Serverless service running through OpenClaw backend. Clients only need to deploy OpenClaw to use the service.

**Key Concepts**:
- **高光点 (Highlight)**: A moment from which viewers are more willing to continue watching (used as clip start point)
- **钩子点 (Hook)**: A moment where sudden ending makes viewers eager to know what happens next (used as clip end point)
- **剪辑组合 (Clip Combination)**: Highlight (start) → Hook (end) combination

## Common Commands

### Video Understanding (Main Workflow)
```bash
# Run complete video understanding pipeline
python -m scripts.understand.video_understand "漫剧素材/项目名" --skill-file "ai-drama-clipping-thoughts-v0.4.md"

# With auto-extraction of keyframes and ASR (recommended)
python -m scripts.understand.video_understand "漫剧素材/项目名"
```

### Clip Rendering (V14+)
```bash
# Basic rendering (with auto ending detection enabled by default)
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名

# Add ending video
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending

# Force re-detect ending credits
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --force-detect

# Skip ending detection
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --skip-ending

# Add overlay text (V15)
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay
```

### Training Pipeline
```bash
# Check data extraction progress
python -m scripts.check_progress

# Batch extract data for all projects
python -m scripts.batch_extract_data

# Run complete training pipeline
python -m scripts.full_training_pipeline

# Individual training steps
python -m scripts.train [options]

# 训练命令选项说明:
# --projects "项目名"     指定要处理的项目
# --force-reextract       强制重新提取关键帧和ASR
# --skip-analysis         跳过AI分析（仅提取数据）
# --resume                从上次中断处继续
# --no-cleanup            项目完成后不清理中间缓存

# 视频理解流程 (分析整部剧)
python -m scripts.understand.video_understand "漫剧素材/项目名" [技能文件]

# 渲染剪辑视频
python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/项目名 漫剧素材/项目名

# 缓存清理说明:
# - 默认情况下，分析/渲染完成后会自动清理中间缓存（关键帧、音频、ASR）
# - 使用 --no-cleanup 参数可跳过清理（调试用）
# - 只保留: 原始视频(漫剧素材/) + 成品(clips/) + 技能文件(skills/)
```

### Testing and Verification
```bash
# Verify data integrity
python -m scripts.verify_data

# Test video understanding
python -m scripts.understand.video_understand "漫剧素材/百里将就" --skill-file "ai-drama-clipping-thoughts-v0.4.md"

# Detect ending credits for a video
python -m scripts.detect_ending_credits "path/to/video.mp4"
```

## Architecture

### Data Flow (High-Level)

```
Training Phase:
Excel Markings → Keyframes + ASR → AI Analysis → Skill File (MD + JSON)

Understanding Phase:
Video Files → Keyframes + ASR → Segment Analysis → Quality Filter → Clip Generation → Render
```

### Core Modules

**Training Pipeline** (`scripts/`):
- `train.py` - Main training orchestration
- `extract_keyframes.py` - FFmpeg-based keyframe extraction (auto-detects FPS)
- `extract_asr.py` - Whisper-based audio transcription
- `analyze_gemini.py` - Gemini API analysis for pattern recognition
- `merge_skills.py` - Skill file generation with automatic type simplification

**Video Understanding** (`scripts/understand/`):
- `video_understand.py` - Main entry point for understanding new videos
- `understand_skill.py` - Parse and understand skill files
- `extract_segments.py` - Extract analysis segments from video
- `analyze_segment.py` - AI-powered segment analysis (uses Gemini with vision)
- `generate_clips.py` - Cartesian product clip generation (highlight × hook)
- `quality_filter.py` - Multi-stage quality filtering pipeline
- `render_clips.py` - FFmpeg-based clip rendering with ending detection

**Ending Credits Detection** (`scripts/`):
- `detect_ending_credits.py` - V13: Dual-layer detection (visual similarity + ASR)
- `asr_analyzer.py` - ASR-based ending detection with plot keyword analysis

**Video Overlay** (`scripts/understand/video_overlay/`):
- V15 feature for adding overlay text/text effects to clips

### Critical Technical Details

#### Frame Rate Handling (V14.2+)

**CRITICAL**: Different projects have different frame rates (25fps, 30fps, 50fps detected across 12 projects). The entire pipeline must auto-detect and use actual FPS:

1. **Keyframe Extraction**: Adjusts sampling density based on actual FPS
   - 50fps: fps=2.0 (denser sampling)
   - 30fps: fps=1.0 (standard)
   - 25fps: fps=0.5 (lighter sampling)

2. **Clip Rendering**: Uses actual FPS for frame-accurate clipping
   ```python
   # Auto-detect FPS
   fps = self.video_files[segment.episode].fps
   # Convert time to frames using ACTUAL fps
   total_frames = math.ceil(end_time * fps)
   # Use -frames:v for frame-accurate clipping
   cmd = ['-frames:v', str(total_frames)]
   ```

**Files affected**:
- `scripts/extract_keyframes.py` - Pass `video_actual_fps` parameter
- `scripts/understand/video_understand.py` - Detect and adjust extraction FPS
- `scripts/understand/render_clips.py` - VideoFile.fps field, auto-detect FPS

#### Ending Credits Detection (V13-V14.7)

**Dual-layer architecture**:
1. **Layer 1 (Visual)**: Frame similarity detection (`detect_ending_credits.py`)
2. **Layer 2 (ASR)**: Whisper transcription + plot keyword analysis (`asr_analyzer.py`)

**V14.7 Critical Fixes**:
- **浮点精度保持**: `Dict[int, int]` → `Dict[int, float]`，避免int()转换丢失ASR内容
  - V14.6: `int(effective_duration)` 导致259.94秒变成259秒，**丢失0.94秒**
  - V14.7: 保持浮点精度，ASR内容完整保留 ✅
- **缓存加载逻辑修复**: 修复`_should_detect_ending()`逻辑，确保effective_duration正确应用
  - V14.6: 缓存存在时返回False，导致缓存未加载 ❌
  - V14.7: 直接返回`auto_detect_ending`，确保缓存正确加载 ✅

**V14.6 Key Improvements**:
- **ASR安全缓冲区**: 从V14.4的3.0秒优化到0.15秒（恢复完美版本参数）
- **去除3秒阈值**: 只要检测到画面相似度就剪掉，不管多短
- **修复long_asr误判**: 检查最后静音是否>2秒，避免把片尾音乐误判为剧情
- **自动适配**: 有片尾的剧自动剪裁，无片尾的剧保持完整

**ASR Analysis Logic (V14.7)**:
- Check last 10 seconds for ASR segments
- Detect plot keywords (30+ keywords for drama content)
- **ASR_SAFETY_BUFFER = 0.15s**: Preserve sentence tail/intonation
- **Float precision**: All duration calculations use float to avoid precision loss
- **Smart pattern handling**:
  - `mixed`: Cut based on silence duration (max 1.0-3.0s)
  - `long_asr_no_silence`: Check trailing silence > 2s to detect ending music
  - `no_asr_only_bgm`: Conservative cutting (max 2.0s)
  - `short_asr_long_silence`: Cut silence beyond buffer

**Full Pipeline Integration**:
- `render_clips.py`: Default `auto_detect_ending=True`
- Automatic cache loading and application (V14.7 fixed)
- Per-episode effective duration: `total_duration - ending_duration` (float precision)
- No ending = no cutting: `effective_duration = total_duration`

#### Video Overlay (V15+, V6倾斜角标更新, V2.1花字叠加更新)

**Three-layer text overlay**:
1. **热门短剧** (Hot Drama): 动态字体大小，倾斜45度角标，右上角/左上角交替
2. **剧名** (Drama Title): 动态字体大小，底部居中，白色/淡紫色随机
3. **免责声明** (Disclaimer): 动态字体大小，底部居中，剧名下方

**视频分辨率自适应 (V6倾斜角标更新)**:

项目视频分辨率统计：
- 360×640 (竖屏标清): 46个视频
- 1080×1920 (竖屏高清): 50个视频
- 640×360 (横屏标清): 4个视频

**动态缩放策略 (V6版本 - 倾斜角标)**:
- 使用**平方根缩放**：字体大小变化更平缓，不会因分辨率差异过大
- 公式：`font_size = 基准值 × √(video_width / 360) × 0.8`
- 位置使用**固定百分比**：
  - X位置：视频宽度的25%处（右边留25%空间）
  - Y位置：视频高度的8%处（顶部留8%空间）

**动态字体策略 (V2.1版本 - 花字叠加)**:
- 基于**视频原有字幕大小**作为参考基准（17px@360p）
- 使用**平方根缩放**计算动态字体大小
- 热门短剧 = 字幕×1.5倍（更醒目）
- 剧名 = 字幕×1.2倍（略大）
- 免责声明 = 字幕×0.9倍（不抢镜）

**分辨率适配效果 (V2.1)**:
| 分辨率 | scale_factor | sqrt_scale | 热门短剧 | 剧名 | 免责声明 |
|--------|-------------|------------|---------|------|----------|
| 360×640 竖屏 | 1.0x | 1.0x | 26px | 20px | 15px |
| 640×360 横屏 | 1.78x | 1.33x | 34px | 27px | 20px |
| 1080×1920 竖屏 | 3.0x | 1.73x | 44px | 35px | 28px |

**参数对照表**:
| 参数 | 360p | 1080p |
|-----|------|-------|
| 缩放比例 | 1.0x (sqrt:1.0) | 3.0x (sqrt:1.73) |
| 角标字体 | 17px | 52px |
| 剧名字体 | 14px | 24px |
| 位置X | 270 (75%处) | 810 (75%处) |
| 位置Y | -51 (8%处) | -153 (8%处) |

**Style system**:
- 10 preset styles: gold_luxury, red_passion, blue_cool, purple_mystery, green_fresh, orange_vitality, pink_romantic, silver_elegant, cyan_tech, retro_brown
- Project-level style unification: Cache style selection based on project name hash
- **Left-right alternation**: Hot drama alternates between left and right corners every 10 seconds
- **50% display time**: Hot drama displays for 10 seconds, hides for 10 seconds, repeats throughout video

**Technical implementation**:
- FFmpeg drawtext filter with **4 layers** (2 hot_drama + title + disclaimer)
- **Dual-layer approach**: Two separate hot_drama layers for left-right alternation
- PNG预渲染：预生成倾斜角标PNG，使用overlay滤镜叠加（高性能）
- Font detection: Prioritize Songti.ttc (macOS), fallback to system fonts
- 动态坐标：`y="h-{height*0.05}"` (title), `y="h-{height*0.028}"` (disclaimer)

**待解决问题**:
- [ ] 360p视频热门短剧角标仍偏小，需微调基准值
- [ ] 1080p视频热门短剧角标偏大，需进一步缩小

**Files affected**:
- `scripts/understand/video_overlay/tilted_label.py` - V6动态缩放版倾斜角标
- `scripts/understand/video_overlay/overlay_styles.py` - 10 preset style definitions
- `scripts/understand/video_overlay/video_overlay.py` - V2.1 FFmpeg命令构建，动态字体计算
- `test/test_complete_packaging.py` - 包装测试脚本

#### Quality Filter Pipeline

**Multi-stage filtering** (V8+):
1. Confidence threshold: >7.0 (adjustable)
2. Time deduplication: 10-second window
3. Same-type per episode limit: 1
4. Fixed opening highlight: Episode 1 at 0s (confidence 10.0)

### Data Structures

**Core Types** (`scripts/data_models.py`):
```python
Marking            # Human annotation from Excel
KeyFrame           # Extracted frame with timestamp
ASRSegment         # Whisper transcription segment
MarkingContext     # Highlight: 10s forward, Hook: 10s backward
AnalysisResult     # AI analysis with multi-dimensional features
Clip               # Generated clip combination
```

### Configuration

**Project Configuration** (`scripts/config.py`):
- `PROJECTS`: List of ProjectConfig objects
- Each project has: name, video_path, excel_path
- Supports 14 projects across 3 directories (漫剧素材, 漫剧参考, 新的漫剧素材)

**Video File Naming**: Enhanced parser supports multiple formats:
- Pure numbers: `1.mp4`, `2.mp4`
- With prefix: `精准-1.mp4`, `机长姐姐-01.mp4`
- EP prefix: `ep01.mp4`, `EP1.mp4`
- Mixed format: `骨血灯_03_1080p.mp4`

## Output Structure

```
data/hangzhou-leiming/
├── skills/                    # Generated skill files
│   ├── ai-drama-clipping-thoughts-v1.0.md
│   ├── ai-drama-clipping-thoughts-latest.md
├── cache/                     # Extraction cache
│   ├── keyframes/            # Per-project/per-episode keyframes
│   ├── audio/                # Extracted audio files
│   └── asr/                  # Whisper transcription results
├── analysis/                 # Video understanding results
│   └── 项目名/
│       └── result.json       # Highlights, hooks, and clip combinations
├── ending_credits/           # V13+: Ending detection cache
│   └── 项目名_ending_credits.json
└── .overlay_style_cache/     # V15+: Overlay style cache
    └── style_{project_hash}.json
```

## Important Notes

### Version History Context

- **V15** (2026-03-05): Video overlay text effects (热门短剧, 剧名, 免责声明)
- **V14.7** (2026-03-05): **Critical fix** - Fixed int() conversion losing precision (0.94s) causing ASR content to be cut, fixed cache loading logic to ensure effective_duration is applied
- **V14.6** (2026-03-05): Ending detection fixes - removed 3s threshold, fixed long_asr misclassification, optimized buffer to 0.15s
- **V14.2** (2026-03-05): Frame rate auto-detection and precision fixes
- **V14.1** (2026-03-05): Automatic ending credits detection with caching
- **V14** (2026-03-05): Ending video splicing feature
- **V13** (2026-03-05): 100% accurate ending detection (ASR enhancement)
- **V12** (2026-03-03): Cartesian product clip generation

### Performance Characteristics

- **Recall rate**: ~29.5% (V11) to 50-60% (V5.0 target)
- **Precision**: ~17.8% (V11) - AI marks many false positives
- **Average markings**: ~1.0 per episode (human baseline)
- **Training data**: 14 projects, 117 episodes

### API Requirements

- **Gemini API Key**: Required for AI analysis (vision + text)
- **Environment variable**: `GEMINI_API_KEY`

### System Dependencies

- **FFmpeg**: Required for keyframe extraction, clip rendering, and video overlay
  - Must be compiled with `--enable-libfreetype` for drawtext filter support
  - Used for: keyframe extraction, clip rendering, overlay text effects
- **Whisper**: Required for ASR transcription
- **Python 3.8+**: Minimum Python version
- **System fonts**: Chinese font support for overlay text (auto-detected)

### File Path Patterns

- **Video files**: Must be in project directories (漫剧素材/, 漫剧参考/, etc.)
- **Excel files**: Human annotations in project folders
- **Cache**: Organized by cache project name (see `PROJECT_NAME_MAP` in config.py)
- **Output**: `clips/` directory for rendered videos (not in git)

## Testing Strategy

### Verification Checklist

When making changes to clip rendering or understanding:
1. Verify frame rate detection is working for different FPS videos
2. Check ending credits detection accuracy (visual + ASR)
3. Validate timestamp precision (should be frame-accurate)
4. Test cross-episode clip combinations
5. Verify quality filtering is not too aggressive

### Common Validation Commands

```bash
# Verify all project frame rates
python test/verify_all_project_fps.py

# Test ending detection on specific video
python -m scripts.detect_ending_credits "path/to/video.mp4"

# Re-analyze project with latest skill
python -m scripts.understand.video_understand "漫剧素材/项目名"
```

## Development Guidelines

### When Modifying Frame Handling

- **ALWAYS** auto-detect actual FPS using `ffprobe`
- **NEVER** assume 30fps for all videos
- Use `-frames:v` parameter instead of `-t` for frame-accurate clipping
- Pass `video_actual_fps` to keyframe extraction functions

### When Modifying Quality Filters

- Default confidence threshold: 7.0 (adjustable)
- Default dedup window: 10 seconds (same-type, same-episode)
- Default max per episode: 1 highlight + 1 hook per type
- Episode 1 always gets opening highlight at 0s

### When Adding New Features

1. Update version number in CHANGELOG.md
2. Document breaking changes in README.md
3. Add technical documentation to `docs/` directory
4. Test on multiple projects with different frame rates
5. Verify ending detection still works correctly

## Documentation Files

- `README.md` - Project overview and quick start
- `TRAINING_SPEC.md` - Detailed training workflow specification
- `CHANGELOG.md` - Version history and changes
- `docs/frame-rate-fix.md` - V14.2 frame rate handling details
- `scripts/README.md` - Script usage documentation
