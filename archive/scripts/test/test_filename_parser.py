"""
测试文件名解析功能

该测试脚本验证文件名解析工具的兼容性，确保支持各种视频文件命名格式。
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.filename_parser import parse_episode_number, find_video_files, validate_video_files


def test_parse_episode_number():
    """测试文件名解析功能"""
    test_cases = [
        # (文件名, 期望结果)
        ("1.mp4", 1),
        ("01.mp4", 1),
        ("001.mp4", 1),
        ("10.mp4", 10),
        ("精准-1.mp4", 1),
        ("精准-01.mp4", 1),
        ("精准-10.mp4", 10),
        ("机长姐姐-1.mp4", 1),
        ("机长姐姐-5.mp4", 5),
        ("ep01.mp4", 1),
        ("ep1.mp4", 1),
        ("EP01.mp4", 1),
        ("EP10.mp4", 10),
        ("e01.mp4", 1),
        ("E05.mp4", 5),
        ("第1集.mp4", 1),
        ("第01集.mp4", 1),
        ("第10集.mp4", 10),
        ("01 骨血灯.mp4", 1),
        ("骨血灯_03_1080p.mp4", 3),
        ("show_05_1080p.mp4", 5),
        ("drama-07-final.mp4", 7),
        ("trailer.mp4", None),  # 应该返回None
        ("preview.mp4", None),
    ]

    print("=" * 80)
    print("测试文件名解析功能")
    print("=" * 80)
    print()

    passed = 0
    failed = 0
    failed_cases = []

    for filename, expected in test_cases:
        result = parse_episode_number(filename)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1
            failed_cases.append((filename, expected, result))

        result_str = f"第{result}集" if result is not None else "None"
        expected_str = f"第{expected}集" if expected is not None else "None"
        print(f"{status} {filename:30s} → {result_str:10s} (期望: {expected_str})")

    print()
    print(f"总计: {passed} 通过, {failed} 失败")
    print()

    if failed_cases:
        print("失败的测试用例:")
        for filename, expected, result in failed_cases:
            print(f"  - {filename}: 期望 {expected}, 得到 {result}")

    return failed == 0


def test_real_files():
    """测试实际视频文件"""
    print("=" * 80)
    print("测试实际视频文件")
    print("=" * 80)
    print()

    # 测试目录（相对于项目根目录）
    test_dirs = [
        "hangzhou-leiming-AI-drama/漫剧素材/小小飞梦",
        "hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧",
        "hangzhou-leiming-AI-drama/漫剧参考/精准",
        "hangzhou-leiming-AI-drama/漫剧参考/机长姐姐",
    ]

    for test_dir in test_dirs:
        full_path = project_root / test_dir

        if not full_path.exists():
            print(f"⚠️  目录不存在: {test_dir}")
            print()
            continue

        print(f"📁 {test_dir}")
        print("-" * 80)

        # 获取前5个mp4文件
        mp4_files = sorted([f for f in full_path.glob("*.mp4")])[:5]

        for video_file in mp4_files:
            episode = parse_episode_number(video_file.name)
            if episode is not None:
                print(f"  ✅ {video_file.name:30s} → 第{episode}集")
            else:
                print(f"  ❌ {video_file.name:30s} → 无法解析")
        print()


def test_video_finding():
    """测试视频文件查找功能"""
    print("=" * 80)
    print("测试视频文件查找功能")
    print("=" * 80)
    print()

    test_cases = [
        ("hangzhou-leiming-AI-drama/漫剧素材/小小飞梦", 1),
        ("hangzhou-leiming-AI-drama/漫剧素材/小小飞梦", 5),
        ("hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧", 1),
        ("hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧", 5),
        ("hangzhou-leiming-AI-drama/漫剧参考/精准", 1),
        ("hangzhou-leiming-AI-drama/漫剧参考/精准", 3),
    ]

    for video_dir, episode in test_cases:
        full_path = project_root / video_dir

        if not full_path.exists():
            print(f"⚠️  目录不存在: {video_dir}")
            continue

        result = find_video_files(str(full_path), episode)
        if result:
            filename = os.path.basename(result)
            print(f"✅ 第{episode:2d}集 ({video_dir.split('/')[-1]:20s}) → {filename}")
        else:
            print(f"❌ 第{episode:2d}集 ({video_dir.split('/')[-1]:20s}) → 未找到")

    print()


def test_validation():
    """测试视频文件验证功能"""
    print("=" * 80)
    print("测试视频文件验证功能")
    print("=" * 80)
    print()

    test_dirs = [
        "hangzhou-leiming-AI-drama/漫剧素材/小小飞梦",
        "hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧",
        "hangzhou-leiming-AI-drama/漫剧参考/精准",
    ]

    for test_dir in test_dirs:
        full_path = project_root / test_dir

        if not full_path.exists():
            continue

        print(f"📁 {test_dir}")
        result = validate_video_files(str(full_path))

        print(f"  总文件数: {result['total']}")
        print(f"  成功解析: {result['parsed']}")
        print(f"  解析失败: {result['failed']}")

        if result['episodes']:
            print(f"  集数范围: 第{min(result['episodes'])}集 - 第{max(result['episodes'])}集")

        if result['missing']:
            print(f"  ⚠️  缺失集数: {result['missing']}")

        if result['duplicates']:
            print(f"  ⚠️  重复集数: {result['duplicates']}")

        if result['unparsed']:
            print(f"  无法解析的文件: {result['unparsed']}")

        print()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "文件名解析工具 - 兼容性测试" + " " * 26 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\n")

    # 运行各项测试
    test1_passed = test_parse_episode_number()
    test_real_files()
    test_video_finding()
    test_validation()

    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()

    if test1_passed:
        print("✅ 文件名解析功能测试通过")
    else:
        print("❌ 文件名解析功能测试失败，需要修复")

    print()
    print("建议:")
    if not test1_passed:
        print("  1. 检查并调整正则表达式")
        print("  2. 添加更多测试用例")
        print("  3. 重新运行测试")
    else:
        print("  1. 继续在实际数据上验证")
        print("  2. 运行训练流程测试")
        print("  3. 运行AI分析流程测试")

    print()

    return test1_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
