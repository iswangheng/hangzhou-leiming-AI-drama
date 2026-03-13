#!/usr/bin/env python3
"""
OCR敏感词检测演示脚本

演示正确的敏感词检测流程：
1. 检测字幕区域（像素变化法）
2. OCR识别字幕内容
3. 匹配敏感词

使用方法：
    python test/test_ocr_sensitive_detection.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from scripts.preprocess.subtitle_detector import detect_subtitle_region_pixel_variance, load_subtitle_config
from scripts.preprocess.subtitle_ocr import extract_subtitle_text, detect_sensitive_words_in_subtitles


def load_sensitive_words(sensitive_file: str = "config/sensitive_words.txt") -> set:
    """加载敏感词列表"""
    words = set()
    with open(sensitive_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(line)
    return words


def main():
    # 测试视频：烈日重生第1集
    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    print("=" * 60)
    print("🔍 OCR敏感词检测演示")
    print("=" * 60)
    print(f"\n📹 测试视频: {video_path}")

    # Step 1: 检测字幕区域
    print("\n📍 Step 1: 检测字幕区域...")
    subtitle_region = detect_subtitle_region_pixel_variance(video_path, verbose=True)

    if not subtitle_region:
        print("❌ 无法检测字幕区域")
        return

    print(f"\n✅ 字幕区域检测完成:")
    print(f"   Y位置比例: {subtitle_region.y_ratio:.2%}")
    print(f"   高度比例: {subtitle_region.height_ratio:.2%}")
    print(f"   检测方法: {subtitle_region.detection_method}")
    print(f"   置信度: {subtitle_region.confidence:.0%}")

    # Step 2: OCR识别字幕内容
    print("\n📝 Step 2: OCR识别字幕内容...")
    subtitle_segments = extract_subtitle_text(
        video_path=video_path,
        subtitle_region=subtitle_region,
        sample_fps=3.0,  # 每秒3帧，平衡精度和速度
        verbose=True
    )

    print(f"\n✅ OCR识别完成: 共识别 {len(subtitle_segments)} 个字幕片段")
    print("\n📋 识别到的字幕内容:")
    for seg in subtitle_segments:
        print(f"   [{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.text}")

    # Step 3: 加载敏感词
    print("\n📚 Step 3: 加载敏感词列表...")
    sensitive_words = load_sensitive_words()
    print(f"   加载了 {len(sensitive_words)} 个敏感词")

    # Step 4: 检测敏感词
    print("\n🔍 Step 4: 敏感词检测...")
    sensitive_segments = detect_sensitive_words_in_subtitles(
        subtitle_segments=subtitle_segments,
        sensitive_words=sensitive_words,
        episode=1,
        verbose=True
    )

    # 总结
    print("\n" + "=" * 60)
    print("📊 检测结果总结")
    print("=" * 60)

    if sensitive_segments:
        print(f"\n⚠️ 发现 {len(sensitive_segments)} 处敏感词:\n")
        for seg in sensitive_segments:
            print(f"   • {seg.sensitive_word}")
            print(f"     时间: {seg.start_time:.1f}s - {seg.end_time:.1f}s")
            print(f"     字幕: {seg.asr_text}")
            print()
    else:
        print("\n✅ 未检测到敏感词")


if __name__ == "__main__":
    main()
