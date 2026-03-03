# 杭州雷鸣 AI 训练流程 - 开发规范文档 (Python)

## 版本更新

### V2.0 - 统计规律与质量标准 (2026-03-03)

**人工标记统计规律**（基于5个项目44集数据）：

| 统计项 | 数值 | 说明 |
|--------|------|------|
| 总标记数 | 44个 | 5个项目，44集 |
| 高光点总数 | 6个 | 平均每集0.14个 |
| 钩子点总数 | 38个 | 平均每集0.86个 |
| **平均每集标记数** | **1.0个** | **核心规律** |
| 标记间隔 | >15秒 | 同集内标记的最小间隔 |

**关键发现**：
- ✅ **宁缺毋滥**：人工只标记最关键的点
- ✅ **稀疏性**：平均每集只有1个标记
- ✅ **第1集规则**：第1集开头默认是开篇高光点

**质量标准**：
- 置信度阈值：>7.0（0-10分）
- 时间精度：±2秒
- 去重窗口：15秒

---

## 一、项目概述

本项目用于从历史短剧数据中训练出通用的 AI 剪辑技能，让另一个 AI 能够针对新剧集自动识别高光点和钩子点。

## 二、输入配置

### 2.1 项目列表配置

```python
from dataclasses import dataclass

@dataclass
class ProjectConfig:
    name: str           # 短剧名称
    video_path: str    # 视频文件夹路径（相对于项目根目录）
    excel_path: str    # Excel 人工标记文件路径
```

**完整配置示例**：
```python
PROJECTS = [
    ProjectConfig(
        name="重生暖宠：九爷的小娇妻不好惹",
        video_path="./漫剧素材/重生暖宠九爷的小娇妻不好惹",
        excel_path="./漫剧素材/重生暖宠九爷的小娇妻不好惹/重生暖宠：九爷的小娇妻不好惹.xlsx"
    ),
    ProjectConfig(
        name="再见，心机前夫",
        video_path="./漫剧素材/再见，心机前夫",
        excel_path="./漫剧素材/再见，心机前夫/再见，心机前夫.xlsx"
    ),
    ProjectConfig(
        name="小小飞梦",
        video_path="./漫剧素材/小小飞梦",
        excel_path="./漫剧素材/小小飞梦/小小飞梦.xlsx"
    ),
    ProjectConfig(
        name="弃女归来：嚣张真千金不好惹",
        video_path="./漫剧素材/弃女归来嚣张真千金不好惹",
        excel_path="./漫剧素材/弃女归来嚣张真千金不好惹/弃女归来：嚣张真千金不好惹.xlsx"
    ),
    ProjectConfig(
        name="百里将就",
        video_path="./漫剧素材/百里将就",
        excel_path="./漫剧素材/百里将就/百里将就.xlsx"
    ),
]
```

### 2.2 Excel 标记文件格式

Excel 文件应包含以下列：

| 列名 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 集数 | 字符串 | 是 | 如：第1集、第2集 |
| 时间点 | 字符串 | 是 | 如：00:35、01:20 |
| 类型 | 字符串 | 是 | 高光点 / 钩子点 |
| 子类型 | 字符串 | 否 | 细分类型 |
| 描述 | 字符串 | 否 | 标记描述 |
| 得分 | 数字 | 否 | 0-100 |

## 三、数据结构定义

### 3.1 核心类型

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Marking:
    """标记数据"""
    id: int
    episode: str           # 集数，如 "第1集"
    episode_number: int    # 集数编号，如 1
    timestamp: str          # 时间点字符串，如 "00:35"
    seconds: float          # 时间点秒数，如 35.0
    type: str              # "高光点" 或 "钩子点"
    sub_type: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = None

@dataclass
class KeyFrame:
    """关键帧"""
    frame_path: str        # 帧图片路径
    timestamp_ms: int      # 时间戳（毫秒）
    base64: Optional[str] = None  # Base64 编码（用于传给 Gemini）

