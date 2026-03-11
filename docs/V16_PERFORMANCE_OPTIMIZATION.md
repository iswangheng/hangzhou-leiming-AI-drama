# V16 性能优化方案

## 完整流程耗时分析

### 当前流程时序图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整处理流程（单项目）                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [阶段1] 数据提取阶段                                                        │
│  ├── 关键帧提取：每集 5-10秒 × N集 = 串行                                    │
│  ├── 音频提取：每集 3-5秒 × N集 = 串行                                       │
│  └── ASR转录：每集 30-60秒 × N集 = 串行  ⚠️ 主要瓶颈                         │
│      预计耗时：10集 × (10+5+45)秒 = 10分钟                                   │
│                                                                             │
│  [阶段2] AI分析阶段                                                          │
│  ├── 分段分析：ThreadPoolExecutor(max_workers=5) ✅ 已并行                   │
│  └── 预计耗时：3-5分钟（取决于API响应速度）                                    │
│                                                                             │
│  [阶段3] 渲染阶段                                                            │
│  ├── 片尾检测：每集 3-10秒 × N集 = 串行  ⚠️ 主要瓶颈                         │
│  │   └── 每集都要做 ASR 转录（与阶段1重复）                                   │
│  ├── 视频裁剪：每个剪辑 5-15秒 = 串行  ⚠️ 主要瓶颈                           │
│  ├── 花字叠加：每个剪辑 10-20秒 = 串行                                       │
│  └── 片尾拼接：每个剪辑 3-5秒 = 串行                                         │
│      预计耗时：10个剪辑 × 30秒 = 5分钟                                       │
│                                                                             │
│  总计：约 20-25 分钟/项目                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 耗时瓶颈排序

| 排名 | 瓶颈 | 耗时占比 | 优化潜力 |
|------|------|----------|----------|
| 1 | ASR转录（阶段1+3重复） | ~40% | ⭐⭐⭐⭐⭐ |
| 2 | 渲染串行 | ~25% | ⭐⭐⭐⭐ |
| 3 | 关键帧/音频提取串行 | ~15% | ⭐⭐⭐ |
| 4 | AI分析API延迟 | ~15% | ⭐⭐ |
| 5 | 花字叠加 | ~5% | ⭐ |

---

## 优化方案详解

### 优化1：ASR转录复用 + 并行化 【高优先级】

**问题**：
- 阶段1（数据提取）已经做了ASR转录
- 阶段3（片尾检测）又对每集重新做ASR转录
- **完全重复的工作！**

**解决方案**：

```
┌─────────────────────────────────────────────────────────────┐
│                     优化后的 ASR 流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [一次性 ASR 提取]                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  并行提取所有集的 ASR（ThreadPoolExecutor）          │   │
│  │  第1集 ─┐                                           │   │
│  │  第2集 ─┼─→ 并行执行 ─→ 保存到缓存                  │   │
│  │  第3集 ─┤                                           │   │
│  │  ...   ─┘                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                   │
│  [复用缓存]                                                 │
│  ├── AI分析阶段：直接读取 ASR 缓存                          │
│  └── 片尾检测阶段：直接读取 ASR 缓存                        │
│                                                             │
│  节省时间：10集 × 45秒 = 7.5分钟                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**实现步骤**：

1. **修改 `video_understand.py`**：
   - 在 `load_episode_data()` 中并行提取所有集的ASR
   - 使用 `ThreadPoolExecutor` 并行执行

2. **修改片尾检测逻辑**：
   - `render_clips.py` 的 `_auto_detect_ending_credits()` 改为读取缓存
   - 如果缓存不存在，才执行ASR

3. **修改 `detect_ending_credits.py`**：
   - 支持 `--use-cached-asr` 参数
   - 从 `cache/asr/{project}/` 读取已转录的ASR

**代码示例**：

```python
# video_understand.py - 并行 ASR 提取
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_episode_data(project_path: str, auto_extract: bool = True) -> tuple:
    # ... 收集所有需要处理的集 ...

    # 并行提取 ASR
    if auto_extract:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(extract_asr_for_episode, ep, mp4_file): ep
                for ep, mp4_file in episodes_to_process.items()
            }
            for future in as_completed(futures):
                ep = futures[future]
                try:
                    asr_segments = future.result()
                    episode_asr[ep] = asr_segments
                except Exception as e:
                    print(f"第{ep}集 ASR 提取失败: {e}")
