# AI检测逻辑分析报告

> 版本: v1.0 | 创建日期: 2026-03-05
> 分析对象: 杭州雷鸣AI短剧剪辑服务 v0.5

---

## 📊 执行摘要

本报告深入分析了杭州雷鸣AI短剧剪辑服务中高光点/钩子点检测的完整技术实现。

### 核心发现
- **检测方法**: 基于Gemini 2.0 Flash视觉模型的多模态分析
- **特征来源**: 关键帧(视觉) + ASR转录文本(听觉)
- **类型体系**: 12种高光类型 + 15种钩子类型
- **性能指标**: 召回率 ~29.5%，精确度 ~17.8%
- **主要瓶颈**: 误报率过高，大量假钩子被标记

---

## 1. 检测方法工作流程

### 1.1 整体架构

```
视频输入
    ↓
关键帧提取 (30张/片段，每秒1帧)
    ↓
ASR转录 (Whisper语音识别)
    ↓
片段分割 (60秒滑动窗口)
    ↓
智能关键帧过滤 (V14优化)
    ↓
Gemini AI分析 (视觉+文本多模态)
    ↓
质量过滤管道 (5阶段)
    ↓
高光点/钩子点输出
```

### 1.2 关键步骤详解

#### 步骤1: 关键帧提取
```python
# scripts/extract_keyframes.py
# 自动检测FPS并调整采样密度
fps = detect_video_fps(video_file)
if fps >= 50:
    sampling_fps = 2.0  # 密集采样
elif fps >= 30:
    sampling_fps = 1.0  # 标准采样
else:
    sampling_fps = 0.5  # 稀疏采样
```

**特点**:
- 自动检测视频实际FPS
- 高帧率视频(50fps)使用更密集的采样
- 每个片段提取约30张关键帧

#### 步骤2: ASR转录
```python
# scripts/extract_asr.py
# 使用Whisper模型转录语音
asr_segments = whisper_model.transcribe(audio)
# 返回格式: [{text: str, start: float, end: float}, ...]
```

**特点**:
- 使用OpenAI Whisper模型
- 返回带时间戳的文本片段
- 用于分析台词内容、情绪关键词

#### 步骤3: 智能关键帧过滤 (V14核心优化)
```python
# scripts/understand/analyze_segment.py: smart_select_keyframes()
def smart_select_keyframes(keyframes, asr_segments, change_threshold=0.4):
    # 1. 计算画面变化度 (感知哈希算法)
    for i in range(len(keyframes) - 1):
        change = calculate_frame_difference(
            keyframes[i], keyframes[i+1]
        )
        if change > 0.4:  # 变化阈值
            significant_changes.append(i)

    # 2. 标记有对话的时刻
    for asr in asr_segments:
        dialogue_indices.add(int(asr.start))

    # 3. 合并: 画面变化 + 对话时刻
    selected_indices = significant_changes ∪ dialogue_indices

    return selected_indices
```

**优化效果**:
- 原始: 30张关键帧 → AI处理
- 优化后: 平均8-15张关键帧 → 减少50-70%的Token消耗
- 保留: 所有"有意义的画面变化"和"对话时刻"

#### 步骤4: Gemini AI分析
```python
# 构建多模态Prompt
parts = [
    {"text": ANALYZE_PROMPT},
    {"inline_data": {"mime_type": "image/jpeg", "data": base64_frame1}},
    {"inline_data": {"mime_type": "image/jpeg", "data": base64_frame2}},
    # ... 更多关键帧
]

# 调用Gemini 2.0 Flash API
response = gemini_api.generate_content(parts)
```

**Prompt结构**:
1. 学习示例: 4个真/假钩子对比案例
2. 定义说明: 高光点 vs 钩子点的明确区别
3. 类型列表: 12种高光 + 15种钩子类型
4. 分析步骤: 5步分析流程
5. 输出格式: JSON格式要求

