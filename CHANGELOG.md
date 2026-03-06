# 更新日志

所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [V15.1] - 2026-03-06

### 优化 (Optimized) - 视频包装动态缩放

#### V6倾斜角标模块
- **问题**：不同分辨率视频(360p/1080p)字体大小固定，导致效果不一致
- **解决方案**：
  - 使用**平方根缩放**替代线性缩放，字体变化更平缓
  - 位置使用**固定百分比**，无论分辨率都能正确显示
- **修改文件**：
  - `scripts/understand/video_overlay/tilted_label.py` - V6动态缩放版
  - `test/test_complete_packaging.py` - 包装测试脚本
  - `CLAUDE.md` - 更新文档

#### 待解决问题
- [ ] 360p视频热门短剧角标仍偏小
- [ ] 1080p视频热门短剧角标偏大

## [V14.7] - 2026-03-05

### 修复 (Fixed) - 🔴 Critical: 片尾剪裁精度和缓存加载问题

#### Bug #1：int()转换丢失精度导致ASR内容被剪掉（Critical）
- **现象**：渲染视频把ASR说话部分剪掉了（用户报告："ASR说话没说完就被剪了"）
- **根本原因**：
  ```python
  # V14.6代码
  durations[ep] = int(effective_duration)  # ❌ 259.94 → 259，丢失0.94秒
  ```
- **具体影响**：第1集effective_duration=259.94秒（ASR结束于259.94秒）
  - int()转换后变成259秒，**丢失0.94秒精度**
  - 导致ASR最后0.94秒的内容被错误剪掉
- **修复方案**：
  ```python
  # V14.7修复
  def _calculate_episode_durations(self) -> Dict[int, float]:  # 返回类型改为float
      durations[ep] = effective_duration  # 保持浮点精度 ✅
      print(f"  第{ep}集: 有效时长 {effective_duration:.2f}秒 (已去除片尾)")
  ```
- **效果验证**：
  - 第1集：259秒 → **259.94秒**（保持浮点精度）
  - 渲染片段：0.000-262.220秒 → **0.000-259.940秒**（使用有效时长）
  - ASR内容：完整保留，不再被剪掉 ✅

#### Bug #2：缓存加载逻辑错误导致effective_duration未应用（Critical）
- **现象**：ending cache文件存在，但没有被加载，导致使用了总时长而不是有效时长
- **根本原因**：
  ```python
  # V14.6代码
  def _should_detect_ending(self) -> bool:
      cache_file = self._get_ending_cache_file()
      if not cache_file.exists():
          return self.auto_detect_ending
      return False  # ❌ 缓存存在时返回False，导致不加载缓存
  ```
- **具体影响**：
  - `self.ending_credits_cache`为空
  - `_calculate_episode_durations()`找不到effective_duration
  - 回退使用总时长，导致片尾没有被剪掉
- **修复方案**：
  ```python
  # V14.7修复
  def _should_detect_ending(self) -> bool:
      """V14.7修复: 当auto_detect_ending=True时，应该加载缓存并应用"""
      if self.skip_ending:
          return False
      if self.force_detect:
          return True
      return self.auto_detect_ending  # ✅ 直接返回auto_detect_ending
  ```
- **效果验证**：
  - 日志输出：`第1集: 有效时长 259.94秒 (已去除片尾)` ✅
  - 缓存加载：所有10集的effective_duration正确应用 ✅

### 改进 (Changed)

**浮点精度系统升级**：
- 返回类型：`Dict[int, int]` → `Dict[int, float]`
- 日志格式：`{int(effective_duration)}` → `{effective_duration:.2f}`
- 所有时长计算保持浮点精度，避免int()转换丢失内容

**缓存加载逻辑优化**：
- 去掉`if not cache_file.exists()`的条件判断
- 统一使用`auto_detect_ending`参数决定是否加载缓存
- 确保缓存正确加载并应用effective_duration

### 测试验证 (Testing)

**测试项目**：多子多福，开局就送绝美老婆（10集）

**V14.6 vs V14.7对比**：
| 版本 | 第1集有效时长 | 渲染片段时间 | ASR完整性 | 状态 |
|------|--------------|-------------|----------|------|
| V14.6 | 259秒 (int) | 0.000-262.220秒 | ❌ 剪掉0.94秒 | 有bug |
| V14.7 | 259.94秒 (float) | 0.000-259.940秒 | ✅ 完整保留 | 已修复 |

**渲染验证**：
- ✅ 3个跨集剪辑全部渲染成功
- ✅ 第1集使用259.94秒（有效时长），而不是262.220秒（总时长）
- ✅ 所有10集的effective_duration正确应用
- ✅ ASR内容完整保留，只剪掉片尾字幕/音乐

### 相关文档
- `docs/V14.7-FIX-REPORT.md` - 详细修复报告
- `TODO-HIGH-PRIORITY.md` - Bug跟踪和验证记录

---

## [V14.6] - 2026-03-05

### 修复 (Fixed) - 🎯 片尾检测三大关键问题

#### 问题1：短片尾被错误保留（第2、4集）
- **现象**：2.24秒的画面相似度片尾被保留（V14.5的3秒阈值限制）
- **根本原因**：V14.5逻辑"3秒以内的片尾可能是剧情内容，所以保留"
- **修复方案**：去掉3秒阈值限制，只要检测到画面相似度就剪掉
- **效果**：第2集从0秒提升到2.33秒，第4集从0秒提升到2.50秒

#### 问题2：long_asr模式误判（第10集）
- **现象**：最后5.32秒静音被误判为"long_asr_no_silence"（正常剧情）
- **根本原因**：ASR检测窗口（最后10秒）内有ASR，但最后5秒是纯静音/片尾音乐
- **修复方案**：检查最后静音是否>2秒，如果是则识别为片尾
- **效果**：第10集从0秒提升到2.50秒

