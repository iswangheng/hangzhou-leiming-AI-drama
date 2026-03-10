"""
逐段分析模块
使用Gemini API分析每个片段，识别高光点/钩子点
V14: 智能关键帧过滤 - 只传"有意义"的帧（对话+画面变化）
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


# ========== V14: 智能关键帧过滤 ==========

def calculate_frame_difference(frame1_path: str, frame2_path: str) -> float:
    """
    计算两帧画面的差异度（使用感知哈希）

    Args:
        frame1_path: 第一帧路径
        frame2_path: 第二帧路径

    Returns:
        0-1的画面变化度
        - 0.0-0.2：几乎相同（静态镜头）
        - 0.2-0.4：小幅变化（人物微动）
        - 0.4-0.6：中等变化（镜头移动）
        - 0.6-1.0：大幅变化（场景切换、动作）
    """
    try:
        from PIL import Image
        import imagehash

        img1 = Image.open(frame1_path)
        img2 = Image.open(frame2_path)

        # 计算感知哈希
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)

        # 计算汉明距离并归一化到0-1
        distance = hash1 - hash2
        max_distance = hash1.hash.size  # 64位哈希
        similarity = 1 - (distance / max_distance)

        # 返回变化度（1 - 相似度）
        return 1 - similarity

    except Exception as e:
        print(f"⚠️  画面差异计算失败: {e}")
        return 0.0


def smart_select_keyframes(
    keyframes: List[KeyFrame],
    asr_segments: List[ASRSegment],
    change_threshold: float = 0.4
) -> List[KeyFrame]:
    """
    智能选择关键帧 - 只传"有意义"的帧给AI

    策略：
    1. 计算画面变化 → 标记"变化大"的时刻
    2. 标记"有对话"的时刻
    3. 合并 → 去重 → 返回所有符合条件的帧

    Args:
        keyframes: 关键帧列表（30张，每秒1帧）
        asr_segments: ASR对话片段列表
        change_threshold: 画面变化阈值（0-1，默认0.4）

    Returns:
        精选后的关键帧列表
    """
    if len(keyframes) <= 5:
        # 帧数太少，全部返回
        return keyframes

    # ========== 步骤1：计算画面变化 ==========
    change_scores = []
    for i in range(len(keyframes) - 1):
        change = calculate_frame_difference(
            keyframes[i].frame_path,
            keyframes[i + 1].frame_path
        )
        change_scores.append({
            'index': i,
            'change': change
        })

    # 标记"变化大"的时刻
    significant_change_indices = [
        item['index']
        for item in change_scores
        if item['change'] > change_threshold
    ]

    # ========== 步骤2：标记有对话的时刻 ==========
    dialogue_indices = set()

    # 每个ASR片段的开始时刻
    for asr in asr_segments:
        start_sec = int(asr.start)
        if 0 <= start_sec < len(keyframes):
            dialogue_indices.add(start_sec)

    # ========== 步骤3：智能合并 ==========
    selected_indices = set()

    # 3.1 添加"变化大"的时刻（同时添加下一帧，确保看到变化后的画面）
    for idx in significant_change_indices:
        selected_indices.add(idx)
        if idx + 1 < len(keyframes):
            selected_indices.add(idx + 1)

    # 3.2 添加"有对话"的时刻
    selected_indices.update(dialogue_indices)

    # 3.3 必选：窗口开头和结尾
    selected_indices.add(0)
    selected_indices.add(len(keyframes) - 1)

    # ========== 步骤4：排序并返回 ==========
    selected_indices = sorted(selected_indices)
    selected_keyframes = [keyframes[i] for i in selected_indices]

    # 打印统计信息
    print(f"  📊 画面变化：{len(significant_change_indices)} 处")
    print(f"  💬 对话时刻：{len(dialogue_indices)} 个")
    print(f"  ✅ 最终选择：{len(selected_keyframes)} 张关键帧（原{len(keyframes)}张）")

    # 可选：警告（如果数量异常）
    if len(selected_keyframes) > 25:
        print(f"  ⚠️  警告：选择了 {len(selected_keyframes)} 张关键帧，数量较多")
    elif len(selected_keyframes) < 3:
        print(f"  ⚠️  警告：仅选择了 {len(selected_keyframes)} 张关键帧，数量较少")

    return selected_keyframes


# ========== v0.6.2 修正版分析Prompt ==========
ANALYZE_PROMPT = """你是一位资深的短剧剪辑分析师。基于13个人工剪辑优秀视频的分析经验，我教你如何精准识别高光点和钩子点。

