"""
提取分析片段模块
将视频分成60秒一个的分析片段，包含关键帧和ASR
"""
import os
from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path

# 尝试导入
try:
    from scripts.config import TrainingConfig
    from scripts.dataclasses import KeyFrame, ASRSegment
except ImportError:
    @dataclass
    class KeyFrame:
        frame_path: str
        timestamp_ms: int
        
    @dataclass  
    class ASRSegment:
        text: str
        start: float
        end: float


# 配置参数
SEGMENT_DURATION = 30  # 片段时长（秒）- V4优化：缩小窗口提高精度
SEGMENT_OVERLAP = 5     # 重叠时长（秒）- V4优化：减少重叠
FRAMES_PER_SEGMENT = 5  # 每片段关键帧数


@dataclass
class VideoSegment:
    """视频分析片段"""
    episode: int           # 第几集
    start_time: int       # 起始秒
    end_time: int         # 结束秒
    keyframes: List[KeyFrame]    # 关键帧
    asr_segments: List[ASRSegment]  # ASR片段
    
    @property
    def duration(self) -> int:
        return self.end_time - self.start_time


def extract_segments_for_episode(
    episode: int,
    keyframes: List[KeyFrame],
    asr_segments: List[ASRSegment],
    video_duration: int,
    segment_duration: int = SEGMENT_DURATION,
    segment_overlap: int = SEGMENT_OVERLAP
) -> List[VideoSegment]:
    """为一个视频提取分析片段
    
    Args:
        episode: 集数
        keyframes: 关键帧列表
        asr_segments: ASR片段列表
        video_duration: 视频总时长（秒）
        segment_duration: 片段时长
        segment_overlap: 重叠时长
        
    Returns:
        片段列表
    """
    segments = []
    start = 0
    
    while start < video_duration:
        end = min(start + segment_duration, video_duration)
        
        # 筛选该时间段的关键帧
        segment_keyframes = [
            kf for kf in keyframes 
            if start * 1000 <= kf.timestamp_ms < end * 1000
        ]
        
        # 筛选该时间段的ASR
        segment_asr = [
            seg for seg in asr_segments
            if start < seg.end and seg.start < end
        ]
        
        segments.append(VideoSegment(
            episode=episode,
            start_time=start,
            end_time=end,
            keyframes=segment_keyframes,
            asr_segments=segment_asr
        ))
        
        # 移动到下一个片段（减去重叠时间）
        start = start + segment_duration - segment_overlap
    
    return segments


def extract_all_segments(
    episode_keyframes: dict[int, List[KeyFrame]],
    episode_asr: dict[int, List[ASRSegment]],
    episode_durations: dict[int, int]
) -> List[VideoSegment]:
    """提取所有集的分析片段
    
    Args:
        episode_keyframes: {集数: 关键帧列表}
        episode_asr: {集数: ASR列表}
        episode_durations: {集数: 时长(秒)}
        
    Returns:
        所有片段列表
    """
    all_segments = []
    
    for episode in sorted(episode_keyframes.keys()):
        keyframes = episode_keyframes.get(episode, [])
        asr = episode_asr.get(episode, [])
        duration = episode_durations.get(episode, 0)
        
        if duration == 0:
            print(f"警告: 第{episode}集时长为0，跳过")
            continue
        
        segments = extract_segments_for_episode(
            episode, keyframes, asr, duration
        )
        all_segments.extend(segments)
        print(f"第{episode}集: 生成了{len(segments)}个片段")
    
    return all_segments


def get_representative_frames(
    keyframes: List[KeyFrame],
    count: int = FRAMES_PER_SEGMENT
) -> List[KeyFrame]:
    """获取代表性的关键帧
    
    从片段的关键帧中均匀采样指定数量
    
    Args:
        keyframes: 关键帧列表
        count: 需要的关键帧数量
        
    Returns:
        代表性关键帧
    """
    if not keyframes:
        return []
    
    if len(keyframes) <= count:
        return keyframes
    
    # 均匀采样
    indices = [int(i * len(keyframes) / count) for i in range(count)]
    return [keyframes[i] for i in indices]


if __name__ == "__main__":
    # 测试
    print("extract_segments 模块已加载")
    print(f"片段时长: {SEGMENT_DURATION}秒")
    print(f"重叠时间: {SEGMENT_OVERLAP}秒")
    print(f"每片段关键帧: {FRAMES_PER_SEGMENT}张")
