"""
精确遮罩测试脚本 - 调试版本

功能：测试精确遮罩功能，调试OCR识别

使用方法：
    python test/test_precise_mask_debug.py
"""

import sys
sys.path.insert(0, '/Users/weilingkeji/Documents/hangzhou-leiming-AI-drama')

from pathlib import Path

# 测试配置
TEST_VIDEO = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"
OUTPUT_DIR = "clips"
OUTPUT_FILE = "clips/烈日重生_1_精确遮罩.mp4"

def main():
    print("=" * 60)
    print("精确遮罩测试 - 调试版")
    print("=" * 60)

    from scripts.preprocess.subtitle_detector import detect_subtitle_region_pixel_variance
    from scripts.preprocess.subtitle_ocr import extract_subtitle_text_with_boxes

    # 检测字幕区域
    print("\n[1/2] 检测字幕区域...")
    subtitle_region = detect_subtitle_region_pixel_variance(TEST_VIDEO)
    print(f"  字幕区域: y={subtitle_region.y_ratio:.2%}, h={subtitle_region.height_ratio:.2%}")

    # OCR识别（带boxes）
    print("\n[2/2] OCR识别字幕（带文字框）...")
    subtitle_segments = extract_subtitle_text_with_boxes(
        TEST_VIDEO,
        subtitle_region,
        sample_fps=1.0,  # 降低采样率以获取更多帧
        verbose=True
    )

    # 显示所有识别到的字幕
    print(f"\n{'=' * 60}")
    print(f"共识别 {len(subtitle_segments)} 个字幕片段")
    print("=" * 60)

    for i, seg in enumerate(subtitle_segments):
        print(f"\n[{i+1}] {seg.start_time:.1f}s - {seg.end_time:.1f}s")
        print(f"    文本: {seg.text}")
        print(f"    文字框数量: {len(seg.boxes)}")
        if seg.boxes:
            # 显示第一个和最后一个文字框
            print(f"    第一个框: {seg.boxes[0]}")
            if len(seg.boxes) > 1:
                print(f"    最后一个框: {seg.boxes[-1]}")

    # 查找包含特定文字的字幕
    print(f"\n{'=' * 60}")
    print("查找包含特定文字的字幕")
    print("=" * 60)

    search_terms = ["高温", "末世", "热", "死", "天气", "太阳"]
    for term in search_terms:
        found = False
        for seg in subtitle_segments:
            if term in seg.text:
                if not found:
                    print(f"\n包含 '{term}' 的字幕:")
                    found = True
                print(f"  [{seg.start_time:.1f}s-{seg.end_time:.1f}s] {seg.text}")

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