#### 步骤5: 质量过滤管道
```python
# scripts/understand/quality_filter.py
def apply_quality_pipeline(analyses, episode_durations):
    # 阶段1: 置信度筛选 (阈值7.0)
    analyses = filter_by_confidence(analyses, 7.0)

    # 阶段2: 时间去重 (10秒窗口)
    analyses = deduplicate_analyses(analyses, 10)

    # 阶段3: 类型多样性限制 (每集同类型最多1个)
    analyses = limit_type_diversity(analyses, 1)

    # 阶段4: 动态数量限制 (每分钟1高光+6钩子)
    analyses = limit_by_top_n(analyses, episode_durations)

    # 阶段5: 添加第1集开篇高光点
    analyses = add_opening_highlight(analyses)

    return analyses
```

---

## 2. 高光点识别规则 (12种类型)

### 2.1 类型列表

| 序号 | 类型 | 描述 | 关键特征 |
|------|------|------|----------|
| 1 | 开篇高光 | 第1集开头的默认高光点 | 开场画面、快速切入 |
| 2 | 剧情反转 | 意想不到的转折 | 严肃/愧疚/惊讶表情，真相揭露 |
| 3 | 信息揭示 | 快速抛出关键信息 | 旁白叙述，身世秘密、情感关系 |
| 4 | 冲突爆发 | 激烈的言语或肢体冲突 | 愤怒/指责表情，质问/争吵台词 |
| 5 | 误会尴尬 | 角色误解或不适导致尴尬 | 困惑/回忆表情，内心独白 |
| 6 | 紧急救援 | 主角专业能力展现 | 严肃/专注表情，推进手术室 |
| 7 | 职场心机 | 职场中的心机和手段 | 微笑/得意/严肃，整理资料/观察周围 |
| 8 | 情感爆发 | 强烈情感冲击的表达 | 痛苦/震惊/焦急，哭泣/抓住 |
| 9 | 信息交代 | 快速交代背景信息 | 平静/严肃/悲伤，旁白叙述 |
| 10 | 重生立威 | 重生后地位/权力变化 | 惊讶/严肃，教训/指责 |
| 11 | 悲惨遭遇 | 不幸和坚韧的展现 | 悲伤/绝望/疲惫，埋葬/跪拜 |
| 12 | 特殊场景 | 其他特殊情节 | - |

### 2.2 识别特征矩阵

#### 视觉特征
```python
visual_features = {
    "表情": [
        "严肃", "愧疚", "惊讶", "微笑", "冷漠", "痛苦", "绝望",
        "愤怒", "指责", "隐忍", "专注", "得意", "焦急", "疲惫"
    ],
    "景别": ["特写", "中景", "近景", "全景", "远景"],
    "动作": [
        "说话", "道歉", "奔跑", "下楼", "踹人", "倒地", "哭泣",
        "抓住", "指认", "对峙", "冲进", "埋葬", "跪拜"
    ],
    "场景": [
        "室内", "宴会厅", "会议室", "办公室", "庭院", "医院",
        "战场", "坟地", "演播厅"
    ]
}
```

#### 听觉特征
```python
audio_features = {
    "台词类型": [
        "解释", "道歉", "质问", "指责", "争吵", "辩解",
        "旁白", "叙述", "独白", "恳求", "自嘲"
    ],
    "情绪关键词": [
        "愧疚", "愤怒", "紧张", "委屈", "悲伤", "绝望",
        "恐惧", "得意", "焦急", "无奈", "痛苦"
    ],
    "内容模式": [
        "揭露真相", "揭示关系", "剧情转折", "交代背景",
        "回忆经历", "争论对错"
    ]
}
```

### 2.3 典型高光点案例

**案例1: 剧情反转高光**
- 时间: 第2集 125秒
- 视觉: 人物表情严肃，特写镜头，道歉场景
- 听觉: "对不起，我骗了你...其实是..."
- 判断依据:
  1. 表情严肃/愧疚 (✅)
  2. 特写镜头 (✅)
  3. 台词包含道歉和真相揭露 (✅)
  4. 剧情功能为反转 (✅)