@dataclass
class ASRSegment:
    """ASR 片段"""
    text: str              # 文本内容
    start: float           # 开始时间（秒）
    end: float             # 结束时间（秒）

@dataclass
class MarkingContext:
    """标记上下文（核心数据结构）"""
    project_name: str
    marking: Marking
    
    # 高光点：从标记时间往后10秒
    # 钩子点：从标记时间往前10秒
    keyframes: List[KeyFrame] = field(default_factory=list)
    asr_segments: List[ASRSegment] = field(default_factory=list)
    asr_text: str = ""

@dataclass
class AnalysisResult:
    """分析结果"""
    type: str              # "高光点" 或 "钩子点"
    category: str          # 泛化的类型名称
    category_description: str  # 类型详细描述
    # 多维度特征
    visual_features: dict = field(default_factory=dict)    # 视觉特征(关键帧画面)
    audio_features: dict = field(default_factory=dict)     # 听觉特征(仅ASR转录分析)
    emotion_features: dict = field(default_factory=dict)   # 情绪特征
    plot_features: dict = field(default_factory=dict)       # 剧情特征
    content_features: dict = field(default_factory=dict)   # 内容爽点特征
    
    reasoning: str = ""   # 分析原因

@dataclass
class HighlightType:
    """高光类型"""
    name: str
    description: str
    
    # 多维度特征
    visual_features: dict = field(default_factory=dict)    # 视觉特征
    audio_features: dict = field(default_factory=dict)     # 听觉特征
    emotion_features: dict = field(default_factory=dict)   # 情绪特征
    plot_features: dict = field(default_factory=dict)       # 剧情特征
    content_features: dict = field(default_factory=dict)   # 内容爽点特征
    
    typical_scenarios: List[str] = field(default_factory=list)

@dataclass
class HookType:
    """钩子类型"""
    name: str
    description: str
    
    # 多维度特征
    visual_features: dict = field(default_factory=dict)    # 视觉特征
    audio_features: dict = field(default_factory=dict)     # 听觉特征
    emotion_features: dict = field(default_factory=dict)   # 情绪特征
    plot_features: dict = field(default_factory=dict)       # 剧情特征
    content_features: dict = field(default_factory=dict)   # 内容氪点特征
    
    typical_scenarios: List[str] = field(default_factory=list)

@dataclass
class EditingRule:
    """剪辑规则"""
    scenario: str
    duration: str
    rhythm: str
    combination: str
    cut_in: str
    cut_out: str

@dataclass
class SkillFile:
    """技能文件结构"""
    version: str
    updated_at: str
    highlight_types: List[HighlightType] = field(default_factory=list)
    hook_types: List[HookType] = field(default_factory=list)
    editing_rules: List[EditingRule] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)
```

## 四、处理流程

### 阶段1: 数据读取

**输入**: ProjectConfig 列表

**处理步骤**:
1. 遍历每个项目配置
2. 使用 pandas 读取 Excel 文件
3. 解析集数、时间点、类型
4. 匹配对应的视频文件路径 (`{集数}.mp4`)
5. 过滤出有标记的集数（去重）

**代码实现**:
```python
import pandas as pd
import os
from pathlib import Path

def load_project_markings(config: ProjectConfig) -> List[Marking]:
    """读取项目的标记数据"""
    # 读取 Excel
    df = pd.read_excel(config.excel_path)
    
    markings = []
    for idx, row in df.iterrows():
        # 解析集数
        episode = str(row['集数'])
        episode_number = int(episode.replace('第', '').replace('集', ''))
        
        # 解析时间点
        timestamp = str(row['时间点'])
        minutes, seconds = timestamp.split(':')
        seconds_val = int(minutes) * 60 + int(seconds)
        
        marking = Marking(
            id=idx,
            episode=episode,
            episode_number=episode_number,
            timestamp=timestamp,
            seconds=seconds_val,
            type=row['类型'],
            sub_type=row.get('子类型'),
            description=row.get('描述'),
            score=int(row['得分']) if pd.notna(row.get('得分')) else None
        )
        markings.append(marking)
    
    return markings

