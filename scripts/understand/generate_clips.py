"""
生成剪辑组合模块
根据高光点/钩子点生成剪辑片段
"""
import json
from typing import List
from dataclasses import dataclass

try:
    from scripts.understand.analyze_segment import SegmentAnalysis
except ImportError:
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class SegmentAnalysis:
        episode: int
        start_time: int
        end_time: int
        is_highlight: bool
        highlight_timestamp: int = 0  # 精确时间戳
        highlight_type: Optional[str] = None
        highlight_desc: str = ""
        highlight_confidence: float = 0.0
        is_hook: bool = False
        hook_timestamp: int = 0  # 精确时间戳
        hook_type: Optional[str] = None
        hook_desc: str = ""
        hook_confidence: float = 0.0


# 配置参数
MIN_CLIP_DURATION = 30   # 最短30秒
MAX_CLIP_DURATION = 300  # 最长5分钟
DEDUP_WINDOW = 30  # 去重时间窗口（秒）


@dataclass
class Clip:
    """剪辑组合"""
    start: int           # 起始秒
    end: int           # 结束秒
    duration: int      # 时长（秒）
    highlight_type: str  # 高光类型
    highlight_desc: str  # 高光描述
    hook_type: str      # 钩子类型
    hook_desc: str      # 钩子描述
    episode: int        # 集数
    
    @property
    def clip_type(self) -> str:
        return f"{self.highlight_type}-{self.hook_type}"
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "highlight": self.highlight_type,
            "highlightDesc": self.highlight_desc,
            "hook": self.hook_type,
            "hookDesc": self.hook_desc,
            "type": self.clip_type,
            "episode": self.episode
        }


def deduplicate_highlights(highlights: List[SegmentAnalysis], window: int = DEDUP_WINDOW) -> List[SegmentAnalysis]:
    """去重高光点

    同一类型在时间窗口内只保留第一个

    Args:
        highlights: 高光点列表
        window: 去重时间窗口

    Returns:
        去重后的高光点
    """
    if not highlights:
        return []

    # 按类型和精确时间戳排序
    sorted_hl = sorted(highlights, key=lambda x: (x.highlight_timestamp, x.highlight_type or ""))

    result = []
    last_by_type = {}  # 记录每个类型最后出现的时间

    for hl in sorted_hl:
        hl_type = hl.highlight_type or ""
        last_time = last_by_type.get(hl_type, -999)

        if hl.highlight_timestamp - last_time >= window:
            result.append(hl)
            last_by_type[hl_type] = hl.highlight_timestamp

    return result


def deduplicate_hooks(hooks: List[SegmentAnalysis], window: int = DEDUP_WINDOW) -> List[SegmentAnalysis]:
    """去重钩子点

    Args:
        hooks: 钩子点列表
        window: 去重时间窗口

    Returns:
        去重后的钩子点
    """
    if not hooks:
        return []

    sorted_hooks = sorted(hooks, key=lambda x: (x.hook_timestamp, x.hook_type or ""))

    result = []
    last_by_type = {}

    for hook in sorted_hooks:
        hook_type = hook.hook_type or ""
        last_time = last_by_type.get(hook_type, -999)

        if hook.hook_timestamp - last_time >= window:
            result.append(hook)
            last_by_type[hook_type] = hook.hook_timestamp

    return result


def generate_clips(
    analyses: List[SegmentAnalysis],
    min_duration: int = MIN_CLIP_DURATION,
    max_duration: int = MAX_CLIP_DURATION,
    dedup_window: int = DEDUP_WINDOW
) -> List[Clip]:
    """生成剪辑组合
    
    遍历每个高光点，找后续最近的钩子点，生成剪辑
    
    Args:
        analyses: 所有分析结果
        min_duration: 最短时长
        max_duration: 最长时长
        dedup_window: 去重时间窗口
        
    Returns:
        剪辑组合列表
    """
    # 分离高光点和钩子点
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]
    
    print(f"原始高光点: {len(highlights)}, 钩子点: {len(hooks)}")
    
    # 去重
    highlights = deduplicate_highlights(highlights, dedup_window)
    hooks = deduplicate_hooks(hooks, dedup_window)
    
    print(f"去重后高光点: {len(highlights)}, 钩子点: {len(hooks)}")
    
    # 按精确时间戳排序
    highlights = sorted(highlights, key=lambda x: x.highlight_timestamp)
    hooks = sorted(hooks, key=lambda x: x.hook_timestamp)

    clips = []

    for hl in highlights:
        # 找该高光点后面的钩子点
        candidate_hooks = [
            h for h in hooks
            if h.hook_timestamp > hl.highlight_timestamp
        ]

        if not candidate_hooks:
            continue

        # 找最近的钩子点
        best_hook = min(candidate_hooks, key=lambda h: h.hook_timestamp - hl.highlight_timestamp)

        # 检查时长（使用精确时间戳）
        duration = best_hook.hook_timestamp - hl.highlight_timestamp

        if min_duration <= duration <= max_duration:
            clip = Clip(
                start=hl.highlight_timestamp,  # 使用精确时间戳
                end=best_hook.hook_timestamp,  # 使用精确时间戳
                duration=duration,
                highlight_type=hl.highlight_type or "未知",
                highlight_desc=hl.highlight_desc,
                hook_type=best_hook.hook_type or "未知",
                hook_desc=best_hook.hook_desc,
                episode=hl.episode
            )
            clips.append(clip)
            print(f"生成剪辑: 第{clip.episode}集 {clip.start}-{clip.end}秒 ({clip.duration}秒) [{clip.clip_type}]")
    
    # 按集数和时间排序
    clips = sorted(clips, key=lambda x: (x.episode, x.start))
    
    print(f"\n共生成 {len(clips)} 个剪辑组合")
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
    print(f"去重窗口: {DEDUP_WINDOW}秒")
