"""
生成剪辑组合模块
根据高光点/钩子点生成剪辑片段（笛卡尔积）
V13: 支持ASR辅助的时间戳精度优化（毫秒级）
V17: 添加剪辑组合排序与智能筛选（Top N 精选）
"""
import json
from typing import List, Dict, Union, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    from scripts.understand.analyze_segment import SegmentAnalysis
    from scripts.data_models import ASRSegment
except ImportError:
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class ASRSegment:
        text: str
        start: float
        end: float

    @dataclass
    class SegmentAnalysis:
        episode: int
        start_time: int
        end_time: int
        is_highlight: bool
        highlight_timestamp: Union[int, float] = 0  # V13: 支持毫秒精度
        highlight_type: Optional[str] = None
        highlight_desc: str = ""
        highlight_confidence: float = 0.0
        is_hook: bool = False
        hook_timestamp: Union[int, float] = 0  # V13: 支持毫秒精度
        hook_type: Optional[str] = None
        hook_desc: str = ""
        hook_confidence: float = 0.0


# 配置参数
MIN_CLIP_DURATION = 120   # 最短2分钟(120秒)
MAX_CLIP_DURATION = 720  # 最长12分钟(720秒)
DEDUP_WINDOW = 5  # 同集内去重时间窗口（秒）

# V13: 导入时间戳优化模块
try:
    from scripts.understand.timestamp_optimizer import optimize_clips_timestamps
    TIMESTAMP_OPTIMIZATION_ENABLED = True
except ImportError:
    TIMESTAMP_OPTIMIZATION_ENABLED = False
    print("警告: 时间戳优化模块不可用，将使用原始时间戳")


@dataclass
class Clip:
    """剪辑组合"""
    start: Union[int, float]           # 起始累积秒（相对于第1集开头）V13: 支持浮点数
    end: Union[int, float]           # 结束累积秒（相对于第1集开头）V13: 支持浮点数
    duration: Union[int, float]      # 时长（秒）V13: 支持浮点数
    highlight_type: str  # 高光类型
    highlight_desc: str  # 高光描述
    hook_type: str      # 钩子类型
    hook_desc: str      # 钩子描述
    episode: int        # 起始集数
    hook_episode: int   # 结束集数

    @property
    def clip_type(self) -> str:
        return f"{self.highlight_type}-{self.hook_type}"

    def to_dict(self) -> dict:
        return {
            "start": int(self.start) if isinstance(self.start, int) or self.start.is_integer() else round(self.start, 3),
            "end": int(self.end) if isinstance(self.end, int) or self.end.is_integer() else round(self.end, 3),
            "duration": int(self.duration) if isinstance(self.duration, int) or self.duration.is_integer() else round(self.duration, 3),
            "highlight": self.highlight_type,
            "highlightDesc": self.highlight_desc,
            "hook": self.hook_type,
            "hookDesc": self.hook_desc,
            "type": self.clip_type,
            "episode": self.episode,
            "hookEpisode": self.hook_episode
        }


def calculate_cumulative_duration(
    episode: int,
    timestamp: Union[int, float],
    episode_durations: Dict[int, int]
) -> float:
    """计算累积时长(跨集)

    将(集数, 时间戳)转换为从第1集开头开始的绝对秒数
    V13: 支持毫秒精度（浮点数时间戳）

    Args:
        episode: 集数
        timestamp: 该集内的时间戳（秒，支持浮点数）
        episode_durations: 各集时长字典 {集数: 时长秒数}

    Returns:
        从第1集0秒开始的累积秒数（浮点数）
    """
    cumulative = 0.0
    for ep in sorted(episode_durations.keys()):
        if ep < episode:
            cumulative += float(episode_durations[ep])
    cumulative += float(timestamp)
    return cumulative


def deduplicate_highlights(highlights: List[SegmentAnalysis], window: int = DEDUP_WINDOW) -> List[SegmentAnalysis]:
    """去重高光点(同集内去重)

    同一集内,同一类型在时间窗口内只保留第一个

    Args:
        highlights: 高光点列表
        window: 去重时间窗口（秒）

    Returns:
        去重后的高光点
    """
    if not highlights:
        return []

    # 按集数、类型和精确时间戳排序
    sorted_hl = sorted(highlights, key=lambda x: (x.episode, x.highlight_type or "", x.highlight_timestamp))

    result = []
    last_by_ep_type = {}  # {(集数, 类型): 时间戳}

    for hl in sorted_hl:
        hl_type = hl.highlight_type or ""
        key = (hl.episode, hl_type)
        last_time = last_by_ep_type.get(key, -999)

        if hl.highlight_timestamp - last_time >= window:
            result.append(hl)
            last_by_ep_type[key] = hl.highlight_timestamp

    return result


