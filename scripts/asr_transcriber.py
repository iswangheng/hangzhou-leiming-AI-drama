"""
ASR转录模块

使用Whisper库转录视频音频，提取对白/旁白内容
用于辅助判断片尾
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
import json

from scripts.utils.subprocess_utils import run_command
from scripts.config import TimeoutConfig


class ASRTranscriber:
    """ASR转录器"""

    def __init__(self, model_size: str = "base"):
        """
        初始化ASR转录器

        Args:
            model_size: Whisper模型大小 (tiny/base/small/medium/large)
        """
        self.model_size = model_size
        self.model = None

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            import whisper
            print(f"  [ASR] 加载Whisper模型 ({self.model_size})...")
            self.model = whisper.load_model(self.model_size)
            print(f"  [ASR] 模型加载完成")

    def transcribe_video_segment(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        转录视频指定时间段

        Args:
            video_path: 视频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            language: 语言代码

        Returns:
            ASR片段列表
        """
        # 延迟加载模型
        self._load_model()

        # 计算时长
        duration = end_time - start_time

        if duration <= 0:
            return []

        print(f"  [ASR] 转录片段: {start_time:.2f}s → {end_time:.2f}s (时长{duration:.2f}s)")

        # 先用ffmpeg提取音频片段
        temp_audio = f"/tmp/temp_audio_{start_time:.0f}.wav"

        try:
            # 使用ffmpeg提取音频片段
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-vn',  # 不处理视频
                '-acodec', 'pcm_s16le',  # 使用PCM编码
                '-ar', '16000',  # 16kHz采样率
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                temp_audio
            ]

            result = run_command(
                cmd,
                timeout=TimeoutConfig.FFMPEG_AUDIO_EXTRACT,
                retries=1,
                error_msg="asr音频提取超时"
            )
            if result is None or result.returncode != 0:
                err = result.stderr if result is not None else "超时"
                print(f"  [ASR] 音频提取失败: {err}")
                return []

            # 使用Whisper转录音频片段
            result = self.model.transcribe(
                temp_audio,
                language=language,
                word_timestamps=True
            )

            # 提取片段并调整时间戳（加上start_time）
            segments = []
            for seg in result['segments']:
                segments.append({
                    'start': start_time + seg['start'],
                    'end': start_time + seg['end'],
                    'text': seg['text'].strip(),
                    'duration': seg['end'] - seg['start']
                })

            print(f"  [ASR] 识别到 {len(segments)} 个片段")
            for i, seg in enumerate(segments):
                print(f"    [{i+1}] {seg['start']:.2f}s-{seg['end']:.2f}s: {seg['text'][:50]}")

            # 清理临时文件
            if Path(temp_audio).exists():
                Path(temp_audio).unlink()

            return segments

        except Exception as e:
            print(f"  [ASR] 转录失败: {e}")
            # 清理临时文件
            if Path(temp_audio).exists():
                Path(temp_audio).unlink()
            return []

    def transcribe_last_seconds(
        self,
        video_path: str,
        seconds: float = 3.5,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        转录视频最后几秒

        Args:
            video_path: 视频文件路径
            seconds: 转录最后几秒
            language: 语言代码

        Returns:
            ASR片段列表
        """
        # 获取视频总时长
        total_duration = self._get_video_duration(video_path)

        # 计算开始时间
        start_time = max(0, total_duration - seconds)

        return self.transcribe_video_segment(
            video_path,
            start_time,
            total_duration,
            language
        )

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频总时长"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = run_command(
            cmd,
            timeout=TimeoutConfig.FFPROBE_QUICK,
            retries=1,
            error_msg="ffprobe获取视频时长超时"
        )
        if result is None or result.returncode != 0:
            raise RuntimeError(f"无法获取视频时长: {video_path}")

        return float(result.stdout.strip())


# 便捷函数
def transcribe_video_ending(
    video_path: str,
    seconds: float = 3.5,
    model_size: str = "base"
) -> List[Dict[str, Any]]:
    """
    转录视频片尾部分的音频

    Args:
        video_path: 视频文件路径
        seconds: 转录最后几秒
        model_size: Whisper模型大小

    Returns:
        ASR片段列表
    """
    transcriber = ASRTranscriber(model_size=model_size)
    return transcriber.transcribe_last_seconds(video_path, seconds)


if __name__ == "__main__":
    # 测试
    print("=" * 80)
    print("🧪 测试ASR转录功能")
    print("=" * 80)

    # 测试视频
    test_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧/1.mp4"

    if Path(test_video).exists():
        segments = transcribe_video_ending(test_video, seconds=3.5)

        print(f"\n转录结果:")
        print(f"  片段数: {len(segments)}")

        if segments:
            print(f"  总文本: {' '.join(seg['text'] for seg in segments)}")
    else:
        print(f"测试视频不存在: {test_video}")