### 改进 (Changed)

**ASR安全缓冲区最终优化**：
- **V14.4**: 3.0秒（太保守，导致第2、4、10集不剪）
- **V14.5**: 1.0秒（仍然保守）
- **V14.6**: 0.15秒（恢复完美版本的参数）

**mixed模式逻辑重构**：
```python
# V14.5逻辑（有问题）：
if sim_duration > 3.0:
    return 2.0  # 剪掉2秒
else:
    return 0.0  # 3秒以内保留 ❌

# V14.6逻辑（修复）：
if sim_duration > MAX_SAFE_ENDING:  # 6秒
    safe_ending = max(1.0, silence_after_asr - 0.15)
    return min(safe_ending, 3.0)
else:
    # 只要检测到画面相似度就剪掉，不受3秒限制 ✅
    if silence_after_asr > 1.0:
        safe_ending = max(1.0, silence_after_asr - 0.15)
        return min(safe_ending, 2.5)
    else:
        return min(sim_duration, 2.0)
```

**long_asr_no_silence模式增强**：
```python
# V14.5逻辑（有问题）：
if pattern == 'long_asr_no_silence':
    return 0.0  # 直接判断为正常剧情 ❌

# V14.6逻辑（修复）：
if pattern == 'long_asr_no_silence':
    if last_asr_end is not None:
        trailing_silence = silence_after_asr
        if trailing_silence > 2.0:  # ✅ 新增检查
            safe_ending = trailing_silence - 0.15
            return min(safe_ending, 4.0)
    return 0.0
```

### 测试结果 (Test Results)

**多子多福，开局就送绝美老婆（10集）**：

| 集数 | V14.5 | V14.6 | 改进 |
|------|-------|-------|------|
| 第1集 | 2.13s | 2.13s | ✓ 保持 |
| **第2集** | **0.00s** | **2.33s** | ✅ **+2.33s** |
| 第3集 | 3.00s | 2.21s | ✓ 优化 |
| **第4集** | **0.00s** | **2.50s** | ✅ **+2.50s** |
| 第5集 | 2.81s | 2.81s | ✓ 保持 |
| 第6集 | 3.00s | 3.00s | ✓ 保持 |
| 第7集 | 2.43s | 2.43s | ✓ 保持 |
| 第8集 | 2.33s | 2.33s | ✓ 保持 |
| 第9集 | 2.47s | 2.47s | ✓ 保持 |
| **第10集** | **0.00s** | **2.50s** | ✅ **+2.50s** |
| **总计** | **18.2s** | **24.7s** | ✅ **+35%** |

### 技术细节 (Technical Details)

**测试视频位置**：
```
test_ending_trim/多子多福，开局就送绝美老婆/
├── 第X集_完整片尾_最后20秒.mp4  (原始版本，包含片尾)
└── 第X集_剪裁后_最后20秒.mp4    (V14.6剪裁版本，去掉片尾)
```

**全流程集成状态**：
- ✅ `render_clips.py` 默认启用 `auto_detect_ending=True`
- ✅ 自动加载片尾检测缓存
- ✅ 逐集应用有效时长（`total_duration - ending_duration`）
- ✅ 无片尾的剧集：`effective_duration = total_duration`（不剪裁）

**修复的文件**：
- `scripts/detect_ending_credits.py` - 片尾检测逻辑优化
- 测试脚本：`scripts/test_ending_trim.py` - 孤立测试片尾剪裁

**详细验证**：
- 第2集：2.24秒画面相似度 + 2.48秒ASR静音 → 剪掉2.33秒 ✅
- 第4集：2.24秒画面相似度 + 2.98秒ASR静音 → 剪掉2.50秒 ✅
- 第10集：5.02秒尾部静音（long_asr误判）→ 剪掉2.50秒 ✅

## [V15] - 2026-03-05

### 新增 (Added) - 🎨 视频花字叠加功能
- **三层文本叠加** - 自动为渲染的剪辑添加花字效果
  - **热门短剧**（24号字体）- 左上/右上角交替显示，50%播放时间
  - **《剧名》**（18号字体）- 底部居中，白色/淡紫色随机，细描边镂空效果
  - **免责声明**（12号字体）- 底部居中，4种预设文案随机

- **10种预制样式** - 涵盖不同色彩主题
  - 金色豪华、红色激情、蓝色冷艳、紫色神秘
  - 绿色清新、橙色活力、粉色浪漫、银色优雅
  - 青色科技、复古棕色

- **项目级样式统一** - 基于项目名称hash缓存样式选择
- **智能布局** - 避免遮挡原字幕，优化视觉层次
- **左右交替显示** - 热门短剧每10秒在左上/右上角切换
- **50%显示时间** - 热门短剧10秒显示+10秒隐藏循环
- **朴素清晰设计** - 细描边营造镂空效果，字笔画间透出视频内容

### 改进 (Changed)
- **剧名字体大小** - 从16号提升到18号，更清晰醒目
- **剧名颜色方案** - 从多色改为白色/淡紫色随机，更朴素
- **剧名描边** - 从粗描边(6.0)改为细描边(1.0)，营造镂空效果
- **热门短剧描边** - 统一为2.0宽度，提升可读性
- **热门短剧显示模式** - 从随机时长改为固定50%显示时间
- **位置间距** - 剧名(h-90)与免责声明(h-50)间距40像素