def deduplicate_hooks(hooks: List[SegmentAnalysis], window: int = DEDUP_WINDOW) -> List[SegmentAnalysis]:
    """去重钩子点(同集内去重)

    同一集内,同一类型在时间窗口内只保留第一个

    Args:
        hooks: 钩子点列表
        window: 去重时间窗口（秒）

    Returns:
        去重后的钩子点
    """
    if not hooks:
        return []

    # 按集数、类型和精确时间戳排序
    sorted_hooks = sorted(hooks, key=lambda x: (x.episode, x.hook_type or "", x.hook_timestamp))

    result = []
    last_by_ep_type = {}  # {(集数, 类型): 时间戳}

    for hook in sorted_hooks:
        hook_type = hook.hook_type or ""
        key = (hook.episode, hook_type)
        last_time = last_by_ep_type.get(key, -999)

        if hook.hook_timestamp - last_time >= window:
            result.append(hook)
            last_by_ep_type[key] = hook.hook_timestamp

    return result


def generate_clips(
    analyses: List[SegmentAnalysis],
    episode_durations: Dict[int, int],
    min_duration: int = MIN_CLIP_DURATION,
    max_duration: int = MAX_CLIP_DURATION,
    dedup_window: int = DEDUP_WINDOW,
    episode_asr: Dict[int, List[ASRSegment]] = None,  # V13时间戳修复: 按集分组的ASR字典
    enable_timestamp_optimization: bool = True,
    video_path: str = None,  # 兼容旧调用，仅在 episode_video_paths 未提供时使用
    video_fps: float = 30.0,
    episode_video_paths: Dict[int, str] = None,  # BugFix: 每集对应视频路径
) -> List[Clip]:
    """生成剪辑组合（笛卡尔积）

    每个高光点 × 每个钩子点 = 所有可能的组合
    支持跨集组合，使用累积时长计算
    V13: 支持ASR辅助的时间戳精度优化（毫秒级）
    V15.2: 支持智能多维度切割点查找（帧级精度）
    V13时间戳修复: 使用按集分组的ASR数据，避免跨集查找

    Args:
        analyses: 所有分析结果
        episode_durations: 各集时长字典 {集数: 时长秒数}
        min_duration: 最短时长（秒）
        max_duration: 最长时长（秒）
        dedup_window: 去重时间窗口（秒）
        episode_asr: 按集分组的ASR数据字典 {集数: [ASRSegment...]}（V13时间戳修复）
        enable_timestamp_optimization: 是否启用时间戳优化（默认True）
        video_path: 视频文件路径（旧接口，兼容用，优先使用 episode_video_paths）
        video_fps: 视频帧率（用于V15.2智能切割）
        episode_video_paths: BugFix - 每集对应视频路径 {集数: 路径}，用于正确的静音检测

    Returns:
        剪辑组合列表
    """
    # 分离高光点和钩子点
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]

    print(f"原始高光点: {len(highlights)}, 钩子点: {len(hooks)}")

    # V13: ASR辅助的时间戳优化（在去重之前进行优化）
    # V15.2: 支持智能多维度切割（需要传入视频路径和帧率）
    # V13时间戳修复: 传入episode_asr字典而不是平铺的asr_segments
    # V15.4: 传入episode_durations限制钩子点最大时长
    # BugFix: 优先使用 episode_video_paths；若未提供，降级为单路径兼容模式
    effective_video_paths = episode_video_paths or ({1: video_path} if video_path else None)

    if enable_timestamp_optimization and episode_asr and TIMESTAMP_OPTIMIZATION_ENABLED:
        if effective_video_paths:
            print("\n[V15.4时间戳优化] 启用智能多维度切割点优化（帧级精度 + 时长限制）...")
        else:
            print("\n[时间戳优化] 启用ASR辅助的毫秒级精度优化...")
        highlights, hooks = optimize_clips_timestamps(
            highlights=highlights,
            hooks=hooks,
            episode_asr_dict=episode_asr,  # V13时间戳修复: 传入按集分组的ASR字典
            buffer_ms=100.0,  # 100ms缓冲
            episode_video_paths=effective_video_paths,  # BugFix: 每集对应视频路径
            video_fps=video_fps,
            episode_durations=episode_durations  # V15.4: 传入各集时长限制
        )
    elif not episode_asr:
        print("\n[时间戳优化] 未提供ASR数据，跳过优化（使用原始秒级时间戳）")
    elif not TIMESTAMP_OPTIMIZATION_ENABLED:
        print("\n[时间戳优化] 时间戳优化模块未加载，跳过优化")

    # 去重（同集内）
    highlights = deduplicate_highlights(highlights, dedup_window)
    hooks = deduplicate_hooks(hooks, dedup_window)

    print(f"去重后高光点: {len(highlights)}, 钩子点: {len(hooks)}")

    # 按累积时间排序
    highlights_with_cumulative = []
    for hl in highlights:
        cum = calculate_cumulative_duration(hl.episode, hl.highlight_timestamp, episode_durations)
        highlights_with_cumulative.append((hl, cum))

    hooks_with_cumulative = []
    for hook in hooks:
        cum = calculate_cumulative_duration(hook.episode, hook.hook_timestamp, episode_durations)
        hooks_with_cumulative.append((hook, cum))

    # 按累积时间排序
    highlights_with_cumulative.sort(key=lambda x: x[1])
    hooks_with_cumulative.sort(key=lambda x: x[1])

    clips = []
    total_combinations = len(highlights) * len(hooks)
    valid_count = 0

    print(f"\n开始生成剪辑组合（笛卡尔积: {len(highlights)} × {len(hooks)} = {total_combinations}种组合）...")

    # 生成笛卡尔积: 每个高光点 × 每个钩子点
    for hl, hl_cumulative in highlights_with_cumulative:
        for hook, hook_cumulative in hooks_with_cumulative:

            # 计算时长（使用累积时间）
            duration = hook_cumulative - hl_cumulative

            # 检查时长范围
            if min_duration <= duration <= max_duration:
                clip = Clip(
                    start=hl_cumulative,
                    end=hook_cumulative,
                    duration=duration,
                    highlight_type=hl.highlight_type or "未知",
                    highlight_desc=hl.highlight_desc,
                    hook_type=hook.hook_type or "未知",
                    hook_desc=hook.hook_desc,
                    episode=hl.episode,
                    hook_episode=hook.episode
                )
                clips.append(clip)
                valid_count += 1

                # 只打印前10个和后5个，避免刷屏
                if valid_count <= 10 or valid_count > total_combinations - 5:
                    if hl.episode == hook.episode:
                        print(f"  [{valid_count}] 第{hl.episode}集 {hl.highlight_timestamp}s → 第{hook.episode}集 {hook.hook_timestamp}s = {duration}s [{clip.clip_type}]")
                    else:
                        print(f"  [{valid_count}] 第{hl.episode}集{hl.highlight_timestamp}s → 第{hook.episode}集{hook.hook_timestamp}s = {duration}s (跨集) [{clip.clip_type}]")
                elif valid_count == 11:
                    print(f"  ... (省略中间{total_combinations - 15}个组合)")

    # 按起始时间和集数排序
    clips = sorted(clips, key=lambda x: (x.start, x.episode))

    # V13.1: 修复除以0错误，当没有高光点或钩子点时
    if total_combinations == 0:
        print(f"\n⚠️  无法生成剪辑组合：高光点={len(highlights)}, 钩子点={len(hooks)}")
        print(f"      需要至少1个高光点和1个钩子点才能生成剪辑")
        return clips

    print(f"\n✅ 共生成 {len(clips)} 个有效剪辑组合（共检查{total_combinations}种组合，有效率{len(clips)/total_combinations*100:.1f}%）")

    return clips


