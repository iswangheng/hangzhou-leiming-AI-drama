"""
视频清洗模块 - 马赛克遮盖

功能：
1. 对视频进行马赛克遮盖处理
2. 支持多个敏感词时间段
3. 生成遮盖记录文件

使用方法：
    from scripts.preprocess.video_cleaner import (
        VideoCleaner,
        clean_video
    )

    # 清洗视频
    cleaner = VideoCleaner()
    output_path = cleaner.clean(
        video_path="input.mp4",
        sensitive_segments=segments,
        subtitle_region=region
    )
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from .sensitive_detector import SensitiveSegment
from .subtitle_detector import SubtitleRegion
from scripts.utils.subprocess_utils import run_command
from scripts.config import TimeoutConfig


def get_video_info(video_path: str) -> dict:
    """
    获取视频信息

    Args:
        video_path: 视频文件路径

    Returns:
        视频信息字典
    """
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
        '-show_entries', 'format=duration',
        '-of', 'json',
        video_path
    ]

    result = run_command(
        cmd,
        timeout=TimeoutConfig.FFPROBE_QUICK,
        retries=2,
        error_msg=f"ffprobe获取视频信息超时: {video_path}"
    )
    if result is None:
        raise RuntimeError(f"无法获取视频信息（超时）: {video_path}")
    if result.returncode != 0:
        raise RuntimeError(f"无法获取视频信息: {video_path}")

    info = json.loads(result.stdout)

    stream = info['streams'][0]
    format_info = info.get('format', {})

    # 解析帧率
    fps_str = stream.get('r_frame_rate', '30/1')
    if '/' in fps_str:
        num, den = map(int, fps_str.split('/'))
        fps = num / den if den != 0 else 30.0
    else:
        fps = float(fps_str)

    return {
        'width': int(stream['width']),
        'height': int(stream['height']),
        'fps': fps,
        'codec': stream.get('codec_name', 'h264'),
        'duration': float(format_info.get('duration', 0))
    }


def build_mosaic_filter(
    video_info: dict,
    subtitle_region: SubtitleRegion,
    sensitive_segments: List[SensitiveSegment]
) -> str:
    """
    构建FFmpeg马赛克滤镜

    Args:
        video_info: 视频信息
        subtitle_region: 字幕区域配置
        sensitive_segments: 敏感词片段列表

    Returns:
        FFmpeg滤镜字符串
    """
    height = video_info['height']

    # 计算字幕区域像素坐标
    y = int(height * subtitle_region.y_ratio)
    h = int(height * subtitle_region.height_ratio)
    w = video_info['width']

    if not sensitive_segments:
        return None

    # 按集数分组（如果是单视频，所有片段都在同一集）
    # 这里假设每个视频文件对应一集

    # 构建滤镜
    # 策略：使用 crop + boxblur + overlay 方式

    filter_parts = []
    current_input = "0:v"

    for i, seg in enumerate(sensitive_segments):
        # 时间条件
        time_condition = f"between(t\\,{seg.start_time:.2f}\\,{seg.end_time:.2f})"

        if i == 0:
            # 第一个马赛克
            filter_parts.append(
                f"[{current_input}]crop=w={w}:h={h}:y={y},boxblur=30:10[blur{i}];"
            )
            filter_parts.append(
                f"[{current_input}][blur{i}]overlay=y={y}:enable='{time_condition}'"
            )
        else:
            # 后续马赛克
            filter_parts.append(f";")
            filter_parts.append(
                f"[v{i-1}]crop=w={w}:h={h}:y={y},boxblur=30:10[blur{i}];"
            )
            filter_parts.append(
                f"[v{i-1}][blur{i}]overlay=y={y}:enable='{time_condition}'"
            )

        # 更新输入标签
        if i > 0:
            current_input = f"v{i-1}"

    # 最终输出标签
    if len(sensitive_segments) > 0:
        filter_parts.append(f"[v{len(sensitive_segments)-1}]")

    return "".join(filter_parts)


def clean_video(
    video_path: str,
    sensitive_segments: List[SensitiveSegment],
    subtitle_region: SubtitleRegion,
    output_path: str,
    verbose: bool = True,
    time_buffer: float = 0.6
) -> str:
    """
    清洗视频（马赛克遮盖）

    Args:
        video_path: 输入视频路径
        sensitive_segments: 敏感词片段列表
        subtitle_region: 字幕区域配置
        output_path: 输出视频路径
        verbose: 是否打印详细信息
        time_buffer: 遮罩时间缓冲区（秒），默认0.6秒

    Returns:
        输出视频路径
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 如果没有敏感词，直接复制
    if not sensitive_segments:
        if verbose:
            print(f"  ℹ️ 无敏感词，直接复制视频")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video_path, output_path)
        return str(output_path)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"视频清洗: {video_path.name}")
        print(f"{'=' * 60}")
        print(f"  敏感词片段: {len(sensitive_segments)}个")
        print(f"  字幕区域: y={subtitle_region.y_ratio:.2%}, h={subtitle_region.height_ratio:.2%}")

    # 获取视频信息
    video_info = get_video_info(str(video_path))

    if verbose:
        print(f"  视频信息: {video_info['width']}x{video_info['height']}, {video_info['fps']:.1f}fps")

    # 计算像素坐标
    y = int(video_info['height'] * subtitle_region.y_ratio)
    h = int(video_info['height'] * subtitle_region.height_ratio)

    if verbose:
        print(f"  遮盖区域: y={y}px, h={h}px")

    # 构建FFmpeg命令
    # 使用 -filter_complex 实现马赛克遮盖

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 简化版：使用 drawbox 滤镜（性能更好）
    # drawbox 可以直接画一个半透明/模糊的框

    # 方案1：使用 boxblur（真正的马赛克效果）
    # 需要裁剪 → 模糊 → 叠加

    # 方案2：使用 drawbox（简单遮盖）
    # drawbox=x=0:y=Y:w=iw:h=H:color=black@0.8:t=fill:enable='between(t,start,end)'

    # 这里使用方案1（马赛克效果更好）

    # 为每个敏感片段构建滤镜
    filter_complex_parts = []
    current_input = "0:v"

    for i, seg in enumerate(sensitive_segments):
        # 添加时间缓冲区
        start_time = max(0, seg.start_time - time_buffer)
        end_time = seg.end_time + time_buffer
        time_cond = f"between(t\\,{start_time:.3f}\\,{end_time:.3f})"

        # 裁剪字幕区域
        filter_complex_parts.append(
            f"[{current_input}]crop=w=iw:h={h}:y={y}[crop{i}];"
        )

        # 应用马赛克（boxblur参数：luma_radius最大16，chroma_radius最大9）
        # 使用 luma_radius:chroma_radius:luma_power:chroma_power 格式
        filter_complex_parts.append(
            f"[crop{i}]boxblur=9:9:5:5[blur{i}];"
        )

        # 叠加回原视频
        if i == 0:
            filter_complex_parts.append(
                f"[0:v][blur{i}]overlay=y={y}:enable='{time_cond}'"
            )
        else:
            filter_complex_parts.append(
                f"[v{i-1}][blur{i}]overlay=y={y}:enable='{time_cond}'"
            )

        # 如果不是最后一个，添加分号和输出标签
        if i < len(sensitive_segments) - 1:
            filter_complex_parts.append(f"[v{i}];")

        current_input = f"v{i}" if i > 0 else "0:v"

    filter_complex = "".join(filter_complex_parts)

    # 构建FFmpeg命令
    cmd = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', str(video_path),
        '-filter_complex', filter_complex,
        '-c:v', 'libx264',  # 视频编码
        '-preset', 'medium',  # 编码速度
        '-crf', '23',  # 质量
        '-c:a', 'copy',  # 音频直接复制
        str(output_path)
    ]

    if verbose:
        print(f"\n  执行FFmpeg命令...")
        # print(f"  滤镜: {filter_complex}")  # 可能很长，可选打印

    # 执行命令（区域遮罩，超时重试 1 次后向上传播）
    result = run_command(
        cmd,
        timeout=TimeoutConfig.FFMPEG_MASK_APPLY,
        retries=1,
        error_msg=f"马赛克遮罩超时（视频: {video_path}）"
    )
    if result is None or result.returncode != 0:
        err = result.stderr[:500] if result is not None else "超时"
        raise RuntimeError(f"视频遮罩处理失败（含超时）: {err}")

    if verbose:
        print(f"✅ 视频清洗完成: {output_path}")

    return str(output_path)


