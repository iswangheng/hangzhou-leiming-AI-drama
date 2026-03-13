"""
精确遮罩测试脚本

功能：测试精确遮罩功能，只遮罩敏感词所在位置的文字

使用方法：
    python test/test_precise_mask.py
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
    print("精确遮罩测试")
    print("=" * 60)

    from scripts.preprocess.subtitle_detector import detect_subtitle_region_pixel_variance
    from scripts.preprocess.subtitle_ocr import extract_subtitle_text_with_boxes, detect_sensitive_words_in_subtitles, get_word_boxes_for_sensitive_word
    from scripts.preprocess.sensitive_detector import load_sensitive_words
    from scripts.preprocess.video_cleaner import clean_video_precise

    # 检测字幕区域
    print("\n[1/4] 检测字幕区域...")
    subtitle_region = detect_subtitle_region_pixel_variance(TEST_VIDEO)
    print(f"  字幕区域: y={subtitle_region.y_ratio:.2%}, h={subtitle_region.height_ratio:.2%}")

    # 加载敏感词
    print("\n[2/4] 加载敏感词...")
    sensitive_words = load_sensitive_words()
    print(f"  敏感词数量: {len(sensitive_words)}")

    # 测试特定敏感词
    test_words = {"高温末世", "热死"}
    for w in test_words:
        if w not in sensitive_words:
            sensitive_words.add(w)
    print(f"  测试敏感词: {test_words}")

    # OCR识别（带boxes）
    print("\n[3/4] OCR识别字幕（带文字框）...")
    subtitle_segments = extract_subtitle_text_with_boxes(
        TEST_VIDEO,
        subtitle_region,
        sample_fps=5.0,
        verbose=True
    )

    # 显示识别到的字幕
    print(f"\n  共识别 {len(subtitle_segments)} 个字幕片段")

    # 查找包含敏感词的字幕
    print("\n  查找包含敏感词的字幕片段:")
    for seg in subtitle_segments:
        for word in test_words:
            boxes, is_match = get_word_boxes_for_sensitive_word(seg.text, seg.boxes, word)
            if is_match:
                print(f"    [{seg.start_time:.1f}s-{seg.end_time:.1f}s] {seg.text}")
                print(f"      文字框数量: {len(boxes)}")

    # 检测敏感词（带boxes）
    print("\n[3.5/4] 检测敏感词...")
    sensitive_segments = detect_sensitive_words_in_subtitles(
        subtitle_segments,
        sensitive_words,
        episode=1,
        verbose=True
    )

    # 显示检测到的敏感词
    print(f"\n  检测到 {len(sensitive_segments)} 个敏感片段")
    for seg in sensitive_segments:
        print(f"    [{seg.start_time:.1f}s-{seg.end_time:.1f}s] '{seg.sensitive_word}'")
        print(f"      文字框数量: {len(seg.boxes)}")

    # 如果有检测到敏感词，进行精确遮罩
    if sensitive_segments:
        print("\n[4/4] 执行精确遮罩...")
        output_path = clean_video_precise(
            TEST_VIDEO,
            sensitive_segments,
            subtitle_region,
            OUTPUT_FILE,
            verbose=True
        )
        print(f"\n  输出视频: {output_path}")
    else:
        print("\n[4/4] 无敏感词，跳过遮罩")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
