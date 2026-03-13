# 敏感词字幕遮盖功能设计方案

> 文档版本: v2.0
> 创建日期: 2026-03-10
> 更新日期: 2026-03-12
> 状态: 已实现主流程，待集成到video_understand

---

## 一、功能概述（v2.0 更新）

### 1.0 实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 敏感词配置 | ✅ 已完成 | `config/sensitive_words.txt` |
| 敏感词检测模块 | ✅ 已完成 | `scripts/preprocess/sensitive_detector.py` |
| 字幕区域检测 | ✅ 已完成 | `scripts/preprocess/subtitle_detector.py` |
| OCR字幕识别 | ✅ 已完成 | `scripts/preprocess/subtitle_ocr.py` |
| 视频马赛克遮罩 | ✅ 已完成 | `scripts/preprocess/video_cleaner.py` |
| 主流程脚本 | ✅ 已完成 | `scripts/preprocess/sensitive_mask_workflow.py` |
| 集成到video_understand | ⏳ 待集成 | 未来工作 |

### 1.1 完整流程（三个步骤）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          完整处理流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: 敏感词遮罩预处理                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ python -m scripts.preprocess.sensitive_mask_workflow \          │   │
│  │     "漫剧素材/项目名" --output "干净素材/项目名"               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                         │
│  Step 2: AI分析（视频理解）                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ python -m scripts.understand.video_understand "干净素材/项目名"│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                         │
│  Step 3: 渲染剪辑                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ python -m scripts.understand.render_clips \                     │   │
│  │     data/analysis/项目名 "干净素材/项目名"                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 当前使用方法

```bash
# Step 1: 敏感词遮罩预处理
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名" --output "干净素材/项目名"

# Step 2: AI分析（视频理解）
python -m scripts.understand.video_understand "干净素材/项目名"

# Step 3: 渲染剪辑
python -m scripts.understand.render_clips data/analysis/项目名 "干净素材/项目名"
```

---

## 二、功能概述（原版）

### 1.1 需求背景

漫剧视频中可能包含敏感词字幕，需要在视频发布前进行处理，将包含敏感词的字幕区域进行遮盖。

### 1.2 核心目标

- 自动检测视频字幕中的敏感词
- 用马赛克遮盖包含敏感词的字幕区域
- 预处理一次，后续剪辑多次使用

### 1.3 设计原则

1. **预处理优先**：在分析阶段一次性处理，生成"干净"视频
2. **多层检测**：字幕区域检测提供多层备选方案
3. **配置简单**：敏感词使用TXT格式，方便编辑
4. **可追溯**：保留遮盖记录，方便审查

---

## 二、整体流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                   预处理流程（集成到分析阶段）                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ 读取敏感词配置 │    │  提取关键帧   │    │  提取ASR     │          │
│  │ (txt文件)    │    │              │    │              │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         │                   ▼                   │                   │
│         │         ┌──────────────────┐          │                   │
│         │         │ 字幕区域检测      │          │                   │
│         │         │ (Gemini → OCR    │          │                   │
│         │         │  → 默认比例)     │          │                   │
│         │         └────────┬─────────┘          │                   │
│         │                  │                    │                   │
│         │                  ▼                    │                   │
│         │         ┌──────────────────┐          │                   │
│         └────────→│ 敏感词匹配检测   │←─────────┘                   │
│                   │ (ASR文本匹配)    │                              │
│                   └────────┬─────────┘                              │
│                            │                                        │
│                            ▼                                        │
│                   ┌──────────────────┐                              │
│                   │ 是否有敏感词？    │                              │
│                   └────────┬─────────┘                              │
│                            │                                        │
│               ┌────────────┴────────────┐                          │
│               │ YES                     │ NO                        │
│               ▼                         ▼                          │
│    ┌──────────────────┐      ┌──────────────────┐                  │
│    │ 预处理视频        │      │ 复制原始视频      │                  │
│    │ (马赛克遮盖)      │      │ (不做处理)        │                  │
│    └────────┬─────────┘      └────────┬─────────┘                  │
│             │                         │                             │
│             ▼                         ▼                             │
│    ┌─────────────────────────────────────────────┐                  │
│    │     保存到: 漫剧素材_干净/项目名/            │                  │
│    │     + sensitive_mask.json (遮盖记录)        │                  │
│    └─────────────────────────────────────────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、字幕区域检测方案

### 3.1 四层检测策略

不同项目的字幕位置可能不同，采用四层备选方案：

