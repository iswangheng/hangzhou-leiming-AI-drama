# 🎯 杭州雷鸣AI短剧剪辑 - V5.0 优化方案

**制定日期**: 2026-03-03
**版本**: V5.0 - 全面优化方案
**状态**: 📝 方案已确认，待实施

---

## 📊 V4.0 测试结果回顾

### 总体性能
- 总人工标记：44个
- 总AI标记：14个
- 总匹配数：13个
- **召回率：29.5%** ← 核心问题
- **精确率：92.9%** ← 质量很好

### 核心问题分析

1. **AI过于保守** ⭐⭐⭐⭐⭐
   - 只标记了14个（应该25-30个）
   - "宁缺毋滥"被AI理解为"极度保守"
   - 置信度7.0阈值偏高

2. **类型系统过于复杂** ⭐⭐⭐⭐⭐
   - 31种钩子类型，AI难以准确匹配
   - 部分标记的type为null
   - 类型边界模糊

3. **数据预处理不完整** ⭐⭐⭐⭐
   - 多集显示"时长为0，跳过"
   - 关键帧只有5张，信息不足

4. **时间精度良好** ⭐⭐
   - 匹配对偏差在±30秒内
   - 30秒窗口已经足够

---

## 🎯 V5.0 优化目标

### 核心目标
- **召回率**：29.5% → **50-60%** (+20.5%~+30.5%)
- **AI标记数量**：14个 → **25-30个** (+78%~+114%)
- **精确率**：保持 **80%+** (允许小幅下降)

### 次要目标
- **类型数量**：31种 → **10-15种** (简化52%)
- **Null类型**：2个 → **0个** (完全消除)
- **数据完整性**：修复所有"时长为0"的问题

---

## 🚀 三大优化方向

### 方向1：Prompt微调 - 适度放宽，保持宁缺毋滥 ⭐⭐⭐⭐⭐

**核心原则**：
- ✅ 保持"宁缺毋滥"，但找到平衡点
- ✅ **适当多标记**，不是泛滥标记
- ❌ 不是"宁可多标记，不要遗漏"

#### 当前问题
```python
# V4 Prompt (过于严格)
"如果没有明确的钩子点，宁缺毋滥，不要强行标记"
→ AI理解为：只有100%确定才标记
→ 结果：只标记了14个（太少）
```

#### 优化策略
```python
# V5 Prompt (适度放宽)
"适度标记可疑钩子点，保持宁缺毋滥原则，但不要错过明显的情节转折"
"每集通常有2-3个钩子点，请仔细寻找"
→ AI理解为：70-80%确定可以标记
→ 预期：标记25-30个（适中）
```

#### 具体调整

**1. 置信度阈值调整**
```python
# scripts/understand/quality_filter.py

# V4配置
min_confidence: float = 7.0  # 过于严格

# V5配置
min_confidence: float = 6.5  # 适度放宽
```

**2. Prompt措辞调整**
```python
# scripts/understand/analyze_segment.py

# V4表述
"如果不确定，宁缺毋滥，不要标记"

# V5表述
"有明显迹象就标记，置信度6.5以上即可"
"每集通常有2-3个钩子点，请仔细寻找"
```

**3. 引导性提示**
```python
# 添加正向引导
"常见的钩子点位置："
"- 对话突然中断"
"- 突然出现新信息"
"- 情节出现转折"
"- 留下悬念的地方"
```

#### 预期效果
- AI标记数量：14个 → 25-30个
- 召回率：29.5% → 50-60%
- 精确率：92.9% → 80%+ (可接受下降)

---

### 方向2：训练流程增强 - 自动类型简化合并 ⭐⭐⭐⭐⭐

**核心思路**：
- ❌ **不在**视频理解阶段单独优化类型
- ✅ **在**训练流程中自动完成类型简化
- ✅ 每次训练时自动整合、去重、合并相似类型
- ✅ 无需手动维护，自动更新

#### 实现位置
**文件**：`scripts/merge_skills.py`

#### 自动化流程

```
原始训练数据
    ↓ 包含100+个类型实例
【步骤1】类型聚类 (按相似度)
    - 按名称关键词聚类（如"反转"、"冲突"）
    - 按特征相似度聚类（如"戛然而止"、"信息截断"）
    - 例如：
      * 悬念反转、剧情反转、反转钩子 → 合并为"悬念反转"
      * 矛盾冲突、冲突升级、对抗 → 合并为"矛盾冲突"
    ↓
【步骤2】类型筛选 (质量控制)
    - 移除出现次数<3的类型（不够普遍）
    - 移除特征重叠度>80%的类型（不够独特）
    - 保留高频次、高独特性的类型
    ↓
【步骤3】类型精简 (数量控制)
    - 目标：10-15种核心钩子类型
    - 按重要性排序（出现次数×独特性）
    - 保留Top 10-15
    ↓
【步骤4】生成技能文件 (MD + JSON)
    - 自动生成简化的类型定义
    - 包含量化特征和阈值
    - 同时保存.md和.json文件
    ↓
最终技能文件 (10-15种类型)
```

