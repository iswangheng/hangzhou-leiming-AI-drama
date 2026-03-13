"""
字幕区域检测模块

功能：
1. 像素变化检测法（最可靠，置信度95%）- 分析多帧像素变化，变化大的区域=字幕
2. Gemini视觉分析检测（备选方案）
3. OCR检测（备选方案）
4. 默认比例检测（底部10-12%区域，最后备选）
5. 保存/加载检测结果

检测策略（按优先级）：
    像素变化检测 → Gemini → OCR → 默认比例

使用方法：
    from scripts.preprocess.subtitle_detector import (
        detect_subtitle_region,
        SubtitleRegion
    )

    # 检测字幕区域（推荐提供video_path以使用像素变化检测法）
    region = detect_subtitle_region(keyframe_paths, video_path="/path/to/video.mp4")

    # 获取像素坐标
    y, height = region.get_pixel_coords(video_height)
"""

import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, asdict

from scripts.utils.subprocess_utils import run_command
from scripts.config import TimeoutConfig


@dataclass
class SubtitleRegion:
    """字幕区域配置"""
    y_ratio: float           # Y位置比例 (0-1)，相对于视频高度
    height_ratio: float      # 高度比例 (0-1)，相对于视频高度
    detection_method: str    # 检测方法: "gemini", "ocr", "default"
    confidence: float        # 置信度 (0-1)

    def get_pixel_coords(self, video_height: int) -> Tuple[int, int]:
        """
        获取像素坐标

        Args:
            video_height: 视频高度（像素）

        Returns:
            (y, height) 像素坐标
        """
        y = int(video_height * self.y_ratio)
        height = int(video_height * self.height_ratio)
        return y, height

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SubtitleRegion':
        """从字典创建"""
        return cls(
            y_ratio=data['y_ratio'],
            height_ratio=data['height_ratio'],
            detection_method=data.get('detection_method', 'unknown'),
            confidence=data.get('confidence', 0.0)
        )

    def __repr__(self):
        return f"SubtitleRegion(y={self.y_ratio:.2%}, h={self.height_ratio:.2%}, method={self.detection_method}, conf={self.confidence:.0%})"


def get_video_resolution(video_path: str) -> Tuple[int, int]:
    """
    获取视频分辨率

    Args:
        video_path: 视频文件路径

    Returns:
        (width, height) 视频分辨率
    """
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0',
        video_path
    ]

    result = run_command(
        cmd,
        timeout=TimeoutConfig.FFPROBE_QUICK,
        retries=1,
        error_msg=f"ffprobe获取分辨率超时: {video_path}"
    )
    if result is None or result.returncode != 0:
        print(f"⚠️ 无法获取视频分辨率: {video_path}")
        return 1920, 1080  # 默认返回1080p

    width, height = map(int, result.stdout.strip().split(','))
    return width, height


def detect_subtitle_region_default() -> SubtitleRegion:
    """
    默认比例检测

    大部分视频字幕位于底部10-12%区域

    Returns:
        SubtitleRegion
    """
    return SubtitleRegion(
        y_ratio=0.88,           # 字幕顶部位置（底部12%区域）
        height_ratio=0.10,      # 字幕高度（10%高度）
        detection_method="default",
        confidence=0.5          # 默认方案置信度较低
    )