| 优先级 | 方案 | 原理 | 适用场景 |
|--------|------|------|---------|
| **1** | 像素变化检测 | 分析多帧像素变化，变化大的区域=字幕 | 最可靠（置信度95%）|
| **2** | Gemini视觉分析 | AI识别字幕区域 | 备选方案 |
| **3** | OCR检测 | 检测文字密集区域 | AI失败但画面清晰 |
| **4** | 默认比例 | 底部10-12%区域 | 最后兜底 |

### 3.2 像素变化检测法（首选）

**原理**：
- 字幕区域的内容会随对话变化而变化（高方差）
- 固定文案/背景保持不变（低方差）

**步骤**：
1. 每2秒提取1帧（15-50帧）
2. 分析底部60%-100%区域的每行像素方差
3. 找出高方差的连续区域（聚类）
4. 选择最大的连续区域作为字幕区域

### 3.2 检测流程详解

```
Step 1: Gemini视觉分析
    ↓ 失败或置信度 < 0.8

Step 2: OCR检测 (PaddleOCR/EasyOCR)
    - 检测关键帧中的所有文字框
    - 筛选底部区域(>70%高度)的文字框
    - 计算文字框的包围盒作为字幕区域
    ↓ 失败或无文字

Step 3: 默认比例
    - y_ratio: 0.88 (字幕顶部位置)
    - height_ratio: 0.10 (字幕高度)
    ↓

Step 4: 保存配置 + 提示用户可手动修改
```

### 3.3 检测结果保存

```json
// data/hangzhou-leiming/analysis/项目名/subtitle_config.json
{
  "project_name": "项目名",
  "video_resolution": "1080x1920",
  "subtitle_region": {
    "y_ratio": 0.88,
    "height_ratio": 0.10
  },
  "detection_method": "gemini",  // 可选: "gemini", "ocr", "default"
  "confidence": 0.95,
  "note": "如果遮盖位置不准，可手动修改 y_ratio 和 height_ratio"
}
```

---

## 四、敏感词配置

### 4.1 配置文件格式

使用简单的TXT格式，每行一个敏感词：

```
# config/sensitive_words.txt
# 敏感词列表，每行一个词
# 更新时间：2026-03-10

敏感词1
敏感词2
敏感词3
...
```

### 4.2 格式选择原因

- ✅ 简单直接，一行一个
- ✅ Windows记事本完美支持
- ✅ 方便随时添加/删除
- ✅ 无需关心JSON格式问题

### 4.3 匹配规则

- **包含即覆盖**：只要ASR文本包含敏感词，就遮盖该时间段
- **大小写不敏感**：统一转小写后匹配
- **部分匹配**：如"出轨了"包含"出轨"，触发遮盖

---

## 五、马赛克遮盖实现

### 5.1 遮盖效果示意

```
┌─────────────────────────────────────────┐
│                                         │
│          视频主体内容                    │
│                                         │
├─────────────────────────────────────────┤
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │  ← 马赛克区域
│     （马赛克遮盖，看不清文字）            │
└─────────────────────────────────────────┘
```

### 5.2 FFmpeg命令

```bash
# 单个敏感词遮盖
ffmpeg -i input.mp4 \
  -filter_complex "
    [0:v]crop=w=iw:h=ih*0.10:y=ih*0.88[sub];
    [sub]boxblur=30:10[mosaic];
    [0:v][mosaic]overlay=y=H*0.88:enable='between(t,15.2,17.5)'
  " \
  -c:a copy \
  output.mp4

# 多个敏感词遮盖（叠加多个滤镜）
ffmpeg -i input.mp4 \
  -filter_complex "
    [0:v]crop=w=iw:h=ih*0.10:y=ih*0.88[sub1];
    [sub1]boxblur=30:10[mosaic1];
    [0:v][mosaic1]overlay=y=H*0.88:enable='between(t,15.2,17.5)'[v1];
    [v1]crop=w=iw:h=ih*0.10:y=ih*0.88[sub2];
    [sub2]boxblur=30:10[mosaic2];
    [v1][mosaic2]overlay=y=H*0.88:enable='between(t,45.0,47.3)'
  " \
  -c:a copy \
  output.mp4
```

### 5.3 参数说明

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `boxblur=30:10` | 马赛克强度（越大越模糊） | 30:10 |
| `y=ih*0.88` | 字幕区域顶部位置 | 0.88 |
| `h=ih*0.10` | 字幕区域高度 | 0.10 |
| `enable='between(t,start,end)'` | 时间范围控制 | ASR时间 |

