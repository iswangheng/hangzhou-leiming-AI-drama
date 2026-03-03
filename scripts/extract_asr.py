"""
ASR转录模块 - 使用Whisper进行音频转录
"""
import subprocess
import os
import json
from pathlib import Path
from typing import List, Optional
import hashlib
import whisper

from .data_models import ASRSegment
from .config import TrainingConfig


def extract_audio(video_path: str, audio_path: str) -> str:
    """从视频提取音频

    Args:
        video_path: 视频文件路径
        audio_path: 输出音频文件路径

    Returns:
        音频文件路径

    Raises:
        FileNotFoundError: 视频文件不存在
        subprocess.CalledProcessError: FFmpeg执行失败
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    # 使用FFmpeg提取音频
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # 不包含视频
        '-acodec', 'pcm_s16le',  # 音频编码
        '-ar', str(TrainingConfig.ASR_SAMPLE_RATE),  # 采样率
        '-ac', '1',  # 单声道
        '-loglevel', 'error',  # 减少日志输出
        audio_path,
        '-y'  # 覆盖输出
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"音频提取完成: {audio_path}")
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg错误: {e.stderr}")
        raise
    except FileNotFoundError:
        raise FileNotFoundError(
            "未找到FFmpeg命令。请确保已安装FFmpeg并添加到PATH环境变量中。"
        )


def transcribe_audio(
    audio_path: str,
    output_path: str,
    model: str = TrainingConfig.ASR_MODEL,
    language: str = TrainingConfig.ASR_LANGUAGE,
    force_retranscribe: bool = False
) -> List[ASRSegment]:
    """ASR 音频转录

    使用 Whisper 转录
    whisper audio.wav --language zh --model tiny --output_json

    Args:
        audio_path: 音频文件路径
        output_path: 输出JSON文件路径
        model: Whisper模型大小
        language: 语言代码
        force_retranscribe: 是否强制重新转录

    Returns:
        ASR片段列表

    Raises:
        FileNotFoundError: 音频文件不存在
        subprocess.CalledProcessError: Whisper执行失败
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    # 检查是否已有转录文件
    if not force_retranscribe and os.path.exists(output_path):
        print(f"使用已缓存的转录文件: {output_path}")
        return load_asr_from_file(output_path)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"开始转录音频: {audio_path}")
    print(f"参数: model={model}, language={language}")

    # 使用 Whisper Python 库进行转录
    print(f"开始转录音频: {audio_path}")
    print(f"参数: model={model}, language={language}")
    
    try:
        # 加载模型
        whisper_model = whisper.load_model(model)
        
        # 转录
        result = whisper_model.transcribe(
            audio_path,
            language=language,
            task='transcribe'
        )
        
        # 保存结果到JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"音频转录完成")
        
    except Exception as e:
        print(f"Whisper错误: {e}")
        raise

    # 读取结果
    return load_asr_from_file(output_path)


def load_asr_from_file(json_path: str) -> List[ASRSegment]:
    """从JSON文件加载ASR结果

    Args:
        json_path: JSON文件路径

    Returns:
        ASR片段列表
    """
    if not os.path.exists(json_path):
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = []
    for seg in data.get('segments', []):
        segments.append(ASRSegment(
            text=seg.get('text', '').strip(),
            start=seg.get('start', 0.0),
            end=seg.get('end', 0.0)
        ))

    print(f"加载了 {len(segments)} 个ASR片段")
    return segments


def get_audio_output_path(project_name: str, episode_number: int) -> str:
    """获取音频文件输出路径"""
    cache_dir = TrainingConfig.CACHE_DIR / "audio" / project_name
    return str(cache_dir / f"{episode_number}.wav")


def get_asr_output_path(project_name: str, episode_number: int) -> str:
    """获取ASR转录文件输出路径"""
    # 使用项目名映射
    from scripts.config import get_cache_project_name
    cache_name = get_cache_project_name(project_name)
    cache_dir = TrainingConfig.CACHE_DIR / "asr" / cache_name
    return str(cache_dir / f"{episode_number}.json")


def clear_asr_cache(project_name: Optional[str] = None, episode_number: Optional[int] = None):
    """清除ASR缓存

    Args:
        project_name: 项目名称，如果为None则清除所有项目
        episode_number: 集数编号，如果为None则清除项目所有集数
    """
    # 清除音频缓存
    audio_cache_dir = TrainingConfig.CACHE_DIR / "audio"
    asr_cache_dir = TrainingConfig.CACHE_DIR / "asr"

    for cache_dir, cache_type in [(audio_cache_dir, "音频"), (asr_cache_dir, "ASR转录")]:
        if project_name is None:
            # 清除所有缓存
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                print(f"已清除所有{cache_type}缓存")
        else:
            project_dir = cache_dir / project_name
            if episode_number is None:
                # 清除项目的所有缓存
                if project_dir.exists():
                    import shutil
                    shutil.rmtree(project_dir)
                    print(f"已清除项目 {project_name} 的所有{cache_type}缓存")
            else:
                # 清除指定集数的缓存
                audio_file = project_dir / f"{episode_number}.wav"
                asr_file = project_dir / f"{episode_number}.json"

                for file_path in [audio_file, asr_file]:
                    if file_path.exists():
                        file_path.unlink()
                        print(f"已清除 {file_path}")


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS, create_directories
    from .read_excel import load_project_markings, validate_markings, get_unique_episodes

    create_directories()

    if PROJECTS:
        project = PROJECTS[0]
        print(f"测试ASR转录: {project.name}")

        try:
            # 读取标记数据
            markings = load_project_markings(project)
            valid_markings = validate_markings(markings, project)

            if valid_markings:
                # 获取第一个有标记的集数
                episode_number = sorted(get_unique_episodes(valid_markings))[0]

                # 获取视频路径
                video_path = project.get_video_path(episode_number)

                # 提取音频
                audio_path = get_audio_output_path(project.name, episode_number)
                extract_audio(video_path, audio_path)

                # 转录音频
                asr_path = get_asr_output_path(project.name, episode_number)
                segments = transcribe_audio(audio_path, asr_path)

                print(f"转录了 {len(segments)} 个片段")
                if segments:
                    print(f"第一个片段: {segments[0].text}")
                    print(f"时间范围: {segments[0].start:.2f}s - {segments[0].end:.2f}s")

        except Exception as e:
            print(f"错误: {e}")