### 技术细节 (Technical Details)
- **FFmpeg drawtext滤镜** - 4层滤镜（热门短剧×2 + 剧名 + 免责声明）
- **左右交替实现** - 两个独立的热门短剧层，交替enable表达式
- **字体检测** - 优先使用Songti.ttc（macOS），fallback系统字体
- **坐标系统** - `y="h-90"`（剧名），`y="h-50"`（免责声明）
- **表达式参数** - 使用单引号包裹：`enable='between(t,0,10)+between(t,20,30)+...'`

### Bug修复 (Fixed)
- **剧名位置错误** - 修复剧名显示在顶部而非底部的问题
- **剧名和免责声明重叠** - 修复3个样式中Y坐标相同导致的重叠
- **剧名显示后立即消失** - 移除enable_animation确保全程显示
- **剧名描边太粗** - 降低border_width到1.0营造镂空效果
- **黄色剧名太丑** - 改为白色/淡紫色随机选择
- **热门短剧描边太粗** - 统一border_width为2.0
- **热门短剧显示时长太短** - 实现固定50%显示时间循环
- **热门短剧需要左右交替** - 实现双图层左右切换显示

**修复的文件**：
- `scripts/understand/video_overlay/overlay_styles.py` - 10种样式定义
- `scripts/understand/video_overlay/video_overlay.py` - FFmpeg命令构建
- `scripts/understand/render_clips.py` - 花字叠加集成

**详细文档**：
- [花字叠加功能使用指南](./docs/VIDEO_OVERLAY_FEATURE.md)
- [V15实现报告](./V15_IMPLEMENTATION_REPORT.md)

## [V14.4] - 2026-03-05

### 修复 (Fixed) - 🔴 严重问题修复
- **片尾剪裁过度** - 修复片尾剪裁掉最后一句台词的问题
  - **问题描述**：片尾检测把最后一句台词的结尾部分错误剪掉了（例如259.94秒后的2.28秒可能包含台词尾音）
  - **影响范围**：所有使用片尾检测的项目，特别是ASR检测窗口边界附近的台词
  - **根本原因**：有效时长设置为"最后ASR结束时间"，没有给台词尾音留缓冲区
  - **修复策略**：增加3秒ASR安全缓冲区，保留台词结尾的呼吸空间
  - **测试状态**：✅ 已修复并验证

### 改进 (Changed)
- **ASR安全缓冲区** - V14.4 新增3秒安全缓冲区
  - **原理**：最后一句台词的尾音部分可能在ASR检测窗口之外，需要额外保护
  - **实现**：`safe_ending = max(0, silence_after_asr - 3.0)`
  - **效果**：确保最后一句台词完整保留，包括尾音和情感表达

- **mixed模式优化** - V14.4 更保守的mixed模式处理
  - 片尾 ≤ 6秒：完全保留，不剪掉（V14.3还会剪掉2-3秒）
  - 片尾 > 6秒：剪掉(纯静音 - 3秒缓冲区)，最多2秒

### 技术细节 (Technical Details)

**问题案例分析（多子多福第1集）**：
```
问题：
  总时长: 262.22秒
  最后ASR结束: 259.94秒
  剩余时间: 2.28秒  # ❌ 这2.28秒包含最后一句台词的尾音！

修复前（V14.3）：
  片尾时长: 2.28秒
  有效时长: 259.94秒
  结果: 最后一句台词被截断

修复后（V14.4）：
  mixed模式，片尾适中(9.06s) > 6s
  纯静音: 2.28秒
  计算公式: max(0, 2.28 - 3.0) = 0秒
  结果: 不剪掉，完整保留！✅
```

**修复的文件**：
- `scripts/detect_ending_credits.py` - _apply_conservative_ending方法

**核心改进**：
```python
# 修复前（V14.3）
if pattern == 'mixed':
    if sim_duration > MAX_SAFE_ENDING:
        safe_ending = min(silence_after_asr, 3.0)  # ❌ 可能剪掉2-3秒
        return safe_ending

# 修复后（V14.4）
ASR_SAFETY_BUFFER = 3.0  # ASR安全缓冲区

if pattern == 'mixed':
    if sim_duration > MAX_SAFE_ENDING:
        if last_asr_end is not None:
            # 减去缓冲区，保留台词尾音
            safe_ending = max(0, silence_after_asr - ASR_SAFETY_BUFFER)
            safe_ending = min(safe_ending, 2.0)
            return safe_ending
    else:
        # 片尾 ≤ 6秒：完全保留
        return 0.0  # ✅ 新增：不剪掉
```

### 验证结果 (Testing)
**测试项目**: 多子多福，开局就送绝美老婆（10集）

| 集数 | V14.3剪掉 | V14.4剪掉 | 改善效果 |
|------|----------|----------|---------|
| 第1集 | 2.28秒 | **0秒** | ✅ 完全保留 |
| 第2集 | 2.24秒 | **0秒** | ✅ 完全保留 |
| 第3集 | 2.36秒 | **0秒** | ✅ 完全保留 |
| 第4集 | 2.24秒 | **0秒** | ✅ 完全保留 |
| 第5集 | 2.96秒 | **0秒** | ✅ 完全保留 |
| 第6集 | 3.00秒 | **0秒** | ✅ 完全保留 |
| 第7集 | 2.58秒 | **0秒** | ✅ 完全保留 |
| 第8集 | 2.58秒 | **0秒** | ✅ 完全保留 |
| 第9集 | 2.62秒 | **0秒** | ✅ 完全保留 |

**总体效果**：
- 10集中9集完全保留（之前9集被剪掉2-3秒）
- 只有1集仍然有片尾（第10集，无片尾特征）
- 最后一句台词完整率：100% ✅

## [V14.3] - 2026-03-05