def find_video_path(config: ProjectConfig, episode_number: int) -> str:
    """查找视频文件路径"""
    video_file = config.video_path / f"{episode_number}.mp4"
    if video_file.exists():
        return str(video_file)
    raise FileNotFoundError(f"视频文件不存在: {video_file}")
```

### 阶段2: 多模态数据提取

**只处理有标记的集数**

#### 2.1 关键帧提取

```python
import subprocess
import os
from pathlib import Path

def extract_keyframes(
    video_path: str,
    output_dir: str,
    fps: float = 2.0  # 每0.5秒 = 2fps
) -> List[KeyFrame]:
    """提取关键帧
    
    使用 FFmpeg 按指定 fps 提取帧
    ffmpeg -i input.mp4 -vf "fps=2" output/%04d.jpg
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用 FFmpeg 提取帧
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps={fps}',
        '-q:v', '2',  # JPEG 质量
        os.path.join(output_dir, '%04d.jpg'),
        '-y'  # 覆盖输出
    ]
    subprocess.run(cmd, capture_output=True)
    
    # 收集帧文件
    keyframes = []
    frame_files = sorted(Path(output_dir).glob('*.jpg'))
    
    for idx, frame_file in enumerate(frame_files):
        # 计算时间戳
        timestamp_ms = int((idx / fps) * 1000)
        keyframes.append(KeyFrame(
            frame_path=str(frame_file),
            timestamp_ms=timestamp_ms
        ))
    
    return keyframes
```

#### 2.2 ASR 音频转录

```python
import subprocess
import json

def extract_audio(video_path: str, audio_path: str):
    """从视频提取音频"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        audio_path, '-y'
    ]
    subprocess.run(cmd, capture_output=True)

def transcribe_audio(
    audio_path: str,
    output_path: str,
    model: str = "tiny",
    language: str = "zh"
) -> List[ASRSegment]:
    """ASR 音频转录
    
    使用 Whisper 转录
    whisper audio.wav --language zh --model tiny --output_json
    """
    # 检查是否已有转录文件
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [ASRSegment(
                text=seg['text'],
                start=seg['start'],
                end=seg['end']
            ) for seg in data.get('segments', [])]
    
    # 使用 Whisper 转录
    cmd = [
        'whisper', audio_path,
        '--language', language,
        '--model', model,
        '--output_format', 'json',
        '--output_file', output_path.replace('.json', '')
    ]
    subprocess.run(cmd, capture_output=True)
    
    # 读取结果
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return [ASRSegment(
        text=seg['text'],
        start=seg['start'],
        end=seg['end']
    ) for seg in data.get('segments', [])]
```

### 阶段3: 标记点上下文提取

**这是核心逻辑！**

```python
from typing import List

def extract_marking_context(
    marking: Marking,
    keyframes: List[KeyFrame],
    asr_segments: List[ASRSegment],
    context_seconds: float = 10.0
) -> MarkingContext:
    """提取标记点上下文
    
    高光点：从标记时间往后 context_seconds 秒
    钩子点：从标记时间往前 context_seconds 秒
    """
    seconds = marking.seconds
    
    if marking.type == "高光点":
        # 高光点：往后找
        start_time = seconds
        end_time = seconds + context_seconds
    else:
        # 钩子点：往前找
        start_time = max(0, seconds - context_seconds)
        end_time = seconds
    
    # 筛选时间范围内的关键帧
    relevant_keyframes = [
        kf for kf in keyframes
        if start_time <= (kf.timestamp_ms / 1000) <= end_time
    ]
    
    # 筛选时间范围内的 ASR 片段
    relevant_asr = [
        seg for seg in asr_segments
        if seg.start < end_time and seg.end > start_time
    ]
    
    # 合并 ASR 文本
    asr_text = ' '.join(seg.text for seg in relevant_asr)
    
    return MarkingContext(
        project_name="",
        marking=marking,
        keyframes=relevant_keyframes,
        asr_segments=relevant_asr,
        asr_text=asr_text
    )
