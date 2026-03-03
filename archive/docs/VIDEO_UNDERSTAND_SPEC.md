# 视频理解与剪辑组合生成 - 开发规范文档

## 版本更新

### V2.0 - 精确时间戳版本 (2026-03-03)

**核心变更**：

1. **时间戳精确化** ⭐⭐⭐⭐⭐
   ```python
   # V1 - 错误：使用窗口开始时间
   timestamp = segment.start_time  # 0, 50, 100, 150...

   # V2 - 正确：返回窗口内精确秒数
   timestamp = precise_second  # 366, 407, 350, 53...
   ```

2. **Prompt优化** ⭐⭐⭐⭐⭐
   - 明确高光点定义："从这个时刻开始"
   - 明确钩子点定义："播放到这个时刻结束"
   - 强调"宁缺毋滥"原则
   - 要求返回精确时间戳和置信度

3. **质量筛选流程** ⭐⭐⭐⭐⭐
   ```
   AI分析结果 (23个)
       ↓ 置信度筛选 (>7.0)
   筛选后 (18个)
       ↓ 去重 (15秒间隔，同集内)
   去重后 (11个)
       ↓ 数量限制 (每集2高光+3钩子)
   最终结果 (6个)
   ```

4. **第1集开篇规则** ⭐⭐⭐⭐⭐
   - 自动识别第1集开头（0-30秒）为"开篇高光点"
   - 置信度设为10.0（满分）

---

## 一、目标

开发本地原型版本，实现：
1. 读取技能文件，生成"技能理解提示词"
2. 对新短剧进行逐段分析，识别**精确的**高光点/钩子点
3. 通过质量筛选，输出**最推荐的**高质量标记
4. 生成剪辑组合（高光→钩子）

---

## 二、输入输出

### 2.1 输入

| 输入 | 说明 | 来源 |
|------|------|------|
| 技能文件 | `ai-drama-clipping-thoughts-v0.1.md` | 训练产出 |
| 新项目视频 | MP4文件 | 用户提供 |
| 关键帧 | 0.5秒/帧，JPEG图片 | FFmpeg提取 |
| ASR转录 | Whisper转录的JSON | 已有或新转录 |

### 2.2 输出

```json
{
  "videoName": "百里将就",
  "highlights": [
    {"timestamp": 30, "type": "重生复仇宣言", "description": "..."}
  ],
  "hooks": [
    {"timestamp": 120, "type": "悬念反转", "description": "..."}
  ],
  "clips": [
    {
      "start": 30,
      "end": 120,
      "duration": 90,
      "highlight": "重生复仇宣言",
      "hook": "悬念反转",
      "type": "重生-悬念"
    }
  ]
}
```

---

## 三、分段策略

### 3.1 设计原则

- **按集分段**：每集作为独立分析单元（因为每集是独立剧情）
- **时间窗口**：每60秒为一个分析片段（方案B：加大窗口减少API调用）
- **滑动窗口**：相邻窗口重叠10秒，避免遗漏

### 3.2 具体实现

```
例如：第1集 8分30秒 (510秒)
  → 片段1: 0-60秒
  → 片段2: 50-110秒 (重叠10秒)
  → 片段3: 100-160秒
  → ...
  → 片段N: 450-510秒
```

### 3.3 每片段包含

- 关键帧：取该时间段内的3-5张代表性帧
- ASR文本：该时间段的语音转录
- 时间戳：起始时间、结束时间

---

## 四、核心流程

### 4.1 流程图

```
输入：技能文件 + 新项目视频
    ↓
【步骤1】提取关键帧 + ASR
    ↓
【步骤2】理解技能文件
    ↓ 调用Gemini API
    生成"技能理解提示词"
    ↓
【步骤3】逐段分析
    ↓ 对每个30秒窗口调用Gemini API
    识别高光点/钩子点
    ↓
【步骤4】生成剪辑组合
    ↓ 按时间限制(30秒-5分钟)匹配
    输出剪辑组合列表
```

### 4.2 详细说明

#### 步骤1：提取关键帧 + ASR
- FFmpeg提取0.5秒/帧
- Whisper转录ASR
- 缓存结果支持断点续传

#### 步骤2：理解技能文件
- 读取技能文件JSON部分
- 调用Gemini API，让AI理解技能
- 生成结构化的"技能理解提示词"

**Prompt模板**：
```
你是一位短剧剪辑专家。请理解以下技能文件，生成一个用于分析视频的分析框架。

技能文件内容：
{SKILL_JSON}

请返回：
1. 高光类型的核心特征
2. 钩子类型的核心特征
3. 判断高光/钩子的关键指标
```

#### 步骤3：逐段分析
- 遍历每个60秒时间窗口
- 构建prompt：技能理解 + 关键帧 + ASR
- 调用Gemini API识别类型
- 汇总所有高光点/钩子点
- **去重处理**：同一类型在30秒内重复识别只保留一次

**Prompt模板**：
```
你是一位短剧剪辑专家。请分析以下视频片段：

时间范围：{START}-{END}秒（60秒窗口）
关键帧：[图片]
ASR文本：{ASR_TEXT}

技能理解框架：
{SKILL_FRAME}

请判断：
1. 这是否是"高光点"？类型是？
2. 这是否是"钩子点"？类型是？
3. 简要描述

返回JSON格式：
{{
  "isHighlight": true/false,
  "highlightType": "类型名",
  "highlightDesc": "描述",
  "isHook": true/false,
  "hookType": "类型名",
  "hookDesc": "描述"
}}
```