- 置信度: 8.5/10

---

## 3. 钩子点识别规则 (15种类型)

### 3.1 类型列表

| 序号 | 类型 | 描述 | 关键特征 |
|------|------|------|----------|
| 1 | 情感冲突 | 男女主事业家庭争执 | 指责/辩解/争吵/质问 |
| 2 | 家庭伦理冲突 | 家庭内部矛盾 | 牺牲偏袒引发冲突 |
| 3 | 情感冲突与威胁 | 情感冲突+潜在威胁 | 争吵+威胁+命令 |
| 4 | 职场冲突预警 | 职场困境暗示 | 催促+命令+施压 |
| 5 | 情感克制与冲突 | 内心挣扎+潜在冲突 | 内心独白+压抑+冷漠 |
| 6 | 情感冲击 | 秘密被突然曝光 | 震惊+愤怒+恐惧 |
| 7 | 情感爆发/真相揭露 | 情感爆发+重要信息 | 独白+悲伤+痛苦 |
| 8 | 反击打脸 | 女主愤怒反击 | 争吵+指责+愤怒 |
| 9 | 情感回忆 | 醉酒后吐露真心 | 内心独白+醉话+依赖 |
| 10 | 职场潜规则暗示 | 职场暗示 | 群聊信息+羡慕+无奈 |
| 11 | 阴谋计划 | 反派透露阴谋 | 独白+阴谋+得意+恶毒 |
| 12 | 水中遇险 | 水中挣扎+疑问恐惧 | 内心独白+痛苦+疑惑 |
| 13 | 虐心剧情 | 女主恳求休妻 | 恳求+诉说+悲伤+哀求 |
| 14 | 反转 | 台词和关系反转 | 愤怒+无奈+各种台词类型 |
| 15 | 突发危机 | 突然遭遇危险 | 打斗声+悲伤+惊呼+惊讶 |

### 3.2 钩子点识别核心逻辑

#### 关键区分: 真钩子 vs 假钩子

**真钩子特征 (应该标记)**:
```python
true_hook_features = {
    "关键信息被截断": {
        "描述": "秘密、真相、重要决定即将揭晓时被打断",
        "关键词": ["秘密", "真相", "揭露", "决定", "身份", "说出"],
        "示例": "夫人正要说出陆大人的秘密，突然被闯入的家丁打断"
    },
    "悬念结束时刻": {
        "描述": "关键行动或事件的高潮时刻画面停住",
        "关键词": ["要", "即将", "马上", "正要"],
        "示例": "女主说：我要进去看陆停松到底怎么了。画面结束"
    },
    "情节重大转折": {
        "描述": "反转、突变、意外、命运改变",
        "特征": ["剧情突变", "人物关系改变", "意外事件"]
    }
}
```

**假钩子特征 (不要标记)**:
```python
false_hook_features = {
    "对话自然结束": {
        "描述": "角色表达完完整意思后停顿",
        "示例": "男主说：那就请太夫人。对话结束"
    },
    "场景切换": {
        "描述": "镜头转换、时间地点变化",
        "示例": "女主说：我这么好语... [下一场景]"
    },
    "日常对话": {
        "描述": "铺垫性情节、问候、闲聊",
        "示例": "今天天气不错"
    }
}
```

### 3.3 典型钩子点案例

**案例1: 真钩子 - 关键信息被截断**
- 时间: 第2集 366秒
- 视觉: 夫人表情严肃，正要说话，突然被闯入者打断
- 听觉: "陆大人他其实是...啊！谁敢擅闯！"
- 判断依据:
  1. 关键信息即将揭露 (✅)
  2. 被第三方突然打断 (✅)
  3. 观众迫切想知道秘密 (✅)
  4. 不是对话自然结束 (✅)
- 置信度: 9.2/10

