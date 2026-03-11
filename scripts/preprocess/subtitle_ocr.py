"""
字幕OCR识别模块 - 使用OCR识别字幕内容并检测敏感词

功能：
1. 对视频帧进行OCR识别字幕内容
2. 检测字幕中的敏感词
3. 返回敏感词出现的时间段

使用方法：
    from scripts.preprocess.subtitle_ocr import (
        extract_subtitle_text,
        detect_sensitive_words_in_subtitles
    )

    # 提取字幕文本
    subtitle_segments = extract_subtitle_text(video_path, subtitle_region)

    # 检测敏感词
    sensitive_segments = detect_sensitive_words_in_subtitles(subtitle_segments, sensitive_words)
"""

import cv2
import numpy as np
from PIL import Image
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from .subtitle_detector import SubtitleRegion
from .sensitive_detector import SensitiveSegment


@dataclass
class SubtitleSegment:
    """字幕片段 - OCR识别的字幕内容"""
    start_time: float        # 开始时间（秒）
    end_time: float          # 结束时间（秒）
    text: str               # 字幕文本
    frame_idx: int          # 帧索引

    def __repr__(self):
        return f"SubtitleSegment({self.start_time:.1f}s-{self.end_time:.1f}s, '{self.text[:20]}...')"


def extract_subtitle_text(
    video_path: str,
    subtitle_region: SubtitleRegion,
    sample_fps: float = 1.0,  # 每秒采样帧数
    verbose: bool = True
) -> List[SubtitleSegment]:
    """
    对视频帧进行OCR识别字幕内容

    Args:
        video_path: 视频文件路径
        subtitle_region: 字幕区域配置
        sample_fps: 采样帧率（每秒采样多少帧）
        verbose: 是否打印详细信息

    Returns:
        字幕片段列表
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang='ch', show_log=False)
    except ImportError:
        print("⚠️ PaddleOCR未安装，无法进行OCR识别")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {video_path}")
        return []

    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    if verbose:
        print(f"  📹 视频: {width}x{height}, {fps}fps, {total_frames}帧")
        print(f"  🔍 字幕区域: y={subtitle_region.y_ratio:.1%}, h={subtitle_region.height_ratio:.1%}")

    # 计算字幕区域像素坐标
    y_start = int(height * subtitle_region.y_ratio)
    y_end = y_start + int(height * subtitle_region.height_ratio)

    # 采样间隔
    sample_interval = int(fps / sample_fps)

    if verbose:
        print(f"  📝 OCR采样: 每{sample_interval}帧采样1帧 (约{sample_fps}fps)")

    # 提取帧并OCR识别
    subtitle_segments = []
    last_text = None
    segment_start_frame = 0

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 只处理采样帧
        if frame_idx % sample_interval == 0:
            # 裁剪字幕区域
            subtitle_area = frame[y_start:y_end, :]

            # OCR识别
            try:
                result = ocr.ocr(subtitle_area, cls=True)

                # 提取文本
                if result and result[0]:
                    texts = [line[1][0] for line in result[0]]
                    current_text = ''.join(texts)
                else:
                    current_text = ""

                # 检测字幕变化
                if current_text != last_text:
                    # 保存上一个字幕段
                    if last_text:
                        subtitle_segments.append(SubtitleSegment(
                            start_time=segment_start_frame / fps,
                            end_time=frame_idx / fps,
                            text=last_text,
                            frame_idx=segment_start_frame
                        ))

                    # 开始新字幕段
                    if current_text:
                        segment_start_frame = frame_idx
                        last_text = current_text
                    else:
                        last_text = None
                        segment_start_frame = frame_idx + 1

            except Exception as e:
                if verbose:
                    print(f"  ⚠️ 帧OCR失败: {e}")

        frame_idx += 1

    cap.release()

    # 保存最后一个字幕段
    if last_text:
        subtitle_segments.append(SubtitleSegment(
            start_time=segment_start_frame / fps,
            end_time=frame_idx / fps,
            text=last_text,
            frame_idx=segment_start_frame
        ))

    if verbose:
        print(f"  ✅ OCR识别完成: 共{len(subtitle_segments)}个字幕片段")

    return subtitle_segments


def detect_sensitive_words_in_subtitles(
    subtitle_segments: List[SubtitleSegment],
    sensitive_words: Set[str],
    episode: int = 1,
    verbose: bool = True
) -> List[SensitiveSegment]:
    """
    检测字幕中的敏感词

    Args:
        subtitle_segments: 字幕片段列表
        sensitive_words: 敏感词集合
        episode: 集数
        verbose: 是否打印详细信息

    Returns:
        敏感词片段列表
    """
    if not sensitive_words:
        if verbose:
            print("⚠️ 敏感词列表为空，跳过检测")
        return []

    results = []

    for seg in subtitle_segments:
        # 检查每个敏感词
        for word in sensitive_words:
            if word in seg.text:
                results.append(SensitiveSegment(
                    episode=episode,
                    sensitive_word=word,
                    asr_text=seg.text,  # 这里是字幕文本，不是ASR
                    start_time=seg.start_time,
                    end_time=seg.end_time
                ))
                if verbose:
                    print(f"  🔍 [{seg.start_time:.1f}s-{seg.end_time:.1f}s] 发现敏感词'{word}'")
                    print(f"     字幕原文: {seg.text}")

    if verbose:
        if results:
            print(f"\n📊 敏感词检测完成: 共发现 {len(results)} 个敏感片段")
        else:
            print("\n📊 敏感词检测完成: 未发现敏感词")

    return results


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("字幕OCR识别模块测试")
    print("=" * 60)

    # 测试视频
    test_video = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    from .subtitle_detector import detect_subtitle_region_pixel_variance

    # 检测字幕区域
    print("\n检测字幕区域...")
    subtitle_region = detect_subtitle_region_pixel_variance(test_video)

    # 提取字幕文本
    print("\n提取字幕文本...")
    subtitle_segments = extract_subtitle_text(test_video, subtitle_region, sample_fps=2.0)

    print(f"\n提取了 {len(subtitle_segments)} 个字幕片段")

    # 显示前10个
    for seg in subtitle_segments[:10]:
        print(f"  [{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.text}")
