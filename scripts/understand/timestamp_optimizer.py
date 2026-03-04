"""
时间戳优化模块 - 使用ASR数据优化时间戳精度
利用语音识别数据，智能调整高光点和钩子点时间戳，确保话不被截断
"""
from typing import List, Tuple
from dataclasses import dataclass


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


def adjust_hook_point(hook_timestamp: float, asr_segments: List[ASRSegment], buffer_ms: float = 100.0) -> float:
    """
    调整钩子点时间戳，确保话已说完

    策略：找到包含钩子点或钩子点之后的第一个ASR片段，返回该片段结束时间+缓冲时间

    Args:
        hook_timestamp: AI标记的钩子点时间戳（秒）
        asr_segments: ASR语音识别数据列表
        buffer_ms: 缓冲时间（毫秒），默认100ms

    Returns:
        调整后的时间戳（秒，浮点数）
    """
    if not asr_segments:
        return float(hook_timestamp)

    # 查找包含钩子点或钩子点之后的ASR片段
    for segment in asr_segments:
        # 如果ASR片段开始时间在钩子点之后，或者钩子点在ASR片段内
        if segment.start > hook_timestamp or (segment.start <= hook_timestamp <= segment.end):
            # 找到该片段的结束时间
            adjusted_time = segment.end + (buffer_ms / 1000.0)
            print(f"  🔧 钩子点优化: {hook_timestamp}秒 → {adjusted_time:.3f}秒（+{buffer_ms}ms缓冲，ASR: '{segment.text[:20]}...'）")
            return adjusted_time

    # 如果没有找到合适的ASR片段，返回原时间戳
    print(f"  ⚠️  钩子点未找到ASR数据，保持原时间: {hook_timestamp}秒")
    return float(hook_timestamp)


def adjust_highlight_point(highlight_timestamp: float, asr_segments: List[ASRSegment], buffer_ms: float = 100.0) -> float:
    """
    调整高光点时间戳，确保话刚开始

    策略：找到包含高光点或高光点之前的最后一个ASR片段，返回该片段开始时间-缓冲时间

    Args:
        highlight_timestamp: AI标记的高光点时间戳（秒）
        asr_segments: ASR语音识别数据列表
        buffer_ms: 缓冲时间（毫秒），默认100ms

    Returns:
        调整后的时间戳（秒，浮点数）
    """
    if not asr_segments:
        return float(highlight_timestamp)

    # 查找包含高光点或高光点之前的ASR片段（逆序查找）
    for segment in reversed(asr_segments):
        # 如果ASR片段结束时间在高光点之前，或者高光点在ASR片段内
        if segment.end < highlight_timestamp or (segment.start <= highlight_timestamp <= segment.end):
            # 找到该片段的开始时间
            adjusted_time = segment.start - (buffer_ms / 1000.0)
            adjusted_time = max(0.0, adjusted_time)  # 确保不小于0
            print(f"  🔧 高光点优化: {highlight_timestamp}秒 → {adjusted_time:.3f}秒（-{buffer_ms}ms缓冲，ASR: '{segment.text[:20]}...'）")
            return adjusted_time

    # 如果没有找到合适的ASR片段，返回原时间戳
    print(f"  ⚠️  高光点未找到ASR数据，保持原时间: {highlight_timestamp}秒")
    return float(highlight_timestamp)


def optimize_clips_timestamps(
    highlights: List[SegmentAnalysis],
    hooks: List[SegmentAnalysis],
    asr_segments: List[ASRSegment],
    buffer_ms: float = 100.0
) -> Tuple[List[SegmentAnalysis], List[SegmentAnalysis]]:
    """
    使用ASR数据优化所有时间戳

    Args:
        highlights: 高光点列表
        hooks: 钩子点列表
        asr_segments: ASR语音识别数据列表
        buffer_ms: 缓冲时间（毫秒），默认100ms

    Returns:
        优化后的高光点和钩子点列表
    """
    print("\n" + "=" * 80)
    print("开始ASR辅助时间戳优化（毫秒级精度）")
    print("=" * 80)
    print(f"缓冲时间: {buffer_ms}ms")
    print(f"ASR片段数: {len(asr_segments)}")

    # 优化钩子点
    print(f"\n优化 {len(hooks)} 个钩子点...")
    for hook in hooks:
        original_time = hook.hook_timestamp
        hook.hook_timestamp = adjust_hook_point(
            hook.hook_timestamp,
            asr_segments,
            buffer_ms
        )

    # 优化高光点
    print(f"\n优化 {len(highlights)} 个高光点...")
    for hl in highlights:
        original_time = hl.highlight_timestamp
        hl.highlight_timestamp = adjust_highlight_point(
            hl.highlight_timestamp,
            asr_segments,
            buffer_ms
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
