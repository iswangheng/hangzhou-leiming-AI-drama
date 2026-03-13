#!/usr/bin/env python3
"""
敏感词遮罩预处理模块

功能：
1. 自动检测字幕区域
2. OCR识别视频字幕
3. 匹配敏感词
4. 生成马赛克遮罩后的"干净"视频

使用方法：
    # 处理整个项目目录
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名"

    # 处理单个视频
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名/1.mp4"

    # 指定输出目录
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名" --output "干净素材/项目名"

    # 跳过已有处理
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/项目名" --skip-existing
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.preprocess.subtitle_detector import (
    detect_subtitle_region_pixel_variance,
    SubtitleRegion
)
from scripts.preprocess.subtitle_ocr import (
    extract_subtitle_text,
    extract_subtitle_text_with_boxes,
    detect_sensitive_words_in_subtitles
)
from scripts.preprocess.sensitive_detector import (
    load_sensitive_words,
    SensitiveSegment
)
from scripts.preprocess.video_cleaner import (
    clean_video,
    clean_video_precise,
    get_video_info
)


@dataclass
class VideoProcessResult:
    """单个视频处理结果"""
    video_path: str
    output_path: str
    sensitive_count: int
    success: bool
    error: str = ""


class SensitiveMaskWorkflow:
    """敏感词遮罩预处理工作流"""

    def __init__(
        self,
        sensitive_words_path: str = "config/sensitive_words.txt",
        sample_fps: float = 5.0,
        time_buffer: float = 0.6,
        verbose: bool = True
    ):
        """
        初始化工作流

        Args:
            sensitive_words_path: 敏感词配置文件路径
            sample_fps: OCR采样帧率
            time_buffer: 遮罩时间缓冲区（秒）
            verbose: 是否打印详细信息
        """
        self.sensitive_words_path = sensitive_words_path
        self.sample_fps = sample_fps
        self.time_buffer = time_buffer
        self.verbose = verbose

        # 加载敏感词
        self.sensitive_words = load_sensitive_words(sensitive_words_path)
        if not self.sensitive_words:
            raise ValueError(f"敏感词列表为空: {sensitive_words_path}")

    def process_video(
        self,
        video_path: str,
        output_path: str,
        subtitle_region: Optional[SubtitleRegion] = None
    ) -> VideoProcessResult:
        """
        处理单个视频

        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            subtitle_region: 字幕区域配置（可选，自动检测）

        Returns:
            处理结果
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            return VideoProcessResult(
                video_path=str(video_path),
                output_path="",
                sensitive_count=0,
                success=False,
                error="视频文件不存在"
            )

        try:
            # Step 1: 检测字幕区域
            if subtitle_region is None:
                if self.verbose:
                    print(f"\n  🔍 检测字幕区域...")
                subtitle_region = detect_subtitle_region_pixel_variance(
                    str(video_path),
                    verbose=False
                )

            if self.verbose:
                print(f"  📍 字幕区域: y={subtitle_region.y_ratio:.1%}, h={subtitle_region.height_ratio:.1%}")

            # Step 2: OCR识别字幕（带boxes坐标）
            if self.verbose:
                print(f"  🔤 OCR识别中 (采样{self.sample_fps}fps)...")

            subtitle_segments = extract_subtitle_text_with_boxes(
                video_path=str(video_path),
                subtitle_region=subtitle_region,
                sample_fps=self.sample_fps,
                verbose=False
            )

            if self.verbose:
                print(f"     识别到 {len(subtitle_segments)} 个字幕片段")

            # Step 3: 敏感词检测（带精确坐标）
            if self.verbose:
                print(f"  🔍 敏感词检测...")

            from scripts.preprocess.sensitive_detector import detect_sensitive_words_with_boxes
            sensitive_segments = detect_sensitive_words_with_boxes(
                subtitle_segments=subtitle_segments,
                sensitive_words=self.sensitive_words,
                episode=1,
                verbose=False
            )

            # 去重（合并相邻片段）
            merged_segments = self._merge_segments(sensitive_segments)

            if self.verbose:
                print(f"     检测到 {len(merged_segments)} 个敏感片段")

            # Step 4: 生成马赛克视频
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if merged_segments:
                if self.verbose:
                    print(f"  🎬 生成精确马赛克遮罩...")

                clean_video_precise(
                    video_path=str(video_path),
                    sensitive_segments=merged_segments,
                    subtitle_region=subtitle_region,
                    output_path=str(output_path),
                    verbose=False,
                    time_buffer=self.time_buffer
                )
            else:
                # 无敏感词，直接复制
                if self.verbose:
                    print(f"  ℹ️ 无敏感词，直接复制视频")
                shutil.copy2(video_path, output_path)

            return VideoProcessResult(
                video_path=str(video_path),
                output_path=str(output_path),
                sensitive_count=len(merged_segments),
                success=True
            )

        except Exception as e:
            return VideoProcessResult(
                video_path=str(video_path),
                output_path="",
                sensitive_count=0,
                success=False,
                error=str(e)
            )

    def _merge_segments(self, segments: List[SensitiveSegment]) -> List[SensitiveSegment]:
        """合并相邻的敏感片段"""
        if not segments:
            return []

        # 按时间排序
        sorted_segments = sorted(segments, key=lambda x: x.start_time)

        merged = []
        current = sorted_segments[0]

        for seg in sorted_segments[1:]:
            # 如果与前一个片段重叠或接近（小于0.5秒），合并
            if seg.start_time - current.end_time < 0.5:
                # 合并boxes
                merged_boxes = current.boxes + seg.boxes if current.boxes else seg.boxes
                current = SensitiveSegment(
                    episode=current.episode,
                    sensitive_word=current.sensitive_word,
                    asr_text=current.asr_text,
                    start_time=current.start_time,
                    end_time=max(current.end_time, seg.end_time),
                    boxes=merged_boxes
                )
            else:
                merged.append(current)
                current = seg

        merged.append(current)
        return merged

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        skip_existing: bool = False
    ) -> List[VideoProcessResult]:
        """
        处理整个目录

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            skip_existing: 跳过已存在的输出文件

        Returns:
            处理结果列表
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        # 查找所有视频文件
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv'}
        video_files = []

        for ext in video_extensions:
            video_files.extend(input_path.glob(f"*{ext}"))
            video_files.extend(input_path.glob(f"*{ext.upper()}"))

        # 排序（按文件名数字排序）
        def sort_key(p):
            name = p.stem
            # 提取数字
            import re
            numbers = re.findall(r'\d+', name)
            return int(numbers[0]) if numbers else 0

        video_files.sort(key=sort_key)

        if not video_files:
            print(f"❌ 未找到视频文件: {input_dir}")
            return []

        print(f"\n{'='*60}")
        print(f"敏感词遮罩预处理")
        print(f"{'='*60}")
        print(f"输入目录: {input_dir}")
        print(f"输出目录: {output_dir}")
        print(f"视频数量: {len(video_files)}")
        print(f"敏感词数量: {len(self.sensitive_words)}")
        print(f"采样帧率: {self.sample_fps}fps")
        print(f"时间缓冲区: {self.time_buffer}秒")

        results = []

        for i, video_file in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}] 处理: {video_file.name}")

            # 构建输出路径
            output_file = output_path / video_file.name

            # 跳过已存在
            if skip_existing and output_file.exists():
                print(f"  ⏭️  跳过（已存在）")
                results.append(VideoProcessResult(
                    video_path=str(video_file),
                    output_path=str(output_file),
                    sensitive_count=0,
                    success=True
                ))
                continue

            # 处理视频
            result = self.process_video(
                video_path=str(video_file),
                output_path=str(output_file)
            )

            if result.success:
                if result.sensitive_count > 0:
                    print(f"  ✅ 完成 ({result.sensitive_count}个敏感片段)")
                else:
                    print(f"  ✅ 完成 (无敏感词)")
            else:
                print(f"  ❌ 失败: {result.error}")

            results.append(result)

        # 统计
        total = len(results)
        success = sum(1 for r in results if r.success)
        total_sensitive = sum(r.sensitive_count for r in results)

        print(f"\n{'='*60}")
        print(f"处理完成")
        print(f"{'='*60}")
        print(f"总计: {total} 个视频")
        print(f"成功: {success} 个")
        print(f"敏感片段: {total_sensitive} 个")

        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="敏感词遮罩预处理模块",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 处理整个项目目录
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生"

    # 处理单个视频
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生/烈日重生-1.mp4"

    # 指定输出目录
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生" --output "干净素材/烈日重生"

    # 跳过已有处理
    python -m scripts.preprocess.sensitive_mask_workflow "漫剧素材/烈日重生" --skip-existing
        """
    )

    parser.add_argument(
        "input",
        help="输入视频目录或文件路径"
    )

    parser.add_argument(
        "--output", "-o",
        help="输出目录（默认: input_dir + _cleaned）"
    )

    parser.add_argument(
        "--sensitive-words",
        default="config/sensitive_words.txt",
        help="敏感词配置文件路径（默认: config/sensitive_words.txt）"
    )

    parser.add_argument(
        "--sample-fps",
        type=float,
        default=5.0,
        help="OCR采样帧率（默认: 5.0）"
    )

    parser.add_argument(
        "--time-buffer",
        type=float,
        default=0.6,
        help="遮罩时间缓冲区秒数（默认: 0.6）"
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已存在的输出文件"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式（不打印详细信息）"
    )

    args = parser.parse_args()

    # 确定输入路径
    input_path = Path(args.input)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        # 默认: input_dir + _cleaned
        output_path = input_path.parent / f"{input_path.stem}_cleaned"

    # 创建工作流
    workflow = SensitiveMaskWorkflow(
        sensitive_words_path=args.sensitive_words,
        sample_fps=args.sample_fps,
        time_buffer=args.time_buffer,
        verbose=not args.quiet
    )

    # 执行处理
    if input_path.is_file():
        # 单个文件
        result = workflow.process_video(
            video_path=str(input_path),
            output_path=str(output_path)
        )

        if result.success:
            print(f"\n✅ 处理完成: {result.output_path}")
            print(f"   敏感片段: {result.sensitive_count} 个")
        else:
            print(f"\n❌ 处理失败: {result.error}")
            sys.exit(1)
    else:
        # 目录
        results = workflow.process_directory(
            input_dir=str(input_path),
            output_dir=str(output_path),
            skip_existing=args.skip_existing
        )

        # 返回状态码
        success = sum(1 for r in results if r.success)
        if success < len(results):
            sys.exit(1)


if __name__ == "__main__":
    main()