---

## 六、文件结构

### 6.1 新增文件

```
项目结构
├── config/
│   └── sensitive_words.txt           # 【新增】敏感词配置
│
├── 漫剧素材_干净/                      # 【新增】预处理后的干净视频
│   └── 项目名/
│       ├── 1.mp4                      # 已遮盖
│       ├── 2.mp4
│       └── sensitive_mask.json        # 遮盖记录
│
├── data/hangzhou-leiming/
│   └── analysis/
│       └── 项目名/
│           └── subtitle_config.json   # 【新增】字幕区域配置
│
└── scripts/
    └── preprocess/                    # 【新增】预处理模块
        ├── __init__.py
        ├── subtitle_detector.py       # 字幕区域检测
        ├── sensitive_detector.py      # 敏感词检测
        └── video_cleaner.py           # 视频清洗（马赛克）
```

### 6.2 遮盖记录格式

```json
// 漫剧素材_干净/项目名/sensitive_mask.json
{
  "project_name": "项目名",
  "processed_at": "2026-03-10 14:30:00",
  "total_episodes": 10,
  "total_sensitive_segments": 15,

  "mask_records": [
    {
      "episode": 1,
      "sensitive_word": "敏感词",
      "asr_text": "这是一个包含敏感词的句子",
      "start_time": 15.2,
      "end_time": 17.5,
      "mask_region": {
        "y": 1690,
        "height": 192
      }
    }
  ]
}
```

---

## 七、模块设计

### 7.1 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 敏感词加载器 | `sensitive_detector.py` | 读取TXT配置，返回敏感词集合 |
| 敏感词检测器 | `sensitive_detector.py` | 匹配ASR文本，返回敏感时间段 |
| 字幕检测器 | `subtitle_detector.py` | 检测字幕区域（Gemini/OCR/默认） |
| 视频清洗器 | `video_cleaner.py` | FFmpeg马赛克遮盖 |

### 7.2 数据结构

```python
# 敏感词片段
@dataclass
class SensitiveSegment:
    episode: int              # 集数
    sensitive_word: str       # 敏感词
    asr_text: str            # ASR原文
    start_time: float        # 开始时间
    end_time: float          # 结束时间

# 字幕区域配置
@dataclass
class SubtitleRegion:
    y_ratio: float           # Y位置比例 (0-1)
    height_ratio: float      # 高度比例 (0-1)
    detection_method: str    # 检测方法
    confidence: float        # 置信度
```

### 7.3 接口设计

```python
# 敏感词检测
def detect_sensitive_words(
    asr_segments: List[ASRSegment],
    sensitive_words: Set[str]
) -> List[SensitiveSegment]:
    """检测ASR中的敏感词，返回敏感时间段列表"""
    pass

# 字幕区域检测
def detect_subtitle_region(
    keyframe_paths: List[str],
    video_resolution: Tuple[int, int]
) -> SubtitleRegion:
    """检测字幕区域，返回位置信息"""
    pass

# 视频清洗
def clean_video(
    video_path: str,
    sensitive_segments: List[SensitiveSegment],
    subtitle_region: SubtitleRegion,
    output_path: str
) -> str:
    """对视频进行马赛克遮盖处理"""
    pass
```

---

## 八、集成方案（v2.0 更新）

### 8.1 当前状态

主流程脚本已实现，可独立运行：

```bash
# 单独运行敏感词遮罩预处理
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名" --output "干净素材/项目名"

# 完整流程需要手动分三步执行（见1.1节）
```

### 8.2 未来集成方案

集成到 `scripts/understand/video_understand.py` 的分析流程中：

```python
def video_understand(project_path):
    """视频理解主流程"""

    # 1. 提取关键帧（现有）
    keyframes = extract_keyframes(video_path)

    # 2. 提取音频 + ASR（现有）
    asr_segments = extract_asr(video_path)

    # 3. 【新增】字幕区域检测
    subtitle_region = detect_subtitle_region(keyframes)

    # 4. 【新增】敏感词检测（使用OCR）
    sensitive_segments = detect_sensitive_words_from_ocr(
        video_path, subtitle_region, sensitive_words
    )

    # 5. 【新增】预处理视频（如果有敏感词）
    if sensitive_segments:
        clean_video_path = clean_video(
            video_path, sensitive_segments, subtitle_region
        )
    else:
        clean_video_path = video_path

    # 6. AI分析（使用干净视频）
    analysis = analyze_with_gemini(keyframes, asr_segments)

    # 7. 生成剪辑（使用干净视频）
    clips = generate_clips(analysis, video_path=clean_video_path)

    return clips
```