#### 代码实现

```python
# scripts/merge_skills.py

def simplify_hook_types(hook_types: List[HookType]) -> List[HookType]:
    """自动简化钩子类型

    每次训练时自动调用，完成：
    1. 类型聚类
    2. 相似类型合并
    3. 低质量类型过滤
    4. 数量控制（10-15种）
    """
    # 步骤1: 按关键词聚类
    clusters = cluster_by_keywords(hook_types)

    # 步骤2: 合并相似类型
    merged_types = []
    for cluster in clusters:
        if len(cluster) > 1:
            merged = merge_similar_types(cluster)
            merged_types.append(merged)
        else:
            merged_types.append(cluster[0])

    # 步骤3: 筛选高质量类型
    filtered = filter_low_quality_types(
        merged_types,
        min_occurrences=3,      # 至少出现3次
        max_overlap=0.8         # 重叠度不超过80%
    )

    # 步骤4: 限制总数（保留最重要的）
    final = select_top_types(filtered, max_count=15)

    return final


def cluster_by_keywords(types: List[HookType]) -> List[List[HookType]]:
    """按关键词聚类类型"""
    keywords_map = {
        '反转': ['悬念反转', '剧情反转', '反转钩子', '情节反转'],
        '冲突': ['矛盾冲突', '冲突升级', '对抗', '激烈冲突'],
        '危机': ['危机预警', '危机暗示', '危机前兆', '危机爆发'],
        # ...
    }

    clusters = []
    # 实现聚类逻辑
    return clusters


def merge_similar_types(types: List[HookType]) -> HookType:
    """合并相似类型"""
    # 合并名称
    # 合并特征
    # 合并阈值
    return merged_type


def filter_low_quality_types(types: List[HookType],
                              min_occurrences: int,
                              max_overlap: float) -> List[HookType]:
    """筛选高质量类型"""
    # 过滤低频类型
    # 过滤高重叠类型
    return filtered


def select_top_types(types: List[HookType], max_count: int) -> List[HookType]:
    """选择最重要的类型"""
    # 按重要性排序（出现次数 × 独特性）
    # 返回Top N
    return top_types
```

#### 类型简化示例

| 原始类型 (31种) | 简化后 (12种) | 合并逻辑 |
|----------------|--------------|---------|
| 悬念反转<br>剧情反转<br>反转钩子<br>情节反转 | → **悬念反转** | 关键词"反转" |
| 矛盾冲突<br>冲突升级<br>对抗<br>激烈冲突 | → **矛盾冲突** | 关键词"冲突" |
| 危机预警<br>危机暗示<br>危机前兆<br>危机爆发 | → **危机预警** | 关键词"危机" |
| 情感揭示<br>信息揭示<br>真相揭露<br>秘密公开 | → **信息揭示** | 关键词"揭示/揭露" |
| 矛盾激化<br>情绪爆发<br>愤怒<br>情绪失控 | → **情绪爆发** | 关键词"情绪/愤怒" |
| 悬念设置<br>疑问产生<br>好奇引发<br>疑惑 | → **悬念设置** | 关键词"悬念/疑问" |
| 危机爆发<br>紧急情况<br>突发事件<br>危险 | → **危机爆发** | 关键词"危机/危险" |
| 情节转折<br>剧情变化<br>走向改变<br>意外 | → **情节转折** | 关键词"转折/变化" |
| 人物变化<br>态度转变<br>立场改变<br>反转 | → **人物变化** | 关键词"人物/态度" |
| 冲突升级<br>矛盾加剧<br>对抗增强<br>激化 | → **冲突升级** | 关键词"升级/加剧" |
| 期待落空<br>愿望破灭<br>失望<br>失败 | → **期待落空** | 关键词"落空/失望" |
| 其他零散类型 (21种) | → **合并到上述类型** | 按特征归类 |

#### 预期效果
- **类型数量**：31种 → 10-15种 (-52%~-52%)
- **Null类型**：2个 → 0个 (-100%)
- **AI匹配成功率**：提升30%+
- **维护成本**：自动化，无需手动维护

---