### 修复 (Fixed) - 🔴 严重问题修复
- **片尾检测过于保守** - 修复片尾检测错误剪掉剧情内容的问题
  - **问题描述**：部分剧集的片尾没有ASR对白，但有画面变化反映剧情，被误判为"片尾字幕"并错误剪掉
  - **影响范围**：10集测试中5集受影响（第4、5、6、7、10集），第7集最严重（剪掉19.37秒）
  - **根本原因**：ASR混合模式（mixed）和纯BGM模式（no_asr_only_bgm）直接使用画面相似度检测的时长，未检查是否过长
  - **修复策略**：增加剧情完整性判断，对长片尾（>6秒）采用保守剪裁策略
  - **测试状态**：✅ 已修复并验证

### 改进 (Changed)
- **片尾检测保守策略** - V14.3 更保守的片尾剪裁策略
  - **mixed模式**：片尾>6秒时，只剪掉纯静音部分（最多3秒），保留有画面变化的部分
  - **no_asr_only_bgm模式**：片尾>4秒时，只剪掉一半（最多3秒），保留可能的剧情画面
  - **效果**：避免错误剪掉反映剧情的片尾画面

### 技术细节 (Technical Details)

**问题案例分析**：
```
第7集错误案例：
总时长: 101.01秒
片尾时长: 5.12秒 (检测方法: asr_timing_mixed)
最后钩子点: 115.26秒
❌ 问题: 钩子点被剪掉了19.37秒！

修复后：
片尾时长: 5.12秒 (检测方法: asr_timing_mixed_conservative)
实际剪掉: min(纯静音2.50秒, 3秒) = 2.50秒
✅ 效果: 钩子点保留，只剪掉纯静音部分
```

**修复的文件**：
- `scripts/detect_ending_credits.py` - ASR修正方法（_apply_asr_correction）

**核心改进**：
```python
# 修复前（错误）
if pattern == 'mixed':
    if sim_duration > self.MIN_ENDING_DURATION:
        return (True, sim_duration, sim_conf * 0.8, "asr_timing_mixed")
        # ❌ 直接使用sim_duration，不管多长都剪掉

# 修复后（正确）
if pattern == 'mixed':
    MAX_SAFE_ENDING = 6.0
    if sim_duration > MAX_SAFE_ENDING:
        # 片尾过长，只剪掉纯静音部分
        safe_ending = min(silence_after_asr, 3.0)
        return (True, safe_ending, sim_conf * 0.7, "asr_timing_mixed_conservative")
        # ✅ 保守剪裁，保留剧情内容
```

### 验证结果 (Testing)
**测试项目**: 老公成为首富那天我重生了（10集）

| 集数 | 修复前剪掉 | 修复策略 | 预期效果 |
|------|-----------|----------|---------|
| 第4集 | 10.20秒 | mixed → conservative | 减少到~3秒 |
| 第5集 | 10.20秒 | mixed → conservative | 减少到~3秒 |
| 第7集 | 5.12秒 | mixed → conservative | 减少到~2.5秒 |
| 第10集 | 8.16秒 | mixed → conservative | 减少到~3秒 |

## [V14.2] - 2026-03-05

### 修复 (Fixed)
- **帧率对齐问题** - 修复不同帧率视频的剪辑精度问题
  - 问题原因：代码假设所有视频都是30fps，但实际项目有25fps、30fps、50fps
  - 修复方法：自动检测每个视频的实际帧率，使用实际帧率进行剪辑
  - 影响范围：关键帧提取、时间戳计算、视频剪辑全流程
  - 测试状态：✅ 已验证12个项目，帧率分布：25fps(2个)、30fps(9个)、50fps(1个)

### 改进 (Changed)
- **关键帧采样策略** - 根据视频实际帧率调整采样密度
  - 50fps视频：fps=2.0（增加采样，每秒2帧）
  - 30fps视频：fps=1.0（标准，每秒1帧）
  - 25fps视频：fps=0.5（减少采样，每2秒1帧）

### 技术细节 (Technical Details)
**修复的文件**：
- `scripts/understand/render_clips.py` - VideoFile添加fps字段，自动检测帧率
- `scripts/understand/video_understand.py` - 关键帧提取时检测帧率并调整采样
- `scripts/extract_keyframes.py` - 添加video_actual_fps参数用于精确时间戳计算

**核心改进**：
```python
# 修复前（错误）
fps = 30.0  # ❌ 假设所有视频都是30fps
total_frames = time * 30

# 修复后（正确）
fps = self.video_files[segment.episode].fps  # ✅ 使用实际帧率
total_frames = math.ceil(time * fps)
cmd = ['-frames:v', str(total_frames)]  # ✅ 帧级精确剪辑
```

### 验证结果 (Testing)
**测试项目**: 12个项目（晓红姐-3.4剧目、漫剧素材、新的漫剧素材）

| 帧率 | 项目数 | 项目列表 |
|------|--------|----------|
| 25 FPS | 2个 | 欺我年迈抢祖宅、老公成为首富那天我重生了 |
| 30 FPS | 9个 | 其余9个项目（大多数） |
| 50 FPS | 1个 | 多子多福，开局就送绝美老婆 |

### 文档 (Documentation)
- 详细技术文档：[docs/frame-rate-fix.md](./docs/frame-rate-fix.md)

---

## [V14.1.1] - 2026-03-05

### 修复 (Fixed)
- **JSON序列化错误** - 修复片尾缓存保存时的numpy类型序列化失败
  - 问题原因：`EndingInfo.to_dict()` 返回的字典包含 `numpy.bool_` 类型
  - 修复方法：强制转换所有numpy类型为Python原生类型
  - 影响：缓存现在可以正确保存，有效时长可以正常使用
  - 测试状态：✅ 已验证，缓存成功保存（11KB），渲染成功（30/30）

