# 片尾检测模块 - 双层防护架构设计

**版本**: v2.0
**更新时间**: 2026-03-04
**状态**: 设计阶段

---

## 📋 问题背景

### 发现的问题
1. **误判率高**："新的漫剧素材"4个项目40集全部误判
2. **算法缺陷**：只检测画面相似度，忽略了ASR内容
3. **项目差异**：不同项目有不同的片尾特征

### 根本原因
- **类型A项目**（晓红姐-3.4剧目）：真正的片尾（慢动作定格）
- **类型B项目**（新的漫剧素材）：艺术效果的相似画面（有ASR旁白）

---

## 🎯 解决方案：双层防护

### 架构图

```
┌──────────────────────────────────────────┐
│  渲染流程调用                              │
│  get_effective_duration(project, video)  │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  第一层：项目级配置（快速开关）             │
├──────────────────────────────────────────┤
│  1. 读取项目配置                           │
│  2. 检查 has_ending_credits               │
│  3. 如果 false → 直接返回总时长            │
│  4. 如果 true → 进入第二层                │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  第二层：智能检测算法（ASR增强）           │
├──────────────────────────────────────────┤
│  步骤1: 画面相似度检测                     │
│  步骤2: ASR转录最后3.5秒                  │
│  步骤3: ASR内容分析                        │
│  步骤4: 综合判断                           │
│  - 无ASR + 画面相似 → 片尾                │
│  - 有ASR + 片尾旁白 → 片尾                │
│  - 有ASR + 正常剧情 → 误判，返回无片尾      │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  返回有效时长                             │
│  effective_duration = total - ending     │
└──────────────────────────────────────────┘
```

---

## 📁 文件结构

```
scripts/
├── detect_ending_credits.py       # 原有检测模块
├── ending_credits_config.py       # 新增：配置管理
├── asr_ending_detector.py         # 新增：ASR增强检测
└── project_config.json            # 新增：项目配置文件

data/hangzhou-leiming/
└── project_config.json            # 项目配置

docs/
└── ENDING_CREDITS_DOUBLE_LAYER.md # 本文档
```

---

## 🔧 第一层：项目级配置

### 配置文件格式

**data/hangzhou-leiming/project_config.json**
```json
{
  "projects": {
    "多子多福，开局就送绝美老婆": {
      "has_ending_credits": true,
      "source": "晓红姐-3.4剧目",
      "ending_type": "慢动作定格",
      "verified": true,
      "notes": "人工验证通过，10集全部有片尾"
    },
    "雪烬梨香": {
      "has_ending_credits": false,
      "source": "新的漫剧素材",
      "ending_type": "无片尾",
      "verified": true,
      "notes": "人工验证，40集全部误判，实际是正常剧情"
    }
  },
  "default_config": {
    "has_ending_credits": true,
    "auto_detect": true
  }
}
```

### 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| has_ending_credits | bool | 是否需要检测片尾 |
| source | string | 项目来源（晓红姐-3.4剧目 / 新的漫剧素材） |
| ending_type | string | 片尾类型（慢动作定格 / 无片尾 / 黑屏淡出等） |
| verified | bool | 是否人工验证过 |
| notes | string | 备注信息 |

### 使用逻辑

```python
def should_detect_ending(project_name):
    """判断项目是否需要检测片尾"""
    config = load_project_config(project_name)

    # 如果项目明确配置为false，跳过检测
    if not config.get("has_ending_credits", True):
        return False

    # 如果配置为true，运行智能检测
    return True
```

---

## 🧠 第二层：智能检测算法（ASR增强）

### ASR转录模块

```python
def transcribe_last_seconds(video_path, seconds=3.5):
    """
    转录视频最后几秒的音频

    Args:
        video_path: 视频路径
        seconds: 转录时长（默认3.5秒）

    Returns:
        asr_segments: ASR片段列表
    """
    import whisper

    total_duration = get_video_duration(video_path)
    start_time = max(0, total_duration - seconds)

    # 使用Whisper转录
    model = whisper.load_model("base")
    result = model.transcribe(
        video_path,
        language="zh",
        initial_timestamp=start_time
    )

    return result["segments"]
```