```

### 阶段4: Gemini AI 分析

#### 4.1 待确认事项

**需要先测试**: Gemini API 是否支持同时分析多张图片 + 文字

#### 4.2 分析函数

```python
import base64
import json
import requests

GEMINI_API_KEY = "your-api-key"
GEMINI_ENDPOINT = "https://yunwu.ai/v1/beta/models/gemini-2.0-flash:generateContent"

def encode_image(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def analyze_marking_with_gemini(
    context: MarkingContext,
    prompt_template: str
) -> AnalysisResult:
    """使用 Gemini 分析标记点"""
    
    # 准备关键帧图片（取前几张）
    keyframe_parts = []
    for kf in context.keyframes[:5]:  # 最多5张
        if os.path.exists(kf.frame_path):
            img_base64 = encode_image(kf.frame_path)
            keyframe_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
            })
    
    # 构建 prompt
    marking = context.marking
    prompt = prompt_template.format(
        episode=marking.episode,
        timestamp=marking.timestamp,
        type=marking.type,
        time_range=f"{max(0, marking.seconds - 10):.1f}s - {marking.seconds:.1f}s" if marking.type == "钩子点" else f"{marking.seconds:.1f}s - {marking.seconds + 10:.1f}s",
        asr_text=context.asr_text or "(无语音)"
    )
    
    # 构建请求体
    contents = [{"parts": [{"text": prompt}]}]
    
    # 添加关键帧图片
    if keyframe_parts:
        for kf_part in keyframe_parts:
            contents[0]["parts"].append(kf_part)
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"
    }
    
    response = requests.post(
        GEMINI_API_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=120
    )
    
    response.raise_for_status()
    
    # 解析响应
    data = response.json()
    text = data['candidates'][0]['content']['parts'][0]['text']
    
    # 提取 JSON
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        result = json.loads(json_match.group())
        return AnalysisResult(
            type=result.get('type', marking.type),
            category=result.get('category', ''),
            category_description=result.get('description', ''),
            visual_features=result.get('visual_features', []),
            audio_features=result.get('audio_features', []),
            reasoning=result.get('analysis', '')
        )
    
    raise ValueError(f"无法解析 Gemini 响应: {text}")
```

#### 4.3 批量分析

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def analyze_markings_batch(
    contexts: List[MarkingContext],
    prompt_template: str,
    max_workers: int = 3
) -> List[AnalysisResult]:
    """批量分析标记点"""
    
    def analyze_with_retry(context: MarkingContext, retries: int = 3) -> AnalysisResult:
        for attempt in range(retries):
            try:
                return analyze_marking_with_gemini(context, prompt_template)
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # 指数退避
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [
            loop.run_in_executor(executor, analyze_with_retry, ctx)
            for ctx in contexts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 过滤失败的结果
    return [r for r in results if isinstance(r, AnalysisResult)]
```

### 阶段5: 螺旋式迭代更新

#### 5.1 读取历史技能文件

```python
import re
import json

def load_latest_skill() -> SkillFile:
    """读取最新的技能文件"""
    latest_path = "./data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-latest.md"
    
    if not os.path.exists(latest_path):
        return None
    
    with open(latest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析版本
    version_match = re.search(r'版本:\s*(v[\d.]+)', content)
    version = version_match.group(1) if version_match else "v0.0"
    
    # 解析高光类型
    highlight_types = parse_highlight_types(content)
    hook_types = parse_hook_types(content)
    
    return SkillFile(
        version=version,
        updated_at="",
        highlight_types=highlight_types,
        hook_types=hook_types,
        editing_rules=[]
    )
```

#### 5.2 合并更新逻辑

