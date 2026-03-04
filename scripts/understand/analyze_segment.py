"""
逐段分析模块
使用Gemini API分析每个片段，识别高光点/钩子点
"""
import json
import re
import time
import base64
import requests
from typing import List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from scripts.config import TrainingConfig
    from scripts.dataclasses import KeyFrame, ASRSegment
    from scripts.understand.extract_segments import VideoSegment
except ImportError:
    @dataclass
    class KeyFrame:
        frame_path: str
        timestamp_ms: int
        
    @dataclass
    class ASRSegment:
        text: str
        start: float
        end: float
    
    @dataclass
    class VideoSegment:
        episode: int
        start_time: int
        end_time: int
        keyframes: List[KeyFrame]
        asr_segments: List[ASRSegment]


# 分析Prompt模板 - V11版本（类型重新定义 + 示例学习）
ANALYZE_PROMPT = """你是一位资深的短剧剪辑分析师。我给你展示4个真实示例，让你学会区分真钩子和假钩子。

## 📚 学习示例：区分真钩子和假钩子

仔细阅读下面的4个示例，理解为什么有些"对话中断"是真钩子，有些是假钩子。

### 示例A（第2集48秒）：真钩子"信息被截断" ✅
ASR: "夫人正要说出陆大人的秘密，突然被闯入的家丁打断"
分析：观众想知道"秘密是什么"，信息关键（秘密），中断意外（第三方闯入）
结论：这是真钩子，应该标记

### 示例B（第1集75秒）：假钩子"对话自然结束" ❌
ASR: "男主说：那就请太夫人。对话结束"
分析：不迫切想知道（普通请求），信息不关键，对话自然结束
结论：这不是钩子，不要标记

### 示例C（第5集54秒）：真钩子"悬念结束时刻" ✅
ASR: "女主说：我要进去看陆停松到底怎么了。画面结束"
分析：观众想知道"会看到什么"，行动关键（进去查看），画面停在高潮
结论：这是真钩子，应该标记

### 示例D（第3集29秒）：假钩子"场景切换" ❌
ASR: "女主说：我这么好语... 镜头切换到下一场景"
分析：没有明确悬念，不是关键信息，场景切换导致的停顿
结论：这不是钩子，不要标记

---

## 核心原则：识别真正的钩子点

根据44个短剧项目的分析经验：**每集通常有2-3个钩子点**。

### ✅ 应该标记的钩子点（高强度）

1. **关键信息被截断**
   - 特征：秘密、真相、重要决定、身份即将揭晓时被打断
   - 关键词：秘密、真相、揭露、决定、身份、说出
   - 应该标记：是

2. **悬念结束时刻**
   - 特征：关键行动或事件的高潮时刻画面停住
   - 关键词：要、即将、马上、正要
   - 应该标记：是

3. **情节重大转折**
   - 特征：反转、突变、意外、命运改变
   - 应该标记：是

4. **秘密揭露或真相揭示**
   - 特征：关键信息暴露、身份揭晓
   - 应该标记：是

5. **情感爆发顶点**
   - 特征：愤怒、震惊、崩溃的极致时刻
   - 应该标记：是

### ❌ 不要标记的情况（假钩子）

1. **普通对话结束**
   - 角色表达完完整意思后停顿
   - 示例："好的，我知道了。"

2. **场景切换导致的停顿**
   - 镜头转换、时间地点变化
   - 示例："好的... [下一场景]"

3. **日常对话、常规剧情**
   - 铺垫性的情节、问候、闲聊
   - 示例："今天天气不错"

4. **已知信息的重复**
   - 前面已经说过的内容
   - 示例："就像我之前说的"

**关键**：不要标记"对话突然中断"这个宽泛的类型，而是判断是否符合上述✅或❌的情况。

## 高光点定义 ⭐
- **含义**：从**这个时刻开始**，观众更愿意看下去
- **特征**：吸引力最强的开始时刻（冲突爆发、悬念引入、情感高潮）
- **关键**：返回窗口内**精确的秒数**，不是窗口开始时间！
- **示例**：窗口350-410秒，高光点在366秒 → 返回 366

## 钩子点定义 🪝
- **含义**：播放到**这个时刻突然结束**，观众迫切想知道后续
- **特征**：悬念最强的结束时刻（欲知后事如何、关键信息被截断、反转前一刻）
- **关键**：返回窗口内**精确的秒数**，不是窗口开始时间！
- **示例**：窗口350-410秒，钩子点在395秒 → 返回 395

## 分析片段信息
时间范围：{START}-{END}秒（第{EPISODE}集，窗口时长{DURATION}秒）
关键帧：[按时间顺序排列，每帧都有时间戳]
ASR文本：{ASR_TEXT}

## 可选的高光类型（必须匹配特征才能标记）
{HIGHLIGHT_TYPES}

## 可选的钩子类型（必须匹配特征才能标记）
{HOOK_TYPES}

## 常见钩子点位置（按优先级）

### 🔥 优先标记（高强度钩子）
1. 关键信息被截断（秘密、真相、决定即将揭晓时被打断）
2. 悬念结束时刻（关键行动画面停在高潮）
3. 情节重大转折（反转、突变、意外）
4. 秘密揭露或真相揭示（关键信息暴露）
5. 情感爆发顶点（愤怒、震惊、崩溃）

### ⚠️ 谨慎标记（需要验证）
- 情感爆发时刻（必须有强烈情绪）
- 冲突爆发时刻（争吵、对抗）

### ❌ 不要标记
- 对话自然结束（角色表达完意思）
- 场景切换停顿（镜头转换导致）
- 普通对话（日常闲聊、问候）

## 分析步骤
1. 仔细观察关键帧的时间变化和画面内容
2. 理解ASR文本中的情节走向
3. **关键**：检查是否为"关键信息被截断"或"悬念结束时刻"
4. **判断假钩子**：
   - 如果是对话自然结束、场景切换、日常对话 → **不要标记**
   - 如果有明显转折、秘密揭露、情感爆发 → **应该标记**
5. 精确定位到**具体哪一秒**
6. 每集通常有2-3个钩子点，请仔细寻找

## 特别规则
1. **第1集开头**：第1集的0秒将由系统自动添加为"开篇高光"，AI无需识别
2. **类型匹配**：优先使用上述5种高强度类型
3. **置信度评分**：0-10分，7.0以上即可标记
4. **不要标记假钩子**：
   - 对话自然结束 → 不标记
   - 场景切换停顿 → 不标记
   - 普通对话 → 不标记
5. **高光点识别**：专注于剧情反转、情感爆发等内容特征，不要基于"开头/开篇"等时间位置判断

## 输出格式
```json
{{
  "highlight": {{
    "exists": true/false,
    "preciseSecond": 125,
    "type": "从上述5种类型中选择（如：剧情反转高光）",
    "confidence": 8.5,
    "reasoning": "女主重生后表达复仇决心，情感强烈，引发观众期待"
  }},
  "hook": {{
    "exists": true/false,
    "preciseSecond": 366,
    "type": "从上述类型中选择，如：悬念反转",
    "confidence": 9.2,
    "reasoning": "男主突然说出关键秘密，画面停在悬念时刻，观众迫切想知道后续"
  }}
}}
```

**只返回JSON，不要其他文字。**
"""