def save_clips(clips: List[Clip], output_path: str):
    """保存剪辑组合到文件

    Args:
        clips: 剪辑列表
        output_path: 输出路径
    """
    result = {
        "clips": [clip.to_dict() for clip in clips],
        "totalClips": len(clips)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"剪辑组合已保存: {output_path}")


if __name__ == "__main__":
    print("generate_clips 模块已加载")
    print(f"最短剪辑: {MIN_CLIP_DURATION}秒")
    print(f"最长剪辑: {MAX_CLIP_DURATION}秒")
    print(f"去重窗口: {DEDUP_WINDOW}秒 (同集内)")
    print("支持: 跨集笛卡尔积组合")
    print("支持: V17 剪辑组合排序与智能筛选")


# =============================================================================
# V17: 剪辑组合排序与智能筛选
# =============================================================================

# 配置参数
TOP_HIGHLIGHTS = 10       # 参与组合的高光数量
TOP_HOOKS = 10            # 参与组合的钩子数量
MAX_CLIPS_OUTPUT = 20    # 最终输出数量
MIN_CLIPS_OUTPUT = 10    # 最少输出数量

# 组合质量权重
COMBO_WEIGHT_HL = 0.4    # 高光权重（钩子更重要，决定用户是否看完）
COMBO_WEIGHT_HOOK = 0.6  # 钩子权重