```python
from typing import Dict, Set

def merge_skills(
    old_skill: SkillFile,
    new_results: List[AnalysisResult],
    project_count: int
) -> SkillFile:
    """合并新旧技能"""
    
    # 从新结果提取类型
    new_highlight_types = extract_types(new_results, "高光点")
    new_hook_types = extract_types(new_results, "钩子点")
    
    # 与历史合并（去重）
    all_highlight_types = merge_type_lists(
        old_skill.highlight_types if old_skill else [],
        new_highlight_types
    )
    all_hook_types = merge_type_lists(
        old_skill.hook_types if old_skill else [],
        new_hook_types
    )
    
    # 添加默认类型
    if not any(t.name == "开篇高光" for t in all_highlight_types):
        all_highlight_types.insert(0, HighlightType(
            name="开篇高光",
            description="每部剧第1集开头的默认高光点",
            visual_features=["开场画面", "快速切入"],
            audio_features=["开场音乐", "快速对白"],
            typical_scenarios=["第1集开头"]
        ))
    
    # 生成版本号
    old_version = old_skill.version if old_skill else "v0.0"
    new_version = increment_version(old_version)
    
    return SkillFile(
        version=new_version,
        updated_at=datetime.now().isoformat(),
        highlight_types=all_highlight_types,
        hook_types=all_hook_types,
        editing_rules=[],
        statistics={
            "project_count": (old_skill.statistics.get("project_count", 0) + project_count) if old_skill else project_count,
            "episode_count": old_skill.statistics.get("episode_count", 0) + len(new_results) if old_skill else len(new_results),
            "highlight_type_count": len(all_highlight_types),
            "hook_type_count": len(all_hook_types)
        }
    )

def merge_type_lists(old: List, new: List) -> List:
    """合并类型列表（去重）"""
    type_map = {}
    
    # 旧类型
    for t in old:
        type_map[t.name] = t
    
    # 新类型
    for t in new:
        if t.name in type_map:
            # 合并特征列表
            old_t = type_map[t.name]
            combined_visual = list(set(old_t.visual_features + t.visual_features))
            combined_audio = list(set(old_t.audio_features + t.audio_features))
            type_map[t.name] = type(
                t.__class__.__name__,
                (),
                {
                    'name': t.name,
                    'description': t.description or old_t.description,
                    'visual_features': combined_visual,
                    'audio_features': combined_audio,
                    'typical_scenarios': list(set(
                        (old_t.typical_scenarios if hasattr(old_t, 'typical_scenarios') else []) + 
                        (t.typical_scenarios if hasattr(t, 'typical_scenarios') else [])
                    ))
                }
            )()
        else:
            type_map[t.name] = t
    
    return list(type_map.values())

def increment_version(version: str) -> str:
    """递增版本号"""
    match = re.search(r'v(\d+)\.(\d+)', version)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) + 1
        return f"v{major}.{minor}"
    return "v1.0"
```

#### 5.3 生成技能文件

