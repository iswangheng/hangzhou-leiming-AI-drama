#!/usr/bin/env python3
"""
敏感词字幕遮盖功能测试脚本

功能：
1. 测试敏感词加载和检测
2. 测试字幕区域检测
3. 测试视频清洗（马赛克遮盖）
4. 完整流程测试

使用方法：
    # 完整测试
    python test/test_sensitive_word_mask.py

    # 只测试敏感词检测
    python test/test_sensitive_word_mask.py --test detector

    # 测试实际视频
    python test/test_sensitive_word_mask.py --video "漫剧素材/项目名/1.mp4"
"""

import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入预处理模块
from scripts.preprocess.sensitive_detector import (
    load_sensitive_words,
    detect_sensitive_segments,
    SensitiveSegment
)
from scripts.preprocess.subtitle_detector import (
    detect_subtitle_region,
    detect_subtitle_region_default,
    SubtitleRegion
)
from scripts.preprocess.video_cleaner import (
    VideoCleaner,
    clean_video,
    get_video_info
)


@dataclass
class MockASRSegment:
    """模拟ASR片段（用于测试）"""
    text: str
    start: float
    end: float
    episode: int = 1


def test_sensitive_detector():
    """测试敏感词检测模块"""
    print("\n" + "=" * 70)
    print("测试1: 敏感词检测模块")
    print("=" * 70)

    # 1. 测试加载敏感词
    print("\n1.1 加载敏感词配置...")
    config_path = project_root / "config" / "sensitive_words.txt"
    words = load_sensitive_words(str(config_path))

    if words:
        print(f"   ✅ 成功加载 {len(words)} 个敏感词")
        print(f"   示例: {list(words)[:5]}...")
    else:
        print("   ⚠️ 敏感词列表为空，请检查配置文件")
        return False

    # 2. 测试敏感词检测
    print("\n1.2 测试敏感词检测...")

    # 模拟ASR数据（包含敏感词）
    test_asr = [
        MockASRSegment("大家好，欢迎收看今天的节目", 0.0, 2.5, 1),
        MockASRSegment("他出轨了，真是让人震惊", 5.0, 7.5, 1),
        MockASRSegment("这个故事很精彩", 10.0, 12.0, 1),
        MockASRSegment("警察来了，快跑", 15.0, 17.0, 1),
        MockASRSegment("第二集开始了", 0.0, 2.0, 2),
        MockASRSegment("这个小三太过分了", 5.0, 7.5, 2),
    ]

    segments = detect_sensitive_segments(test_asr, words, verbose=True)

    if segments:
        print(f"\n   ✅ 检测到 {len(segments)} 个敏感片段:")
        for seg in segments:
            print(f"      - 第{seg.episode}集 {seg.start_time:.1f}s: '{seg.sensitive_word}' in '{seg.asr_text}'")
    else:
        print("   ℹ️ 未检测到敏感词")

    return True


def test_subtitle_detector():
    """测试字幕区域检测模块"""
    print("\n" + "=" * 70)
    print("测试2: 字幕区域检测模块")
    print("=" * 70)

    # 1. 测试默认检测
    print("\n2.1 测试默认比例检测...")
    region = detect_subtitle_region_default()
    print(f"   ✅ 默认字幕区域: {region}")

    # 2. 测试像素坐标计算
    print("\n2.2 测试像素坐标计算...")

    test_resolutions = [
        (1920, 1080),  # 横屏1080p
        (1080, 1920),  # 竖屏1080p
        (640, 360),    # 横屏360p
        (360, 640),    # 竖屏360p
    ]

    for width, height in test_resolutions:
        y, h = region.get_pixel_coords(height)
        print(f"   {width}x{height}: y={y}px, h={h}px")

    # 3. 测试保存/加载配置
    print("\n2.3 测试配置保存/加载...")

    from scripts.preprocess.subtitle_detector import save_subtitle_config, load_subtitle_config

    test_project = "test_project"
    test_resolution = (1920, 1080)

    # 保存
    config_path = save_subtitle_config(region, test_project, test_resolution)
    print(f"   ✅ 配置已保存: {config_path}")

    # 加载
    loaded_region = load_subtitle_config(test_project)
    if loaded_region:
        print(f"   ✅ 配置已加载: {loaded_region}")
    else:
        print("   ⚠️ 加载配置失败")

    # 清理测试文件
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
        config_file.parent.rmdir()
        print("   🧹 已清理测试文件")

    return True


def test_video_cleaner_mock():
    """测试视频清洗模块（模拟数据）"""
    print("\n" + "=" * 70)
    print("测试3: 视频清洗模块（模拟数据）")
    print("=" * 70)

    # 创建模拟数据
    region = SubtitleRegion(
        y_ratio=0.88,
        height_ratio=0.10,
        detection_method="default",
        confidence=0.5
    )

    segments = [
        SensitiveSegment(
            episode=1,
            sensitive_word="测试词1",
            asr_text="这是一个测试词1的句子",
            start_time=5.0,
            end_time=7.5
        ),
        SensitiveSegment(
            episode=1,
            sensitive_word="测试词2",
            asr_text="这里也有测试词2",
            start_time=15.0,
            end_time=17.0
        ),
    ]

    print(f"\n3.1 模拟敏感片段:")
    for seg in segments:
        print(f"   - {seg}")

    print(f"\n3.2 字幕区域: {region}")

    print("\n   ℹ️ 实际视频清洗需要真实视频文件")
    print("   使用 --video 参数指定视频文件进行实际测试")

    return True