## ⚠️ 重要修正（v0.6.2）

### ❌ 错误的识别方式（不要使用）
- 识别"查看更多视频"按钮或箭头提示（实际视频中不存在这个元素）
- 识别画面边缘的引导性UI元素

### ✅ 正确的识别方式（必须使用）
1. 视觉元素优先（权重70%）+ 台词辅助（权重30%）
2. 分析视觉构图（镜头角度、景别、焦点、色彩）
3. 识别画面中的文字元素（位置、类型）
4. 识别BGM配合（结尾静音、戛然而止）

---

## 🎨 视觉构图分析（v0.6新增，权重70%）

### 镜头角度识别
- **俯拍**: 第一视角代入感，常见于现代题材、危险场景
- **仰拍**: 人物气势强化，常见于仙侠题材、权威展示
- **主观视角**: 强烈代入感，常见于追逐、危险场景
- **平视**: 日常视角，生活化场景

### 景别类型识别
- **特写**: 关键道具/表情强调，高光点标配（诊断报告、法宝、戒指）
- **浅景深虚化**: 焦点集中，突出核心元素（人物清晰、背景模糊）
- **中近景**: 展示人物状态，钩子点标配（通话中、行走中）
- **全景**: 环境展示，场景信息

### 构图位置识别
- **画面中心**: 核心元素，视觉焦点（关键道具、预警文字）
- **黄金分割点**: 次要元素，平衡构图（配角、环境）
- **背景虚化**: 突出前景，制造层次（人物清晰、背景模糊）

### 色彩运用识别
- **暖色调(黄/橙)**: 温馨、日常、现代题材、室内场景
- **冷色调(蓝/绿)**: 神秘、危险、仙侠题材、夜晚场景
- **对比色(冷暖)**: 冲突、奇幻、反转、情绪爆发

---

## 📝 文字元素识别（v0.6新增）

### 文字位置识别
- **画面中央**: 预警性文字（"小心"、"注意"）→ 危险/冲突
- **画面底部**: 标题性文字（剧名）→ 类型确认
- **流动字幕**: 疑问性文字（"看大雪如何衰老的"）→ 好奇心缺口
- **人物胸部**: 核心字幕（"婚礼三天后举行"、"下车礼还没给"）→ 时间节点/未完成事件

### 文字类型识别
- **预警性**: 危险、冲突前奏（"小心"、"注意"）
- **疑问性**: 好奇心缺口（"如何..."、"为什么..."）
- **时间节点**: 明确未来时间（"三天后"、"今晚"）
- **未完成事件**: 指出未完成的冲突（"还没给"、"还没说"）

---

## 🎵 BGM信号分析（v0.6.2重大修正）

### BGM是重要钩子信号，占10%判断权重（基于人工剪辑分析）

#### 强烈钩子信号（需要其他线索配合）
- **BGM戛然而止** + 人物动作维持/定格 → 强钩子点
  - 示例：通话中人物 + BGM戛然而止
  - 置信度：+1.5

- **BGM静音** + 关键道具特写/表情定格 → 强钩子点
  - 示例：诊断报告特写 + BGM静音
  - 置信度：+1.5

#### 中等钩子信号
- **BGM戛然而止** + 有情节暗示 → 中等钩子点
  - 示例：追逐场景 + BGM戛然而止
  - 置信度：+1.0

- **BGM静音** + 时间节点字幕 → 强钩子点
  - 示例："婚礼三天后" + BGM静音
  - 置信度：+1.5

- **BGM静音** + 未完成事件字幕 → 强钩子点
  - 示例："还没给" + BGM静音
  - 置信度：+1.5

#### 弱钩子信号（需要谨慎验证）
- **只有BGM静音/戛然而止**，无明显视觉特征
  - 需要结合：人物动作、表情、场景
  - 如果：人物动作定格/微妙表情 + BGM静音 → 可能是钩子点（置信度 +0.5至+1.0）
  - 如果：平淡场景 + BGM静音 → 可能不是钩子点（置信度 -0.5）

#### 明确不是钩子点
- **BGM维持正常** + 对话自然结束 → 不是钩子点（置信度 -1.0）
- **场景切换导致的停顿** + BGM静音 → 不是钩子点（置信度 -1.0）

