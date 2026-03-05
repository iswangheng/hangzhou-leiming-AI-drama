#!/usr/bin/env python3
"""
快速测试所有8个项目（每项目3集）
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from scripts.detect_ending_credits import EndingCreditsDetector

# Ground Truth
GROUND_TRUTH = {
    # 晓红姐-3.4剧目（有片尾）
    "多子多福，开局就送绝美老婆": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "欺我年迈抢祖宅，和贫道仙法说吧": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "老公成为首富那天我重生了": {"has_ending": True, "source": "晓红姐-3.4剧目"},
    "飒爽女友不好惹": {"has_ending": True, "source": "晓红姐-3.4剧目"},

    # 新的漫剧素材（无片尾）
    "雪烬梨香": {"has_ending": False, "source": "新的漫剧素材"},
    "休书落纸": {"has_ending": False, "source": "新的漫剧素材"},
    "不晚忘忧": {"has_ending": False, "source": "新的漫剧素材"},
    "恋爱综艺，匹配到心动男友": {"has_ending": False, "source": "新的漫剧素材"},
}

detector = EndingCreditsDetector()

print("=" * 100)
print("🎯 快速测试：所有8个项目（每项目3集）")
print("=" * 100)

results = []
total_videos = 0
correct_count = 0
false_positives = 0
false_negatives = 0

for project_name, ground_truth in GROUND_TRUTH.items():
    source = ground_truth['source']
    expected = ground_truth['has_ending']

    # 构建项目路径
    project_path = Path(source) / project_name

    if not project_path.exists():
        print(f"\n⚠️  项目路径不存在: {project_path}")
        continue

    # 查找视频文件
    video_files = sorted(project_path.glob('*.mp4'), key=lambda x: int(x.stem))

    if not video_files:
        print(f"\n⚠️  未找到视频文件: {project_path}")
        continue

    # 测试第1、中间、最后一集（共3集）
    test_indices = [0, len(video_files)//2, len(video_files)-1]
    test_episodes = [video_files[i] for i in test_indices if i < len(video_files)]

    print(f"\n{'=' * 100}")
    print(f"项目: {project_name}")
    print(f"来源: {source}")
    print(f"期望: {'有片尾' if expected else '无片尾'}")
    print(f"测试集数: {len(test_episodes)}集")
    print(f"{'=' * 100}")

    for video_file in test_episodes:
        episode = int(video_file.stem)
        video_path = str(video_file)

        # 执行检测
        result = detector.detect_video_ending(video_path, episode)

        total_videos += 1
        actual = result.ending_info.has_ending
        is_correct = (actual == expected)

        if is_correct:
            correct_count += 1
            status = "✅"
        else:
            if expected and not actual:
                false_negatives += 1
                status = "❌ 漏报"
            else:
                false_positives += 1
                status = "❌ 误报"

        print(f"  第{episode:2d}集: {status} - {'有片尾' if actual else '无片尾'} ({result.ending_info.duration:.2f}秒)")

        results.append({
            'project': project_name,
            'episode': episode,
            'expected': expected,
            'actual': actual,
            'correct': is_correct,
            'duration': result.ending_info.duration,
            'method': result.ending_info.method
        })

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

for project_name in GROUND_TRUTH.keys():
    project_results = [r for r in results if r['project'] == project_name]
    if not project_results:
        continue

    correct = sum(1 for r in project_results if r['correct'])
    total = len(project_results)
    accuracy = correct / total

    expected = project_results[0]['expected']
    status = "✅" if accuracy == 1.0 else "❌"

    print(f"\n{status} {project_name}")
    print(f"  期望: {'有片尾' if expected else '无片尾'}")
    print(f"  准确率: {accuracy:.1%} ({correct}/{total})")

# 检查是否达到100%准确率
if correct_count == total_videos:
    print(f"\n{'=' * 100}")
    print("🎉 恭喜！快速测试达到100%准确率！")
    print(f"{'=' * 100}")
else:
    print(f"\n{'=' * 100}")
    print("⚠️  未达到100%准确率，需要优化算法")
    print(f"{'=' * 100}")

    # 列出错误案例
    print(f"\n❌ 错误案例详情:")
    for r in results:
        if not r['correct']:
            print(f"  {r['project']} 第{r['episode']}集:")
            print(f"    期望: {'有片尾' if r['expected'] else '无片尾'}")
            print(f"    实际: {'有片尾' if r['actual'] else '无片尾'}")
            print(f"    片尾时长: {r['duration']:.2f}秒")
            print(f"    检测方法: {r['method']}")

# 返回退出码
sys.exit(0 if correct_count == total_videos else 1)