# 置信度归一化权重
CONF_WEIGHT = 0.4         # 置信度权重
TYPE_WEIGHT = 0.3         # 类型权重
TIMING_WEIGHT = 0.2       # 时机权重
DESC_WEIGHT = 0.1         # 描述详细程度权重

# 类型强度排序（越靠前越能吸引观众）
HIGHLIGHT_TYPE_STRENGTH = {
    '反转': 10,
    '打脸': 9,
    '冲突': 8,
    '爽点': 7,
    '情感': 6,
    '搞笑': 5,
    '悬念': 4,
    '日常': 3,
    '其他': 2,
    '未知': 1,
}

HOOK_TYPE_STRENGTH = {
    '反转': 10,
    '悬念': 9,
    '冲突': 8,
    '危机': 7,
    '情感': 6,
    '搞笑': 5,
    '日常': 4,
    '其他': 3,
    '未知': 2,
}


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """归一化分数到 0-1 范围

    Args:
        value: 原始分数
        min_val: 最小值
        max_val: 最大值

    Returns:
        归一化后的分数
    """
    if max_val <= min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def calculate_type_weight(hl_type: Optional[str], hook_type: Optional[str]) -> tuple:
    """计算类型权重

    Args:
        hl_type: 高光类型
        hook_type: 钩子类型

    Returns:
        (高光类型权重, 钩子类型权重)
    """
    hl_score = HIGHLIGHT_TYPE_STRENGTH.get(hl_type or '未知', 1)
    hook_score = HOOK_TYPE_STRENGTH.get(hook_type or '未知', 1)

    # 归一化到 0-1
    max_hl = max(HIGHLIGHT_TYPE_STRENGTH.values())
    max_hook = max(HOOK_TYPE_STRENGTH.values())

    return hl_score / max_hl, hook_score / max_hook


def calculate_timing_weight(
    hl_timestamp: float,
    hl_episode: int,
    hook_timestamp: float,
    hook_episode: int,
    episode_durations: Dict[int, int]
) -> tuple:
    """计算时机权重

    高光：在集前/集中越好（能吸引观众看下去）
    钩子：在集末越好（观众想看后续）

    Args:
        hl_timestamp: 高光时间戳
        hl_episode: 高光集数
        hook_timestamp: 钩子时间戳
        hook_episode: 钩子集数
        episode_durations: 各集时长

    Returns:
        (高光时机权重, 钩子时机权重)
    """
    # 高光时机：集的前30%给予加分
    ep_duration = episode_durations.get(hl_episode, 180)
    hl_position = hl_timestamp / ep_duration  # 0=开头, 1=结尾
    hl_timing = 1.0 - hl_position * 0.5  # 越靠前分数越高

    # 钩子时机：集的末尾30%给予加分
    ep_duration = episode_durations.get(hook_episode, 180)
    hook_position = hook_timestamp / ep_duration
    hook_timing = hook_position * 0.5 + 0.5  # 越靠后分数越高

    return hl_timing, hook_timing


def calculate_desc_weight(desc: str) -> float:
    """计算描述详细程度权重

    描述越详细越可信

    Args:
        desc: 描述文本

    Returns:
        详细程度分数 (0-1)
    """
    if not desc or len(desc) < 5:
        return 0.2
    if len(desc) < 20:
        return 0.5
    if len(desc) < 50:
        return 0.8
    return 1.0