---

## 🎯 高光点识别（v0.6优化）

### "3秒抓眼球"原则
高光点必须在开头3秒内抓住观众注意力：
- **0-1秒**: 视觉冲击（强对比色彩、夸张表情、关键道具前置）
- **1-2秒**: 悬念抛出（文字提示、未知危险、道具特写）
- **2-3秒**: 类型确认（剧名、场景特征、题材确认）

### 高光点视觉公式
```
高光点 = 情绪人物(30%) + 关键道具/场景(30%) + 悬念文字(40%)
```

### 优先标记的高光点（按强度）
1. **视觉冲击强**: 夸张表情、关键道具前置、强对比色彩
2. **悬念抛出快**: 预警文字、疑问文字、未解之谜
3. **类型确认快**: 3秒内能确认题材和剧情方向

---

## 🪝 钩子点识别（v0.6.2重大修正）

### 真实钩子制造方式（v0.6.2基于人工剪辑分析）

#### ✅ 应该标记的钩子点（高强度）

1. **时间节点型**（40%人工剪辑使用）
   - 特征：明确未来时间 + 未完成事件
   - 示例："婚礼三天后举行"、"下车礼还没给"
   - 字幕位置：人物胸部区域
   - BGM配合：如果BGM静音/戛然而止，置信度加成 +1.0
   - 应该标记：是

2. **未完成事件型**（30%人工剪辑使用）
   - 特征：指出未完成的冲突，想知道结果
   - 示例："还没给"、"还没说"、"继续..."
   - 人物状态：动作维持（通话中、行走中）
   - BGM配合：如果BGM静音/戛然而止，置信度加成 +1.0
   - 应该标记：是

3. **对话留白型**（20%人工剪辑使用）
   - 特征：对话进行中，只给开头，想知道后续
   - 示例："你好"（通话开场，不知道对方说什么）
   - BGM配合：如果BGM戛然而止，置信度加成 +0.5
   - 应该标记：是

4. **悬念结束时刻**
   - 特征：关键行动或事件的高潮时刻画面停住
   - 关键词：要、即将、马上、正要
   - BGM配合：如果BGM戛然而止/静音，置信度加成 +0.8
   - 应该标记：是

5. **情节重大转折**
   - 特征：反转、突变、意外、命运改变
   - BGM配合：如果BGM高潮后骤降，置信度加成 +0.5
   - 应该标记：是

6. **纯画面型**（10%人工剪辑使用）⭐ **v0.6.2新增**
   - 特征：无字幕，人物动作定格/维持，情绪未释放
   - BGM配合：BGM戛然而止或静音（关键信号）
   - 示例：人物手指即将按下按钮 + BGM静音
   - 示例：门即将打开 + BGM戛然而止
   - 示例：人物表情定格（震惊/疑惑） + BGM静音
   - 应该标记：是

#### ❌ 不要标记的情况（假钩子）

1. **普通对话结束**
   - 角色表达完完整意思后停顿
   - 示例："好的，我知道了。"
   - 注意：即使BGM静音，也不标记

2. **场景切换导致的停顿**
   - 镜头转换、时间地点变化
   - 示例："好的... [下一场景]"
   - 注意：即使BGM静音，也不标记

3. **日常对话、常规剧情**
   - 铺垫性的情节、问候、闲聊
   - 示例："今天天气不错"
   - 注意：即使BGM静音，也不标记

4. **已知信息的重复**
   - 前面已经说过的内容
   - 示例："就像我之前说的"
   - 注意：即使BGM静音，也不标记

---

## 📊 分析权重分配（v0.6.2重大修正）

### 高光点判断权重
- **视觉构图**（镜头、景别、色彩、文字）：40%
- **人物情绪**（表情、动作）：30%
- **道具/场景**（关键元素、符号化）：20%
- **台词**（关键词、语气）：10%

### 钩子点判断权重（v0.6.2修正）
- **视觉元素**（字幕、人物状态、构图）：40%
- **情节未完成**（时间节点、事件未完）：30%
- **情绪未释放**（紧张、期待）：20% ⭐ **v0.6.2提升**
- **BGM配合**（戛然而止/静音）：10% ⭐ **v0.6.2从辅助提升为独立权重**

---

## 核心原则：识别真正的钩子点（v0.6.2修正）

