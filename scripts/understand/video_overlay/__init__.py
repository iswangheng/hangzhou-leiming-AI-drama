"""
视频包装花字叠加模块

功能：
1. 在视频上叠加三行花字："热门短剧"、剧名、免责声明
2. 支持5-10种预制样式
3. 项目级样式统一
4. 避免遮挡原字幕
5. 45度倾斜角标功能
"""

from .video_overlay import (
    VideoOverlayRenderer,
    OverlayConfig,
    apply_overlay_to_video,
    batch_apply_overlay
)

from .tilted_label import (
    TiltedLabelRenderer,
    TiltedLabelConfig,
    add_tilted_label
)

__all__ = [
    # Video Overlay Module
    "VideoOverlayRenderer",
    "OverlayConfig",
    "apply_overlay_to_video",
    "batch_apply_overlay",
    # Tilted Label Module
    "TiltedLabelRenderer",
    "TiltedLabelConfig",
    "add_tilted_label",
]