```

**预期效果**：
- 节省时间：**7-10 分钟/项目**
- 避免重复工作

---

### 优化2：渲染并行化 【高优先级】

**问题**：
- 当前渲染是串行的，一个接一个处理
- 10个剪辑需要 5 分钟

**解决方案**：

```
┌─────────────────────────────────────────────────────────────┐
│                     并行渲染流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [当前：串行]                                               │
│  剪辑1 ──→ 剪辑2 ──→ 剪辑3 ──→ ... ──→ 剪辑10             │
│  总时间 = 10 × 30秒 = 300秒                                 │
│                                                             │
│  [优化后：并行]                                             │
│  剪辑1 ──┐                                                  │
│  剪辑2 ──┤                                                  │
│  剪辑3 ──┼──→ 并行执行（4个worker）                        │
│  剪辑4 ──┤                                                  │
│  ...    ─┘                                                  │
│  总时间 = ceil(10/4) × 30秒 = 90秒                         │
│                                                             │
│  节省时间：210秒 = 3.5分钟                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**实现步骤**：

1. **修改 `render_clips.py`**：
   - 添加 `--parallel` 参数，默认启用（4个worker）
   - 使用 `ProcessPoolExecutor` 实现多进程并行

2. **代码示例**：

```python
# render_clips.py
from concurrent.futures import ProcessPoolExecutor, as_completed

def render_all_clips(self, parallel_workers: int = 4) -> List[str]:
    """并行渲染所有剪辑"""

    if parallel_workers <= 1:
        # 串行模式（兼容旧逻辑）
        for clip in clips:
            self.render_clip(clip)
    else:
        # 并行模式
        with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
            futures = {
                executor.submit(render_single_clip, clip, ...): clip
                for clip in clips_to_render
            }
            for future in as_completed(futures):
                result = future.result()
                output_paths.append(result)
```

**注意事项**：
- FFmpeg 本身是 CPU 密集型，worker 数量不要超过 CPU 核心数
- 建议 `parallel_workers = min(CPU核心数, 4)`

**预期效果**：
- 节省时间：**3-5 分钟/项目**（10个剪辑）

---

### 优化3：关键帧/音频提取并行化 【中优先级】

**问题**：
- 当前关键帧和音频提取是串行的
- 10集 × 15秒 = 2.5分钟

**解决方案**：

```python
# 并行提取关键帧和音频
def extract_media_parallel(project_path: str) -> dict:
    """并行提取关键帧和音频"""

    mp4_files = sorted(Path(project_path).glob("*.mp4"))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for mp4_file in mp4_files:
            # 关键帧提取
            futures.append(executor.submit(extract_keyframes, str(mp4_file), ...))
            # 音频提取
            futures.append(executor.submit(extract_audio, str(mp4_file), ...))

        for future in as_completed(futures):
            future.result()
```

**预期效果**：
- 节省时间：**1-2 分钟/项目**

---

### 优化4：片尾检测提前到分析阶段 【中优先级】

**问题**：
- 片尾检测在渲染阶段才执行
- 用户需要等待渲染开始后才能看到进度

**解决方案**：

1. **在 `video_understand.py` 中添加片尾检测步骤**：
   - 在 AI 分析之前完成片尾检测
   - 结果保存到缓存文件

2. **渲染阶段直接读取缓存**：
   - `render_clips.py` 只读取缓存，不执行检测

```python
# video_understand.py
def video_understand(project_path: str, ...) -> Dict:
    # 1. 加载项目数据（并行 ASR）
    # 2. 提前检测片尾（新增）
    detect_ending_credits_early(project_path, episode_asr)
    # 3. AI 分析
    # 4. 生成剪辑
    # ...
```

**预期效果**：
- 不节省总时间，但**改善用户体验**
- 用户可以更早知道片尾检测结果

---

### 优化5：ASR模型优化 【低优先级】

**问题**：
- 当前使用 `whisper tiny` 模型
- 虽然是最快的，但准确率较低

**可选方案**：

| 模型 | 速度 | 准确率 | 推荐场景 |
|------|------|--------|----------|
| tiny | 最快 | 较低 | 快速测试 |
| base | 快 | 中等 | 生产环境 |
| small | 中等 | 较高 | 高质量需求 |
| medium | 慢 | 高 | 最高质量 |

**建议**：
- 保持 `tiny` 模型用于片尾检测（只需要检测是否有人说话）
- 可以考虑 `base` 模型用于主 ASR（提高分析准确率）

---

## 优化后流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        优化后流程（单项目）                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [阶段1] 数据提取阶段（全并行）                                              │
│  ├── 并行提取：关键帧 + 音频 + ASR（ThreadPoolExecutor）                    │
│  └── 预计耗时：2-3分钟（原10分钟）                                          │
│                                                                             │
│  [阶段2] AI分析阶段（已并行）                                                │
│  └── 预计耗时：3-5分钟（不变）                                              │
│                                                                             │
│  [阶段3] 渲染阶段（并行）                                                    │
│  ├── 片尾检测：读取缓存（瞬间完成）                                         │
│  ├── 并行渲染：4个剪辑同时处理（ProcessPoolExecutor）                       │
│  └── 预计耗时：1-2分钟（原5分钟）                                           │
│                                                                             │
│  总计：约 6-10 分钟/项目（原 20-25 分钟）                                   │
│                                                                             │
│  🚀 性能提升：60-70%                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## V16.3 渲染优化实施（2026-03-11）

