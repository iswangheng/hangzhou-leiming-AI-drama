#!/usr/bin/env python3
"""
测试ASR增强检测算法的准确率

目标：验证在8个项目（80集视频）上是否达到100%准确率

Ground Truth:
- 有片尾（需要剪）: 多子多福, 欺我年迈抢祖宅, 老公成为首富, 飒爽女友不好惹
- 无片尾（不剪）: 雪烬梨香, 休书落纸, 不晚忘忧, 恋爱综艺
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.detect_ending_credits import EndingCreditsDetector, detect_project_endings
from scripts.ending_credits_config import should_detect_ending, load_project_config

# Ground Truth数据
GROUND_TRUTH = {
    # 晓红姐-3.4剧目（有片尾）
    "多子多福，开局就送绝美老婆": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "欺我年迈抢祖宅，和贫道仙法说吧": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "老公成为首富那天我重生了": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "飒爽女友不好惹": {"has_ending": True, "source": "晓红姐-3.4剧目"},

    # 新的漫剧素材（无片尾，之前误判）
    "雪烬梨香": {"has_ending": False, "source": "新的漫剧素材"},
    "休书落纸": {"has_ending": False, "source": "新的漫剧素材"},
    "不晚忘忧": {"has_ending": False, "source": "新的漫剧素材"},
    "恋爱综艺，匹配到心动男友": {"has_ending": False, "source": "新的漫剧素材"},
}


def test_detection_accuracy(base_path: str):
    """
    测试检测准确率

    Args:
        base_path: 视频库基础路径
    """
    print("=" * 100)
    print("🎯 测试ASR增强检测算法准确率")
    print("=" * 100)

    results = []
    total_videos = 0
    correct_count = 0
    false_positives = 0  # 误报：无片尾被检测为有片尾
    false_negatives = 0  # 漏报：有片尾被检测为无片尾

    for project_name, ground_truth in GROUND_TRUTH.items():
        print(f"\n{'=' * 100}")
        print(f"项目: {project_name}")
        print(f"来源: {ground_truth['source']}")
        print(f"Ground Truth: {'有片尾' if ground_truth['has_ending'] else '无片尾'}")
        print(f"{'=' * 100}")

        # 构建项目路径
        project_path = Path(base_path) / ground_truth['source'] / project_name

        if not project_path.exists():
            print(f"⚠️  项目路径不存在: {project_path}")
            continue

        # 执行检测
        try:
            result = detect_project_endings(
                project_path=str(project_path),
                project_name=project_name,
                output_dir="data/hangzhou-leiming/ending_credits_asr"
            )

            if not result:
                print(f"❌ 检测失败")
                continue

            # 统计该项目的检测结果
            episodes_with_ending = sum(1 for ep in result.episodes if ep.ending_info.has_ending)
            total_episodes = len(result.episodes)

            print(f"\n检测结果:")
            print(f"  总集数: {total_episodes}")
            print(f"  检测为有片尾: {episodes_with_ending}集")
            print(f"  检测为无片尾: {total_episodes - episodes_with_ending}集")

            # 判断该项目是否准确
            expected = ground_truth['has_ending']
            detected = (episodes_with_ending / total_episodes) > 0.5  # 超过50%集数有片尾就算有

            # 统计每一集的准确性
            for ep in result.episodes:
                total_videos += 1
                is_correct = ep.ending_info.has_ending == expected

                if is_correct:
                    correct_count += 1
                else:
                    if expected and not ep.ending_info.has_ending:
                        false_negatives += 1
                        print(f"  ❌ 第{ep.episode}集: 漏报（有片尾被检测为无片尾）")
                    else:
                        false_positives += 1
                        print(f"  ❌ 第{ep.episode}集: 误报（无片尾被检测为有片尾）")

            results.append({
                'project_name': project_name,
                'expected_has_ending': expected,
                'detected_has_ending': detected,
                'episodes_with_ending': episodes_with_ending,
                'total_episodes': total_episodes,
                'accuracy': sum(1 for ep in result.episodes if ep.ending_info.has_ending == expected) / total_episodes
            })

            # 显示该项目结果
            accuracy = results[-1]['accuracy']
            status = "✅" if accuracy == 1.0 else "❌"
            print(f"\n{status} 该项目准确率: {accuracy:.1%}")

        except Exception as e:
            print(f"❌ 检测过程出错: {e}")
            import traceback
            traceback.print_exc()

    # 输出总体结果
    print(f"\n{'=' * 100}")
    print("📊 总体测试结果")
    print(f"{'=' * 100}")
    print(f"总视频数: {total_videos}")
    print(f"正确数: {correct_count}")
    print(f"误报数（无→有）: {false_positives}")
    print(f"漏报数（有→无）: {false_negatives}")
    print(f"\n总体准确率: {correct_count / total_videos:.1%}")

    # 按项目统计
    print(f"\n{'=' * 100}")
    print("📋 各项目详细结果")
    print(f"{'=' * 100}")

    for result in results:
        status = "✅" if result['accuracy'] == 1.0 else "❌"
        print(f"\n{status} {result['project_name']}")
        print(f"  期望: {'有片尾' if result['expected_has_ending'] else '无片尾'}")
        print(f"  检测: {'有片尾' if result['detected_has_ending'] else '无片尾'}")
        print(f"  准确率: {result['accuracy']:.1%}")
        print(f"  有片尾集数: {result['episodes_with_ending']}/{result['total_episodes']}")

    # 检查是否达到100%准确率
    if correct_count == total_videos:
        print(f"\n{'=' * 100}")
        print("🎉 恭喜！达到100%准确率！")
        print(f"{'=' * 100}")
        return True
    else:
        print(f"\n{'=' * 100}")
        print("⚠️  未达到100%准确率，需要继续优化算法")
        print(f"{'=' * 100}")
        return False


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python scripts/test_asr_enhanced_detection.py <视频库基础路径>")
        print("\n示例:")
        print("  python scripts/test_asr_enhanced_detection.py /path/to/videos")
        sys.exit(1)

    base_path = sys.argv[1]

    # 执行测试
    success = test_detection_accuracy(base_path)

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
