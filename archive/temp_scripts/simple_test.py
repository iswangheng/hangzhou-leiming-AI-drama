#!/usr/bin/env python3
"""
简单测试脚本：测试单个项目
"""
import sys
import subprocess
from pathlib import Path

# 测试配置
test_configs = [
    ("多子多福，开局就送绝美老婆", "晓红姐-3.4剧目", True),
    ("雪烬梨香", "新的漫剧素材", False),
]

print("=" * 100)
print("🎯 简化测试：2个项目（有片尾 vs 无片尾）")
print("=" * 100)

results = []

for project_name, source, expected_has_ending in test_configs:
    print(f"\n{'=' * 100}")
    print(f"测试项目: {project_name}")
    print(f"来源: {source}")
    print(f"期望: {'有片尾' if expected_has_ending else '无片尾'}")
    print(f"{'=' * 100}")

    # 构建项目路径
    project_path = Path(source) / project_name

    if not project_path.exists():
        print(f"⚠️  项目路径不存在: {project_path}")
        continue

    # 查找视频文件
    video_files = sorted(project_path.glob('*.mp4'), key=lambda x: int(x.stem))

    if not video_files:
        print(f"⚠️  未找到视频文件")
        continue

    # 测试第1集
    video_path = str(video_files[0])
    episode = 1

    print(f"\n测试视频: {Path(video_path).name}")

    # 调用检测模块
    cmd = [
        'python3', '-c',
        f'''
import sys
sys.path.insert(0, '.')

from scripts.detect_ending_credits import EndingCreditsDetector

detector = EndingCreditsDetector()
result = detector.detect_video_ending("{video_path}", {episode})

print(f"RESULT: {{'has_ending': {result.ending_info.has_ending}, 'duration': {result.ending_info.duration}, 'method': '{result.ending_info.method}'}}")
'''
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=Path.cwd())

        # 解析结果
        for line in result.stdout.split('\n'):
            if line.startswith('RESULT:'):
                import ast
                result_dict = ast.literal_eval(line.split('RESULT:')[1].strip())

                actual_has_ending = result_dict['has_ending']
                duration = result_dict['duration']
                method = result_dict['method']

                is_correct = (actual_has_ending == expected_has_ending)
                status = "✅ 正确" if is_correct else "❌ 错误"

                print(f"{status} - {'有片尾' if actual_has_ending else '无片尾'} ({duration:.2f}秒)")
                print(f"  检测方法: {method}")

                results.append({
                    'project': project_name,
                    'expected': expected_has_ending,
                    'actual': actual_has_ending,
                    'correct': is_correct
                })

                break
    except Exception as e:
        print(f"❌ 测试失败: {e}")

# 输出总结
print(f"\n{'=' * 100}")
print("📊 测试总结")
print(f"{'=' * 100}")

correct_count = sum(1 for r in results if r['correct'])
total_count = len(results)

for r in results:
    status = "✅" if r['correct'] else "❌"
    print(f"{status} {r['project']}: {'有片尾' if r['expected'] else '无片尾'}")

print(f"\n准确率: {correct_count}/{total_count} = {correct_count/total_count:.1%}")

if correct_count == total_count:
    print("🎉 全部正确！")
else:
    print("⚠️  存在错误，需要优化")