def clean_video_precise(
    video_path: str,
    sensitive_segments: List[SensitiveSegment],
    subtitle_region: SubtitleRegion,
    output_path: str,
    verbose: bool = True,
    time_buffer: float = 0.3
) -> str:
    """
    精确遮罩 - 只遮罩敏感词所在位置的文字，不影响其他字幕

    Args:
        video_path: 输入视频路径
        sensitive_segments: 敏感词片段列表（包含boxes信息）
        subtitle_region: 字幕区域配置
        output_path: 输出视频路径
        verbose: 是否打印详细信息
        time_buffer: 遮罩时间缓冲区（秒），默认0.3秒

    Returns:
        输出视频路径
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 过滤出有boxes信息的片段
    segments_with_boxes = [seg for seg in sensitive_segments if seg.boxes]

    if not segments_with_boxes:
        if verbose:
            print(f"  ℹ️ 无精确坐标信息，使用区域遮罩")
        return clean_video(video_path, sensitive_segments, subtitle_region, output_path, verbose, time_buffer)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"精确遮罩: {video_path.name}")
        print(f"{'=' * 60}")
        print(f"  精确遮罩片段: {len(segments_with_boxes)}个")
        print(f"  字幕区域: y={subtitle_region.y_ratio:.2%}, h={subtitle_region.height_ratio:.2%}")

    # 获取视频信息
    video_info = get_video_info(str(video_path))

    if verbose:
        print(f"  视频信息: {video_info['width']}x{video_info['height']}, {video_info['fps']:.1f}fps")

    # 计算字幕区域的基准坐标
    video_height = video_info['height']
    video_width = video_info['width']
    subtitle_y = int(video_height * subtitle_region.y_ratio)
    subtitle_h = int(video_height * subtitle_region.height_ratio)
    subtitle_x = 0  # 字幕区域从视频左侧开始

    if verbose:
        print(f"  字幕区域: y={subtitle_y}px, h={subtitle_h}px")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建FFmpeg滤镜
    # 策略：每个敏感词的每个文字框分别应用boxblur
    filter_complex_parts = []
    
    # 首先需要对源视频进行split，分成 N 份供 crop 使用，外加 1 份作为底图
    num_splits = len(segments_with_boxes)
    split_str = "".join([f"[orig{i}]" for i in range(num_splits)])
    filter_complex_parts.append(f"[0:v]split={num_splits+1}{split_str}[base0];")

    # 处理每个敏感词片段
    for i, seg in enumerate(segments_with_boxes):
        boxes = seg.boxes
        if not boxes:
            continue

        # 计算时间范围
        start_time = max(0, seg.start_time - time_buffer)
        end_time = seg.end_time + time_buffer
        time_cond = f"between(t\\,{start_time:.3f}\\,{end_time:.3f})"

        if verbose:
            print(f"  处理: '{seg.sensitive_word}' @ {seg.start_time:.1f}s-{seg.end_time:.1f}s")
            print(f"    文字框数量: {len(boxes)}")

        # 合并所有文字框，获取整体覆盖区域
        # 注意：PaddleOCR返回的boxes已经是全屏坐标（相对于完整视频）
        # 但y坐标是相对于裁剪后的字幕区域，需要加上subtitle_y偏移
        all_x = []
        all_y = []
        for box in boxes:
            if isinstance(box, (list, tuple)):
                if len(box) >= 4 and isinstance(box[0], (list, tuple)):
                    # 四点坐标格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    for p in box[:4]:
                        all_x.append(p[0])
                        all_y.append(p[1] + subtitle_y)
                elif len(box) >= 4:
                    # 格式: [x1, y1, x2, y2]
                    x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                    all_x.append(x1)
                    all_x.append(x2)
                    all_y.append(y1 + subtitle_y)
                    all_y.append(y2 + subtitle_y)

        if not all_x or not all_y:
            continue

        # 计算合并后的区域
        min_x = int(min(all_x))
        max_x = int(max(all_x))
        min_y = int(min(all_y))
        max_y = int(max(all_y))

        # 扩展区域以确保完整覆盖文字
        padding = 5
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(video_info['width'], max_x + padding)
        max_y = min(video_height, max_y + padding)

        box_w = max_x - min_x
        box_h = max_y - min_y

        if verbose:
            print(f"    遮罩区域: x={min_x}, y={min_y}, w={box_w}, h={box_h}")

        # 使用split分离出的流进行crop和模糊
        filter_complex_parts.append(
            f"[orig{i}]crop=x={min_x}:y={min_y}:w={box_w}:h={box_h},boxblur=5[blur{i}];"
        )
        out_pad = f"[base{i+1}]" if i < len(segments_with_boxes) - 1 else ""
        filter_complex_parts.append(
            f"[base{i}][blur{i}]overlay=x={min_x}:y={min_y}:enable='{time_cond}'{out_pad}"
        )
        if i < len(segments_with_boxes) - 1:
            filter_complex_parts.append(";")

    if not filter_complex_parts:
        if verbose:
            print(f"  ℹ️ 无有效文字框，直接复制视频")
        shutil.copy2(video_path, output_path)
        return str(output_path)

    # 构建完整的滤镜链（用分号连接多个滤镜）
    filter_complex = "".join(filter_complex_parts)

    # 构建FFmpeg命令
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(video_path),
        '-filter_complex', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'copy',
        str(output_path)
    ]

    if verbose:
        print(f"\n  执行FFmpeg命令...")

    # 精确遮罩执行（超时重试 1 次；仍失败则回退到区域遮罩）
    result = run_command(
        cmd,
        timeout=TimeoutConfig.FFMPEG_MASK_APPLY,
        retries=1,
        error_msg="精确遮罩超时"
    )
    if result is None or result.returncode != 0:
        if result is not None:
            print(f"❌ FFmpeg执行失败:")
            print(result.stderr)
        # 精确失败/超时 → 回退到区域遮罩
        if verbose:
            print(f"  回退到区域遮罩模式...")
        return clean_video(video_path, sensitive_segments, subtitle_region, output_path, verbose, time_buffer)

    if verbose:
        print(f"✅ 精确遮罩完成: {output_path}")

    return str(output_path)


def save_mask_record(
    project_name: str,
    video_files: dict,  # {episode: video_path}
    sensitive_segments: List[SensitiveSegment],
    subtitle_region: SubtitleRegion,
    output_dir: str = "漫剧素材_干净"
) -> str:
    """
    保存遮盖记录

    Args:
        project_name: 项目名称
        video_files: 视频文件字典 {集数: 视频路径}
        sensitive_segments: 敏感词片段列表
        subtitle_region: 字幕区域配置
        output_dir: 输出目录

    Returns:
        记录文件路径
    """
    output_path = Path(output_dir) / project_name / "sensitive_mask.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 按集数分组统计
    episode_stats = {}
    for seg in sensitive_segments:
        ep = seg.episode
        if ep not in episode_stats:
            episode_stats[ep] = []
        episode_stats[ep].append(seg)

    # 构建记录
    record = {
        "project_name": project_name,
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_episodes": len(video_files),
        "total_sensitive_segments": len(sensitive_segments),
        "subtitle_region": subtitle_region.to_dict(),

        "episode_summary": {
            str(ep): len(segs) for ep, segs in episode_stats.items()
        },

        "mask_records": [
            {
                "episode": seg.episode,
                "sensitive_word": seg.sensitive_word,
                "asr_text": seg.asr_text,
                "start_time": round(seg.start_time, 3),
                "end_time": round(seg.end_time, 3)
            }
            for seg in sensitive_segments
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"✅ 遮盖记录已保存: {output_path}")
    return str(output_path)


class VideoCleaner:
    """
    视频清洗器（类封装版本）

    使用方法：
        cleaner = VideoCleaner()
        output = cleaner.clean(video_path, segments, region)
    """

    def __init__(self, output_dir: str = "漫剧素材_干净"):
        """
        初始化清洗器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir

    def clean(
        self,
        video_path: str,
        sensitive_segments: List[SensitiveSegment],
        subtitle_region: SubtitleRegion,
        output_path: Optional[str] = None,
        verbose: bool = True
    ) -> str:
        """
        清洗视频

        Args:
            video_path: 输入视频路径
            sensitive_segments: 敏感词片段列表
            subtitle_region: 字幕区域配置
            output_path: 输出视频路径（可选，自动生成）
            verbose: 是否打印详细信息

        Returns:
            输出视频路径
        """
        video_path = Path(video_path)

        # 自动生成输出路径
        if output_path is None:
            output_path = Path(self.output_dir) / video_path.name

        return clean_video(
            video_path=str(video_path),
            sensitive_segments=sensitive_segments,
            subtitle_region=subtitle_region,
            output_path=str(output_path),
            verbose=verbose
        )

    def clean_project(
        self,
        project_name: str,
        video_files: dict,  # {episode: video_path}
        sensitive_segments: List[SensitiveSegment],
        subtitle_region: SubtitleRegion,
        verbose: bool = True
    ) -> dict:
        """
        清洗整个项目的视频

        Args:
            project_name: 项目名称
            video_files: 视频文件字典 {集数: 视频路径}
            sensitive_segments: 敏感词片段列表
            subtitle_region: 字幕区域配置
            verbose: 是否打印详细信息

        Returns:
            输出文件字典 {集数: 输出路径}
        """
        output_dir = Path(self.output_dir) / project_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # 按集数分组敏感片段
        segments_by_episode = {}
        for seg in sensitive_segments:
            if seg.episode not in segments_by_episode:
                segments_by_episode[seg.episode] = []
            segments_by_episode[seg.episode].append(seg)

        output_files = {}

        for episode, video_path in video_files.items():
            video_path = Path(video_path)
            output_path = output_dir / video_path.name

            # 获取该集的敏感片段
            ep_segments = segments_by_episode.get(episode, [])

            if verbose:
                print(f"\n处理第{episode}集: {video_path.name}")
                print(f"  敏感片段: {len(ep_segments)}个")

            # 清洗视频
            clean_video(
                video_path=str(video_path),
                sensitive_segments=ep_segments,
                subtitle_region=subtitle_region,
                output_path=str(output_path),
                verbose=verbose
            )

            output_files[episode] = str(output_path)

        # 保存遮盖记录
        save_mask_record(
            project_name=project_name,
            video_files=video_files,
            sensitive_segments=sensitive_segments,
            subtitle_region=subtitle_region,
            output_dir=self.output_dir
        )

        return output_files


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("视频清洗模块测试")
    print("=" * 60)

    # 模拟数据
    from .sensitive_detector import SensitiveSegment
    from .subtitle_detector import SubtitleRegion

    # 测试获取视频信息
    # video_info = get_video_info("test.mp4")
    # print(f"视频信息: {video_info}")

    # 测试字幕区域
    region = SubtitleRegion(
        y_ratio=0.88,
        height_ratio=0.10,
        detection_method="default",
        confidence=0.5
    )

    # 测试敏感片段
    segments = [
        SensitiveSegment(
            episode=1,
            sensitive_word="测试词",
            asr_text="这是一个测试词",
            start_time=5.0,
            end_time=7.5
        )
    ]

    print(f"\n字幕区域: {region}")
    print(f"敏感片段: {segments}")

    # 实际清洗需要视频文件
    # output = clean_video("input.mp4", segments, region, "output.mp4")