def test_video_cleaner_real(video_path: str):
    """测试视频清洗模块（实际视频）"""
    print("\n" + "=" * 70)
    print("测试4: 视频清洗模块（实际视频）")
    print("=" * 70)

    video_path = Path(video_path)

    if not video_path.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    # 1. 获取视频信息
    print(f"\n4.1 获取视频信息...")
    try:
        video_info = get_video_info(str(video_path))
        print(f"   ✅ 视频信息:")
        print(f"      分辨率: {video_info['width']}x{video_info['height']}")
        print(f"      帧率: {video_info['fps']:.1f} fps")
        print(f"      时长: {video_info['duration']:.1f} 秒")
        print(f"      编码: {video_info['codec']}")
    except Exception as e:
        print(f"   ❌ 获取视频信息失败: {e}")
        return False

    # 2. 创建模拟敏感片段（实际使用时应该从ASR检测）
    print(f"\n4.2 创建测试敏感片段...")

    duration = video_info['duration']
    segments = [
        SensitiveSegment(
            episode=1,
            sensitive_word="测试词",
            asr_text="[测试]这是一个测试片段",
            start_time=min(5.0, duration - 1),
            end_time=min(7.5, duration)
        ),
    ]

    print(f"   ✅ 创建 {len(segments)} 个测试片段")

    # 3. 字幕区域
    print(f"\n4.3 字幕区域检测...")
    region = detect_subtitle_region_default()
    print(f"   ✅ 使用默认区域: {region}")

    # 4. 清洗视频
    print(f"\n4.4 开始清洗视频...")

    output_dir = project_root / "test" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"cleaned_{video_path.name}"

    try:
        result = clean_video(
            video_path=str(video_path),
            sensitive_segments=segments,
            subtitle_region=region,
            output_path=str(output_path),
            verbose=True
        )

        print(f"\n   ✅ 视频清洗成功!")
        print(f"   输出文件: {result}")

        # 验证输出文件
        if Path(result).exists():
            output_info = get_video_info(result)
            print(f"   输出视频: {output_info['width']}x{output_info['height']}, {output_info['duration']:.1f}秒")
            return True
        else:
            print(f"   ❌ 输出文件不存在")
            return False

    except Exception as e:
        print(f"   ❌ 视频清洗失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow(video_path: Optional[str] = None):
    """测试完整工作流程"""
    print("\n" + "=" * 70)
    print("完整工作流程测试")
    print("=" * 70)

    # 1. 加载敏感词
    print("\n[Step 1] 加载敏感词...")
    config_path = project_root / "config" / "sensitive_words.txt"
    words = load_sensitive_words(str(config_path))

    if not words:
        print("❌ 敏感词列表为空")
        return False

    # 2. 模拟ASR数据
    print("\n[Step 2] 准备ASR数据...")
    test_asr = [
        MockASRSegment("大家好", 0.0, 2.0, 1),
        MockASRSegment("他出轨了", 5.0, 7.0, 1),
        MockASRSegment("警察来了", 10.0, 12.0, 1),
    ]

    # 3. 检测敏感词
    print("\n[Step 3] 检测敏感词...")
    segments = detect_sensitive_segments(test_asr, words, verbose=False)
    print(f"   检测到 {len(segments)} 个敏感片段")

    # 4. 检测字幕区域
    print("\n[Step 4] 检测字幕区域...")
    region = detect_subtitle_region_default()
    print(f"   字幕区域: {region}")

    # 5. 如果有视频，进行清洗
    if video_path and Path(video_path).exists():
        print("\n[Step 5] 清洗视频...")
        output_dir = project_root / "test" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        cleaner = VideoCleaner(output_dir=str(output_dir))
        output = cleaner.clean(
            video_path=video_path,
            sensitive_segments=segments,
            subtitle_region=region,
            verbose=True
        )
        print(f"   输出: {output}")
    else:
        print("\n[Step 5] 跳过视频清洗（未提供视频文件）")

    print("\n✅ 完整流程测试通过!")
    return True


def main():
    parser = argparse.ArgumentParser(description="敏感词字幕遮盖功能测试")
    parser.add_argument(
        '--test',
        choices=['detector', 'subtitle', 'cleaner', 'full'],
        help='指定测试模块'
    )
    parser.add_argument(
        '--video',
        type=str,
        help='指定测试视频文件'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("敏感词字幕遮盖功能测试")
    print("=" * 70)
    print(f"项目根目录: {project_root}")

    # 运行测试
    success = True

    if args.test == 'detector' or args.test is None:
        success = test_sensitive_detector() and success

    if args.test == 'subtitle' or args.test is None:
        success = test_subtitle_detector() and success

    if args.test == 'cleaner':
        if args.video:
            success = test_video_cleaner_real(args.video) and success
        else:
            success = test_video_cleaner_mock() and success

    if args.test == 'full':
        success = test_full_workflow(args.video) and success

    # 如果提供了视频但没有指定测试，运行实际视频测试
    if args.video and args.test is None:
        success = test_video_cleaner_real(args.video) and success

    # 总结
    print("\n" + "=" * 70)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