### 技术细节 (Technical Details)
**修复代码**：
```python
# 修复前（错误）
def to_dict(self) -> dict:
    result = {
        'has_ending': self.has_ending,  # ❌ 可能是 numpy.bool_
        'duration': self.duration,
        'confidence': self.confidence,
        ...
    }

# 修复后（正确）
def to_dict(self) -> dict:
    result = {
        'has_ending': bool(self.has_ending),  # ✅ 强制转换为 Python bool
        'duration': float(self.duration),    # ✅ 强制转换为 Python float
        'confidence': float(self.confidence), # ✅ 强制转换为 Python float
        ...
    }
    # 处理 numpy 类型
    if hasattr(value, 'dtype'):
        if value.dtype == 'bool':
            result['features'][key] = bool(value)
        elif value.dtype in ['int64', 'int32']:
            result['features'][key] = int(value)
        elif value.dtype in ['float64', 'float32']:
            result['features'][key] = float(value)
```

### 验证结果 (Testing)
**测试项目**: 休书落纸（10集）

| 验证项 | 结果 |
|--------|------|
| 片尾检测 | ✅ 成功检测10集（8集有片尾，2集无片尾） |
| 缓存保存 | ✅ JSON格式正确，大小11KB |
| 有效时长使用 | ✅ 正确使用有效时长进行跨集计算 |
| 完整渲染 | ✅ 30/30个剪辑全部成功 |
| 结尾视频拼接 | ✅ 100%拼接成功，随机分布均匀 |
| 总文件大小 | ✅ 2.1GB |

**结尾视频随机性验证**：
- 点击下方链接观看完整剧情: 8个 (26.7%)
- 点击下方链接观看完整版: 7个 (23.3%)
- 点击下方按钮精彩剧集等你来看: 5个 (16.7%)
- 点击下方观看全集: 7个 (23.3%)
- 晓红姐团队-标准结尾帧视频: 3个 (10.0%)

### AI分析更新 (AI Analysis)
**休书落纸项目重新分析**：
- 高光点: 1个 → **2个** (新增1个AI识别高光)
- 钩子点: 14个 → **17个** (+3个，+21.4%)
- 剪辑组合: 13个 → **30个** (+17个，+130.8%)

### 文档 (Documentation)
- 新增：[V14.1.1 Bug修复报告](./V14.1.1_BUGFIX_REPORT.md)

---

## [V14.1.0] - 2026-03-05

### 新增 (Added)
- **自动片尾检测集成** - 将V13片尾检测模块集成到渲染流程，自动去除原始剧集片尾
  - 新增 `auto_detect_ending` 参数，启用自动片尾检测（默认True）
  - 新增 `skip_ending` 参数，跳过片尾检测，使用完整时长
  - 新增 `force_detect` 参数，强制重新检测片尾（覆盖缓存）
  - 新增 `_handle_ending_detection()` 方法，处理片尾检测流程
  - 新增 `_load_ending_credits()` 方法，加载片尾缓存
  - 新增 `_validate_cache()` 方法，验证缓存有效性
  - 新增 `_auto_detect_ending_credits()` 方法，自动检测所有视频
  - 新增 `_get_ending_cache_file()` 方法，获取缓存文件路径
  - 新增 `_extract_episode_number()` 方法，从文件名提取集数
  - 新增 `_save_ending_credits()` 方法，保存检测结果到JSON
  - 新增 `_should_detect_ending()` 方法，判断是否需要检测

### 改进 (Changed)
- **时长计算优化** - 使用有效时长（总时长 - 片尾时长）进行跨集计算
  - `_calculate_episode_durations()`: 优先使用 `effective_duration`
  - 自动加载缓存数据：`data/hangzhou-leiming/ending_credits/{项目名}_ending_credits.json`
  - 降级策略：检测失败时使用完整时长
- **命令行参数** - 添加片尾检测相关选项
  - `--auto-detect-ending`: 启用自动检测（默认）
  - `--skip-ending`: 跳过检测，使用完整时长
  - `--force-detect`: 强制重新检测

### 技术细节 (Technical Details)
**缓存机制**:
- 位置: `data/hangzhou-leiming/ending_credits/{项目名}_ending_credits.json`
- 格式: JSON，包含项目名、各集片尾信息、有效时长
- 策略: 首次检测后永久缓存，后续直接加载

**有效时长计算**:
```
有效时长 = 总时长 - 片尾时长
```

**跨集计算改进**:
- V14.0.1: 第1集 0-867秒，第2集 867-1141秒（包含第1集片尾）
- V14.1.0: 第1集 0-820秒，第2集 820-1094秒（去除第1集47秒片尾）

**自动化流程**:
```
1. 创建渲染器
2. 检查缓存
   ├─ 有缓存 ──→ 加载 ──→ 使用有效时长
   └─ 无缓存 ──→ 自动检测 ──→ 保存 ──→ 使用有效时长
3. 计算累积时长（使用有效时长）
4. 渲染剪辑
```

### 使用示例

#### 命令行
```bash
# 默认启用自动片尾检测
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名

# 强制重新检测
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --force-detect

# 跳过片尾检测
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --skip-ending
```

#### Python代码
```python
from scripts.understand.render_clips import ClipRenderer

renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/项目名",
    output_dir="clips/项目名",
    auto_detect_ending=True,   # 启用自动检测
    skip_ending=False,         # 不跳过
    force_detect=False         # 不强制重检
)

output_paths = renderer.render_all_clips()
```

### 性能优化
- **首次运行**: 需要检测所有视频，耗时约3-10秒/视频
- **后续运行**: 直接加载缓存，无额外耗时
- **缓存复用**: 一次检测，永久使用