def detect_subtitle_region_pixel_variance(video_path: str, verbose: bool = True) -> SubtitleRegion:
    """
    像素变化检测法（最可靠）

    原理：
    1. 提取多帧底部区域
    2. 计算每行的像素变化（方差）
    3. 变化大的行 = 字幕行（对话在变）
    4. 变化小的行 = 固定文案或背景

    Args:
        video_path: 视频文件路径
        verbose: 是否打印详细信息

    Returns:
        SubtitleRegion
    """
    import cv2
    import numpy as np

    if verbose:
        print("  🔍 使用像素变化检测法...")

    # 提取多帧
    if verbose:
        print("  📹 提取多帧...")

    cap = cv2.VideoCapture(video_path)
    frames = []

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 优化帧提取策略：每2秒提取1帧，确保至少15帧
    sample_interval = int(fps * 2)  # 2秒间隔，更密集采样
    if sample_interval < 1:
        sample_interval = 1

    # 计算可提取的帧数
    available_frames = total_frames // sample_interval
    frame_count = min(50, max(15, available_frames))  # 15-50帧

    for i in range(frame_count):
        frame_idx = i * sample_interval
        if frame_idx >= total_frames:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()

    if len(frames) < 2:
        if verbose:
            print("  ⚠️ 声数不够，使用默认参数")
        return detect_subtitle_region_default()

    if verbose:
        print(f"  ✅ 提取了 {len(frames)} 帧")

    # 分析底部区域（高度50%-100%，扩大范围以覆盖不同位置）
    h, w = frames[0].shape[:2]
    bottom_start = int(h * 0.5)  # 从50%高度开始分析，覆盖更多位置
    bottom_end = h

    # 计算每行的方差
    variances = []

    for y in range(bottom_start, bottom_end):
        row_pixels = []
        for frame in frames:
            # 获取该行的像素值（灰度）
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            row_pixels.append(gray[y, :])

        # 计算方差
        variance = np.var(row_pixels)
        variances.append((y, variance))

    # 找出变化较大的区域（字幕）
    variance_values = [v[1] for v in variances]
    threshold = np.mean(variance_values) + np.std(variance_values)

    subtitle_regions = [y for y, v in variances if v > threshold]

    if not subtitle_regions:
        if verbose:
            print("  ⚠️ 未检测到明显的字幕区域，使用默认参数")
        return detect_subtitle_region_default()

    # 找出连续的高方差区域（聚类）
    # 这样可以避免把分散的高方差行都算进去
    clusters = []
    cluster_start = subtitle_regions[0]
    prev_y = subtitle_regions[0]

    for y in subtitle_regions[1:]:
        if y - prev_y <= 5:  # 5行以内认为是连续的
            prev_y = y
        else:
            # 结束当前聚类，开始新聚类
            clusters.append((cluster_start, prev_y))
            cluster_start = y
            prev_y = y

    # 添加最后一个聚类
    clusters.append((cluster_start, prev_y))

    # 选择最大的连续区域作为字幕区域
    if clusters:
        largest_cluster = max(clusters, key=lambda c: c[1] - c[0])
        subtitle_start = largest_cluster[0]
        subtitle_end = largest_cluster[1] + 1
    else:
        subtitle_start = min(subtitle_regions)
        subtitle_end = max(subtitle_regions) + 1

    # 添加一些上下边距（2%高度，更精确）
    padding = int(h * 0.02)
    subtitle_start = max(bottom_start, subtitle_start - padding)
    subtitle_end = min(bottom_end, subtitle_end + padding)

    # 计算比例
    y_ratio = subtitle_start / h
    height_ratio = (subtitle_end - subtitle_start) / h

    if verbose:
        print(f"  ✅ 检测到字幕区域:")
        print(f"     开始行: Y={subtitle_start} ({y_ratio:.1%})")
        print(f"     结束行: Y={subtitle_end} ({subtitle_end/h:.1%})")
        print(f"     字幕高度: {subtitle_end - subtitle_start}px ({height_ratio:.1%})")

    return SubtitleRegion(
        y_ratio=y_ratio,
        height_ratio=height_ratio,
        detection_method="pixel_variance",
        confidence=0.95
    )


def detect_subtitle_region_gemini(keyframe_paths: List[str]) -> Optional[SubtitleRegion]:
    """
    Gemini视觉分析检测字幕区域

    Args:
        keyframe_paths: 关键帧图片路径列表

    Returns:
        SubtitleRegion 或 None（检测失败）
    """
    try:
        import google.generativeai as genai
        import os

        # 检查API Key
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ 未设置 GEMINI_API_KEY，跳过Gemini检测")
            return None

        # 配置Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # 选择中间的关键帧进行分析（更有代表性）
        if not keyframe_paths:
            return None

        sample_frame = keyframe_paths[len(keyframe_paths) // 2]

        # 读取图片
        from PIL import Image
        img = Image.open(sample_frame)
        video_width, video_height = img.size

        # 构建Prompt
        prompt = f"""分析这张视频截图，识别字幕区域的位置。

请返回JSON格式（不要包含```json标记）：
{{
    "has_subtitle": true或false,
    "subtitle_y": 字幕顶部Y坐标（像素值）,
    "subtitle_height": 字幕高度（像素值）,
    "confidence": 置信度（0-1之间的小数）
}}

注意：
1. 字幕通常在视频底部
2. 如果没有字幕，返回 has_subtitle: false
3. subtitle_y 是字幕区域的顶部Y坐标
4. confidence 表示你对检测结果的信心程度

图片尺寸: {video_width}x{video_height}"""

        # 调用Gemini
        response = model.generate_content([prompt, img])
        result_text = response.text.strip()

        # 解析JSON
        import json
        # 移除可能的markdown标记
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]  # 移除第一行
            result_text = result_text.rsplit('\n', 1)[0]  # 移除最后一行

        result = json.loads(result_text)

        if not result.get('has_subtitle', False):
            print("  ℹ️ Gemini检测: 该帧没有字幕")
            return None

        # 计算比例
        y_ratio = result['subtitle_y'] / video_height
        height_ratio = result['subtitle_height'] / video_height
        confidence = result.get('confidence', 0.8)

        print(f"  ✅ Gemini检测: 字幕区域 y={y_ratio:.2%}, h={height_ratio:.2%}, 置信度={confidence:.0%}")

        return SubtitleRegion(
            y_ratio=y_ratio,
            height_ratio=height_ratio,
            detection_method="gemini",
            confidence=confidence
        )

    except Exception as e:
        print(f"  ⚠️ Gemini检测失败: {e}")
        return None