**案例2: 假钩子 - 对话自然结束**
- 时间: 第1集 75秒
- 视觉: 男主平静表达请求
- 听觉: "那就请太夫人。" (停顿)
- 判断依据:
  1. 信息不关键 (❌)
  2. 没有迫切感 (❌)
  3. 对话自然结束 (❌)
- 判断结果: 不标记

---

## 4. 置信度评估方式

### 4.1 AI评分标准 (0-10分)

```python
# Gemini AI的评分逻辑
confidence_scoring = {
    "完美匹配 (9.0-10.0)": {
        "描述": "符合所有识别规则",
        "要求": [
            "视觉特征完全匹配",
            "听觉特征完全匹配",
            "剧情功能完全匹配",
            "时间定位精确"
        ]
    },
    "良好匹配 (7.5-8.9)": {
        "描述": "符合大部分识别规则",
        "要求": [
            "主要特征匹配",
            "部分辅助特征匹配",
            "剧情功能合理",
            "时间定位较精确"
        ]
    },
    "中等匹配 (6.0-7.4)": {
        "描述": "符合核心规则，但缺少辅助特征",
        "要求": [
            "核心特征匹配",
            "辅助特征部分匹配",
            "剧情功能可能"
        ]
    },
    "弱匹配 (<6.0)": {
        "描述": "仅符合少量规则",
        "处理": "被质量过滤管道移除"
    }
}
```

### 4.2 质量过滤阈值

```python
# scripts/understand/quality_filter.py
quality_thresholds = {
    "置信度阈值": 7.0,  # 低于此值直接过滤
    "时间去重窗口": 10,  # 10秒内同类型只保留最高置信度
    "类型多样性限制": 1,  # 每集同类型最多1个
    "动态数量限制": {
        "高光点": "每分钟1个",
        "钩子点": "每分钟6个"
    }
}
```

### 4.3 置信度计算示例

**高光点置信度计算**:
```python
def calculate_highlight_confidence(analysis_result):
    score = 0.0

    # 视觉特征匹配 (40%)
    if analysis_result.visual_cues_match:
        score += 4.0

    # 听觉特征匹配 (30%)
    if analysis_result.audio_cues_match:
        score += 3.0

    # 剧情功能匹配 (20%)
    if analysis_result.plot_function_match:
        score += 2.0

    # 时间定位精度 (10%)
    if analysis_result.timestamp_accurate:
        score += 1.0

    return score
```

---

## 5. 优缺点分析

### 5.1 优点

#### 1. 多模态融合分析
- ✅ 同时利用视觉(关键帧)和听觉(ASR)信息
- ✅ 画面变化度算法有效过滤静态镜头
- ✅ 对话时刻标记确保不遗漏关键信息

#### 2. 智能关键帧过滤 (V14优化)
- ✅ 减少Token消耗50-70%
- ✅ 保留所有"有意义"的画面变化
- ✅ 提升AI处理速度

#### 3. 详细的类型体系
- ✅ 12种高光类型覆盖多种剧情模式
- ✅ 15种钩子类型覆盖多种悬念形式
- ✅ 每种类型都有明确的特征定义

#### 4. 真/假钩子区分机制
- ✅ 通过4个示例教会AI区分真/假钩子
- ✅ 明确列出"不要标记"的情况
- ✅ 减少误报

#### 5. 多阶段质量过滤
- ✅ 置信度筛选移除低质量标记
- ✅ 时间去重避免重复标记
- ✅ 类型多样性保证丰富性
- ✅ 动态数量限制适应不同时长

### 5.2 缺点

#### 1. 召回率低 (~29.5%)
**问题**: 大量真实高光点/钩子点未被识别

**原因分析**:
- **Prompt限制**: Token限制导致关键帧和ASR文本被截断
  ```python
  # analyze_segment.py:386
  ASR_TEXT=asr_text[:800],  # 只传前800字符
  ```
  - 影响: 后半部分的对话内容丢失
  - 后果: 错过后半部分的钩子点

