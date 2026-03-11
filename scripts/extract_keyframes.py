"""
关键帧提取模块 - 使用FFmpeg提取视频关键帧
"""
import subprocess
import os
from pathlib import Path
from typing import List, Optional
import hashlib

from .data_models import KeyFrame
from .config import TrainingConfig


def extract_keyframes(
    video_path: str,
    output_dir: str,
    fps: float = TrainingConfig.KEYFRAME_FPS,
    quality: int = TrainingConfig.KEYFRAME_QUALITY,
    force_reextract: bool = False,
    video_actual_fps: float = None  # V14.2: 新增参数，视频实际帧率
) -> List[KeyFrame]:
    """提取关键帧

    使用 FFmpeg 按指定 fps 提取帧
    ffmpeg -i input.mp4 -vf "fps=2" output/%04d.jpg

    V14.2 更新：支持传入视频实际帧率，用于精确计算时间戳

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        fps: 提取帧率（每秒帧数，用于FFmpeg -vf滤镜）
        quality: JPEG质量 (1-31, 越小越好)
        force_reextract: 是否强制重新提取
        video_actual_fps: 视频实际帧率（用于精确计算时间戳）

    Returns:
        关键帧列表

    Raises:
        FileNotFoundError: 视频文件不存在
        subprocess.CalledProcessError: FFmpeg执行失败
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 生成缓存文件名
    video_hash = hashlib.md5(video_path.encode()).hexdigest()[:8]
    cache_file = os.path.join(output_dir, f".extracted_{video_hash}")

    # 检查是否已经提取过
    if not force_reextract and os.path.exists(cache_file):
        keyframes = load_existing_keyframes(output_dir)
        if keyframes:
            print(f"使用已缓存的关键帧: {len(keyframes)} 帧")
            return keyframes

    print(f"开始提取关键帧: {video_path}")
    print(f"参数: fps={fps}, quality={quality}")

    # 使用 FFmpeg 提取帧
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'fps={fps}',
        '-q:v', str(quality),  # JPEG 质量
        '-loglevel', 'error',  # 减少日志输出
        os.path.join(output_dir, '%04d.jpg'),
        '-y'  # 覆盖输出
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"关键帧提取完成")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg错误: {e.stderr}")
        raise
    except FileNotFoundError:
        raise FileNotFoundError(
            "未找到FFmpeg命令。请确保已安装FFmpeg并添加到PATH环境变量中。"
            "安装方法: brew install ffmpeg (macOS) 或 apt-get install ffmpeg (Linux)"
        )

    # 收集帧文件
    keyframes = []
    frame_files = sorted(Path(output_dir).glob('*.jpg'))

    for idx, frame_file in enumerate(frame_files):
        # V14.2: 使用视频实际帧率计算精确时间戳
        if video_actual_fps is not None:
            # 使用实际帧率计算：时间戳 = (帧索引 / 提取帧率) * (实际帧率 / 提取帧率) * 1000
            timestamp_ms = int((idx / fps) * (video_actual_fps / fps) * 1000)
        else:
            # 回退到原来的计算方式
            timestamp_ms = int((idx / fps) * 1000)

        keyframes.append(KeyFrame(
            frame_path=str(frame_file),
            timestamp_ms=timestamp_ms
        ))

    # 创建缓存标记文件
    with open(cache_file, 'w') as f:
        f.write(f"{len(keyframes)} frames extracted from {video_path}\n")

    print(f"提取了 {len(keyframes)} 帧")
    return keyframes


def load_existing_keyframes(output_dir: str, video_actual_fps: float = None) -> Optional[List[KeyFrame]]:
    """加载已提取的关键帧"""
    frame_files = sorted(Path(output_dir).glob('*.jpg'))
    if not frame_files:
        return None

    keyframes = []
    fps = TrainingConfig.KEYFRAME_FPS

    for idx, frame_file in enumerate(frame_files):
        timestamp_ms = int((idx / fps) * 1000)
        keyframes.append(KeyFrame(
            frame_path=str(frame_file),
            timestamp_ms=timestamp_ms
        ))

    return keyframes


def get_keyframe_output_path(project_name: str, episode_number: int) -> str:
    """获取关键帧输出路径"""
    # 使用项目名映射
    from scripts.config import get_cache_project_name
    cache_name = get_cache_project_name(project_name)
    cache_dir = TrainingConfig.CACHE_DIR / "keyframes" / cache_name
    episode_dir = cache_dir / str(episode_number)
    return str(episode_dir)


def extract_ending_keyframes(
    video_path: str,
    output_dir: str,
    last_seconds: float = 3.5,
    quality: int = TrainingConfig.KEYFRAME_QUALITY,
    force_reextract: bool = False
) -> List[KeyFrame]:
    """提取视频最后N秒的高密度关键帧（用于片尾检测）

    与普通关键帧提取不同，这里每帧都采样（而不是按固定fps）
    用于画面相似度检测

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        last_seconds: 提取最后多少秒（默认3.5秒）
        quality: JPEG质量
        force_reextract: 是否强制重新提取

    Returns:
        关键帧列表

    Raises:
        FileNotFoundError: 视频文件不存在
        subprocess.CalledProcessError: FFmpeg执行失败
    """
    import cv2

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 获取视频信息
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"无法打开视频: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / video_fps
    cap.release()

    # 计算起始帧位置
    start_time = max(0, total_duration - last_seconds)
    start_frame = int(start_time * video_fps)

    print(f"提取最后{last_seconds}秒高密度关键帧: {video_path}")
    print(f"视频: {total_duration:.1f}秒, {video_fps}fps")
    print(f"提取范围: {start_time:.2f}秒 ~ {total_duration:.2f}秒")

    # 使用FFmpeg提取最后N秒，使用FPS滤镜实现每帧采样
    # fps=video_fps 表示每秒采样video_fps帧（即每帧都采样）
    cmd = [
        'ffmpeg',
        '-ss', str(start_time),
        '-i', video_path,
        '-vf', f'fps={video_fps}',
        '-q:v', str(quality),
        '-loglevel', 'error',
        os.path.join(output_dir, 'ending_%04d.jpg'),
        '-y'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"高密度关键帧提取完成")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg错误: {e.stderr}")
        raise

    # 收集帧文件
    keyframes = []
    frame_files = sorted(Path(output_dir).glob('ending_*.jpg'))

    for idx, frame_file in enumerate(frame_files):
        # 时间戳 = 起始时间 + (帧索引 / 视频帧率)
        timestamp_ms = int((start_time + (idx / video_fps)) * 1000)
        
        # 确保不超过视频总时长
        if timestamp_ms <= total_duration * 1000:
            keyframes.append(KeyFrame(
                frame_path=str(frame_file),
                timestamp_ms=timestamp_ms
            ))

    print(f"提取了 {len(keyframes)} 帧高密度关键帧")
    return keyframes


def get_ending_keyframe_output_path(project_name: str, episode_number: int) -> str:
    """获取片尾检测用的高密度关键帧输出路径"""
    from scripts.config import get_cache_project_name
    cache_name = get_cache_project_name(project_name)
    cache_dir = TrainingConfig.CACHE_DIR / "keyframes" / cache_name / "ending"
    episode_dir = cache_dir / str(episode_number)
    return str(episode_dir)


def clear_keyframe_cache(project_name: Optional[str] = None, episode_number: Optional[int] = None):
    """清除关键帧缓存

    Args:
        project_name: 项目名称，如果为None则清除所有项目
        episode_number: 集数编号，如果为None则清除项目所有集数
    """
    cache_dir = TrainingConfig.CACHE_DIR / "keyframes"

    if project_name is None:
        # 清除所有缓存
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            print(f"已清除所有关键帧缓存")
    else:
        project_dir = cache_dir / project_name
        if episode_number is None:
            # 清除项目的所有缓存
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)
                print(f"已清除项目 {project_name} 的所有关键帧缓存")
        else:
            # 清除指定集数的缓存
            episode_dir = project_dir / str(episode_number)
            if episode_dir.exists():
                import shutil
                shutil.rmtree(episode_dir)
                print(f"已清除项目 {project_name} 第{episode_number}集的关键帧缓存")


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS, create_directories
    from .read_excel import load_project_markings, validate_markings, get_unique_episodes

    create_directories()

    if PROJECTS:
        project = PROJECTS[0]
        print(f"测试提取关键帧: {project.name}")

        try:
            # 读取标记数据
            markings = load_project_markings(project)
            valid_markings = validate_markings(markings, project)

            if valid_markings:
                # 获取第一个有标记的集数
                episode_number = sorted(get_unique_episodes(valid_markings))[0]

                # 获取视频路径
                video_path = project.get_video_path(episode_number)

                # 提取关键帧
                output_dir = get_keyframe_output_path(project.name, episode_number)
                keyframes = extract_keyframes(video_path, output_dir)

                print(f"提取了 {len(keyframes)} 帧")
                if keyframes:
                    print(f"第一帧: {keyframes[0].frame_path}")
                    print(f"最后一帧: {keyframes[-1].frame_path}")

        except Exception as e:
            print(f"错误: {e}")


# ========== V5.0 新增：按秒提取关键帧功能 ==========

def extract_keyframes_for_segment(
    video_path: str,
    start_time: int,
    end_time: int,
    output_dir: str,
    quality: int = TrainingConfig.KEYFRAME_QUALITY
) -> List[KeyFrame]:
    """为特定片段提取关键帧（每秒1帧）

    V5.0 优化：为分析窗口提供更密集的关键帧

    Args:
        video_path: 视频文件路径
        start_time: 片段开始时间（秒）
        end_time: 片段结束时间（秒）
        output_dir: 输出目录
        quality: JPEG质量 (1-31, 越小越好)

    Returns:
        关键帧列表（每秒1帧）

    Example:
        start_time=0, end_time=30
        → 提取0s, 1s, 2s, ..., 29s共30张关键帧
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    keyframes = []

    # 每秒提取1帧
    for second in range(start_time, end_time):
        timestamp_ms = second * 1000
        frame_path = extract_frame_at(video_path, second, output_dir, quality)

        if frame_path:
            keyframes.append(KeyFrame(
                frame_path=frame_path,
                timestamp_ms=timestamp_ms
            ))

    return keyframes


def extract_frame_at(video_path: str, second: int, output_dir: str, quality: int = 2) -> Optional[str]:
    """在指定时间戳提取一帧

    Args:
        video_path: 视频文件路径
        second: 时间戳（秒）
        output_dir: 输出目录
        quality: JPEG质量 (1-31, 越小越好)

    Returns:
        提取的帧文件路径，如果失败则返回None
    """
    output_filename = f"frame_{second:04d}s.jpg"
    output_path = os.path.join(output_dir, output_filename)

    # 如果文件已存在，跳过
    if os.path.exists(output_path):
        return output_path

    # 使用FFmpeg提取单帧
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-ss', str(second),      # 时间戳（秒）
        '-vframes', '1',          # 提取1帧
        '-q:v', str(quality),     # JPEG质量
        '-loglevel', 'error',     # 减少日志输出
        output_path,
        '-y'                      # 覆盖输出
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"警告: 提取第{second}秒的帧失败: {e}")
        return None