def detect_subtitle_region_ocr(keyframe_paths: List[str]) -> Optional[SubtitleRegion]:
    """
    OCR检测字幕区域

    Args:
        keyframe_paths: 关键帧图片路径列表

    Returns:
        SubtitleRegion 或 None（检测失败）
    """
    try:
        # 尝试导入OCR库
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        except ImportError:
            print("  ℹ️ PaddleOCR未安装，跳过OCR检测")
            return None

        from PIL import Image

        # 分析多个关键帧
        all_boxes = []

        for frame_path in keyframe_paths[:5]:  # 只分析前5帧
            try:
                img = Image.open(frame_path)
                img_width, img_height = img.size

                # OCR识别
                result = ocr.ocr(frame_path, cls=True)

                if result and result[0]:
                    for line in result[0]:
                        box = line[0]  # 文字框坐标
                        # 获取Y坐标范围
                        y_coords = [point[1] for point in box]
                        min_y = min(y_coords)
                        max_y = max(y_coords)

                        # 只保留底部30%区域的文字（字幕通常在底部）
                        if min_y > img_height * 0.7:
                            all_boxes.append({
                                'min_y': min_y,
                                'max_y': max_y,
                                'height': max_y - min_y
                            })

            except Exception as e:
                continue

        if not all_boxes:
            print("  ℹ️ OCR检测: 未找到字幕区域的文字")
            return None

        # 计算字幕区域（取所有文字框的包围盒）
        min_y = min(box['min_y'] for box in all_boxes)
        max_y = max(box['max_y'] for box in all_boxes)

        # 获取图片尺寸
        img = Image.open(keyframe_paths[0])
        _, img_height = img.size

        # 计算比例
        y_ratio = min_y / img_height
        height_ratio = (max_y - min_y) / img_height

        # 添加一些边距（10%）
        height_ratio *= 1.1

        print(f"  ✅ OCR检测: 字幕区域 y={y_ratio:.2%}, h={height_ratio:.2%}")

        return SubtitleRegion(
            y_ratio=y_ratio,
            height_ratio=height_ratio,
            detection_method="ocr",
            confidence=0.7
        )

    except Exception as e:
        print(f"  ⚠️ OCR检测失败: {e}")
        return None