@dataclass
class SegmentAnalysis:
    """片段分析结果"""
    episode: int
    start_time: int
    end_time: int

    # 高光点数据
    is_highlight: bool
    highlight_timestamp: float  # V13: 支持毫秒精度（精确时间戳）
    highlight_type: Optional[str]
    highlight_desc: str
    highlight_confidence: float  # 置信度 0-10

    # 钩子点数据
    is_hook: bool
    hook_timestamp: float  # V13: 支持毫秒精度（精确时间戳）
    hook_type: Optional[str]
    hook_desc: str
    hook_confidence: float  # 置信度 0-10


def encode_image(image_path: str) -> str:
    """将图片编码为base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def build_analyze_prompt(segment: VideoSegment, skill_framework: dict) -> dict:
    """构建分析请求

    Args:
        segment: 视频片段
        skill_framework: 技能框架

    Returns:
        API请求payload
    """
    # 合并ASR文本
    asr_text = ' '.join(seg.text for seg in segment.asr_segments)
    if not asr_text:
        asr_text = "(无语音)"

    # 计算窗口时长
    duration = segment.end_time - segment.start_time

    # 提取类型信息用于Prompt
    highlight_types_text = format_types_for_prompt(skill_framework.get('highlight_types', []))
    hook_types_text = format_types_for_prompt(skill_framework.get('hook_types', []))

    # 构建prompt
    prompt = ANALYZE_PROMPT.format(
        START=segment.start_time,
        END=segment.end_time,
        EPISODE=segment.episode,
        DURATION=duration,
        ASR_TEXT=asr_text[:800],
        HIGHLIGHT_TYPES=highlight_types_text,
        HOOK_TYPES=hook_types_text
    )

    # 准备关键帧图片
    keyframe_parts = []
    for kf in segment.keyframes[:5]:  # 最多5张
        if segment.keyframes.index(kf) >= 5:
            break
        if segment.keyframes.index(kf) % 3 == 0:  # 每3张取1张，减少API调用
            try:
                img_base64 = encode_image(kf.frame_path)
                keyframe_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img_base64
                    }
                })
            except Exception as e:
                print(f"警告: 无法编码图片 {kf.frame_path}: {e}")

    # 构建请求
    parts = [{"text": prompt}]
    parts.extend(keyframe_parts)

    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": TrainingConfig.GEMINI_TEMPERATURE,
            "maxOutputTokens": 1024
        }
    }


def format_types_for_prompt(types: list) -> str:
    """将类型列表格式化为Prompt文本

    Args:
        types: 类型列表（从技能JSON中提取）

    Returns:
        格式化的文本
    """
    if not types:
        return "（无）"

    lines = []
    for t in types[:10]:  # 最多显示10个类型
        name = t.get('name', '未知')
        desc = t.get('description', '')
        required = t.get('required_features', {})

        # 提取关键特征
        keywords = required.get('dialogue_keywords', [])[:3]
        emotion = required.get('emotion_keywords', [])[:2]

        lines.append(f"- **{name}**: {desc}")

        if keywords:
            lines.append(f"  - 关键词: {', '.join(keywords)}")
        if emotion:
            lines.append(f"  - 情绪: {', '.join(emotion)}")

    return '\n'.join(lines)


def parse_analysis_response(response_text: str, segment_start: int, segment_end: int) -> dict:
    """解析V6响应 - 包含精确时间戳和置信度

    Args:
        response_text: API响应文本
        segment_start: 窗口开始时间
        segment_end: 窗口结束时间

    Returns:
        分析结果dict
    """
    # 清理markdown
    clean = response_text.strip()
    if clean.startswith('```json'):
        clean = clean[7:]
    if clean.startswith('```'):
        clean = clean[3:]
    if clean.endswith('```'):
        clean = clean[:-3]

    # 提取JSON
    json_match = re.search(r'\{[\s\S]*\}', clean)
    if not json_match:
        return _get_empty_result(segment_start)

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return _get_empty_result(segment_start)

    # 验证并提取高光点数据
    highlight_data = data.get("highlight", {})
    if highlight_data.get("exists", False):
        hl_timestamp = highlight_data.get("preciseSecond")
        # 验证时间戳在窗口内
        if hl_timestamp is None or not (segment_start <= hl_timestamp <= segment_end):
            hl_timestamp = segment_start  # 超出范围使用默认值
    else:
        hl_timestamp = None

    # 验证并提取钩子点数据
    hook_data = data.get("hook", {})
    if hook_data.get("exists", False):
        hook_timestamp = hook_data.get("preciseSecond")
        # 验证时间戳在窗口内
        if hook_timestamp is None or not (segment_start <= hook_timestamp <= segment_end):
            hook_timestamp = segment_start  # 超出范围使用默认值
    else:
        hook_timestamp = None

    return {
        "highlight": {
            "exists": highlight_data.get("exists", False),
            "preciseSecond": hl_timestamp,
            "type": highlight_data.get("type"),
            "confidence": highlight_data.get("confidence", 0.0),
            "reasoning": highlight_data.get("reasoning", "")
        },
        "hook": {
            "exists": hook_data.get("exists", False),
            "preciseSecond": hook_timestamp,
            "type": hook_data.get("type"),
            "confidence": hook_data.get("confidence", 0.0),
            "reasoning": hook_data.get("reasoning", "")
        }
    }


def _get_empty_result(segment_start: int) -> dict:
    """返回空结果"""
    return {
        "highlight": {
            "exists": False,
            "preciseSecond": None,
            "type": None,
            "confidence": 0.0,
            "reasoning": ""
        },
        "hook": {
            "exists": False,
            "preciseSecond": None,
            "type": None,
            "confidence": 0.0,
            "reasoning": ""
        }
    }


def analyze_segment(
    segment: VideoSegment,
    skill_framework: dict,
    max_retries: int = 3
) -> SegmentAnalysis:
    """分析单个片段
    
    Args:
        segment: 视频片段
        skill_framework: 技能框架
        max_retries: 最大重试次数
        
    Returns:
        分析结果
    """
    url = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={TrainingConfig.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(max_retries):
        try:
            payload = build_analyze_prompt(segment, skill_framework)
            
            response = requests.post(
                url, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            response_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # 使用新的解析函数（传入窗口边界）
            result = parse_analysis_response(
                response_text,
                segment.start_time,
                segment.end_time
            )

            # 提取数据
            hl_data = result.get("highlight", {})
            hook_data = result.get("hook", {})

            return SegmentAnalysis(
                episode=segment.episode,
                start_time=segment.start_time,
                end_time=segment.end_time,

                # 高光点（V13: 转换为浮点数支持毫秒精度）
                is_highlight=hl_data.get("exists", False),
                highlight_timestamp=float(hl_data.get("preciseSecond", segment.start_time)),
                highlight_type=hl_data.get("type"),
                highlight_desc=hl_data.get("reasoning", ""),
                highlight_confidence=hl_data.get("confidence", 0.0),

                # 钩子点（V13: 转换为浮点数支持毫秒精度）
                is_hook=hook_data.get("exists", False),
                hook_timestamp=float(hook_data.get("preciseSecond", segment.start_time)),
                hook_type=hook_data.get("type"),
                hook_desc=hook_data.get("reasoning", ""),
                hook_confidence=hook_data.get("confidence", 0.0)
            )
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 5
                print(f"分析片段 {segment.start_time}-{segment.end_time}秒失败，{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"分析片段失败: {e}")
                return SegmentAnalysis(
                    episode=segment.episode,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    is_highlight=False,
                    highlight_timestamp=0.0,  # V13: 浮点数
                    highlight_type=None,
                    highlight_desc="分析失败",
                    highlight_confidence=0.0,
                    is_hook=False,
                    hook_timestamp=0.0,  # V13: 浮点数
                    hook_type=None,
                    hook_desc="分析失败",
                    hook_confidence=0.0
                )


def analyze_all_segments(
    segments: List[VideoSegment],
    skill_framework: dict,
    max_concurrent: int = 3
) -> List[SegmentAnalysis]:
    """并行分析所有片段
    
    Args:
        segments: 片段列表
        skill_framework: 技能框架
        max_concurrent: 最大并发数
        
    Returns:
        所有分析结果
    """
    results = []
    total = len(segments)
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(analyze_segment, seg, skill_framework): seg 
            for seg in segments
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            # 打印进度
            if result.is_highlight or result.is_hook:
                marker = []
                if result.is_highlight:
                    marker.append(f"高光:{result.highlight_type}")
                if result.is_hook:
                    marker.append(f"钩子:{result.hook_type}")
                print(f"[{i}/{total}] {result.start_time}-{result.end_time}秒: {', '.join(marker)}")
            else:
                print(f"[{i}/{total}] {result.start_time}-{result.end_time}秒: 无")
    
    return results


if __name__ == "__main__":
    print("analyze_segment 模块已加载")
