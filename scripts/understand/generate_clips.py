"""
生成剪辑组合模块
根据高光点/钩子点生成剪辑片段（笛卡尔积）
V13: 支持ASR辅助的时间戳精度优化（毫秒级）
"""
import json
from typing import List, Dict, Union
from dataclasses import dataclass

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
    asr_segments: List[ASRSegment] = None,
    enable_timestamp_optimization: bool = True,
    video_path: str = None,
    video_fps: float = 30.0
) -> List[Clip]:
    """生成剪辑组合（笛卡尔积）

    每个高光点 × 每个钩子点 = 所有可能的组合
    支持跨集组合，使用累积时长计算
    V13: 支持ASR辅助的时间戳精度优化（毫秒级）
    V15.2: 支持智能多维度切割点查找（帧级精度）

    Args:
        analyses: 所有分析结果
        episode_durations: 各集时长字典 {集数: 时长秒数}
        min_duration: 最短时长（秒）
        max_duration: 最长时长（秒）
        dedup_window: 去重时间窗口（秒）
        asr_segments: ASR语音识别数据（用于时间戳优化，可选）
        enable_timestamp_optimization: 是否启用时间戳优化（默认True）
        video_path: 视频文件路径（用于V15.2智能切割）
        video_fps: 视频帧率（用于V15.2智能切割）

    Returns:
        剪辑组合列表
    """
    # 分离高光点和钩子点
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]

    print(f"原始高光点: {len(highlights)}, 钩子点: {len(hooks)}")

    # V13: ASR辅助的时间戳优化（在去重之前进行优化）
    # V15.2: 支持智能多维度切割（需要传入视频路径和帧率）
    if enable_timestamp_optimization and asr_segments and TIMESTAMP_OPTIMIZATION_ENABLED:
        if video_path:
            print("\n[V15.2时间戳优化] 启用智能多维度切割点优化（帧级精度）...")
        else:
            print("\n[时间戳优化] 启用ASR辅助的毫秒级精度优化...")
        highlights, hooks = optimize_clips_timestamps(
            highlights=highlights,
            hooks=hooks,
            asr_segments=asr_segments,
            buffer_ms=100.0,  # 100ms缓冲
            video_path=video_path,
            video_fps=video_fps
        )
    elif not asr_segments:
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