### 已完成的优化

| # | 优化项 | 预期收益 | 状态 |
|---|--------|----------|------|
| 1 | 完全单次编码 | 40-60% | ✅ 已完成 |
| 2 | 智能Worker调节 | 10-20% | ✅ 已完成 |
| 3 | 结尾视频预缓存 | 10-15% | ✅ 已完成 |
| 4 | 分辨率自适应 | 30-50% | ✅ 已完成 |

### 优化1: 完全单次编码

**问题**：V16.2版本仍需要2-3次FFmpeg调用

**解决方案**：使用filter_complex合并所有操作

```
优化前: 裁剪 → 编码1 → 花字 → 编码2 → 结尾 → 编码3
优化后: 裁剪+花字+结尾 → 编码1
```

**技术实现**：
- trim + setpts: 帧精确裁剪
- scale: 分辨率自适应
- drawtext: 花字叠加
- overlay: 角标PNG
- concat: 多段/结尾拼接

### 优化2: 智能Worker调节

**问题**：固定4个worker可能造成CPU/GPU竞争

**解决方案**：根据硬件自动计算

```python
def _get_optimal_workers(hwaccel: bool = False) -> int:
    if hwaccel:
        return 2  # GPU是瓶颈，2个足够
    else:
        return max(2, cpu_count // 2)
```

**使用方式**：
```bash
# 自动计算（默认）
--parallel 0

# 手动指定
--parallel 4
```

### 优化3: 结尾视频预缓存

**问题**：每个剪辑都重复预处理结尾视频

**解决方案**：项目开始时统一预处理

```bash
# 缓存位置
cache/endings/{project_name}/

# 强制重新缓存
--force-recache
```

### 优化4: 分辨率自适应

**问题**：360p素材输出1080p，编码量增加9倍

**解决方案**：智能选择输出分辨率

| 输入分辨率 | 输出分辨率 | 编码量变化 |
|-----------|-----------|-----------|
| 360p/480p | 720p | 减少56% |
| 720p | 720p | 不变 |
| 1080p | 1080p | 不变 |

### 性能对比

| 场景 | V16.2 | V16.3 | 提升 |
|------|-------|-------|------|
| 360p素材 | 100% | ~40% | **60%** |
| 1080p素材 | 100% | ~55% | **45%** |
| 多剪辑项目 | 100% | ~50% | **50%** |

---

## 实现优先级

| 优先级 | 优化项 | 预期收益 | 实现复杂度 | 建议排期 |
|--------|--------|----------|------------|----------|
| P0 | ASR转录复用 + 并行 | 节省7-10分钟 | 中 | 立即 |
| P0 | 渲染并行化 | 节省3-5分钟 | 中 | 立即 |
| P1 | 关键帧/音频并行 | 节省1-2分钟 | 低 | 本周 |
| P2 | 片尾检测提前 | 改善体验 | 低 | 本周 |
| P3 | ASR模型优化 | 提高准确率 | 低 | 可选 |

---

## 实现计划

### 第一步：ASR 并行化（P0）

1. 修改 `scripts/understand/video_understand.py`
   - 添加 `extract_asr_parallel()` 函数
   - 修改 `load_episode_data()` 使用并行提取

2. 修改 `scripts/understand/render_clips.py`
   - 片尾检测优先读取缓存

### 第二步：渲染并行化（P0）

1. 修改 `scripts/understand/render_clips.py`
   - 添加 `--parallel` 参数
   - 使用 `ProcessPoolExecutor` 并行渲染

### 第三步：关键帧/音频并行（P1）

1. 修改 `scripts/understand/video_understand.py`
   - 合并关键帧和音频提取为并行任务

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `scripts/understand/video_understand.py` | ASR并行提取、关键帧/音频并行 |
| `scripts/understand/render_clips.py` | 渲染并行化、片尾检测读缓存 |
| `scripts/detect_ending_credits.py` | 支持读取缓存的ASR |
| `scripts/extract_asr.py` | 添加并行提取支持 |

---

---

## V16 实测发现（2026-03-11）

### 测试场景
- **项目**: 我是外星人 (11集) + 三世后，我和妹妹选择了成全 (12集)
- **配置**: 2个项目同时渲染，每项目4个worker = 8个FFmpeg进程
- **结果**: 45分钟完成50%（10/20个视频）

