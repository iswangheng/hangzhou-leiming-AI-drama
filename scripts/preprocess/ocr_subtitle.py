"""
OCR字幕识别模块

功能：
1. 对视频帧进行OCR识别字幕文本
2. 检测字幕中的敏感词
3. 返回敏感词出现的时间戳

使用方法：
    from scripts.preprocess.ocr_subtitle import (
        detect_sensitive_words_from_ocr
    )

    # 检测字幕中的敏感词
    video_path = "path/to/video.mp4"
    sensitive_words = {"死", "杀", "血"}
    subtitle_region = SubtitleRegion(...)  # 字幕区域
    sample_fps = 1.0  # 采样帧率（每秒1帧）

    segments = detect_sensitive_words_from_ocr(
        video_path=video_path,
        sensitive_words=sensitive_words,
        subtitle_region=subtitle_region
    )
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Set, Optional, Tuple
from dataclasses import dataclass
import json

from .subtitle_detector import SubtitleRegion


@dataclass
class SubtitleSegment:
    """字幕片段 - OCR识别的字幕内容"""
    start_time: float        # 开始时间（秒）
    end_time: float          # 结束时间（秒）
    subtitle_text: str      # 字幕文本
    sensitive_word: str       # 检测到的敏感词
    frame_idx: int            # 帧索引

    def __repr__(self):
        return f"SubtitleSegment({self.start_time:.1f}s-{self.end_time:.1f}s, '{self.subtitle_text[:20]}...')"


def extract_frames_for_ocr(
    video_path: str,
    sample_fps: float = 1.0,
    output_dir: Optional[str] = None
) -> List[Tuple[int, np.ndarray, float]]:
    """
    提取视频帧用于OCR识别

    Args:
        video_path: 视频文件路径
        sample_fps: 采样帧率（每秒采样多少帧）
        output_dir: 输出目录（可选，用于保存帧图片）

    Returns:
        寧列表 [(帧索引, 帧图像, 时间戳)]
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 计算采样间隔
    sample_interval = max(1, int(fps / sample_fps))

    frames = []
    for i in range(0, total_frames, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            timestamp = i / fps
            frames.append((i, frame, timestamp))

            # 保存帧图片（如果指定了输出目录）
            if output_dir:
                output_path = Path(output_dir) / f"frame_{i:06d}.jpg"
                cv2.imwrite(str(output_path), frame)

    cap.release()
    return frames


def init_ocr_engine():
    """初始化OCR引擎"""
    try:
        # 尝试导入EasyOCR（更轻量级）
        from easyocr import Reader
        ocr = Reader(['ch_sim', 'en'], gpu=False)
        return ocr
    except ImportError:
        print("⚠️ EasyOCR未安装，尝试使用PaddleOCR...")
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
            return ocr
        except ImportError:
            print("⚠️ PaddleOCR未安装")
            return None
        except Exception as e:
            print(f"⚠️ OCR初始化失败: {e}")
            return None


def ocr_subtitle_region(
    frame: np.ndarray,
    subtitle_region: SubtitleRegion,
    ocr_engine
) -> Optional[str]:
    """
    对帧的指定字幕区域进行OCR识别

    Args:
        frame: 帧图像
        subtitle_region: 字幕区域配置
        ocr_engine: OCR引擎

    Returns:
        识别到的字幕文本（如果没有字幕返回None）
    """
    h, w = frame.shape[:2]

    # 提取字幕区域
    y = int(h * subtitle_region.y_ratio)
    region_h = int(h * subtitle_region.height_ratio)
    subtitle_img = frame[y:y+region_h, :]

    # OCR识别
    try:
        if hasattr(ocr_engine, 'readtext'):  # EasyOCR
            result = ocr_engine.readtext(subtitle_img)
            if result:
                texts = [line[1] for line in result]
                return ' '.join(texts) if texts else None
        else:  # PaddleOCR
            result = ocr_engine.ocr(subtitle_img)
            if result and result[0]:
                texts = []
                for line in result[0]:
                    if line[1][0]:  # line[1][0] 是文字识别结果
                        texts.append(line[1][0])
                if texts:
                    return ' '.join(texts)
                return None
    except Exception as e:
        print(f"OCR识别失败: {e}")
        return None


    return None


def detect_sensitive_words_from_ocr(
    video_path: str,
    sensitive_words: Set[str],
    subtitle_region: SubtitleRegion,
    sample_fps: float = 1.0,
    verbose: bool = True,
    output_dir: Optional[str] = None
) -> List[SubtitleSegment]:
    """
    对视频进行OCR字幕识别，检测敏感词

    Args:
        video_path: 视频文件路径
        sensitive_words: 敏感词集合
        subtitle_region: 字幕区域配置
        sample_fps: 采样帧率（每秒采样多少帧）
        verbose: 是否打印详细信息
        output_dir: 输出目录（可选，用于保存标注图）

    Returns:
        敏感词片段列表
    """
    if verbose:
        print("=" * 60)
        print("OCR字幕识别 - 敏感词检测")
        print("=" * 60)
        print(f"视频: {video_path}")
        print(f"敏感词: {sensitive_words}")
        print(f"采样率: {sample_fps} fps (每秒{sample_fps}帧)")

    # 初始化OCR引擎
    ocr_engine = init_ocr_engine()
    if ocr_engine is None:
        print("❌ OCR引擎初始化失败")
        return []

    # 提取视频帧
    if verbose:
        print("\n提取视频帧...")

    frames = extract_frames_for_ocr(video_path, sample_fps, output_dir)

    if not frames:
        print("❌ 未提取到任何帧")
        return []

    if verbose:
        print(f"提取了 {len(frames)} 帧")

    # 获取视频FPS
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    # 对每帧进行OCR识别
    all_subtitle_segments = []

    for frame_idx, frame, timestamp in frames:
        # 对字幕区域进行OCR识别
        subtitle_text = ocr_subtitle_region(frame, subtitle_region, ocr_engine)

        if subtitle_text:
            # 检查是否包含敏感词
            for word in sensitive_words:
                if word in subtitle_text:
                    # 记录敏感词片段
                    segment = SubtitleSegment(
                        start_time=timestamp,
                        end_time=timestamp + 1.0 / sample_fps,
                        subtitle_text=subtitle_text,
                        sensitive_word=word,
                        frame_idx=frame_idx
                    )
                    all_subtitle_segments.append(segment)

                    if verbose:
                        print(f"  帧 {frame_idx} ({timestamp:.1f}s): 发现敏感词 '{word}'")
                        print(f"     字幕: {subtitle_text}")

                    # 生成标注图（如果指定了输出目录）
                    if output_dir:
                        _generate_annotation_frame(
                            frame, frame_idx, subtitle_text, subtitle_region,
                            output_dir
                        )

    # 合并连续的敏感词片段
    if not all_subtitle_segments:
        return []

    merged_segments = _merge_continuous_segments(all_subtitle_segments, gap_threshold=1.0)

    if verbose:
        print(f"\n检测到 {len(merged_segments)} 个敏感词片段（已合并连续片段）")

    return merged_segments


def _merge_continuous_segments(
    segments: List[SubtitleSegment],
    gap_threshold: float = 1.0
) -> List[SubtitleSegment]:
    """
    合并连续的敏感词片段

    Args:
        segments: 敏感词片段列表
        gap_threshold: 间隔阈值（秒），如果间隔小于这个阈值，则认为是同一个敏感词

    Returns:
        合并后的片段列表
    """
    if not segments:
        return []

    # 按时间排序
    segments.sort(key=lambda x: x.start_time)

    merged = []

    for seg in segments:
        if not merged:
            merged.append(seg)
        else:
            # 检查与上一个片段的间隔
            if seg.start_time - merged[-1].end_time <= gap_threshold:
                # 合并到上一个片段
                merged[-1] = SubtitleSegment(
                    start_time=merged[-1].start_time,
                    end_time=seg.end_time,
                    subtitle_text=f"{merged[-1].subtitle_text} {seg.subtitle_text}",
                    sensitive_word=seg.sensitive_word,
                    frame_idx=merged[-1].frame_idx
                )
            else:
                # 创建新片段
                merged.append(seg)

    return merged


def _generate_annotation_frame(
    frame: np.ndarray,
    frame_idx: int,
    subtitle_text: str,
    subtitle_region: SubtitleRegion,
    output_dir: str
) -> str:
    """生成标注帧（保存到文件）"""
    from PIL import Image, ImageDraw, ImageFont

    # 从BGR转RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 转换为PIL图像
    img = Image.fromarray(rgb_frame)
    draw = ImageDraw.Draw(img)

    h, w = frame.shape[:2]
    y = int(h * subtitle_region.y_ratio)
    region_h = int(h * subtitle_region.height_ratio)

    # 红框标注字幕区域
    draw.rectangle(
        [(0, y), (w, y + region_h)],
        outline=(255, 0, 0),
        width=2
    )

    # 标注字幕文本
    font = None
    try:
        font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 16)
    except:
        pass

    # 显示字幕文本（截断）
    display_text = subtitle_text[:50] + "..." if len(subtitle_text) > 50 else subtitle_text
    draw.text((10, y + region_h + 10), display_text, fill=(255, 0, 0), font=font)

    # 保存
    output_path = Path(output_dir) / f"frame_{frame_idx}_annotated.jpg"
    img.save(output_path)

    return str(output_path)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("OCR字幕识别模块测试")
    print("=" * 60)

    # 测试《烈日重生》
    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    import os
    if not os.path.exists(video_path):
        print(f"视频不存在: {video_path}")
    else:
        # 模拟字幕区域
        subtitle_region = SubtitleRegion(
            y_ratio=0.60,
            height_ratio=0.061,
            detection_method="pixel_variance",
            confidence=0.95
        )

        # 测试敏感词
        sensitive_words = {"死", "杀", "血", "尸体", "干尸"}

        result = detect_sensitive_words_from_ocr(
            video_path=video_path,
            sensitive_words=sensitive_words,
            subtitle_region=subtitle_region,
            sample_fps=1.0,
            verbose=True,
            output_dir="test/temp/ocr_test"
        )

        if result:
            print("\n✅ 测试完成!")
            for seg in result:
                print(f"  [{seg.start_time:.1f}s - {seg.end_time:.1f}s] '{seg.subtitle_text}'")
        else:
            print("\n❌ 未检测到敏感词")
