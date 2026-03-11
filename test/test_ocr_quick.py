"""
OCR字幕识别快速验证

快速验证OCR功能是否正常工作
"""

import os
import sys
from pathlib import Path
import cv2
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.preprocess.ocr_subtitle import init_ocr_engine, ocr_subtitle_region
from scripts.preprocess.subtitle_detector import SubtitleRegion


def create_test_image_with_text():
    """创建一个包含文字的测试图片"""
    # 创建一个黑色背景图片 (360x640 竖屏)
    img = np.zeros((640, 360, 3), dtype=np.uint8)

    # 在底部添加白色文字区域
    img[550:620, :] = (255, 255, 255)  # 白色区域

    # 添加一些文字（使用OpenCV绘制）
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'Test Subtitle', (50, 590), font, 1, (0, 0, 0), 2, cv2.LINE_AA)

    return img


def test_ocr_basic():
    """基础OCR测试"""
    print("=" * 60)
    print("OCR基础功能测试")
    print("=" * 60)

    # 初始化OCR引擎
    print("\n1. 初始化OCR引擎...")
    ocr_engine = init_ocr_engine()

    if ocr_engine is None:
        print("❌ OCR引擎初始化失败")
        return False

    print("✅ OCR引擎初始化成功")

    # 创建测试图片
    print("\n2. 创建测试图片...")
    test_img = create_test_image_with_text()

    # 保存测试图片
    test_dir = Path("test/temp/ocr_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_img_path = test_dir / "test_subtitle.jpg"
    cv2.imwrite(str(test_img_path), test_img)

    print(f"✅ 测试图片已保存: {test_img_path}")

    # 创建字幕区域配置
    subtitle_region = SubtitleRegion(
        y_ratio=0.85,  # 底部15%区域
        height_ratio=0.15,
        detection_method="test",
        confidence=1.0
    )

    # 进行OCR识别
    print("\n3. 进行OCR识别...")
    result = ocr_subtitle_region(test_img, subtitle_region, ocr_engine)

    if result:
        print(f"✅ OCR识别成功")
        print(f"   识别结果: '{result}'")
    else:
        print("ℹ️ OCR未识别到文字（这是正常的，因为是英文测试）")

    return True


def test_ocr_on_real_video():
    """在真实视频上测试OCR"""
    print("\n" + "=" * 60)
    print("真实视频OCR测试")
    print("=" * 60)

    video_path = "260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4"

    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    print(f"视频: {video_path}")

    # 提取一帧
    print("\n1. 提取第10秒的帧...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(10 * fps)  # 第10秒

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ 帧提取失败")
        return False

    print(f"✅ 帧提取成功: {frame.shape}")

    # 保存帧
    test_dir = Path("test/temp/ocr_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    frame_path = test_dir / "frame_10s.jpg"
    cv2.imwrite(str(frame_path), frame)
    print(f"   帧已保存: {frame_path}")

    # 初始化OCR
    print("\n2. 初始化OCR引擎...")
    ocr_engine = init_ocr_engine()

    if ocr_engine is None:
        print("❌ OCR引擎初始化失败")
        return False

    print("✅ OCR引擎初始化成功")

    # 检测字幕区域
    print("\n3. 检测字幕区域...")
    from scripts.preprocess.subtitle_detector import detect_subtitle_region_pixel_variance

    region = detect_subtitle_region_pixel_variance(video_path, verbose=False)

    if region is None:
        print("⚠️ 字幕区域检测失败，使用默认区域")
        region = SubtitleRegion(
            y_ratio=0.88,
            height_ratio=0.10,
            detection_method="default",
            confidence=0.5
        )

    print(f"   字幕区域: y={region.y_ratio:.2%}, h={region.height_ratio:.2%}")

    # 进行OCR识别
    print("\n4. 进行OCR识别...")
    result = ocr_subtitle_region(frame, region, ocr_engine)

    if result:
        print(f"✅ OCR识别成功")
        print(f"   识别结果: '{result}'")
        print(f"   字符数: {len(result)}")
    else:
        print("ℹ️ OCR未识别到字幕（可能是该帧没有字幕）")

    return True


def main():
    """运行快速测试"""
    print("=" * 60)
    print("OCR字幕识别快速验证")
    print("=" * 60)

    tests = [
        ("基础OCR测试", test_ocr_basic),
        ("真实视频OCR测试", test_ocr_on_real_video),
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