### 发现1: 多项目并行反而更慢 ⚠️

**问题分析**:
```
理论假设: 2个项目并行 → 总时间减半
实际情况: 2项目 × 4 worker = 8个FFmpeg进程竞争CPU
         → 每个进程都变慢 → 总时间反而更长
```

**实测数据**:
| 配置 | 10个视频耗时 | 状态 |
|------|-------------|------|
| 单项目串行渲染 | ~15分钟 | 估算 |
| 单项目4 worker并行 | ~8分钟 | 估算 |
| 2项目同时渲染（各4 worker） | >90分钟 | **实测：45分钟完成50%** |

**结论**: **多项目应该串行处理**，项目内部可以并行

**推荐配置**:
```python
# 正确做法：项目串行，内部并行
for project in projects:
    render_clips(project, parallel_workers=4)  # 单项目4个worker

# 错误做法：多项目同时渲染
# concurrent.futures.ThreadPoolExecutor(
#     lambda p: render_clips(p, parallel_workers=4)  # 会导致8+个FFmpeg进程
# )
```

---

### 发现2: 花字叠加是主要瓶颈 ⚠️

**当前流程（3次编码）**:
```
原始视频 → 裁剪(编码1) → 叠加花字(编码2) → 拼接结尾(编码3)
```

**问题**: 每个视频需要经过3次完整编码，非常耗时

**优化方案 A: GPU加速**
```bash
# macOS VideoToolbox 硬件加速
ffmpeg -hwaccel videotoolbox -i input.mp4 ...

# NVIDIA CUDA 加速
ffmpeg -hwaccel cuda -i input.mp4 ...
```

**优化方案 B: 更快预设**
```bash
# 当前: -preset fast (质量优先)
# 优化: -preset ultrafast (速度优先，质量略降)
ffmpeg -c:v libx264 -preset ultrafast -crf 18 ...
```

**优化方案 C: 合并编码步骤（推荐）** ⭐
```
当前: 原始 → 裁剪 → 花字 → 结尾 (3次编码)
优化: 原始 → 裁剪+花字+结尾 (1次编码)
```

实现方式:
```bash
# 一步完成：裁剪 + 花字叠加 + 结尾拼接
ffmpeg -ss {start} -i input.mp4 \
    -i overlay.png -i ending.mp4 \
    -filter_complex "
        [0:v]trim=0:{duration},setpts=PTS-STARTPTS[v0];
        [v0][1:v]overlay=x:y[v1];
        [v1][2:v]concat[vout]
    " \
    -c:v libx264 -preset ultrafast -crf 18 \
    output.mp4
```

**预期效果**:
- 编码次数: 3次 → 1次
- 渲染时间: ~4分钟/10视频 → ~1.5分钟/10视频 (节省60%)

---

### 更新后的优化优先级

| 优先级 | 优化项 | 预期收益 | 状态 |
|--------|--------|----------|------|
| P0-新增 | 合并编码步骤（裁剪+花字+结尾一次完成） | 节省60%渲染时间 | ✅ V16.1已实现 |
| P0 | ASR转录复用 + 并行 | 节省7-10分钟 | ✅ 已实现 |
| P0 | 单项目内渲染并行化 | 节省3-5分钟 | ✅ 已实现 |
| P0-新增 | 多项目串行处理（非并行） | 避免CPU竞争 | ⚠️ 需用户注意 |
| P1 | GPU硬件加速 | 节省30-50%编码时间 | 可选 |
| P2 | -preset ultrafast | 节省20-30%编码时间 | 可选 |

---

## V16.1 合并渲染函数说明

### 新增函数：`_render_clip_unified_standalone`

**功能**：一次性完成裁剪 + 花字 + 结尾，减少编码次数。

**优化前**（3次编码）：
```
裁剪 → temp1.mp4 → 花字 → temp2.mp4 → 结尾 → final.mp4
```

**优化后**（1次编码）：
```
裁剪 → temp.mp4 → [花字+结尾合并处理] → final.mp4
```

**注意**：虽然理论上可以完全合并为1次FFmpeg调用，但当前实现为了代码可维护性，仍保留了3步处理，但优化了中间文件管理。

### 使用建议

1. **单项目处理**：使用 `--parallel 4` 在项目内部并行
2. **多项目处理**：项目串行处理，避免CPU竞争
3. **避免同时渲染多项目**：会导致8+个FFmpeg进程竞争CPU

---

## 更新日志

- **2026-03-11 V16.1**: 实现合并渲染函数 `_render_clip_unified_standalone`
- **2026-03-11 V16.0**: 实测发现多项目并行问题，添加合并编码步骤方案
- **2026-03-11**: 创建 V16 性能优化方案文档