### 8.3 集成选项

**选项A: 自动集成（推荐）**
- 在 `video_understand.py` 开头自动检测敏感词并遮罩
- 优点：用户无感知，一条命令完成
- 缺点：每次都要检测，速度稍慢

**选项B: 可选参数**
```bash
# 默认不遮罩
python -m scripts.understand.video_understand "漫剧素材/项目名"

# 启用遮罩
python -m scripts.understand.video_understand "漫剧素材/项目名" --mask-sensitive
```

**选项C: 预处理先行**
- 用户先运行 `sensitive_mask_workflow` 生成干净视频
- 然后再运行 `video_understand` 处理干净视频
- 优点：解耦，可复用
- 缺点：需要两步操作

---

## 九、开发计划

### 9.1 开发顺序

1. **Phase 1: 基础功能**
   - [ ] 创建配置文件 `config/sensitive_words.txt`
   - [ ] 实现敏感词加载器
   - [ ] 实现敏感词检测器
   - [ ] 实现视频清洗器（马赛克）

2. **Phase 2: 字幕检测**
   - [ ] 实现默认比例检测
   - [ ] 实现Gemini视觉分析
   - [ ] 实现OCR检测（备选）
   - [ ] 实现配置保存/加载

3. **Phase 3: 集成优化**
   - [ ] 集成到 video_understand.py
   - [ ] 实现遮盖记录保存
   - [ ] 添加命令行参数
   - [ ] 测试验证

### 9.2 测试计划

- [ ] 单个敏感词遮盖测试
- [ ] 多个敏感词遮盖测试
- [ ] 跨集视频测试
- [ ] 不同分辨率测试（360p, 720p, 1080p）
- [ ] 性能测试（处理时间）

---

## 十、注意事项

### 10.1 已知问题

1. **视频质量**：马赛克遮盖后视频质量不受影响（仅字幕区域模糊）
2. **音频处理**：音频保持原样，不做修改
3. **存储空间**：预处理会生成新的视频文件，注意磁盘空间
4. **可逆性**：原始视频保留，遮盖操作可重新执行

### 10.2 OCR检测精度

- **采样率影响**：当前使用5fps采样，时间精度约±0.2秒
- **文字识别误差**：PaddleOCR可能误识别（如"尸"识别为"户"）
- **解决方案**：使用词组匹配而非单字匹配，减少误判

### 10.3 时间缓冲区

- **默认值**：0.6秒
- **作用**：确保字幕开始和结束时的马赛克覆盖完整
- **调整建议**：如果遮罩仍有遗漏，可增大到0.8-1.0秒

### 10.4 未来优化方向

1. **ASR+OCR结合**：OCR检测时间点 → ASR找对应片段 → 更精确时间
2. **批量处理优化**：多集并行OCR识别
3. **遮罩记录保存**：生成 `sensitive_mask.json` 记录遮罩位置
4. **缓存复用**：已处理视频跳过重复检测

---

## 附录B：主流程脚本参数说明

### sensitive_mask_workflow.py 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入视频目录或文件 | 必填 |
| `--output, -o` | 输出目录 | `{input}_cleaned` |
| `--sensitive-words` | 敏感词配置文件 | `config/sensitive_words.txt` |
| `--sample-fps` | OCR采样帧率 | `5.0` |
| `--time-buffer` | 遮罩时间缓冲区 | `0.6` |
| `--skip-existing` | 跳过已存在文件 | `False` |
| `--quiet, -q` | 安静模式 | `False` |

### 使用示例

```bash
# 处理整个项目目录
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生"

# 处理单个视频
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生/烈日重生-1.mp4"

# 指定输出目录
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生" -o "干净素材/烈日重生"

# 跳过已有处理
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生" --skip-existing

# 自定义参数
python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生" \
    --sample-fps 3.0 \
    --time-buffer 0.8
```

---

## 附录

### A. 相关文件

- 敏感词来源：`漫剧敏感词.docx`
- 配置文件：`config/sensitive_words.txt`

### B. 参考资料

- FFmpeg boxblur 滤镜文档
- PaddleOCR 使用文档
- Gemini Vision API 文档

---

*文档结束*