```python
def generate_skill_file(skill: SkillFile, output_dir: str) -> str:
    """生成技能文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    lines = []
    lines.append("# AI 短剧剪辑技能")
    lines.append(f"> 版本: {skill.version} | 更新日期: {skill.updated_at}")
    lines.append("---")
    lines.append("")
    
    # 统计信息
    lines.append("## 📊 统计信息")
    lines.append(f"- 训练项目数: {skill.statistics.get('project_count', 0)}")
    lines.append(f"- 累计集数: {skill.statistics.get('episode_count', 0)}")
    lines.append(f"- 高光类型数: {skill.statistics.get('highlight_type_count', 0)}")
    lines.append(f"- 钩子类型数: {skill.statistics.get('hook_type_count', 0)}")
    lines.append("---")
    lines.append("")
    
    # 高光类型
    lines.append("## 🎯 高光类型")
    for i, ht in enumerate(skill.highlight_types, 1):
        lines.append(f"### {i}. {ht.name}")
        lines.append(f"**描述**: {ht.description}")
        lines.append("**视觉特征**:")
        for f in ht.visual_features:
            lines.append(f"- {f}")
        lines.append("**听觉特征**:")
        for f in ht.audio_features:
            lines.append(f"- {f}")
        lines.append("**典型场景**:")
        for s in ht.typical_scenarios:
            lines.append(f"- {s}")
        lines.append("")
    
    # 钩子类型
    lines.append("## 🪝 钩子类型")
    for i, ht in enumerate(skill.hook_types, 1):
        lines.append(f"### {i}. {ht.name}")
        lines.append(f"**描述**: {ht.description}")
        lines.append("**视觉特征**:")
        for f in ht.visual_features:
            lines.append(f"- {f}")
        lines.append("**听觉特征**:")
        for f in ht.audio_features:
            lines.append(f"- {f}")
        lines.append("**典型场景**:")
        for s in ht.typical_scenarios:
            lines.append(f"- {s}")
        lines.append("")
    
    content = '\n'.join(lines)
    
    # 保存文件
    version = skill.version
    file_path = os.path.join(output_dir, f"ai-drama-clipping-thoughts-{version}.md")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 更新 latest 软链接
    latest_link = os.path.join(output_dir, "ai-drama-clipping-thoughts-latest.md")
    if os.path.exists(latest_link):
        os.remove(latest_link)
    os.symlink(file_path, latest_link)
    
    return file_path
```

## 五、代码实现要求

### 5.1 目录结构

```
hangzhou-leiming-ai-drama/
├── data/
│   └── hangzhou-leiming/
│       └── skills/                    # 技能文件输出目录
├── 漫剧素材/                          # 视频文件
├── scripts/                           # 训练脚本
│   ├── __init__.py
│   ├── config.py                     # 项目配置
│   ├── train.py                     # 主入口
│   ├── read_excel.py                # 读取 Excel
│   ├── extract_keyframes.py         # 关键帧提取
│   ├── extract_asr.py              # ASR 转录
│   ├── extract_context.py           # 提取上下文
│   ├── analyze_gemini.py           # Gemini 分析
│   └── merge_skills.py             # 合并技能
├── prompts/                           # Prompt 模板
│   └── hl-learning.md
├── archive/                           # 参考代码
├── TRAINING_SPEC.md                   # 本文档
└── requirements.txt                   # Python 依赖
```

### 5.2 依赖

```txt
# requirements.txt
pandas>=2.0.0
openpyxl>=3.1.0
requests>=2.31.0
Pillow>=10.0.0
```

**系统依赖**:
- FFmpeg（关键帧提取、音频提取）
- Whisper（ASR 转录）

### 5.3 执行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行完整训练流程
python scripts/train.py

# 或指定项目
python scripts/train.py --projects "重生暖宠,再见心机前夫"

# 仅测试数据读取
python scripts/read_excel.py
```

## 六、待确认事项

- [ ] **Gemini API 图片支持**: 需要测试是否支持同时分析多张图片 + 文字
- [ ] **API 速率限制**: 需要确认 yunwu.ai 的速率限制，决定并发数

## 七、输出

1. **技能文件**: `data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-vX.md`
2. **训练日志**: 控制台输出（带进度百分比）

## 八、错误处理

### 8.1 常见错误

| 错误 | 原因 | 处理 |
|------|------|------|
| FFmpeg not found | 未安装 FFmpeg | 提示安装 |
| Excel 文件不存在 | 路径错误 | 抛出异常 |
| 视频文件不存在 | 集数不匹配 | 跳过该标记 |
| Whisper 失败 | 音频质量问题 | 重试或跳过 |
| Gemini API 失败 | 网络/配额 | 自动重试 3 次 |

### 8.2 断点续传

每次处理完一个阶段后，保存进度到 JSON 文件：
```python
{
    "last_stage": "analyze_gemini",
    "processed_markings": [1, 2, 3, 4, 5],
    "results": [...]
}
```

重启时检查进度，从上次中断处继续。
