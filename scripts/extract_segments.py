"""
片段提取模块 - 提取视频分析片段
"""
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
from pathlib import Path
import subprocess

from .config import TrainingConfig
from .data_models import KeyFrame, ASRSegment


@dataclass
class VideoSegment:
    """视频片段"""
    start_time: int         # 起始秒
    end_time: int           # 结束秒
    duration: int           # 时长（秒）
    keyframes: List[KeyFrame] = field(default_factory=list)
    asr_segments: List[ASRSegment] = field(default_factory=list)
    asr_text: str = ""


@dataclass
class EpisodeSegments:
    """剧集片段数据"""
    project_name: str
    episode_number: int
    video_path: str
    segments: List[VideoSegment] = field(default_factory=list)


def extract_keyframes_from_video(
    video_path: str,
    output_dir: str,
    fps: float = TrainingConfig.KEYFRAME_FPS,
    quality: int = TrainingConfig.KEYFRAME_QUALITY
) -> List[KeyFrame]:
    """从视频中提取关键帧

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        fps: 提取帧率（每秒帧数）
        quality: JPEG质量（1-31，越小越好）

    Returns:
        关键帧列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 使用FFmpeg提取关键帧
    output_pattern = os.path.join(output_dir, "frame_%06d.jpg")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-qscale:v", str(quality),
        output_pattern,
        "-y"  # 覆盖已存在的文件
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # 收集生成的帧文件
        keyframes = []
        frame_files = sorted(Path(output_dir).glob("frame_*.jpg"))

        for frame_file in frame_files:
            # 从文件名提取时间戳
            frame_number = int(frame_file.stem.split("_")[1])
            timestamp_ms = int((frame_number / fps) * 1000)

            keyframes.append(KeyFrame(
                frame_path=str(frame_file),
                timestamp_ms=timestamp_ms
            ))

        return keyframes

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg错误: {e.stderr}")
        raise Exception(f"关键帧提取失败: {e}")


def load_asr_from_cache(cache_dir: str) -> List[ASRSegment]:
    """从缓存加载ASR数据

    Args:
        cache_dir: 缓存目录

    Returns:
        ASR片段列表
    """
    asr_file = os.path.join(cache_dir, "asr.json")

    if not os.path.exists(asr_file):
        return []

    with open(asr_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [
        ASRSegment(
            text=segment["text"],
            start=segment["start"],
            end=segment["end"]
        )
        for segment in data
    ]


def transcribe_asr(
    video_path: str,
    cache_dir: str,
    model: str = TrainingConfig.ASR_MODEL,
    language: str = TrainingConfig.ASR_LANGUAGE
) -> List[ASRSegment]:
    """使用Whisper转录ASR

    Args:
        video_path: 视频文件路径
        cache_dir: 缓存目录
        model: Whisper模型大小
        language: 语言代码

    Returns:
        ASR片段列表
    """
    os.makedirs(cache_dir, exist_ok=True)

    asr_file = os.path.join(cache_dir, "asr.json")

    # 检查缓存
    if os.path.exists(asr_file):
        print("  使用缓存的ASR数据")
        return load_asr_from_cache(cache_dir)

    try:
        import whisper

        print(f"  正在使用Whisper转录 ({model}模型)...")
        model_instance = whisper.load_model(model)

        # 转录音频
        result = model_instance.transcribe(
            video_path,
            language=language,
            task="transcribe"
        )

        # 转换为ASR片段
        segments = []
        for segment in result["segments"]:
            segments.append(ASRSegment(
                text=segment["text"].strip(),
                start=segment["start"],
                end=segment["end"]
            ))

        # 保存到缓存
        asr_data = [
            {"text": seg.text, "start": seg.start, "end": seg.end}
            for seg in segments
        ]

        with open(asr_file, 'w', encoding='utf-8') as f:
            json.dump(asr_data, f, ensure_ascii=False, indent=2)

        print(f"  ASR转录完成: {len(segments)} 个片段")
        return segments

    except ImportError:
        raise Exception("Whisper库未安装，请运行: pip install openai-whisper")
    except Exception as e:
        raise Exception(f"ASR转录失败: {e}")


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）

    Args:
        video_path: 视频文件路径

    Returns:
        视频时长（秒）
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        raise Exception(f"无法获取视频时长: {video_path}")


def extract_segments_for_episode(
    project_name: str,
    episode_number: int,
    video_path: str,
    segment_duration: int = 60,
    segment_overlap: int = 10,
    frames_per_segment: int = 5,
    force_reextract: bool = False
) -> EpisodeSegments:
    """为单个剧集提取分析片段

    Args:
        project_name: 项目名称
        episode_number: 剧集编号
        video_path: 视频文件路径
        segment_duration: 片段时长（秒）
        segment_overlap: 相邻片段重叠时长（秒）
        frames_per_segment: 每片段提取的关键帧数
        force_reextract: 是否强制重新提取

    Returns:
        剧集片段数据
    """
    # 缓存目录
    cache_dir = TrainingConfig.CACHE_DIR / project_name / f"episode_{episode_number}"

    # 提取关键帧
    keyframes_dir = cache_dir / "keyframes"

    if not force_reextract and keyframes_dir.exists():
        print(f"  使用缓存的关键帧")
        keyframes = []
        for frame_file in sorted(keyframes_dir.glob("frame_*.jpg")):
            frame_number = int(frame_file.stem.split("_")[1])
            timestamp_ms = int((frame_number / TrainingConfig.KEYFRAME_FPS) * 1000)
            keyframes.append(KeyFrame(
                frame_path=str(frame_file),
                timestamp_ms=timestamp_ms
            ))
    else:
        print(f"  提取关键帧...")
        keyframes = extract_keyframes_from_video(video_path, str(keyframes_dir))

    # 转录ASR
    asr_segments = transcribe_asr(video_path, str(cache_dir))

    # 获取视频时长
    video_duration = get_video_duration(video_path)
    print(f"  视频时长: {video_duration:.1f}秒")

    # 生成时间窗口片段
    segments = []
    current_time = 0

    while current_time < video_duration:
        end_time = min(current_time + segment_duration, int(video_duration))

        # 提取该时间段的关键帧（均匀采样）
        segment_keyframes = []
        segment_start_ms = current_time * 1000
        segment_end_ms = end_time * 1000

        # 筛选该时间段内的关键帧
        valid_keyframes = [
            kf for kf in keyframes
            if segment_start_ms <= kf.timestamp_ms <= segment_end_ms
        ]

        # 均匀采样指定数量的帧
        if valid_keyframes:
            step = max(1, len(valid_keyframes) // frames_per_segment)
            segment_keyframes = valid_keyframes[::step][:frames_per_segment]

        # 提取该时间段的ASR文本
        segment_asr = []
        asr_texts = []

        for asr_seg in asr_segments:
            # 检查是否有重叠
            seg_start = asr_seg.start
            seg_end = asr_seg.end

            if seg_end >= current_time and seg_start <= end_time:
                segment_asr.append(asr_seg)
                asr_texts.append(asr_seg.text)

        segment_asr_text = " ".join(asr_texts).strip()

        # 创建片段
        segment = VideoSegment(
            start_time=current_time,
            end_time=end_time,
            duration=end_time - current_time,
            keyframes=segment_keyframes,
            asr_segments=segment_asr,
            asr_text=segment_asr_text
        )

        segments.append(segment)

        # 移动到下一个窗口（考虑重叠）
        current_time = end_time - segment_overlap
        if current_time < 0:
            current_time = end_time

    print(f"  生成了 {len(segments)} 个分析片段")

    return EpisodeSegments(
        project_name=project_name,
        episode_number=episode_number,
        video_path=video_path,
        segments=segments
    )


def save_episode_segments(segments: EpisodeSegments, output_dir: str):
    """保存剧集片段数据

    Args:
        segments: 剧集片段数据
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        f"episode_{segments.episode_number}_segments.json"
    )

    # 转换为可序列化的格式
    data = {
        "project_name": segments.project_name,
        "episode_number": segments.episode_number,
        "video_path": segments.video_path,
        "segments": [
            {
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "duration": seg.duration,
                "keyframes": [
                    {
                        "frame_path": kf.frame_path,
                        "timestamp_ms": kf.timestamp_ms
                    }
                    for kf in seg.keyframes
                ],
                "asr_text": seg.asr_text
            }
            for seg in segments.segments
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"片段数据已保存: {output_file}")


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS

    if PROJECTS:
        project = PROJECTS[0]
        print(f"测试片段提取: {project.name}")

        try:
            # 获取第一集视频
            video_path = project.get_video_path(1)

            # 提取片段
            segments = extract_segments_for_episode(
                project.name,
                1,
                video_path
            )

            # 保存结果
            output_dir = TrainingConfig.DATA_DIR / "segments" / project.name
            save_episode_segments(segments, str(output_dir))

            # 显示统计信息
            print(f"\n统计信息:")
            print(f"  总片段数: {len(segments.segments)}")
            if segments.segments:
                print(f"  第一个片段: {segments.segments[0].start_time}s - {segments.segments[0].end_time}s")
                print(f"  关键帧数: {len(segments.segments[0].keyframes)}")
                print(f"  ASR文本长度: {len(segments.segments[0].asr_text)}")

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()