#### 步骤4：生成剪辑组合
- 遍历所有高光点
- 找后续最近的钩子点
- 检查时间限制（默认30秒-5分钟）
- 生成剪辑片段

```python
def generate_clips(highlights, hooks, min_duration=30, max_duration=300):
    clips = []
    for hl in highlights:
        # 找该高光点后面的钩子点
        candidate_hooks = [h for h in hooks if h.timestamp > hl.timestamp]
        
        for hook in candidate_hooks:
            duration = hook.timestamp - hl.timestamp
            if min_duration <= duration <= max_duration:
                clips.append(Clip(
                    start=hl.timestamp,
                    end=hook.timestamp,
                    duration=duration,
                    highlight=hl.type,
                    hook=hook.type
                ))
                break  # 只取最近的
    
    return clips
```

---

## 五、配置参数

### 5.1 默认配置

```python
# 分析参数
SEGMENT_DURATION = 60  # 片段时长（秒）- 方案B加大窗口
SEGMENT_OVERLAP = 10     # 相邻片段重叠时长（秒）
FRAMES_PER_SEGMENT = 5  # 每片段提取的关键帧数（增加到5张）

# 剪辑参数
MIN_CLIP_DURATION = 30   # 最短剪辑（秒）
MAX_CLIP_DURATION = 300  # 最长剪辑（秒）

# 去重参数
DEDUP_WINDOW = 30  # 去重时间窗口（秒）

# API参数
GEMINI_MODEL = "gemini-2.0-flash"
MAX_CONCURRENT = 3  # 最大并发数
```

---

## 六、数据结构

### 6.1 关键帧

```python
@dataclass
class KeyFrame:
    frame_path: str      # 图片路径
    timestamp_ms: int   # 时间戳（毫秒）
```

### 6.2 ASR片段

```python
@dataclass
class ASRSegment:
    text: str        # 文本
    start: float    # 开始时间（秒）
    end: float      # 结束时间（秒）
```

### 6.3 分析结果

```python
@dataclass
class SegmentAnalysis:
    start_time: int           # 起始秒
    end_time: int           # 结束秒
    is_highlight: bool       # 是否高光点
    highlight_type: str      # 高光类型
    highlight_desc: str      # 高光描述
    is_hook: bool           # 是否钩子点
    hook_type: str           # 钩子类型
    hook_desc: str          # 钩子描述
```

### 6.4 剪辑组合

```python
@dataclass
class Clip:
    start: int         # 起始秒
    end: int          # 结束秒
    duration: int     # 时长（秒）
    highlight: str    # 高光类型
    hook: str         # 钩子类型
    clip_type: str    # 组合类型 "高光类型-钩子类型"
```

---

## 七、模块设计

### 7.1 模块列表

```
scripts/
├── understand_skill.py      # 理解技能文件，生成提示词
├── extract_segments.py      # 提取分析片段
├── analyze_segment.py      # 逐段分析（调用Gemini）
├── generate_clips.py       # 生成剪辑组合
└── video_understand.py    # 主入口
```

### 7.2 接口说明

#### understand_skill.py
```python
def understand_skill(skill_file_path: str) -> str:
    """理解技能文件，生成技能框架
    
    Args:
        skill_file_path: 技能文件路径
        
    Returns:
        技能框架JSON字符串
    """
```

#### analyze_segment.py
```python
def analyze_segment(
    keyframes: List[KeyFrame],
    asr_segments: List[ASRSegment],
    skill_framework: str,
    start_time: int,
    end_time: int
) -> SegmentAnalysis:
    """分析单个时间片段
    
    Args:
        keyframes: 关键帧列表
        asr_segments: ASR片段列表
        skill_framework: 技能框架
        start_time: 起始秒
        end_time: 结束秒
        
    Returns:
        分析结果
    """
```

#### generate_clips.py
```python
def generate_clips(
    highlights: List[SegmentAnalysis],
    hooks: List[SegmentAnalysis],
    min_duration: int = 30,
    max_duration: int = 300
) -> List[Clip]:
    """生成剪辑组合
    
    Args:
        highlights: 高光点列表
        hooks: 钩子点列表
        min_duration: 最短时长
        max_duration: 最长时长
        
    Returns:
        剪辑组合列表
    """
```

---

## 八、输出文件

### 8.1 技能框架文件

`data/hangzhou-leiming/frameworks/{version}.json`

```json
{
  "skillVersion": "v0.1",
  "generatedAt": "2026-03-02T19:00:00Z",
  "framework": {
    "highlightTypes": [...],
    "hookTypes": [...]
  }
}
```

### 8.2 分析结果文件

`data/hangzhou-leiming/analysis/{project_name}/result.json`

```json
{
  "projectName": "百里将就",
  "analyzedAt": "2026-03-02T19:30:00Z",
  "highlights": [...],
  "hooks": [...],
  "clips": [...]
}
```

---

## 九、错误处理

1. **API调用失败**：指数退避重试3次
2. **关键帧不存在**：跳过该片段，记录警告
3. **ASR为空**：记录警告，继续分析
4. **无有效剪辑组合**：返回空列表
5. **重复识别**：同类型在30秒内只保留第一个

---

## 十、待确认问题

暂无

---

**文档版本**: v1.0
**创建时间**: 2026-03-02
