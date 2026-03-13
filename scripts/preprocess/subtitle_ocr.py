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
    boxes: List = None       # 每个文字的box坐标列表

    def __post_init__(self):
        if self.boxes is None:
            self.boxes = []

    def __repr__(self):
        return f"SubtitleSegment({self.start_time:.1f}s-{self.end_time:.1f}s, '{self.text[:20]}...')"


def extract_subtitle_text_with_boxes(
    video_path: str,
    subtitle_region: SubtitleRegion,
    sample_fps: float = 5.0,  # 每秒采样帧数
    verbose: bool = True
) -> List[SubtitleSegment]:
    """
    对视频帧进行OCR识别，返回每个文字的box坐标

    Args:
        video_path: 视频文件路径
        subtitle_region: 字幕区域配置
        sample_fps: 采样帧率（每秒采样多少帧）
        verbose: 是否打印详细信息

    Returns:
        字幕片段列表，每个片段包含文字的box坐标
        格式: [
            {
                'text': '高温末世',
                'boxes': [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ...],  # 每个字的box
                'start_time': 19.6,
                'end_time': 20.6
            },
            ...
        ]
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang='ch')
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

    # 提取帧并OCR识别（带box坐标）
    subtitle_segments = []
    last_text = None
    last_boxes = None
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
                result = ocr.ocr(subtitle_area)

                current_text = ""
                current_boxes = []

                if result and len(result) > 0:
                    # PaddleOCR 3.x 返回格式: dict with 'rec_texts' and 'rec_boxes'
                    ocr_result = result[0]

                    # 检查是否是新版格式
                    if isinstance(ocr_result, dict):
                        rec_texts = ocr_result.get('rec_texts', [])
                        # 优先使用 rec_polys，它包含了四个顶点坐标
                        rec_boxes_data = ocr_result.get('rec_polys', ocr_result.get('rec_boxes', []))

                        # 收集所有行的文字和box
                        for text, box in zip(rec_texts, rec_boxes_data):
                            current_text += text
                            if not text: continue
                            
                            # 转为普通的 list
                            if hasattr(box, 'tolist'):
                                box = box.tolist()

                            # 假设是四点坐标: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            if len(box) == 4 and isinstance(box[0], (list, tuple)) and len(box[0]) == 2:
                                p0, p1, p2, p3 = box[0], box[1], box[2], box[3]
                                char_w = (p1[0] - p0[0]) / len(text)
                                for i, char in enumerate(text):
                                    cx1 = p0[0] + i * char_w
                                    cx2 = p0[0] + (i + 1) * char_w
                                    cx3 = p3[0] + (i + 1) * char_w
                                    cx4 = p3[0] + i * char_w
                                    current_boxes.append([[cx1, p0[1]], [cx2, p1[1]], [cx3, p2[1]], [cx4, p3[1]]])
                            # 如果是两点或长度等: [x1, y1, x2, y2]
                            elif len(box) == 4 and isinstance(box[0], (int, float)):
                                x1, y1, x2, y2 = box
                                char_w = (x2 - x1) / len(text)
                                for i, char in enumerate(text):
                                    cx1 = x1 + i * char_w
                                    cx2 = x1 + (i + 1) * char_w
                                    current_boxes.append([[cx1, y1], [cx2, y1], [cx2, y2], [cx1, y2]])
                    else:
                        # 旧版格式兼容: [[[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], "文字", 置信度], ...]
                        for line in ocr_result:
                            if len(line) >= 2:
                                box = line[0]
                                text = line[1][0] if isinstance(line[1], tuple) else line[1]
                                current_text += text
                                if not text: continue
                                p0, p1, p2, p3 = box[0], box[1], box[2], box[3]
                                char_w = (p1[0] - p0[0]) / len(text)
                                for i, char in enumerate(text):
                                    cx1 = p0[0] + i * char_w
                                    cx2 = p0[0] + (i + 1) * char_w
                                    cx3 = p3[0] + (i + 1) * char_w
                                    cx4 = p3[0] + i * char_w
                                    current_boxes.append([[cx1, p0[1]], [cx2, p1[1]], [cx3, p2[1]], [cx4, p3[1]]])

                # 检测字幕变化
                if current_text != last_text:
                    # 保存上一个字幕段
                    if last_text:
                        subtitle_segments.append(SubtitleSegment(
                            start_time=segment_start_frame / fps,
                            end_time=frame_idx / fps,
                            text=last_text,
                            frame_idx=segment_start_frame,
                            boxes=last_boxes.copy() if last_boxes else []
                        ))

                    # 开始新字幕段
                    if current_text:
                        segment_start_frame = frame_idx
                        last_text = current_text
                        last_boxes = current_boxes.copy() if current_boxes else []
                    else:
                        last_text = None
                        last_boxes = None
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
            frame_idx=segment_start_frame,
            boxes=last_boxes.copy() if last_boxes else []
        ))

    if verbose:
        print(f"  ✅ OCR识别完成: 共{len(subtitle_segments)}个字幕片段")

    return subtitle_segments


def extract_subtitle_text(
    video_path: str,
    subtitle_region: SubtitleRegion,
    sample_fps: float = 5.0,  # 每秒采样帧数，5fps提高时间精度
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
        # PaddleOCR 3.x 版本
        ocr = PaddleOCR(lang='ch')
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
                result = ocr.ocr(subtitle_area)

                # PaddleOCR 3.x 返回格式: [dict], 包含 rec_texts 和 rec_scores
                current_text = ""
                current_boxes = []

                if result and len(result) > 0:
                    # 处理 3.x 格式
                    if isinstance(result[0], dict):
                        rec_texts = result[0].get('rec_texts', [])
                        if rec_texts:
                            # 拼接多行文本（处理换行情况）
                            current_text = ''.join(rec_texts)
                    else:
                        # 旧格式兼容 - 同时收集box信息
                        texts = []
                        for line in result[0]:
                            if len(line) >= 2:
                                texts.append(line[1][0] if isinstance(line[1], tuple) else line[1])
                                if len(line) >= 1:
                                    current_boxes.append(line[0])
                        current_text = ''.join(texts)

                # 检测字幕变化
                if current_text != last_text:
                    # 保存上一个字幕段
                    if last_text:
                        subtitle_segments.append(SubtitleSegment(
                            start_time=segment_start_frame / fps,
                            end_time=frame_idx / fps,
                            text=last_text,
                            frame_idx=segment_start_frame,
                            boxes=last_boxes.copy() if last_boxes else []
                        ))

                    # 开始新字幕段
                    if current_text:
                        segment_start_frame = frame_idx
                        last_text = current_text
                        last_boxes = current_boxes.copy() if current_boxes else []
                    else:
                        last_text = None
                        last_boxes = None
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
            frame_idx=segment_start_frame,
            boxes=last_boxes.copy() if last_boxes else []
        ))

    if verbose:
        print(f"  ✅ OCR识别完成: 共{len(subtitle_segments)}个字幕片段")

    return subtitle_segments


def get_word_boxes_for_sensitive_word(
    full_text: str,
    boxes: List[List[float]],
    sensitive_word: str
) -> Tuple[List[List[List[float]]], bool]:
    """
    从完整字幕的boxes中找出敏感词对应的文字框坐标

    Args:
        full_text: 完整字幕文本
        boxes: 每个文字的box坐标列表
        sensitive_word: 敏感词

    Returns:
        (文字框坐标列表, 是否找到匹配)
    """
    if not full_text or not boxes or not sensitive_word:
        return [], False

    word_len = len(sensitive_word)
    found_idx = -1
    
    # 1. 精确匹配
    if sensitive_word in full_text:
        found_idx = full_text.index(sensitive_word)
    else:
        # 2. 模糊匹配 (长度>=3时允许1个错别字)
        if word_len >= 3:
            for i in range(len(full_text) - word_len + 1):
                substr = full_text[i:i + word_len]
                errors = sum(1 for a, b in zip(substr, sensitive_word) if a != b)
                if errors <= 1:
                    found_idx = i
                    break

    if found_idx != -1:
        if found_idx < len(boxes):
            end_idx = min(found_idx + word_len, len(boxes))
            return boxes[found_idx:end_idx], True
            
    return [], False


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
        敏感词片段列表，每个片段包含文字框坐标（用于精确遮罩）
    """
    if not sensitive_words:
        if verbose:
            print("⚠️ 敏感词列表为空，跳过检测")
        return []

    results = []

    for seg in subtitle_segments:
        # 检查每个敏感词
        for word in sensitive_words:
            word_boxes, is_match = get_word_boxes_for_sensitive_word(
                seg.text,
                seg.boxes,
                word
            )
            
            if is_match:
                results.append(SensitiveSegment(
                    episode=episode,
                    sensitive_word=word,
                    asr_text=seg.text,  # 这里是字幕文本，不是ASR
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    boxes=word_boxes if word_boxes else []
                ))
                if verbose:
                    print(f"  🔍 [{seg.start_time:.1f}s-{seg.end_time:.1f}s] 发现敏感词'{word}'")
                    print(f"     字幕原文: {seg.text}")
                    print(f"     文字框数量: {len(word_boxes)}")

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