### 方向3：数据预处理修复 - 完整性 + 丰富度 ⭐⭐⭐⭐

#### 问题1：数据完整性

**当前问题**：
```
警告: 第2集时长为0，跳过
警告: 第4集时长为0，跳过
警告: 第5集时长为0，跳过
```

**影响**：
- 可分析的片段数量减少
- 召回率进一步下降

**修复方案**：

```python
# 需要检查的脚本
1. scripts/extract_keyframes.py  - 关键帧提取
2. scripts/extract_asr.py         - ASR转录
3. scripts/video/metadata.py      - 视频元数据
```

**验证脚本**（新增）：

```python
# scripts/verify_data.py

def verify_project_data(project_path: str) -> Dict[str, Any]:
    """验证项目数据完整性

    检查：
    1. 所有关键帧是否提取成功
    2. 所有ASR是否转录成功
    3. 所有视频时长是否正确
    4. 数据是否损坏
    """
    # 检查视频文件
    # 检查关键帧文件
    # 检查ASR文件
    # 生成验证报告
    return report


def reprocess_missing_data(project_path: str):
    """重新处理缺失的数据"""
    # 识别缺失的数据
    # 重新提取关键帧
    # 重新转录ASR
    pass
```

#### 问题2：关键帧丰富度 ⭐⭐⭐⭐⭐

**当前配置**：
```python
# scripts/understand/extract_segments.py (V4)
FRAMES_PER_SEGMENT = 5  # 每片段固定5张关键帧
```

**问题**：
- 30秒窗口只有5张关键帧（每6秒一张）
- 信息密度太低
- AI可能错过快速变化的情节

**优化配置**：
```python
# scripts/understand/extract_segments.py (V5)
FRAMES_PER_SEGMENT = None  # 不使用固定数量

# 改为：每秒1帧
def extract_segments_for_episode(...):
    """提取片段时，每秒提取1帧"""
    segment_duration = 30  # 30秒窗口
    frames_per_segment = segment_duration  # 每秒1帧 = 30张
```

**具体实现**：

```python
# scripts/extract_keyframes.py

def extract_keyframes_for_segment(
    video_path: str,
    start_time: int,  # 片段开始时间（秒）
    end_time: int,    # 片段结束时间（秒）
    output_dir: str
) -> List[KeyFrame]:
    """提取片段的关键帧（每秒1帧）

    Args:
        video_path: 视频路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        output_dir: 输出目录

    Returns:
        关键帧列表

    Example:
        start_time=0, end_time=30
        → 提取0s, 1s, 2s, ..., 29s共30张关键帧
    """
    keyframes = []

    # 每秒提取1帧
    for second in range(start_time, end_time):
        timestamp_ms = second * 1000
        frame_path = extract_frame_at(video_path, timestamp_ms, output_dir)
        keyframes.append(KeyFrame(
            frame_path=frame_path,
            timestamp_ms=timestamp_ms
        ))

    return keyframes


def extract_frame_at(video_path: str, timestamp_ms: int, output_dir: str) -> str:
    """在指定时间戳提取一帧"""
    import subprocess

    output_path = f"{output_dir}/frame_{timestamp_ms//1000}s.jpg"

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-ss', str(timestamp_ms / 1000),  # 时间戳（秒）
        '-vframes', '1',                    # 提取1帧
        '-q:v', '2',                        # 高质量
        output_path
    ]

    subprocess.run(cmd, capture_output=True)
    return output_path
```

**配置调整**：

```python
# scripts/understand/extract_segments.py

# V4配置（旧）
FRAMES_PER_SEGMENT = 5  # 固定5张
SEGMENT_DURATION = 30

# V5配置（新）
EXTRACT_FRAME_EVERY_SECOND = True  # 每秒1帧
SEGMENT_DURATION = 30

# 实际效果：
# - 30秒窗口 → 30张关键帧（每秒1张）
# - 信息密度提升6倍（从5张→30张）
```

#### 预期效果
- **关键帧数量**：5张/片段 → 30张/片段 (+500%)
- **信息密度**：每6秒1张 → 每秒1张
- **AI识别准确率**：提升20%+
- **快速情节捕捉**：不会错过快速变化

---

## 📁 修改文件清单