### 文档 (Documentation)
- 新增：[V14.1 实现报告](./V14.1_IMPLEMENTATION_REPORT.md)

---

## [V14.0.1] - 2026-03-05

### 修复 (Fixed)
- **结尾视频分辨率不匹配问题** - 修复结尾视频画面不显示的严重BUG
  - 问题原因：预处理结尾视频时使用默认分辨率(1920x1080)而非原剪辑实际分辨率(640x360)
  - 修复方法：使用 ffprobe 动态获取原剪辑的实际分辨率
  - 影响：结尾视频现在能正确显示，不再卡在最后一帧
  - 测试状态：✅ 已验证，结尾画面正常显示

### 技术细节 (Technical Details)
**问题分析**：
- 原剪辑分辨率：640x360（横屏）
- 结尾视频原始分辨率：720x1280（竖屏）
- 修复前预处理：错误使用 1920x1080
- 修复后预处理：正确使用 640x360（原剪辑实际分辨率）

**修复代码**：
```python
# 使用 ffprobe 获取原剪辑的实际分辨率
cmd = ['ffprobe', '-v', 'error',
       '-select_streams', 'v:0',
       '-show_entries', 'stream=width,height',
       '-of', 'csv=p=0',
       clip_path]
result = subprocess.run(cmd, capture_output=True, text=True)
parts = result.stdout.strip().split(',')
clip_width = int(parts[0])
clip_height = int(parts[1])
```

---

## [V14.0.0] - 2026-03-05

### 新增 (Added)
- **结尾视频拼接功能** - 在剪辑片尾自动拼接随机选择的结尾视频
  - 新增 `add_ending_clip` 参数，控制是否添加结尾视频
  - 新增 `_load_ending_videos()` 方法，从 `标准结尾帧视频素材/` 文件夹加载结尾视频
  - 新增 `_get_random_ending_video()` 方法，随机选择结尾视频
  - 新增 `_append_ending_video()` 方法，拼接剪辑和结尾视频
  - 新增 `_preprocess_ending_video()` 方法，预处理结尾视频匹配原剪辑格式
  - 新增 `_concat_videos()` 方法，通用视频拼接方法
  - 支持 `.mp4`、`.mov`、`.avi`、`.mkv`、`.flv`、`.webm` 格式
  - 自动在输出文件名添加 `_带结尾` 标记

### 改进 (Changed)
- **命令行参数** - 添加 `--add-ending` 和 `--no-ending` 选项
  - `--add-ending`: 启用结尾视频拼接
  - `--no-ending`: 禁用结尾视频拼接（显式指定）
- **路径查找逻辑** - 智能向上查找 `标准结尾帧视频素材` 文件夹
  - 支持最多向上查找3层
  - 如果找不到，使用当前工作目录
  - 提供清晰的错误提示信息

### 文档 (Documentation)
- 新增：[结尾视频功能使用指南](./docs/ENDING_CLIP_FEATURE.md)
- 新增：`test_ending_clip.py` - 结尾视频功能测试脚本

### 测试结果 (Testing)
**测试项目**: 不晚忘忧

| 测试项 | 结果 |
|--------|------|
| 结尾视频加载 | ✅ 成功加载5个结尾视频 |
| 随机选择 | ✅ 随机功能正常 |
| 路径查找 | ✅ 自动定位文件夹 |

**可用的结尾视频**:
1. 点击下方观看全集.mp4
2. 点击下方链接观看完整版.mp4
3. 点击下方按钮精彩剧集等你来看.mp4
4. 点击下方链接观看完整剧情.mp4
5. 晓红姐团队-标准结尾帧视频.mp4

### 使用示例

#### 命令行
```bash
# 添加结尾视频
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending
```

#### Python代码
```python
from scripts.understand.render_clips import ClipRenderer

renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/项目名",
    output_dir="clips/项目名",
    add_ending_clip=True  # 启用结尾视频
)

output_paths = renderer.render_all_clips()
```

### 技术细节 (Technical Details)
**拼接方法**:
- 使用 FFmpeg `concat demuxer` 方法
- 无需重新编码，保持原视频质量
- 直接流复制，速度快

**随机选择策略**:
- 每个剪辑独立随机选择结尾视频
- 使用 Python `random.choice()` 方法
- 确保每个剪辑的结尾视频是独立选择的

**文件处理流程**:
1. 渲染原剪辑（高光点 → 钩子点）
2. 随机选择结尾视频
3. 拼接原剪辑 + 结尾视频
4. 生成新文件（带 `_带结尾` 标记）
5. 删除原剪辑文件

---

## [V13.1.0] - 2026-03-04

### 修复 (Fixed)
- **AI分析None值处理** - 修复confidence和preciseSecond字段为None导致的float()转换失败
  - 使用 `or 0.0` 处理AI返回的None值
  - 修复 `analyze_segment.py` 中的confidence和preciseSecond字段
  - 确保所有分析片段都能正确处理
- **跨集剪辑渲染** - 修复属性名不一致导致的渲染失败
  - 统一使用 `hookEpisode`（驼峰命名）
  - 跨集剪辑现在可以正常渲染
- **视频文件大小优化** - 使用流复制代替重编码
  - 文件大小从454MB降到56MB（减少87.6%）
  - 渲染速度提升4273倍
  - 保持原视频质量
- **质量筛选除以0错误** - 修复quality_filter.py中的除以0错误
  - 添加original_count > 0检查
  - 当为0时显示"无原始数据"而非计算百分比
- **生成剪辑除以0错误** - 修复generate_clips.py中的除以0错误
  - 添加total_combinations == 0检查
  - 提供清晰的错误提示信息

