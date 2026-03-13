"""
时间戳优化模块 - 使用ASR数据优化时间戳精度
利用语音识别数据，智能调整高光点和钩子点时间戳，确保话不被截断

V15.3 更新：
- 高光点优化：添加智能算法，找到整句话的开始时间
- 帧级精度：高光点和钩子点都使用帧级精度
- 解决高光点从"一句话中间"开始的问题
"""
from typing import List, Tuple, Optional, Dict, Union
from dataclasses import dataclass


# V15.2: 导入智能切割查找模块
try:
    from scripts.understand.smart_cut_finder import (
        smart_adjust_hook_point,
        smart_adjust_highlight_point,
        SmartCutFinder
    )
    SMART_CUT_ENABLED = True
except ImportError:
    SMART_CUT_ENABLED = False
    print("⚠️ 智能切割模块不可用，使用基础ASR优化")


try:
    from scripts.understand.analyze_segment import SegmentAnalysis
    from scripts.data_models import ASRSegment
except ImportError:
    @dataclass
    class SegmentAnalysis:
        episode: int
        highlight_timestamp: float
        hook_timestamp: float
        is_highlight: bool = False
        is_hook: bool = False

    @dataclass
    class ASRSegment:
        text: str
        start: float
        end: float
        episode: int = 1  # 默认为第1集


def adjust_hook_point(
    hook_timestamp: float,
    asr_segments: List[ASRSegment],
    episode: int = 1,  # 新增参数，默认为第1集
    buffer_ms: float = 100.0,
    video_path: Optional[str] = None,
    video_fps: float = 30.0,
    max_duration: Optional[float] = None  # V15.4: 新增最大时长限制
) -> float:
    """
    调整钩子点时间戳，确保话已说完

    V15.2 策略：
    - 如果提供视频路径和帧率，使用智能多维度切割算法
    - 否则使用基础ASR优化（找到包含钩子点的第一个片段）

    V15.4 更新：
    - 新增 max_duration 参数，确保优化后的时间戳不超过视频有效时长

    Args:
        hook_timestamp: AI标记的钩子点时间戳（秒）
        asr_segments: ASR语音识别数据列表（所有集）
        episode: 目标集数，默认为1
        buffer_ms: 缓冲时间（毫秒），默认100ms（仅在基础模式使用）
        video_path: 视频文件路径（可选，用于智能切割）
        video_fps: 视频帧率（可选，默认30fps）
        max_duration: V15.4新增 - 该集的最大有效时长（秒），优化结果不会超过此值

    Returns:
        调整后的时间戳（秒，浮点数）
    """
    # 筛选目标episode的ASR
    target_asr = [seg for seg in asr_segments if seg.episode == episode]

    if not target_asr:
        print(f"  ⚠️ 第{episode}集无ASR数据，跳过优化")
        return float(hook_timestamp)

    print(f"  🎯 优化第{episode}集钩子点 {hook_timestamp}秒，使用{len(target_asr)}个ASR片段")

    # V15.2: 优先使用智能切割算法
    if SMART_CUT_ENABLED and video_path:
        try:
            adjusted_time = smart_adjust_hook_point(
                hook_timestamp=hook_timestamp,
                asr_segments=target_asr,  # 使用筛选后的ASR
                video_path=video_path,
                video_fps=video_fps,
                search_window=2.0,
                max_duration=max_duration  # V15.4: 传递最大时长限制
            )
            print(f"  🔧 钩子点优化(V15.2智能): {hook_timestamp}秒 → {adjusted_time:.4f}秒")
            return adjusted_time
        except Exception as e:
            print(f"  ⚠️ 智能切割失败，回退到基础模式: {e}")

    # 基础模式：先检查钩子点是否落在某个 ASR 片段内
    # V18修复：gap 情况（钩子点在两段之间的间隙）应停在间隙处，不应包含下一句话
    buffer_seconds = buffer_ms / 1000.0
    for segment in target_asr:
        if segment.start <= hook_timestamp <= segment.end:
            # 钩子点在片段内：返回该片段结束时间
            adjusted_time = segment.end + buffer_seconds
            print(f"  🔧 钩子点优化(基础): {hook_timestamp}秒 → {adjusted_time:.3f}秒（片段内，ASR: '{segment.text[:20]}'）")
            return adjusted_time

    # gap 情况：钩子点在两段之间的静音间隙内，停在间隙处
    # 修复前的错误行为：取"下一个片段的 end"，把整句话都包含进去
    print(f"  🔧 钩子点优化(基础-gap): {hook_timestamp}秒 → {hook_timestamp + buffer_seconds:.3f}秒（在间隙内停止）")
    return hook_timestamp + buffer_seconds