def calculate_combo_score(
    highlight: 'SegmentAnalysis',
    hook: 'SegmentAnalysis',
    episode_durations: Dict[int, int],
    hl_confidence_range: tuple,
    hook_confidence_range: tuple
) -> float:
    """计算组合质量分数

    综合多维度计算高光×钩子的组合质量

    Args:
        highlight: 高光点分析结果
        hook: 钩子点分析结果
        episode_durations: 各集时长
        hl_confidence_range: (min, max) 高光置信度范围
        hook_confidence_range: (min, max) 钩子置信度范围

    Returns:
        组合质量分数 (0-1)
    """
    # 1. 归一化置信度
    hl_conf_norm = normalize_score(
        highlight.highlight_confidence,
        hl_confidence_range[0],
        hl_confidence_range[1]
    )
    hook_conf_norm = normalize_score(
        hook.hook_confidence,
        hook_confidence_range[0],
        hook_confidence_range[1]
    )

    # 2. 类型权重
    hl_type_weight, hook_type_weight = calculate_type_weight(
        highlight.highlight_type,
        hook.hook_type
    )

    # 3. 时机权重
    hl_timing_weight, hook_timing_weight = calculate_timing_weight(
        highlight.highlight_timestamp,
        highlight.episode,
        hook.hook_timestamp,
        hook.episode,
        episode_durations
    )

    # 4. 描述详细程度
    hl_desc_weight = calculate_desc_weight(highlight.highlight_desc)
    hook_desc_weight = calculate_desc_weight(hook.hook_desc)

    # 5. 综合分数计算
    hl_score = (
        hl_conf_norm * CONF_WEIGHT +
        hl_type_weight * TYPE_WEIGHT +
        hl_timing_weight * TIMING_WEIGHT +
        hl_desc_weight * DESC_WEIGHT
    )

    hook_score = (
        hook_conf_norm * CONF_WEIGHT +
        hook_type_weight * TYPE_WEIGHT +
        hook_timing_weight * TIMING_WEIGHT +
        hook_desc_weight * DESC_WEIGHT
    )

    # 6. 组合分数（钩子权重更高）
    combo_score = hl_score * COMBO_WEIGHT_HL + hook_score * COMBO_WEIGHT_HOOK

    return combo_score