- **时间窗口限制**: 60秒滑动窗口可能错过关键片段
  ```python
  # extract_segments.py
  WINDOW_SIZE = 60  # 60秒窗口
  ```
  - 影响: 跨窗口的情节断裂被忽略
  - 后果: 无法识别需要上下文的钩子点

- **关键帧采样不足**: 每秒1帧可能错过瞬间动作
  ```python
  # extract_keyframes.py
  sampling_fps = 1.0  # 每秒1帧
  ```
  - 影响: 快速动作/表情变化可能被遗漏
  - 后果: 错过短暂的高光时刻

#### 2. 精确度低 (~17.8%)
**问题**: 大量误报，标记了很多"假钩子"

**原因分析**:
- **AI过度解读**: Gemini倾向于"标记一切可疑的"
  - 对话自然结束被误判为"悬念"
  - 场景切换停顿被误判为"钩子点"
  - 日常对话被误判为"冲突"

- **类型特征重叠**: 15种钩子类型特征相似度高
  - "情感冲突"、"家庭伦理冲突"、"情感冲突与威胁"难以区分
  - AI难以精准匹配到具体类型

- **上下文缺失**: 分析时缺少前后文信息
  ```python
  # analyze_segment.py只传入当前窗口的信息
  # 没有传入前后窗口的上下文
  ```
  - 影响: 无法判断这是"真悬念"还是"日常对话"

#### 3. 特征覆盖不全

**视觉特征缺失**:
- ❌ 没有分析色彩变化 (如: 暗色调变亮色调)
- ❌ 没有分析镜头运动 (推拉摇移)
- ❌ 没有分析构图变化 (如: 对称构图变不对称)
- ❌ 没有分析服装/化妆变化

**听觉特征缺失**:
- ❌ 没有分析背景音乐 (BGM)变化
  - 悬念时刻通常BGM突然静音或变调
  - 高潮时刻BGM音量提升
- ❌ 没有分析音效 (如: 打击声、心跳声)
- ❌ 没有分析语速变化 (如: 突然变快/变慢)
- ❌ 没有分析音量变化 (如: 突然提高/降低)

**剧情特征缺失**:
- ❌ 没有分析人物关系变化
- ❌ 没有分析情节伏笔
- ❌ 没有分析节奏变化

#### 4. 时间定位不够精确

**问题**: AI返回的时间戳误差较大

**现状**:
```python
# AI返回的是秒级精度
"preciseSecond": 366  # 秒级

# 但实际需要帧级精度
actual_frame = 366 * 30  # 第10980帧
```

**影响**:
- 剪辑时可能错过最佳帧
- 尤其对于快速动作，1秒误差影响很大

#### 5. 质量过滤过于严格

**问题**: 多阶段过滤可能移除真实标记

**示例**:
```python
# 一个置信度6.8的真实钩子点
# 阶段1: 置信度筛选 (阈值7.0) → 被移除 ❌
# 即使它可能是真实的钩子点
```

**影响**:
- 提高了精确度，但降低了召回率
- 需要更好的平衡

---

## 6. 改进方向

### 6.1 短期改进 (1-2周)

#### 1. 增加BGM分析
```python
# 建议新增: scripts/extract_bgm.py
def extract_bgm_features(audio_path):
    """
    提取背景音乐特征

    Returns:
        {
            "silence_moments": [12.5, 36.6, ...],  # BGM静音时刻
            "volume_changes": [(10.2, "low_to_high"), ...],
            "tempo_changes": [(25.3, "slow_to_fast"), ...]
        }
    """
    # 使用librosa分析音频
    y, sr = librosa.load(audio_path)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    # ... 更多分析
```

**集成到检测流程**:
```python
# 在analyze_segment.py中
bgm_features = extract_bgm_features(audio_path)
if bgm_features["silence_moments"]:
    # BGM静音时刻 = 强烈钩子点信号
    hook_candidates.extend(bgm_features["silence_moments"])
```