def detect_subtitle_region(
    keyframe_paths: List[str],
    video_path: Optional[str] = None,
    force_method: Optional[str] = None,
    verbose: bool = True
) -> SubtitleRegion:
    """
    检测字幕区域（四层策略）

    检测顺序：像素变化检测 → Gemini → OCR → 默认比例

    像素变化检测法最可靠（置信度95%），因为它：
    1. 分析多帧的像素变化
    2. 变化大的区域 = 字幕区域（对话在变化）
    3. 变化小的区域 = 固定文案或背景

    Args:
        keyframe_paths: 关键帧图片路径列表（用于Gemini/OCR备选方案）
        video_path: 视频文件路径（用于像素变化检测，推荐提供）
        force_method: 强制使用指定方法 ("pixel_variance", "gemini", "ocr", "default")
        verbose: 是否打印详细信息

    Returns:
        SubtitleRegion 字幕区域配置
    """
    if verbose:
        print("\n" + "=" * 60)
        print("字幕区域检测")
        print("=" * 60)

    # 如果强制指定方法
    if force_method:
        if force_method == "default":
            if verbose:
                print("📌 使用默认比例检测")
            return detect_subtitle_region_default()
        elif force_method == "pixel_variance":
            if verbose:
                print("📌 使用像素变化检测法")
            if video_path:
                return detect_subtitle_region_pixel_variance(video_path, verbose)
            else:
                print("  ⚠️ 未提供video_path，回退到默认比例")
                return detect_subtitle_region_default()
        elif force_method == "gemini":
            if verbose:
                print("📌 使用Gemini视觉分析")
            return detect_subtitle_region_gemini(keyframe_paths) or detect_subtitle_region_default()
        elif force_method == "ocr":
            if verbose:
                print("📌 使用OCR检测")
            return detect_subtitle_region_ocr(keyframe_paths) or detect_subtitle_region_default()

    # 自动检测流程：像素变化检测法优先（最可靠）
    if video_path:
        if verbose:
            print("🔍 Step 1: 使用像素变化检测法（最可靠）...")

        region = detect_subtitle_region_pixel_variance(video_path, verbose)

        if region and region.confidence >= 0.9:
            if verbose:
                print(f"✅ 像素变化检测成功，置信度: {region.confidence:.0%}")
            return region

    # 像素变化检测失败或无video_path，尝试Gemini
    if verbose:
        print("🔍 Step 2: 尝试Gemini视觉分析...")

    region = detect_subtitle_region_gemini(keyframe_paths)

    if region and region.confidence >= 0.8:
        if verbose:
            print(f"✅ Gemini检测成功，置信度: {region.confidence:.0%}")
        return region

    # Gemini失败或置信度低，尝试OCR
    if verbose:
        print("🔍 Step 3: 尝试OCR检测...")

    region = detect_subtitle_region_ocr(keyframe_paths)

    if region:
        if verbose:
            print(f"✅ OCR检测成功")
        return region

    # OCR也失败，使用默认比例
    if verbose:
        print("🔍 Step 4: 使用默认比例...")

    region = detect_subtitle_region_default()
    if verbose:
        print(f"✅ 使用默认比例: y={region.y_ratio:.2%}, h={region.height_ratio:.2%}")

    return region


def save_subtitle_config(
    region: SubtitleRegion,
    project_name: str,
    video_resolution: Tuple[int, int],
    output_dir: str = "data/analysis"
) -> str:
    """
    保存字幕区域配置

    Args:
        region: 字幕区域配置
        project_name: 项目名称
        video_resolution: 视频分辨率 (width, height)
        output_dir: 输出目录

    Returns:
        配置文件路径
    """
    output_path = Path(output_dir) / project_name / "subtitle_config.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "project_name": project_name,
        "video_resolution": f"{video_resolution[0]}x{video_resolution[1]}",
        "subtitle_region": region.to_dict(),
        "note": "如果遮盖位置不准，可手动修改 y_ratio 和 height_ratio"
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ 字幕区域配置已保存: {output_path}")
    return str(output_path)


def load_subtitle_config(
    project_name: str,
    config_dir: str = "data/analysis"
) -> Optional[SubtitleRegion]:
    """
    加载字幕区域配置

    Args:
        project_name: 项目名称
        config_dir: 配置目录

    Returns:
        SubtitleRegion 或 None（配置不存在）
    """
    config_path = Path(config_dir) / project_name / "subtitle_config.json"

    if not config_path.exists():
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    region = SubtitleRegion.from_dict(config['subtitle_region'])
    print(f"✅ 加载字幕区域配置: {region}")

    return region


class SubtitleDetector:
    """
    字幕区域检测器（类封装版本）

    使用方法：
        detector = SubtitleDetector()
        region = detector.detect(keyframe_paths, video_path)
    """

    def __init__(self, force_method: Optional[str] = None):
        """
        初始化检测器

        Args:
            force_method: 强制使用指定方法 ("gemini", "ocr", "default")
        """
        self.force_method = force_method

    def detect(
        self,
        keyframe_paths: List[str],
        video_path: Optional[str] = None,
        verbose: bool = True
    ) -> SubtitleRegion:
        """
        检测字幕区域

        Args:
            keyframe_paths: 关键帧图片路径列表
            video_path: 视频文件路径
            verbose: 是否打印详细信息

        Returns:
            SubtitleRegion
        """
        return detect_subtitle_region(keyframe_paths, video_path, self.force_method, verbose)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("字幕区域检测模块测试")
    print("=" * 60)

    # 测试默认检测
    region = detect_subtitle_region_default()
    print(f"\n默认字幕区域: {region}")

    # 测试像素坐标计算
    y, height = region.get_pixel_coords(1920)
    print(f"1080p视频像素坐标: y={y}, height={height}")

    y, height = region.get_pixel_coords(1920)
    print(f"竖屏1080x1920视频像素坐标: y={y}, height={height}")
