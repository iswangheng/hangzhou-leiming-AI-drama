"""
预处理模块 - 敏感词字幕遮盖功能

功能：
1. 敏感词检测：读取配置 + ASR匹配
2. 字幕区域检测：Gemini/OCR/默认比例
3. 视频清洗：FFmpeg马赛克遮盖

使用方法：
    from scripts.preprocess import SensitiveDetector, SubtitleDetector, VideoCleaner
"""

from .sensitive_detector import (
    SensitiveDetector,
    SensitiveSegment,
    load_sensitive_words,
    detect_sensitive_segments
)

from .subtitle_detector import (
    SubtitleDetector,
    SubtitleRegion,
    detect_subtitle_region
)

from .video_cleaner import (
    VideoCleaner,
    clean_video
)

__all__ = [
    # 敏感词检测
    'SensitiveDetector',
    'SensitiveSegment',
    'load_sensitive_words',
    'detect_sensitive_segments',

    # 字幕区域检测
    'SubtitleDetector',
    'SubtitleRegion',
    'detect_subtitle_region',

    # 视频清洗
    'VideoCleaner',
    'clean_video'
]