#### 2. 优化Prompt工程
```python
# 当前问题: Prompt过长，Token消耗大
# 解决方案: 分层Prompt

ANALYZE_PROMPT_V2 = """
# 第1层: 快速筛选
"快速判断这个30秒片段是否包含高光点/钩子点"

# 第2层: 精细分析 (仅对筛选通过的片段)
"详细分析标记点的类型、置信度、推理"
"""
```

**预期效果**:
- Token消耗减少60%
- 处理速度提升2倍
- 召回率提升10%

#### 3. 增加上下文窗口
```python
# 当前: 只传入当前60秒窗口
# 改进: 传入当前窗口 + 前后10秒上下文

def build_contextual_prompt(segment, before_context, after_context):
    prompt = f"""
    # 前情提要 (前10秒)
    {before_context.asr_text}

    # 当前片段 (60秒)
    {segment.asr_text}

    # 后续发展 (后10秒)
    {after_context.asr_text}
    """
    return prompt
```

### 6.2 中期改进 (1个月)

#### 1. 引入镜头运动分析
```python
# 建议新增: scripts/analyze_camera_movement.py
def detect_camera_movement(keyframes):
    """
    检测镜头运动类型

    Returns:
        {
            "push_in": [5.2, 15.6],      # 推镜头
            "pull_out": [8.3, 20.1],     # 拉镜头
            "pan_left": [12.5, 18.9],    # 左摇
            "tilt_up": [22.1, 25.3]      # 上仰
        }
    """
    # 使用光流法分析镜头运动
    # 推镜头通常 = 强调重点 = 高光点
    # 拉镜头通常 = 结束场景 = 钩子点
```

#### 2. 训练专用模型
```python
# 当前: 使用通用Gemini模型
# 改进: 微调专用模型

training_data = {
    "positive_samples": [
        # 真实高光点/钩子点样本
    ],
    "negative_samples": [
        # 假钩子样本
    ]
}

# 使用LoRA微调Gemini
# 专门针对短剧剪辑场景优化
```

**预期效果**:
- 精确度提升至35%+
- 召回率提升至50%+

#### 3. 时序关系分析
```python
# 分析标记点之间的时序关系
def analyze_temporal_relationship(highlights, hooks):
    """
    分析高光点和钩子点的时序关系

    Returns:
        {
            "perfect_pairs": [(hl1, hook1), (hl2, hook2)],
            "orphan_highlights": [hl3, hl4],
            "orphan_hooks": [hook3, hook4]
        }
    """
    # 理想的剪辑组合: 高光点 → 钩子点
    # 孤立的高光点/钩子点可能是误报
```

### 6.3 长期改进 (3个月+)

#### 1. 多模型集成
```python
# 集成多个AI模型的判断结果
def ensemble_prediction(segment):
    results = {
        "gemini": gemini_model.predict(segment),
        "gpt4_vision": gpt4_model.predict(segment),
        "claude_vision": claude_model.predict(segment),
        "custom_model": custom_model.predict(segment)
    }

    # 投票机制
    final_result = majority_vote(results)
    return final_result
```

#### 2. 用户反馈闭环
```python
# 人工校验结果反馈到训练数据
def collect_human_feedback(ai_result, human_correction):
    """
    收集人工校验结果

    用途:
    1. 更新训练数据
    2. 微调模型
    3. 优化质量过滤阈值
    """
    feedback_data = {
        "ai_prediction": ai_result,
        "human_correction": human_correction,
        "confidence": ai_result.confidence
    }
    return feedback_data
```

#### 3. 自适应学习
```python
# 根据项目特征自适应调整
def adaptive_thresholds(project_stats):
    """
    根据项目统计自适应调整阈值

    Args:
        project_stats: {
            "avg_highlights_per_episode": 1.2,
            "avg_hooks_per_episode": 2.5,
            "avg_confidence": 7.8
        }

    Returns:
        优化后的阈值
    """
    if project_stats["avg_confidence"] > 8.0:
        # 高置信度项目，提高阈值
        confidence_threshold = 7.5
    else:
        # 低置信度项目，降低阈值
        confidence_threshold = 6.5

    return confidence_threshold
```

