"""
OCR字幕识别模块测试

测试目标：
1. 验证OCR库能正常识别字幕
2. 验证敏感词检测功能
3. 验证字幕区域检测功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.preprocess.ocr_subtitle import (
    detect_sensitive_words_from_ocr,
    init_ocr_engine,
    extract_frames_for_ocr
)
from scripts.preprocess.subtitle_detector import (
    SubtitleRegion,
    detect_subtitle_region_pixel_variance
)


def test_ocr_engine():
    """测试1: OCR引擎初始化"""
    print("\n" + "=" * 60)
    print("测试1: OCR引擎初始化")
    print("=" * 60)

    ocr_engine = init_ocr_engine()

    if ocr_engine is None:
        print("❌ OCR引擎初始化失败")
        return False

    print("✅ OCR引擎初始化成功")

    # 检查OCR引擎类型
    if hasattr(ocr_engine, 'readtext'):
        print("   引擎类型: EasyOCR")
    else:
        print("   引擎类型: PaddleOCR")

    return True


def test_frame_extraction():
    """测试2: 帧提取功能"""
    print("\n" + "=" * 60)
    print("测试2: 帧提取功能")
    print("=" * 60)

    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    print(f"视频: {video_path}")
    print("提取5帧（采样率0.5fps）...")

    frames = extract_frames_for_ocr(
        video_path=video_path,
        sample_fps=0.5,
        output_dir=None  # 不保存帧图片
    )

    if not frames:
        print("❌ 未提取到任何帧")
        return False

    print(f"✅ 提取了 {len(frames)} 帧")
    print(f"   第一帧: 索引={frames[0][0]}, 时间戳={frames[0][2]:.2f}s")
    print(f"   最后一帧: 索引={frames[-1][0]}, 时间戳={frames[-1][2]:.2f}s")

    return True


def test_subtitle_region_detection():
    """测试3: 字幕区域检测"""
    print("\n" + "=" * 60)
    print("测试3: 字幕区域检测（像素变化检测法）")
    print("=" * 60)

    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    print(f"视频: {video_path}")

    region = detect_subtitle_region_pixel_variance(video_path, verbose=True)

    if region is None:
        print("❌ 字幕区域检测失败")
        return False

    print(f"✅ 字幕区域检测成功")
    print(f"   Y位置: {region.y_ratio:.2%}")
    print(f"   高度: {region.height_ratio:.2%}")
    print(f"   方法: {region.detection_method}")
    print(f"   置信度: {region.confidence:.0%}")

    return True


def test_sensitive_word_detection():
    """测试4: 敏感词检测（完整流程）"""
    print("\n" + "=" * 60)
    print("测试4: 敏感词检测（完整流程）")
    print("=" * 60)

    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    # 先检测字幕区域
    print("Step 1: 检测字幕区域...")
    region = detect_subtitle_region_pixel_variance(video_path, verbose=False)

    if region is None:
        print("❌ 字幕区域检测失败，使用默认区域")
        region = SubtitleRegion(
            y_ratio=0.88,
            height_ratio=0.10,
            detection_method="default",
            confidence=0.5
        )

    print(f"   字幕区域: y={region.y_ratio:.2%}, h={region.height_ratio:.2%}")

    # 读取敏感词列表
    sensitive_words_file = "config/sensitive_words.txt"
    if not os.path.exists(sensitive_words_file):
        print(f"❌ 敏感词文件不存在: {sensitive_words_file}")
        return False

    with open(sensitive_words_file, 'r', encoding='utf-8') as f:
        sensitive_words = set()
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                sensitive_words.add(line)

    print(f"Step 2: 加载敏感词列表 ({len(sensitive_words)} 个)")
    print(f"   示例: {list(sensitive_words)[:5]}")

    # 进行OCR识别和敏感词检测
    print("Step 3: OCR识别和敏感词检测...")
    print("   采样率: 0.5fps (每2秒1帧)")
    print("   这可能需要几分钟，请耐心等待...")

    # 创建输出目录
    output_dir = "test/temp/ocr_test"
    os.makedirs(output_dir, exist_ok=True)

    result = detect_sensitive_words_from_ocr(
        video_path=video_path,
        sensitive_words=sensitive_words,
        subtitle_region=region,
        sample_fps=0.5,
        verbose=True,
        output_dir=output_dir
    )

    print(f"\n检测结果:")
    if result:
        print(f"✅ 检测到 {len(result)} 个敏感词片段")
        for i, seg in enumerate(result, 1):
            print(f"\n片段 {i}:")
            print(f"   时间: {seg.start_time:.1f}s - {seg.end_time:.1f}s")
            print(f"   敏感词: '{seg.sensitive_word}'")
            print(f"   字幕: '{seg.subtitle_text[:50]}...'")
    else:
        print("ℹ️ 未检测到敏感词")

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("OCR字幕识别模块测试套件")
    print("=" * 60)

    tests = [
        ("OCR引擎初始化", test_ocr_engine),
        ("帧提取功能", test_frame_extraction),
        ("字幕区域检测", test_subtitle_region_detection),
        ("敏感词检测", test_sensitive_word_detection),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # 打印测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    # 计算通过率
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")


if __name__ == "__main__":
    main()