| 序号 | 文件 | 修改内容 | 优先级 | 复杂度 |
|------|------|---------|--------|--------|
| 1 | `scripts/merge_skills.py` | **新增**自动类型简化函数 | P0 | ⭐⭐⭐⭐ |
| 2 | `scripts/understand/analyze_segment.py` | Prompt微调：适度放宽 | P0 | ⭐⭐ |
| 3 | `scripts/understand/quality_filter.py` | 置信度阈值：7.0→6.5 | P0 | ⭐ |
| 4 | `scripts/extract_keyframes.py` | 关键帧：每秒1帧 | P0 | ⭐⭐⭐ |
| 5 | `scripts/understand/extract_segments.py` | 调整关键帧提取逻辑 | P0 | ⭐⭐ |
| 6 | `scripts/verify_data.py` | **新增**数据验证脚本 | P1 | ⭐⭐⭐ |
| 7 | `scripts/video/metadata.py` | 修复时长为0的bug | P1 | ⭐⭐⭐ |

---

## 🔄 优化实施流程

### 阶段1：训练流程优化 (30分钟)

**目标**：生成简化版技能文件

```
步骤1.1：修改 merge_skills.py
  - 添加 simplify_hook_types() 函数
  - 添加聚类、合并、筛选逻辑
  - 集成到主流程

步骤1.2：测试类型简化
  - 基于v0.3技能文件测试
  - 验证简化效果（31→10-15种）
  - 检查合并合理性

步骤1.3：重新训练
  - 运行 python -m scripts.train
  - 生成 v0.4 技能文件（MD + JSON）
  - 验证文件内容
```

### 阶段2：理解流程优化 (30分钟)

**目标**：调整Prompt和参数

```
步骤2.1：修改 analyze_segment.py
  - 更新ANALYZE_PROMPT
  - 添加"适度标记"引导
  - 添加"每集2-3个钩子"提示

步骤2.2：修改 quality_filter.py
  - 调整默认阈值：7.0→6.5
  - 更新相关注释

步骤2.3：测试Prompt效果
  - 单个片段测试
  - 验证AI是否更积极标记
```

### 阶段3：数据预处理优化 (1小时)

**目标**：修复数据完整性 + 关键帧丰富度

```
步骤3.1：修改 extract_keyframes.py
  - 实现每秒1帧提取
  - extract_frame_at() 函数
  - 性能优化（批量提取）

步骤3.2：修改 extract_segments.py
  - 调整关键帧提取逻辑
  - 每秒1帧配置

步骤3.3：新增 verify_data.py
  - 实现数据验证函数
  - reprocess_missing_data() 函数
  - 生成验证报告

步骤3.4：修复 metadata.py
  - 调查时长为0的原因
  - 修复bug
  - 重新处理所有视频
```

### 阶段4：全面测试 (30分钟)

**目标**：验证优化效果

```
步骤4.1：重新处理数据
  - 运行数据验证
  - 重新提取关键帧（每秒1帧）
  - 验证完整性

步骤4.2：测试全部5个项目
  - 重生暖宠九爷的小娇妻不好惹
  - 小小飞梦
  - 再见，心机前夫
  - 弃女归来嚣张真千金不好惹
  - 百里将就

步骤4.3：生成对比报告
  - V4 vs V5 性能对比
  - 召回率、精确率对比
  - 各项目详细对比
```

### 阶段5：文档更新 (15分钟)

**目标**：生成V5优化报告

```
步骤5.1：生成 OPTIMIZATION_V5_REPORT.md
  - 优化内容总结
  - 性能对比表格
  - 关键发现和建议

步骤5.2：更新相关文档
  - 更新 README.md
  - 更新使用指南
```

---

## 📊 预期效果

### 核心指标对比

| 指标 | V4当前 | V5目标 | 提升 | 评估 |
|------|--------|--------|------|------|
| **召回率** | 29.5% | **50-60%** | +20.5%~+30.5% | ✅ 核心目标 |
| **AI标记数量** | 14个 | **25-30个** | +78%~+114% | ✅ 显著提升 |
| **精确率** | 92.9% | **80%+** | -12.9% | ✅ 可接受下降 |
| **类型数量** | 31种 | **10-15种** | -52%~-52% | ✅ 大幅简化 |
| **Null类型** | 2个 | **0个** | -100% | ✅ 完全消除 |
| **关键帧密度** | 5张/30秒 | **30张/30秒** | +500% | ✅ 显著提升 |
| **数据完整性** | 60% | **100%** | +40% | ✅ 完全修复 |

### 各项目预期

| 项目 | V4召回率 | V5目标召回率 | 提升 |
|------|---------|-------------|------|
| 再见，心机前夫 | 37.5% | 60-70% | +22.5%~+32.5% |
| 百里将就 | 30.0% | 50-60% | +20%~+30% |
| 小小飞梦 | 30.0% | 50-60% | +20%~+30% |
| 重生暖宠 | 25.0% | 45-55% | +20%~+30% |
| 弃女归来 | 25.0% | 45-55% | +20%~+30% |