def adjust_highlight_point(
    highlight_timestamp: float,
    asr_segments: List[ASRSegment],
    episode: int = 1,  # 新增参数，默认为第1集
    buffer_ms: float = 100.0,
    video_path: Optional[str] = None,
    video_fps: float = 30.0
) -> float:
    """
    调整高光点时间戳，确保话刚开始

    V15.3 策略：
    - 如果提供视频路径和帧率，使用智能算法找到整句话的开始
    - 否则使用基础ASR优化（找到包含高光点的第一个片段）

    Args:
        highlight_timestamp: AI标记的高光点时间戳（秒）
        asr_segments: ASR语音识别数据列表（所有集）
        episode: 目标集数，默认为1
        buffer_ms: 缓冲时间（毫秒），默认100ms
        video_path: 视频文件路径（可选，用于智能优化）
        video_fps: 视频帧率（可选，默认30fps）

    Returns:
        调整后的时间戳（秒，帧级精度）
    """
    # 筛选目标episode的ASR
    target_asr = [seg for seg in asr_segments if seg.episode == episode]

    if not target_asr:
        print(f"  ⚠️ 第{episode}集无ASR数据，跳过优化")
        return float(highlight_timestamp)

    print(f"  🎯 优化第{episode}集高光点 {highlight_timestamp}秒，使用{len(target_asr)}个ASR片段")

    # V15.3: 优先使用智能算法
    if SMART_CUT_ENABLED and video_path:
        try:
            adjusted_time = smart_adjust_highlight_point(
                highlight_timestamp=highlight_timestamp,
                asr_segments=target_asr,  # 使用筛选后的ASR
                video_path=video_path,
                video_fps=video_fps,
                buffer_ms=buffer_ms
            )
            print(f"  🔧 高光点优化(V15.3智能): {highlight_timestamp}秒 → {adjusted_time:.4f}秒")
            return adjusted_time
        except Exception as e:
            print(f"  ⚠️ 智能优化失败，回退到基础模式: {e}")

    # 基础模式：找到包含高光点的ASR片段，返回该片段开始时间-缓冲
    for segment in reversed(target_asr):  # 使用筛选后的ASR
        if segment.end < highlight_timestamp or (segment.start <= highlight_timestamp <= segment.end):
            adjusted_time = segment.start - (buffer_ms / 1000.0)
            adjusted_time = max(0.0, adjusted_time)
            print(f"  🔧 高光点优化(基础): {highlight_timestamp}秒 → {adjusted_time:.3f}秒（-{buffer_ms}ms缓冲，ASR: '{segment.text[:20]}...'）")
            return adjusted_time

    print(f"  ⚠️  高光点未找到ASR数据，保持原时间: {highlight_timestamp}秒")
    return float(highlight_timestamp)


