# 时间戳优化问题分析

## 问题背景

测试项目：烈日重生
渲染时出现的问题：
1. 高光点：话说到一半突然切入
2. 钩子点：话说到一半还没说完就被截断

---

## 数据流转过程

### 阶段1：AI分析（Gemini）

- AI分析关键帧，输出 `preciseSecond` 时间戳
- **问题1：输出的是秒数，假设30fps，不是精确帧数**
- **问题2：输出的是累积时间（从第1集0秒开始计算），不是集内时间**

### 阶段2：加载ASR数据

- 按集分开存储：episode_asr = {1: [ASR...], 2: [ASR...], 3: [ASR...]}
- ASR时间是**集内时间**（每集从0开始）

### 阶段3：混在一起传入优化算法

```python
# video_understand.py 第367-369行
all_asr_segments = []
for asr_list in episode_asr.values():
    all_asr_segments.extend(asr_list)  # 混在一起，丢失episode信息
```

**问题3：ASRSegment没有episode字段，不知道属于哪一集**

### 阶段4：时间戳优化算法

- 输入：highlight_timestamp（AI输出的累积时间）
- 处理：在混在一起的ASR里找对应时间点
- **问题4：类型不匹配 - AI输出累积时间，ASR是集内时间**

### 阶段5：生成剪辑组合

- 用优化后的时间生成笛卡尔积
- 保存到result.json（累积时间）

### 阶段6：渲染

- 读取result.json的累积时间
- 检测视频实际帧率
- 秒数 → 帧数，用帧级精度剪辑 ✓

---

## 可能的根因（待验证）

### 假设1：时间类型不匹配

AI输出的preciseSecond是累积时间（如97.9秒），但ASR时间是集内时间（如0-126秒）。

优化算法在找97.9秒时：
- 第1集ASR: 0-68秒，没有97.9
- 第2集ASR: 0-126秒，找到97.9秒 ← 找到了第2集的97.9秒

这可能导致在错误位置找到句子边界。

### 假设2：ASR时间戳本身不准确

Whisper ASR对句子边界的识别可能有误差，导致找到的句子开始/结束点不精确。

### 假设3：buffer参数不合理

- 高光点buffer: 100ms（太短，可能不够）
- 钩子点buffer: 150ms

---

## 待验证事项

1. AI输出的preciseSecond到底是累积时间还是集内时间？
2. 优化算法是否正确处理了时间类型？
3. ASR时间戳本身是否准确？

---

## 优化方向

### 方案A：禁用时间戳优化
- 直接使用AI原始时间戳
- 快速验证效果

### 方案B：修复时间类型问题
- AI输出改为帧数（而非秒数）
- 或在优化前将累积时间转换为集内时间

### 方案C：改进ASR算法
- 使用word-level timestamps
- 音频波形分析检测句子边界

### 方案D：混合策略
- ASR时间明显不合理时回退到原始时间戳

---

## 相关代码位置

- `scripts/understand/analyze_segment.py` - AI分析，输出preciseSecond
- `scripts/understand/video_understand.py` - 混用ASR数据（第367-369行）
- `scripts/understand/smart_cut_finder.py` - 时间戳优化算法
- `scripts/understand/timestamp_optimizer.py` - 时间戳优化入口
- `scripts/understand/generate_clips.py` - 生成剪辑组合
- `scripts/data_models.py` - ASRSegment数据结构（缺少episode字段）

---

*记录时间：2026-03-10*
