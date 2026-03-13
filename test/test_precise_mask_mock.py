"""
精确遮罩测试脚本 - 使用模拟数据

功能：使用模拟数据测试精确遮罩功能

使用方法：
    python test/test_precise_mask_mock.py
"""

import sys
sys.path.insert(0, '/Users/weilingkeji/Documents/hangzhou-leiming-AI-drama')

from pathlib import Path
import shutil

# 测试配置
TEST_VIDEO = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"
OUTPUT_DIR = "clips"
OUTPUT_FILE = "clips/烈日重生_1_精确遮罩_test.mp4"

def main():
    print("=" * 60)
    print("精确遮罩测试 - 模拟数据版")
    print("=" * 60)

    from scripts.preprocess.subtitle_detector import SubtitleRegion
    from scripts.preprocess.sensitive_detector import SensitiveSegment
    from scripts.preprocess.video_cleaner import clean_video_precise

    # 视频信息
    video_path = Path(TEST_VIDEO)
    if not video_path.exists():
        print(f"❌ 视频文件不存在: {TEST_VIDEO}")
        return

    print(f"\n视频: {TEST_VIDEO}")

    # 创建字幕区域配置
    # 视频是 406x720，字幕区域大约在底部 10%
    subtitle_region = SubtitleRegion(
        y_ratio=0.85,  # 字幕在85%高度位置
        height_ratio=0.10,  # 字幕高度占10%
        detection_method="default",
        confidence=0.9
    )
    print(f"字幕区域: y={subtitle_region.y_ratio:.2%}, h={subtitle_region.height_ratio:.2%}")

    # 创建模拟的敏感词片段（带有boxes信息）
    # 模拟"高温末世"四个字，每个字大约占20像素宽度
    # 注意：boxes坐标是相对于裁剪后的字幕区域图片的
    # 字幕区域是 frame[y_start:y_end, :], y_start = 612, height = 72
    # 所以boxes的y坐标应该是在0-72范围内
    sensitive_segments = [
        SensitiveSegment(
            episode=1,
            sensitive_word="高温末世",
            asr_text="真正的高温末世就要开始了吧",
            start_time=20.0,
            end_time=22.0,
            boxes=[
                # "高"字的box - 相对于字幕区域(72px高)
                [[100, 10], [120, 10], [120, 40], [100, 40]],
                # "温"字的box
                [[122, 10], [142, 10], [142, 40], [122, 40]],
                # "末"字的box
                [[144, 10], [164, 10], [164, 40], [144, 40]],
                # "世"字的box
                [[166, 10], [186, 10], [186, 40], [166, 40]],
            ]
        )
    ]

    print(f"\n模拟敏感词片段:")
    for seg in sensitive_segments:
        print(f"  [{seg.start_time:.1f}s - {seg.end_time:.1f}s] '{seg.sensitive_word}'")
        print(f"    ASR: {seg.asr_text}")
        print(f"    文字框数量: {len(seg.boxes)}")

    # 执行精确遮罩
    print("\n执行精确遮罩...")
    output_path = clean_video_precise(
        TEST_VIDEO,
        sensitive_segments,
        subtitle_region,
        OUTPUT_FILE,
        verbose=True
    )

    print(f"\n{'=' * 60}")
    print(f"测试完成")
    print(f"输出视频: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