---

## 7. 性能基准

### 7.1 当前性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 召回率 | 29.5% | 100个人工标记中，AI识别出29.5个 |
| 精确度 | 17.8% | AI标记的100个中，17.8个是正确的 |
| F1分数 | 0.22 | 召回率和精确度的调和平均 |
| 平均处理时间 | ~3分钟/集 | 包含关键帧提取、ASR、AI分析 |
| Token消耗 | ~15K tokens/片段 | Gemini API消耗 |

### 7.2 目标性能指标

| 指标 | 当前 | 目标 | 改进幅度 |
|------|------|------|----------|
| 召回率 | 29.5% | 60% | +103% |
| 精确度 | 17.8% | 50% | +181% |
| F1分数 | 0.22 | 0.55 | +150% |
| 处理时间 | 3分钟 | 2分钟 | -33% |
| Token消耗 | 15K | 8K | -47% |

---

## 8. 结论

### 8.1 核心发现

1. **多模态方法有效**: 结合视觉和听觉特征是正确方向
2. **类型体系完善**: 12+15种类型覆盖了大部分短剧模式
3. **真/假钩子区分是关键**: 减少"假钩子"误报是提升精确度的核心
4. **质量过滤是一把双刃剑**: 提升了精确度但降低了召回率
5. **特征覆盖仍需扩展**: BGM、镜头运动、时序关系等特征尚未利用

### 8.2 最有价值的改进方向

按投入产出比排序:

1. **增加BGM分析** (投入: 低，产出: 高)
   - 实现: 1周
   - 效果: 召回率+10%, 精确度+15%

2. **优化Prompt工程** (投入: 中，产出: 高)
   - 实现: 2周
   - 效果: Token消耗-60%, 处理速度+100%

3. **增加上下文窗口** (投入: 中，产出: 中)
   - 实现: 2周
   - 效果: 精确度+10%

4. **引入镜头运动分析** (投入: 高，产出: 中)
   - 实现: 4周
   - 效果: 召回率+8%, 精确度+12%

5. **训练专用模型** (投入: 高，产出: 高)
   - 实现: 8周
   - 效果: 召回率+20%, 精确度+25%

### 8.3 最终建议

**优先实施**:
1. BGM分析功能
2. Prompt优化
3. 上下文窗口

**中期规划**:
1. 镜头运动分析
2. 用户反馈闭环
3. 自适应阈值

**长期愿景**:
1. 多模型集成
2. 专用模型训练
3. 端到端优化

---

## 附录A: 关键文件索引

| 文件路径 | 功能 | 核心代码行 |
|---------|------|-----------|
| `scripts/understand/analyze_segment.py` | AI片段分析 | 168-327 |
| `scripts/understand/quality_filter.py` | 质量过滤管道 | 313-368 |
| `scripts/extract_keyframes.py` | 关键帧提取 | 全文 |
| `scripts/extract_asr.py` | ASR转录 | 全文 |
| `data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.5.md` | 技能定义 | 12-425 |

## 附录B: 配置参数索引

| 参数名 | 默认值 | 位置 | 说明 |
|--------|--------|------|------|
| `WINDOW_SIZE` | 60 | `extract_segments.py` | 分析窗口大小(秒) |
| `MIN_CONFIDENCE` | 7.0 | `quality_filter.py` | 最低置信度阈值 |
| `MIN_DISTANCE` | 10 | `quality_filter.py` | 去重时间窗口(秒) |
| `CHANGE_THRESHOLD` | 0.4 | `analyze_segment.py` | 画面变化阈值 |
| `sampling_fps` | 1.0 | `extract_keyframes.py` | 关键帧采样密度 |

---

**报告结束**

> 下一步: 基于本分析报告，设计新的检测规则或优化现有逻辑