根据人工剪辑优秀视频分析：**每集通常有2-3个钩子点**。

**关键**：
1. 不要标记"对话突然中断"这个宽泛的类型
2. 重点识别：时间节点字幕、未完成事件、对话留白
3. 视觉元素比台词更重要（视觉70%，台词30%）
4. BGM戛然而止/静音是重要钩子信号（占10%权重）⭐ **v0.6.2修正**
   - ✅ 正确：人物动作定格/情绪未释放 + BGM戛然而止 → 钩子点
   - ✅ 正确：时间节点字幕 + BGM静音 → 强钩子点
   - ✅ 正确：纯画面型（无字幕）+ 人物定格 + BGM静音 → 钩子点
   - ❌ 错误：只有BGM静音，但平淡场景 → 可能不是钩子点
5. "纯画面型"钩子识别（10%人工剪辑使用）⭐ **v0.6.2新增**
   - 无字幕，但人物动作定格 + 情绪未释放 + BGM戛然而止

## 高光点定义 ⭐
- **含义**：从**这个时刻开始**，观众更愿意看下去
- **3秒原则**：开头3秒内必须抓住观众
- **视觉优先**：视觉冲击（70%）> 台词（30%）
- **关键**：返回窗口内**精确的秒数**，不是窗口开始时间！

## 钩子点定义 🪝
- **含义**：播放到**这个时刻突然结束**，观众迫切想知道后续
- **真实方式**：时间节点字幕、未完成事件、对话留白（不是"查看更多"）
- **关键**：返回窗口内**精确的秒数**，不是窗口开始时间！

## 分析片段信息
时间范围：{START}-{END}秒（第{EPISODE}集，窗口时长{DURATION}秒)
关键帧：[按时间顺序排列，每帧都有时间戳]
ASR文本（**V15.5: 每句话都有精确时间戳**）：
{ASR_TEXT}

**⏰️ V15.5 时间戳格式说明**：
- ASR文本格式为 `[开始时间-结束时间秒] 对话内容`
- 例如：`[19.0-24.0秒] 在过十小时真正的高温末世就要开始了`
- **请根据时间戳精确定位钩子点位置**，返回精确的秒数！

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
    # V15.5: 合并ASR文本,包含精确时间戳信息
    asr_text_parts = []
    for seg in segment.asr_segments:
        # 每句话都标注精确的时间戳范围
        asr_text_parts.append(f"[{seg.start:.1f}-{seg.end:.1f}秒] {seg.text}")
    asr_text = '\n'.join(asr_text_parts)
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

    # ========== V14: 智能关键帧过滤 ==========
    # 使用智能过滤：只传"有意义"的帧（对话 + 画面变化）
    selected_keyframes = smart_select_keyframes(
        keyframes=segment.keyframes,
        asr_segments=segment.asr_segments,
        change_threshold=0.4  # 画面变化阈值
    )

    # 准备关键帧图片
    keyframe_parts = []
    for kf in selected_keyframes:
        try:
            img_base64 = encode_image(kf.frame_path)
            keyframe_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
            })
        except Exception as e:
            print(f"  ⚠️  无法编码图片 {kf.frame_path}: {e}")

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
            "confidence": highlight_data.get("confidence") or 0.0,  # V13.1: 处理None值
            "reasoning": highlight_data.get("reasoning", "")
        },
        "hook": {
            "exists": hook_data.get("exists", False),
            "preciseSecond": hook_timestamp,
            "type": hook_data.get("type"),
            "confidence": hook_data.get("confidence") or 0.0,  # V13.1: 处理None值
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
                highlight_timestamp=float(hl_data.get("preciseSecond") or segment.start_time),  # V13.1: 处理None值
                highlight_type=hl_data.get("type"),
                highlight_desc=hl_data.get("reasoning", ""),
                highlight_confidence=hl_data.get("confidence") or 0.0,  # V13.1: 处理None值

                # 钩子点（V13: 转换为浮点数支持毫秒精度）
                is_hook=hook_data.get("exists", False),
                hook_timestamp=float(hook_data.get("preciseSecond") or segment.start_time),  # V13.1: 处理None值
                hook_type=hook_data.get("type"),
                hook_desc=hook_data.get("reasoning", ""),
                hook_confidence=hook_data.get("confidence") or 0.0  # V13.1: 处理None值
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