def sort_and_filter_clips(
    highlights: List['SegmentAnalysis'],
    hooks: List['SegmentAnalysis'],
    episode_durations: Dict[int, int],
    max_output: int = MAX_CLIPS_OUTPUT,
    min_output: int = MIN_CLIPS_OUTPUT,
    top_highlights: int = TOP_HIGHLIGHTS,
    top_hooks: int = TOP_HOOKS,
    max_same_type: int = 2,
    max_same_episode: int = 2
) -> List['Clip']:
    """剪辑组合排序与智能筛选 (V17)

    核心思路：
    1. 高光按综合质量取 Top N
    2. 钩子按综合质量取 Top N
    3. 生成组合后按组合质量排序
    4. 取 Top M，兼顾类型和集数多样性

    Args:
        highlights: 所有高光点
        hooks: 所有钩子点
        episode_durations: 各集时长
        max_output: 最大输出数量
        min_output: 最小输出数量
        top_highlights: 参与组合的高光数量
        top_hooks: 参与组合的钩子数量
        max_same_type: 同类型最多保留数
        max_same_episode: 同集最多保留数

    Returns:
        排序并筛选后的剪辑组合列表
    """
    if not highlights or not hooks:
        print("  ⚠️ 高光点或钩子点为空，跳过排序筛选")
        return []

    print(f"\n{'='*60}")
    print("V17 剪辑组合排序与智能筛选")
    print(f"{'='*60}")

    # 步骤1: 计算置信度范围（用于归一化）
    hl_confidences = [h.highlight_confidence for h in highlights]
    hook_confidences = [h.hook_confidence for h in hooks]
    hl_conf_range = (min(hl_confidences), max(hl_confidences))
    hook_conf_range = (min(hook_confidences), max(hook_confidences))

    print(f"  高光置信度范围: {hl_conf_range[0]:.1f} - {hl_conf_range[1]:.1f}")
    print(f"  钩子置信度范围: {hook_conf_range[0]:.1f} - {hook_conf_range[1]:.1f}")

    # 步骤2: 为每个高光点计算综合分数
    for hl in highlights:
        hl_type_w, _ = calculate_type_weight(hl.highlight_type, None)
        hl_timing_w, _ = calculate_timing_weight(
            hl.highlight_timestamp, hl.episode, 0, 0, episode_durations
        )
        hl_desc_w = calculate_desc_weight(hl.highlight_desc)

        # 综合分数
        hl_conf_norm = normalize_score(hl.highlight_confidence, hl_conf_range[0], hl_conf_range[1])
        hl.quality_score = (
            hl_conf_norm * CONF_WEIGHT +
            hl_type_w * TYPE_WEIGHT +
            hl_timing_w * TIMING_WEIGHT +
            hl_desc_w * DESC_WEIGHT
        )

    # 步骤3: 为每个钩子点计算综合分数
    for hook in hooks:
        _, hook_type_w = calculate_type_weight(None, hook.hook_type)
        _, hook_timing_w = calculate_timing_weight(
            0, 0, hook.hook_timestamp, hook.episode, episode_durations
        )
        hook_desc_w = calculate_desc_weight(hook.hook_desc)

        hook_conf_norm = normalize_score(hook.hook_confidence, hook_conf_range[0], hook_conf_range[1])
        hook.quality_score = (
            hook_conf_norm * CONF_WEIGHT +
            hook_type_w * TYPE_WEIGHT +
            hook_timing_w * TIMING_WEIGHT +
            hook_desc_w * DESC_WEIGHT
        )

    # 步骤4: 按综合质量排序，取 Top N
    sorted_hl = sorted(highlights, key=lambda x: x.quality_score, reverse=True)[:top_highlights]
    sorted_hooks = sorted(hooks, key=lambda x: x.quality_score, reverse=True)[:top_hooks]

    print(f"  筛选后: {len(sorted_hl)} 个高光 × {len(sorted_hooks)} 个钩子")

    # 步骤5: 生成所有组合并计算组合质量分数
    temp_clips = []
    for hl in sorted_hl:
        for hook in sorted_hooks:
            # 计算时长（使用累积时间）
            hl_cumulative = calculate_cumulative_duration(
                hl.episode, hl.highlight_timestamp, episode_durations
            )
            hook_cumulative = calculate_cumulative_duration(
                hook.episode, hook.hook_timestamp, episode_durations
            )

            duration = hook_cumulative - hl_cumulative

            # 检查时长范围
            if MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION:
                combo_score = calculate_combo_score(
                    hl, hook, episode_durations, hl_conf_range, hook_conf_range
                )

                temp_clips.append({
                    'hl': hl,
                    'hook': hook,
                    'start': hl_cumulative,
                    'end': hook_cumulative,
                    'duration': duration,
                    'combo_score': combo_score
                })

    print(f"  时长筛选后: {len(temp_clips)} 个有效组合")

    if not temp_clips:
        print("  ⚠️ 没有满足时长要求的组合")
        return []

    # 步骤6: 按组合质量分数排序
    temp_clips.sort(key=lambda x: x['combo_score'], reverse=True)

    # 步骤7: 兼顾多样性（类型和集数分布）
    final_clips = []
    type_count = defaultdict(int)
    ep_count = defaultdict(int)

    for clip in temp_clips:
        hl = clip['hl']
        hook = clip['hook']

        # 检查类型多样性
        clip_type = f"{hl.highlight_type}-{hook.hook_type}"
        if type_count[clip_type] >= max_same_type:
            continue

        # 检查集数多样性
        ep_key = f"{hl.episode}-{hook.episode}"
        if ep_count[ep_key] >= max_same_episode:
            continue

        # 添加到最终结果
        final_clips.append(clip)
        type_count[clip_type] += 1
        ep_count[ep_key] += 1

        # 达到最大数量停止
        if len(final_clips) >= max_output:
            break

    # 如果多样性筛选后数量不足，补充高分组合
    if len(final_clips) < min_output:
        for clip in temp_clips:
            if clip in final_clips:
                continue
            final_clips.append(clip)
            if len(final_clips) >= min_output:
                break

    print(f"  多样性筛选后: {len(final_clips)} 个精选组合")

    # 步骤8: 转换为 Clip 对象
    result_clips = []
    for i, clip in enumerate(final_clips):
        hl = clip['hl']
        hook = clip['hook']

        result_clips.append(Clip(
            start=clip['start'],
            end=clip['end'],
            duration=clip['duration'],
            highlight_type=hl.highlight_type or "未知",
            highlight_desc=hl.highlight_desc,
            hook_type=hook.hook_type or "未知",
            hook_desc=hook.hook_desc,
            episode=hl.episode,
            hook_episode=hook.episode
        ))

    # 打印 Top 5 详情
    print(f"\n  Top 5 组合预览:")
    for i, c in enumerate(result_clips[:5]):
        print(f"    [{i+1}] 第{c.episode}集{c.start:.0f}s → 第{c.hook_episode}集{c.end:.0f}s "
              f"时长{c.duration:.0f}s [{c.highlight_type} × {c.hook_type}]")

    print(f"\n✅ 排序筛选完成: {len(result_clips)} 个精选组合")
    print(f"{'='*60}\n")

    return result_clips
