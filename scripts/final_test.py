#!/usr/bin/env python3
"""
修复版全面测试脚本
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, '.')

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

# 创建输出目录
output_dir = Path("test/comprehensive_test")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 100)
print("🎯 全面测试：所有8个项目（80集）")
print("=" * 100)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"输出目录: {output_dir.absolute()}")
print()

# 初始化检测器
detector = EndingCreditsDetector()

results = []
total_videos = 0
correct_count = 0
errors = []

for project_name, ground_truth in GROUND_TRUTH.items():
    source = ground_truth['source']
    expected = ground_truth['has_ending']

    # 构建项目路径
    project_path = Path(source) / project_name

    if not project_path.exists():
        print(f"⚠️  项目路径不存在: {project_path}")
        continue

    # 查找视频文件
    video_files = sorted(project_path.glob('*.mp4'), key=lambda x: int(x.stem))

    if not video_files:
        print(f"⚠️  未找到视频文件: {project_path}")
        continue

    print(f"\n{'=' * 100}")
    print(f"项目: {project_name}")
    print(f"来源: {source}")
    print(f"期望: {'有片尾' if expected else '无片尾'}")
    print(f"总集数: {len(video_files)}")
    print(f"{'=' * 100}")

    # 测试所有集
    for video_file in video_files:
        episode = int(video_file.stem)
        video_path = str(video_file)

        try:
            # 调用检测模块
            result = detector.detect_video_ending(video_path, episode)

            total_videos += 1
            actual = result.ending_info.has_ending
            is_correct = (actual == expected)

            if is_correct:
                correct_count += 1
                status = "✅"
            else:
                status = "❌"

            print(f"  第{episode:2d}集: {status} - {'有片尾' if actual else '无片尾'} ({result.ending_info.duration:.2f}秒)")

            # 保存结果
            results.append({
                'project': project_name,
                'source': source,
                'episode': episode,
                'video_path': video_path,
                'expected': expected,
                'actual': actual,
                'correct': is_correct,
                'duration': result.ending_info.duration,
                'method': result.ending_info.method,
                'confidence': result.ending_info.confidence,
                'effective_duration': result.effective_duration
            })

        except Exception as e:
            print(f"  第{episode:2d}集: ❌ 异常 - {e}")
            errors.append(f"{project_name} 第{episode}集: {str(e)}")
            import traceback
            traceback.print_exc()

# 保存详细结果到JSON
results_file = output_dir / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'total_videos': total_videos,
        'correct_count': correct_count,
        'accuracy': correct_count / total_videos if total_videos > 0 else 0,
        'results': results,
        'errors': errors
    }, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 100}")
print("📊 测试完成")
print(f"{'=' * 100}")
print(f"总视频数: {total_videos}")
print(f"正确数: {correct_count}")
print(f"错误数: {len(errors)}")
print(f"\n总体准确率: {correct_count / total_videos:.1%}" if total_videos > 0 else "无数据")
print(f"\n结果已保存到: {results_file}")

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
    status = "✅" if accuracy == 1.0 else "⚠️"

    print(f"\n{status} {project_name}")
    print(f"  期望: {'有片尾' if expected else '无片尾'}")
    print(f"  准确率: {accuracy:.1%} ({correct}/{total})")

    # 列出错误案例
    if accuracy < 1.0:
        for r in project_results:
            if not r['correct']:
                print(f"    ❌ 第{r['episode']}集: {'有片尾' if r['actual'] else '无片尾'} (期望: {'有片尾' if r['expected'] else '无片尾'})")

if correct_count == total_videos and total_videos > 0:
    print(f"\n{'=' * 100}")
    print("🎉 恭喜！达到100%准确率！")
    print(f"{'=' * 100}")
    sys.exit(0)
else:
    print(f"\n{'=' * 100}")
    print("⚠️  未达到100%准确率")
    print(f"{'=' * 100}")

    # 列出所有错误
    if errors:
        print(f"\n错误详情:")
        for error in errors:
            print(f"  - {error}")

    sys.exit(1)