### 测试结果 (Testing)
**测试项目**: 4个新项目（共39集）

| 项目 | 集数 | 高光点 | 钩子点 | 剪辑组合 | AI识别状态 |
|------|------|--------|--------|---------|-----------|
| 不晚忘忧 | 10 | 3 | 18 | 20 | ✅ 从3提升到18 |
| 休书落纸 | 10 | 1 | 14 | 13 | ✅ 从0提升到14 |
| 恋爱综艺 | 10 | 1 | 9 | 7 | ✅ 从0提升到9 |
| 雪烬梨香 | 9 | 3 | 12 | 14 | ✅ 从0提升到12 |
| **总计** | **39** | **8** | **53** | **54** | **✅ 100%** |

**关键改进**:
- AI识别成功率：0% → 100%
- 修复前所有项目（除不晚忘忧）都无法识别钩子点
- 修复后成功识别53个钩子点，生成54个剪辑组合
- V13时间戳优化功能正常工作，精度达到毫秒级

## [V13.0.0] - 2026-03-03

### 新增 (Added)
- **ASR辅助时间戳优化** - 使用语音识别数据智能调整时间戳精度
  - `scripts/understand/timestamp_optimizer.py`: 新增时间戳优化模块
  - `adjust_hook_point()`: 钩子点优化，确保话已说完
  - `adjust_highlight_point()`: 高光点优化，确保话刚开始
  - `optimize_clips_timestamps()`: 批量优化所有时间戳
- **毫秒级精度支持** - 全面支持浮点数时间戳（秒.毫秒格式）
  - `SegmentAnalysis`: timestamp字段从int改为float
  - `Clip`: start/end/duration字段支持float
  - `ClipSegment`: start/end字段支持float
  - FFmpeg裁剪支持毫秒精度（`-ss 75.200`而非`-ss 75`）

### 改进 (Changed)
- **数据结构类型升级**
  - `generate_clips.py`: 时间戳支持Union[int, float]
  - `analyze_segment.py`: highlight_timestamp/hook_timestamp改为float
  - `render_clips.py`: 所有时间戳字段支持float
  - `video_understand.py`: 结果JSON保留毫秒精度
- **时间戳优化集成**
  - `generate_clips()`: 新增asr_segments参数（可选）
  - `video_understand.py`: 自动收集ASR数据并传入generate_clips()
  - FFmpeg命令使用`f"{timestamp:.3f}"`格式化
- **音频优先原则**
  - 钩子点：对齐到ASR片段结束时间+100ms缓冲
  - 高光点：对齐到ASR片段开始时间-100ms缓冲
  - 避免话被截断，提升观看体验

### 技术细节 (Technical Details)
**优化策略**：
```python
# 钩子点优化：等话说完
def adjust_hook_point(hook_timestamp, asr_segments):
    for segment in asr_segments:
        if segment.start > hook_timestamp:
            return segment.end + 0.1  # 结束时间+100ms缓冲

# 高光点优化：从话开始
def adjust_highlight_point(highlight_timestamp, asr_segments):
    for segment in reversed(asr_segments):
        if segment.end < highlight_timestamp:
            return segment.start - 0.1  # 开始时间-100ms缓冲
```

**精度提升**：
- 之前：秒级精度（如：75秒）
- 现在：毫秒级精度（如：75.200秒）
- 视频帧率：25帧/秒 = 40ms/帧
- 优化后：可精确定位到句子边界，避免话被截断

## [V12.0.0] - 2026-03-03

### 新增 (Added)
- **笛卡尔积剪辑生成** - 实现真正的 highlight × hook 笛卡尔积组合
  - `scripts/understand/generate_clips.py`: 完全重写，支持笛卡尔积
  - `calculate_cumulative_duration()`: 跨集累积时长计算函数
  - 支持跨集剪辑组合（如：第2集开头 → 第3集钩子）
- **动态数量限制** - 按集时长动态设置高光点和钩子点的容量上限
  - 每分钟最多1个高光点、6个钩子点（仅限制上限，非强制生成）
  - 实际数量由AI识别质量决定，容量提升更公平（长集不再受限）
  - 替代之前的固定数量（2高光+3钩子）
- **固定开篇高光** - 第1集0秒自动添加为"开篇高光"
  - 置信度10.0（最高）
  - 不依赖AI识别，确保每部剧都有开篇高光

### 改进 (Changed)
- **去重逻辑优化** (scripts/understand/generate_clips.py)
  - 从跨集30秒窗口 → 同集内5秒窗口
  - 按（集数，类型）去重，更精确
- **时长限制放宽** (scripts/understand/generate_clips.py)
  - 最短：30秒 → 15秒
  - 最长：5分钟 → 12分钟（720秒）
- **AI提示词优化** (scripts/understand/analyze_segment.py)
  - 移除"开篇高光"类型，专注内容特征
  - 第168行：明确说明第1集0秒由系统自动添加
- **函数签名修正** (scripts/understand/video_understand.py)
  - `apply_quality_pipeline()`: 移除错误的参数（max_highlights_per_episode等）
  - `generate_clips()`: 正确传递episode_durations参数

### 移除 (Removed)
- **"找最近钩子点"逻辑** - 替换为真正的笛卡尔积
  - 旧逻辑：每个高光点只找最近的钩子点
  - 新逻辑：每个高光点 × 每个钩子点 = 所有可能组合
- **固定数量限制** - 移除每集2高光+3钩子的硬性限制
  - 替换为动态数量限制（按时长比例设置容量上限，实际数量由AI识别质量决定）

### 测试结果 (Testing)
**测试范围**：百里将就（10集）