def optimize_clips_timestamps(
    highlights: List[SegmentAnalysis],
    hooks: List[SegmentAnalysis],
    episode_asr_dict: Dict[int, List[ASRSegment]],  # 新增参数：按集分组的ASR字典
    buffer_ms: float = 100.0,
    video_path: Optional[str] = None,
    video_fps: float = 30.0,
    episode_durations: Optional[Dict[int, Union[int, float]]] = None  # V15.4: 新增各集时长限制
) -> Tuple[List[SegmentAnalysis], List[SegmentAnalysis]]:
    """
    使用ASR数据优化所有时间戳

    V15.2 更新：
    - 支持传入视频路径和帧率，启用智能多维度切割算法

    V15.4 更新：
    - 新增 episode_durations 参数，限制钩子点不超过该集总时长

    Args:
        highlights: 高光点列表
        hooks: 钩子点列表
        episode_asr_dict: 按集分组的ASR数据字典 {episode: [ASRSegment]}
        buffer_ms: 缓冲时间（毫秒），默认100ms
        video_path: 视频文件路径（可选，用于智能切割）
        video_fps: 视频帧率（可选，默认30fps）
        episode_durations: V15.4新增 - 各集时长字典 {集数: 时长秒数}，用于限制钩子点最大时间

    Returns:
        优化后的高光点和钩子点列表
    """
    print("\n" + "=" * 80)
    if SMART_CUT_ENABLED and video_path:
        print(f"开始V15.4智能时间戳优化（帧级精度 + 时长限制）")
    else:
        print("开始ASR辅助时间戳优化（毫秒级精度）")
    print("=" * 80)
    print(f"缓冲时间: {buffer_ms}ms")

    # 统计ASR数据
    total_asr_count = sum(len(asr_list) for asr_list in episode_asr_dict.values())
    print(f"ASR片段数: {total_asr_count} (分布在 {len(episode_asr_dict)} 集中)")
    for ep, asr_list in sorted(episode_asr_dict.items()):
        print(f"  - 第{ep}集: {len(asr_list)}个片段")

    if video_path:
        print(f"视频路径: {video_path}")
        print(f"视频帧率: {video_fps}fps")

    # V15.4: 打印时长限制信息
    if episode_durations:
        print(f"时长限制: 已提供 {len(episode_durations)} 集的时长信息")

    # 优化钩子点
    print(f"\n优化 {len(hooks)} 个钩子点...")
    for hook in hooks:
        original_time = hook.hook_timestamp
        # 获取该钩子点所在集的ASR数据
        episode_asr = episode_asr_dict.get(hook.episode, [])
        if not episode_asr:
            print(f"  ⚠️ 钩子点(第{hook.episode}集)无ASR数据，跳过优化")
            continue

        # V15.4: 获取该集的最大时长限制
        max_duration = None
        if episode_durations:
            max_duration = float(episode_durations.get(hook.episode, 0))
            if max_duration > 0:
                print(f"  📏 第{hook.episode}集最大时长限制: {max_duration:.3f}秒")

        hook.hook_timestamp = adjust_hook_point(
            hook.hook_timestamp,
            episode_asr,  # 传入所有ASR，函数内部会筛选
            hook.episode,  # 传入集数
            buffer_ms,
            video_path,
            video_fps,
            max_duration=max_duration  # V15.4: 传入该集的最大时长限制
        )

    # 优化高光点
    print(f"\n优化 {len(highlights)} 个高光点...")
    for hl in highlights:
        original_time = hl.highlight_timestamp
        # 获取该高光点所在集的ASR数据
        episode_asr = episode_asr_dict.get(hl.episode, [])
        if not episode_asr:
            print(f"  ⚠️ 高光点(第{hl.episode}集)无ASR数据，跳过优化")
            continue

        hl.highlight_timestamp = adjust_highlight_point(
            hl.highlight_timestamp,
            episode_asr,  # 传入所有ASR，函数内部会筛选
            hl.episode,  # 传入集数
            buffer_ms,
            video_path,
            video_fps
        )

    print("\n" + "=" * 80)
    print("时间戳优化完成！")
    print("=" * 80)

    return highlights, hooks


def optimize_single_timestamp(
    timestamp: float,
    point_type: str,  # 'highlight' 或 'hook'
    asr_segments: List[ASRSegment],
    buffer_ms: float = 100.0
) -> float:
    """
    优化单个时间戳

    Args:
        timestamp: 原始时间戳（秒）
        point_type: 类型（'highlight' 或 'hook'）
        asr_segments: ASR语音识别数据列表
        buffer_ms: 缓冲时间（毫秒）

    Returns:
        优化后的时间戳（秒）
    """
    if point_type == 'hook':
        return adjust_hook_point(timestamp, asr_segments, buffer_ms)
    elif point_type == 'highlight':
        return adjust_highlight_point(timestamp, asr_segments, buffer_ms)
    else:
        return timestamp