### ASR内容分析

```python
def analyze_asr_content(asr_segments, video_end_time):
    """
    分析ASR内容是否是片尾旁白

    Args:
        asr_segments: ASR片段列表
        video_end_time: 视频结束时间

    Returns:
        analysis: 分析结果字典
    """
    # 检查1: 有无ASR
    if not asr_segments or len(asr_segments) == 0:
        return {
            "has_speech": False,
            "is_ending": True,
            "reason": "无对白"
        }

    # 检查2: ASR停止时间
    last_asr_end = max(seg['end'] for seg in asr_segments)
    silence_duration = video_end_time - last_asr_end

    # 检查3: ASR内容类型
    full_text = " ".join(seg['text'].strip() for seg in asr_segments)

    # 片尾旁白关键词
    ending_keywords = [
        "精彩剧集", "敬请期待", "下集", "预告",
        "关注", "点赞", "收藏", "转发",
        "未完待续", "待续", "想看更多"
    ]

    is_ending_narration = any(kw in full_text for kw in ending_keywords)

    # 检查4: ASR时长（片尾旁白通常很短）
    asr_duration = last_asr_end - asr_segments[0]['start']
    is_short_asr = asr_duration < 2.0  # 小于2秒

    return {
        "has_speech": True,
        "last_asr_end": last_asr_end,
        "silence_duration": silence_duration,
        "is_ending_narration": is_ending_narration,
        "is_short_asr": is_short_asr,
        "full_text": full_text,
        "reason": "片尾旁白" if is_ending_narration else "正常对白"
    }
```

### 综合判断逻辑

```python
def detect_ending_double_layer(project_name, video_path, asr_segments=None):
    """
    双层防护片尾检测

    Args:
        project_name: 项目名称
        video_path: 视频路径
        asr_segments: ASR数据（可选）

    Returns:
        VideoEndingResult: 检测结果
    """
    # ========== 第一层：项目级配置 ==========
    config = load_project_config(project_name)

    # 如果配置明确为false，直接返回无片尾
    if config.get("has_ending_credits", True) is False:
        total_duration = get_video_duration(video_path)
        return VideoEndingResult(
            video_path=video_path,
            episode=extract_episode(video_path),
            total_duration=total_duration,
            ending_info=EndingCreditsInfo(
                has_ending=False,
                duration=0.0,
                confidence=1.0,
                method="project_config",
                features={"reason": "项目配置为无片尾"}
            ),
            effective_duration=total_duration
        )

    # ========== 第二层：智能检测算法 ==========

    # 步骤1: 画面相似度检测
    similarity_result = detect_by_similarity(video_path)

    # 步骤2: 如果没有ASR数据，转录最后3.5秒
    if asr_segments is None:
        asr_segments = transcribe_last_seconds(video_path, seconds=3.5)

    # 步骤3: ASR内容分析
    total_duration = get_video_duration(video_path)
    asr_analysis = analyze_asr_content(asr_segments, total_duration)

    # 步骤4: 综合判断
    return make_final_decision(similarity_result, asr_analysis, video_path)


def make_final_decision(similarity_result, asr_analysis, video_path):
    """综合判断最终结果"""
    total_duration = get_video_duration(video_path)

    # 情况1: 无ASR + 画面相似 → 真实片尾
    if not asr_analysis["has_speech"]:
        if similarity_result.has_ending:
            return VideoEndingResult(
                video_path=video_path,
                episode=extract_episode(video_path),
                total_duration=total_duration,
                ending_info=similarity_result.ending_info,
                effective_duration=total_duration - similarity_result.ending_info.duration
            )

    # 情况2: 有ASR + 片尾旁白 → 片尾
    if asr_analysis["is_ending_narration"] and asr_analysis["is_short_asr"]:
        # 使用ASR结束时间作为片尾开始时间
        ending_start = asr_analysis["last_asr_end"]
        ending_duration = total_duration - ending_start

        return VideoEndingResult(
            video_path=video_path,
            episode=extract_episode(video_path),
            total_duration=total_duration,
            ending_info=EndingCreditsInfo(
                has_ending=True,
                duration=ending_duration,
                confidence=0.95,
                method="asr_ending_narration",
                features={
                    "ending_type": "片尾旁白",
                    "last_asr_end": ending_start,
                    "asr_text": asr_analysis["full_text"]
                }
            ),
            effective_duration=ending_start
        )

    # 情况3: 有ASR + 正常剧情 + 画面相似 → 误判
    if asr_analysis["has_speech"] and not asr_analysis["is_ending_narration"]:
        # 画面相似但有正常对白 → 不是片尾
        return VideoEndingResult(
            video_path=video_path,
            episode=extract_episode(video_path),
            total_duration=total_duration,
            ending_info=EndingCreditsInfo(
                has_ending=False,
                duration=0.0,
                confidence=1.0,
                method="asr_filter",
                features={
                    "reason": "画面相似但检测到正常剧情对白",
                    "asr_text": asr_analysis["full_text"]
                }
            ),
            effective_duration=total_duration
        )

    # 默认情况：使用画面相似度结果
    if similarity_result.has_ending:
        return VideoEndingResult(
            video_path=video_path,
            episode=extract_episode(video_path),
            total_duration=total_duration,
            ending_info=similarity_result.ending_info,
            effective_duration=total_duration - similarity_result.ending_info.duration
        )

    # 无片尾
    return VideoEndingResult(
        video_path=video_path,
        episode=extract_episode(video_path),
        total_duration=total_duration,
        ending_info=EndingCreditsInfo(
            has_ending=False,
            duration=0.0,
            confidence=1.0,
            method="none",
            features={}
        ),
        effective_duration=total_duration
    )
```