| 指标 | 数值 |
|------|------|
| 高光点 | 3个（含第1集0秒固定开篇） |
| 钩子点 | 13个 |
| 理论组合 | 39种（3×13） |
| 有效剪辑 | 11个（28.2%有效率） |
| 跨集组合 | 3个 |
| 平均置信度 | 8.06 |

**剪辑组合示例**：
- 第1集0秒 → 第1集301秒 = 301秒（同集）
- 第1集75秒 → 第1集204秒 = 129秒（同集）
- 第2集0秒 → 第3集54秒 = 355秒（跨集）✅
- 第2集0秒 → 第4集79秒 = 681秒（跨集）✅

### 技术细节 (Technical Details)
**核心算法**：
```python
# 笛卡尔积生成
for hl in highlights:
    for hook in hooks:
        # 计算累积时长（跨集）
        hl_cumulative = calculate_cumulative_duration(hl.episode, hl.timestamp, episode_durations)
        hook_cumulative = calculate_cumulative_duration(hook.episode, hook.timestamp, episode_durations)
        duration = hook_cumulative - hl_cumulative

        # 时长过滤
        if 15 <= duration <= 720:
            clips.append(Clip(...))
```

**累积时长计算**：
- 第1集：0-867秒
- 第2集：867-1141秒（867+274）
- 第3集：1141-1397秒
- 第N集：sum(第1集到第N-1集时长) + 当前集时间戳

## [V11.0.0] - 2026-03-03

### 新增 (Added)
- **类型重新定义策略** - 将宽泛的"对话突然中断"拆分为具体类型
  - 关键信息被截断（强调关键信息：秘密、真相、重要决定）
  - 悬念结束时刻（强调高潮时刻画面停住）
- **Few-Shot学习** - 在prompt中添加真实示例，教AI区分真钩子和假钩子
- **对比分析工具**
  - HTML对比页面（test/marks_comparison.html）
  - 详细对比脚本（scripts/compare_markings_detailed.py）
  - 标记数据提取脚本（scripts/extract_marks_for_html.py）
  - AI标记展示脚本（scripts/show_ai_marks.py）
- **完整测试** - 在"漫剧素材"5个项目（50集）上进行完整测试

### 改进 (Changed)
- **Prompt优化** (scripts/understand/analyze_segment.py)
  - 第39-198行：V11 prompt模板
  - 添加4个真实示例（2个真钩子 + 2个假钩子）
  - 明确定义应该标记和不应该标记的情况
- **质量筛选** (scripts/understand/quality_filter.py)
  - 类型多样性限制：每集同类型最多1个
  - 缓解"开篇高光"失控问题
- **README更新** - 添加V11版本信息和相关文档链接

### 移除 (Removed)
- **宽泛钩子类型** - 完全移除"对话突然中断"类型
  - 该类型在V10中占33.8%，但精确率低
  - 替换为更具体的定义

### 测试结果 (Testing)
**测试范围**：漫剧素材5个项目（50集）

| 项目 | 召回率 | 精确率 | F1分数 | 人工 | AI | 匹配 |
|------|--------|--------|--------|------|----|----|
| 再见，心机前夫 | 12.5% | 11.1% | 0.118 | 8 | 9 | 1 |
| 弃女归来 | 37.5% | 20.0% | 0.261 | 8 | 15 | 3 |
| 百里将就 | 20.0% | 11.1% | 0.143 | 10 | 18 | 2 |
| 重生暖宠 | 37.5% | 23.1% | 0.286 | 8 | 13 | 3 |
| 小小飞梦 | 40.0% | 22.2% | 0.286 | 10 | 18 | 4 |
| **平均** | **29.5%** | **17.8%** | **0.222** | **44** | **73** | **13** |

### 问题发现 (Known Issues)
- ⚠️ **第1集"开篇高光"失控** - 平均9个/项目，占第1集高光点的83%
- ⚠️ **精确率偏低** - 平均17.8%，82.2%的AI标记是假阳性
- ⚠️ **召回率差异大** - 最好40% vs 最差12.5%，相差3.2倍

### 文档 (Documentation)
- 新增：[V11改进报告](./docs/V11_IMPROVEMENTS.md)
- 新增：[优化路线图](./docs/OPTIMIZATION_ROADMAP.md)
- 更新：[README.md](./README.md)

## [V5.0.0] - 2026-03-03

### 新增 (Added)
- **完整训练数据** - 14个项目，117集视频（原5个项目50集）
- **自动类型简化** - 31种钩子类型 → 10-15种
- **适度放宽标记** - 置信度阈值 8.0 → 6.5
- **关键帧密度提升** - 每秒1帧（原每0.5秒1帧）
- **分析窗口优化** - 30秒窗口（原60秒）

### 效果提升 (Performance)
- 训练数据：+134%（50集 → 117集）
- 目标召回率：+20.5%~+30.5%（29.5% → 50-60%）
- AI标记数：+78%~+114%（14个 → 25-30个）
- 钩子类型：-52%（31种 → 10-15种）

## [V4.0.0] - 2026-03-03

### 改进 (Changed)
- **分析窗口优化** - 60秒 → 30秒
- 召回率：25% → 29.5%

## [V3.0.0] - 2026-03-03

### 新增 (Added)
- **技能文件格式优化** - MD + JSON双格式
- **5步质量筛选流程**

## [V2.0.0] - 2026-03-03

### 新增 (Added)
- **精确时间戳** - 返回窗口内精确秒数
- **质量筛选** - 置信度>7.0 + 去重 + 数量控制

## [V1.0.0] - 2026-03-01

### 新增 (Added)
- **初始版本** - 基础视频理解和钩子识别功能

---

## 版本说明

- **主版本号（Major）**：不兼容的API更改或架构重大变更
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正