### 关键改进点

**1. 召回率提升 (29.5% → 50-60%)**
- Prompt适度放宽：+10~15%
- 类型简化：+5~8%
- 关键帧丰富：+3~5%
- 数据完整性：+2~3%

**2. 类型匹配改善**
- 31种 → 10-15种
- Null类型：2个 → 0个
- AI更容易准确匹配

**3. 数据质量提升**
- 关键帧：5张 → 30张（6倍提升）
- 完整性：60% → 100%
- 不再遗漏片段

---

## ✅ 成功标准

### 必须达成 (P0)
- ✅ 召回率 ≥ 50%
- ✅ AI标记数量 ≥ 25个
- ✅ 精确率 ≥ 80%
- ✅ Null类型 = 0个
- ✅ 数据完整性 = 100%

### 期望达成 (P1)
- ✅ 召回率 ≥ 55%
- ✅ AI标记数量 ≥ 28个
- ✅ 精确率 ≥ 85%
- ✅ 类型数量 ≤ 12种

### 加分项 (P2)
- ✅ 召回率 ≥ 60%
- ✅ 各项目召回率均衡（标准差<10%）
- ✅ 处理速度无明显下降

---

## 🎓 关键原则

### 优化原则
1. ✅ **宁缺毋滥，适度放宽** - 不是泛滥标记
2. ✅ **训练时简化类型** - 不在理解时单独优化
3. ✅ **数据质量优先** - 完整性 + 丰富度
4. ✅ **自动化优先** - 减少手动维护

### 不做的原则
1. ❌ **不过度标记** - 保持质量，不泛滥
2. ❌ **不在理解阶段优化类型** - 在训练时完成
3. ❌ **不牺牲太多精确率** - 控制在80%以上
4. ❌ **不引入过度复杂性** - 保持代码简洁

---

## 📝 实施检查清单

### 阶段1：训练流程
- [ ] 修改 `scripts/merge_skills.py`
  - [ ] 添加 `simplify_hook_types()` 函数
  - [ ] 添加 `cluster_by_keywords()` 函数
  - [ ] 添加 `merge_similar_types()` 函数
  - [ ] 添加 `filter_low_quality_types()` 函数
  - [ ] 添加 `select_top_types()` 函数
- [ ] 测试类型简化效果
- [ ] 重新训练生成v0.4技能文件
- [ ] 验证MD和JSON文件内容

### 阶段2：理解流程
- [ ] 修改 `scripts/understand/analyze_segment.py`
  - [ ] 更新 `ANALYZE_PROMPT`
  - [ ] 添加"适度标记"引导
- [ ] 修改 `scripts/understand/quality_filter.py`
  - [ ] 调整默认阈值 7.0→6.5
- [ ] 测试Prompt效果

### 阶段3：数据预处理
- [ ] 修改 `scripts/extract_keyframes.py`
  - [ ] 实现 `extract_keyframes_for_segment()`
  - [ ] 实现 `extract_frame_at()` 函数
- [ ] 修改 `scripts/understand/extract_segments.py`
  - [ ] 调整关键帧提取逻辑
- [ ] 新增 `scripts/verify_data.py`
  - [ ] 实现 `verify_project_data()` 函数
  - [ ] 实现 `reprocess_missing_data()` 函数
- [ ] 修复 `scripts/video/metadata.py`
  - [ ] 调查时长为0的原因
  - [ ] 修复bug

### 阶段4：测试验证
- [ ] 验证数据完整性
- [ ] 测试全部5个项目
- [ ] 生成性能对比报告
- [ ] 验证优化效果

### 阶段5：文档
- [ ] 生成 `OPTIMIZATION_V5_REPORT.md`
- [ ] 更新 `README.md`
- [ ] 更新使用指南

---

## 📅 预估时间

| 阶段 | 预估时间 | 实际时间 | 状态 |
|------|---------|---------|------|
| 阶段1：训练流程优化 | 30分钟 | - | ⏳ 待开始 |
| 阶段2：理解流程优化 | 30分钟 | - | ⏳ 待开始 |
| 阶段3：数据预处理优化 | 1小时 | - | ⏳ 待开始 |
| 阶段4：全面测试 | 30分钟 | - | ⏳ 待开始 |
| 阶段5：文档更新 | 15分钟 | - | ⏳ 待开始 |
| **总计** | **2小时45分钟** | - | - |

---

**方案制定完成时间**: 2026-03-03
**制定人**: AI助手 Claude
**版本**: V5.0 Final
**状态**: ✅ 已确认，可以开始实施