---

## 🔄 集成到渲染流程

### 修改 render_clips.py

```python
from scripts.ending_credits_config import load_project_config
from scripts.asr_ending_detector import detect_ending_double_layer

def render_clip_with_ending_detection(project_name, video_path, start_time, end_time):
    """渲染视频片段（集成片尾检测）"""

    # 1. 获取项目的有效时长
    result = detect_ending_double_layer(project_name, video_path)

    # 2. 使用有效时长调整裁剪时间
    effective_end = min(end_time, result.effective_duration)

    # 3. 渲染视频
    render_video_segment(video_path, start_time, effective_end)

    return rendered_video
```

---

## 📊 优势总结

| 优势 | 说明 |
|------|------|
| **准确率高** | 第一层配置100%准确 |
| **适应性强** | 第二层算法自动识别新项目 |
| **可控性强** | 人工可以干预和调整 |
| **性能优化** | 配置为false的项目跳过ASR转录 |
| **容错性好** | 两层验证，相互补充 |

---

## 🚀 实施计划

### Phase 1: 项目配置（快速实现）
- [ ] 创建 project_config.json
- [ ] 实现配置读取模块
- [ ] 更新8个项目的配置
- [ ] 集成到渲染流程

### Phase 2: ASR增强（逐步优化）
- [ ] 实现ASR转录功能
- [ ] 实现ASR内容分析
- [ ] 实现综合判断逻辑
- [ ] 测试验证效果

---

## 📝 配置示例

### 已验证项目

```json
{
  "多子多福，开局就送绝美老婆": {
    "has_ending_credits": true,
    "source": "晓红姐-3.4剧目",
    "ending_type": "慢动作定格",
    "verified": true,
    "avg_ending_duration": 2.04,
    "notes": "人工验证通过，10集全部有片尾"
  },
  "不晚忘忧": {
    "has_ending_credits": false,
    "source": "新的漫剧素材",
    "ending_type": "无片尾",
    "verified": true,
    "notes": "人工验证，10集全部误判，实际是正常剧情"
  }
}
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-04
