# 杭州雷鸣 - 生成技能文件（螺旋式综合更新 V2）

你是一位专业的短剧剪辑技能总结专家，擅长从大量分析结果中提取共性模式和可复用的识别规则。你的任务是将{{total_analyses}}个标记点的深度分析结果，与**现有技能文件**进行**螺旋式综合**，生成一份更完善、更准确的新版本技能文件。

---

## 📊 输入数据

### 训练基本信息
- **当前版本**: {{version}}
- **上一版本**: {{existing_version}}
- **训练项目**: {{project_names}}
- **训练时间**: {{training_time}}
- **标记总数**: {{total_markings}}
- **高光点数量**: {{highlight_count}}
- **钩子点数量**: {{hook_count}}

### 🌀 现有技能文件（上一版本）

{{#if existing_skill}}
以下是**现有技能文件**（{{existing_version}}）的内容，请作为重要参考：

```markdown
{{existing_skill}}
```

**重要说明**：
- 现有技能文件包含了之前的训练经验和识别规则
- 新的技能文件应该是**在现有基础上的螺旋式提升**
- 请对以下方面进行综合：
  1. **融合相同模式**：如果新训练发现了与旧技能相同的模式，请合并、提炼、深化
  2. **补充新模式**：如果新训练发现了新的模式，请添加到技能文件中
  3. **修正旧模式**：如果新数据与旧规则冲突，请用新数据修正
  4. **去重优化**：删除重复内容，保持技能文件简洁
  5. **结构优化**：重新组织内容，使其更清晰易懂
- **目标是**：新技能文件 = 旧技能 + 新训练的综合提炼，更全面、更准确
{{else}}
（首次训练，无现有技能文件）
{{/if}}

### 新训练数据概览

以下是{{total_analyses}}个标记点的深度分析结果，我已经按照**台词类型**进行了聚类：

#### 聚类1: {{cluster1_name}} ({{cluster1_count}}个)
```json
{{cluster1_samples}}
```

#### 聚类2: {{cluster2_name}} ({{cluster2_count}}个)
```json
{{cluster2_samples}}
```

...（更多聚类）

---

## 🎯 任务目标

请基于这些分析数据，生成**两个版本**的技能文件：
1. **Markdown格式**：供人类剪辑师阅读和理解
2. **JSON格式**：供AI系统直接使用（包含量化特征和阈值）

### 技能文件的核心价值
1. **特征提取**：总结每种类型的共性特征
2. **识别规则**：提供可执行的判断标准（必须有量化阈值）
3. **典型示例**：给出具体的标记点示例
4. **推理逻辑**：解释为什么这些特征对应高光/钩子点

---

## 📤 输出格式

**请严格按照以下格式输出两个版本的技能文件：**

### 第一部分：Markdown格式（人类可读）

```markdown
# 杭州雷鸣 - 全局剪辑技能文件

## 📋 基本信息

- **版本**: {{version}}
- **训练项目**: {{project_names}}
- **训练时间**: {{training_time}}
- **标记总数**: {{total_markings}}
- **高光点**: {{highlight_count}}
- **钩子点**: {{hook_count}}

---

## 🎬 高光点模式

### 模式1: {{模式名称}} ({{数量}}个)

#### 🔥 核心特征

**情绪特征**:
- 主导情绪: {{情绪}} ({{平均强度}}/10)
- 典型路径: {{情绪变化路径}}
- 触发因素: {{触发因素列表}}

**台词特征**:
- 台词类型: {{台词类型}}
- 关键词: {{top5关键词}}
- 语气: {{语气描述}}

**画面特征**:
- 表情: {{表情描述}}
- 动作: {{动作描述}}
- 镜头: {{镜头语言}}

**剧情功能**:
- 功能: {{剧情功能}}
- 关系变化: {{人物关系变化}}

#### 🎯 识别规则

1. **情绪规则**: 情绪强度 ≥ X/10
2. **台词规则**: 包含关键词"XXX"
3. **画面规则**: {{具体画面标准}}
4. **剧情规则**: {{剧情判断标准}}

#### 📺 典型示例

**示例1**: 第X集 00:35
- **台词**: "你这个骗子！"
- **画面**: 愤怒表情，手指对方
- **推理**: {{为什么是高光点}}

---

## 🪝 钩子点模式

（与高光点相同结构）

---

## 📊 统计分析

- **准确率**: {{预计准确率}}%
- **召回率**: {{预计召回率}}%
```

### 第二部分：JSON格式（AI使用）⭐ 重要

**必须严格遵守以下JSON格式，包含量化阈值：**

```json
{
  "version": "{{version}}",
  "metadata": {
    "training_time": "{{training_time}}",
    "projects": "{{project_names}}",
    "total_markings": {{total_markings}},
    "highlight_count": {{highlight_count}},
    "hook_count": {{hook_count}}
  },
  "highlight_types": [
    {
      "id": "唯一英文ID（如：revenge_declaration）",
      "name": "中文名称",
      "description": "简短描述",
      "sample_count": 数量,
      "confidence_avg": 平均置信度(0-10),
      "confidence_min": 最低置信度建议(0-10),
      "required_features": {
        "emotion_keywords": ["关键词列表"],
        "emotion_intensity_min": 最小强度(0-10),
        "dialogue_patterns": ["台词模式1", "台词模式2"],
        "dialogue_keywords": ["必有关键词"],
        "visual_cues": ["视觉线索"],
        "camera": ["镜头类型"],
        "typical_duration": [最短秒数, 最长秒数]
      },
      "optional_features": {
        "location": ["场景类型"],
        "characters": ["人物关系"],
        "action": ["动作描述"]
      },
      "examples": [
        {
          "video": "第X集",
          "time": 时间戳秒数,
          "dialogue": "台词内容",
          "emotion": "情绪",
          "visual": "画面描述",
          "reasoning": "推理"
        }
      ]
    }
  ],
  "hook_types": [
    {
      "id": "唯一英文ID",
      "name": "中文名称",
      "description": "简短描述",
      "sample_count": 数量,
      "confidence_avg": 平均置信度,
      "confidence_min": 最低置信度建议,
      "required_features": {
        "has_twist": true/false,
        "information_cut_off": true/false,
        "emotion_keywords": ["关键词"],
        "dialogue_patterns": ["台词模式"],
        "visual_cues": ["视觉线索"]
      },
      "optional_features": {
        "timing": ["位置特征：开头/中间/结尾"],
        "camera": ["镜头类型"]
      },
      "examples": [
        {
          "video": "第X集",
          "time": 时间戳,
          "dialogue": "台词",
          "reasoning": "推理"
        }
      ]
    }
  ],
  "editing_rules": {
    "min_clip_duration": 30,
    "max_clip_duration": 300,
    "confidence_threshold": 8.0,
    "dedup_interval_seconds": 10,
    "max_same_type_per_episode": 1
  }
}
```

---

## ⚠️ 关键要求

### JSON格式要求
1. **量化阈值必须精确**：
   - emotion_intensity_min: 具体数字（如8.0）
   - confidence_min: 具体数字（如7.5）
   - typical_duration: [10, 30] 秒数范围

2. **必选特征vs可选特征明确**：
   - required_features: 必须满足
   - optional_features: 可选参考

3. **关键词列表完整**：
   - dialogue_keywords: 具体词汇列表
   - emotion_keywords: 具体情绪列表

4. **示例真实可验证**：
   - 每个类型至少3个真实示例
   - 包含时间戳、台词、画面、推理

### 数据质量要求
1. **基于真实数据**：所有特征必须从提供的分析结果中提取
2. **可执行性**：规则要具体到可以直接用于代码判断
3. **可复用性**：提取的是规律，不是个案描述
4. **完整性**：覆盖所有聚类，不要遗漏

---

## ✅ 输出检查清单

在输出JSON前，请检查：
- [ ] 每个类型都有唯一的id（英文）
- [ ] required_features包含emotion_intensity_min（具体数字）
- [ ] dialogue_keywords是非空数组
- [ ] examples至少有3个真实样本
- [ ] 所有时间戳都是整数（秒）
- [ ] confidence_min是0-10之间的数字
- [ ] editing_rules包含所有配置项

---

## 🎓 参考示例

### 高光类型示例

```json
{
  "id": "revenge_declaration",
  "name": "重生复仇宣言",
  "description": "主角重生后表达复仇决心",
  "sample_count": 12,
  "confidence_avg": 8.5,
  "confidence_min": 7.5,
  "required_features": {
    "emotion_keywords": ["愤怒", "决心", "悲愤"],
    "emotion_intensity_min": 8.0,
    "dialogue_patterns": ["我发誓", "不会放过", "报仇", "改变命运"],
    "dialogue_keywords": ["复仇", "报仇", "发誓", "恨"],
    "visual_cues": ["特写", "眼神坚定", "表情严肃"],
    "camera": ["特写", "近景"],
    "typical_duration": [10, 30]
  },
  "optional_features": {
    "location": ["室内", "卧室"],
    "characters": ["独白", "对他人"],
    "action": ["站立", "坐着"]
  },
  "examples": [
    {
      "video": "第1集",
      "time": 45,
      "dialogue": "我发誓，这辈子绝不会放过伤害我的人！",
      "emotion": "愤怒+决心",
      "visual": "女主紧握拳头，眼神坚定",
      "reasoning": "情绪强度9/10，包含'发誓'、'不放过'等关键词，特写镜头聚焦决心表情"
    }
  ]
}
```

### 钩子类型示例

```json
{
  "id": "suspense_reversal",
  "name": "悬念反转",
  "description": "关键信息突然揭示，戛然而止",
  "sample_count": 25,
  "confidence_avg": 8.2,
  "confidence_min": 7.0,
  "required_features": {
    "has_twist": true,
    "information_cut_off": true,
    "emotion_keywords": ["惊讶", "疑惑", "震惊"],
    "dialogue_patterns": ["等等", "原来你是", "你说什么", "怎么会"],
    "visual_cues": ["突然停顿", "表情变化", "特写"],
    "timing": ["中间", "结尾"]
  },
  "optional_features": {
    "camera": ["特写", "推镜头"],
    "characters": ["两人对话", "多人对话"]
  },
  "examples": [
    {
      "video": "第1集",
      "time": 366,
      "dialogue": "等等，你刚才说什么？你是...",
      "emotion": "惊讶+疑惑",
      "visual": "镜头推至特写，人物表情震惊",
      "reasoning": "关键信息即将揭示但被截断，有'等等'、'你是'等悬念台词，情绪强度8/10"
    }
  ]
}
```

---

现在，请基于提供的{{total_analyses}}个标记点分析数据，生成完整的Markdown和JSON两个版本的技能文件。

**重要**：先输出Markdown版本，然后输出JSON版本。两个版本都要完整。
