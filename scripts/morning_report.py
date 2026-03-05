#!/usr/bin/env python3
"""
清晨汇报脚本：生成测试结果报告
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

# 读取测试结果
output_dir = Path("test/comprehensive_test")
result_files = sorted(output_dir.glob("results_*.json"), reverse=True)

if not result_files:
    print("⚠️  未找到测试结果文件")
    print(f"   请检查目录: {output_dir.absolute()}")
    sys.exit(1)

latest_result = result_files[0]

with open(latest_result, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 生成报告
print("=" * 100)
print("🌅 早安！测试结果报告")
print("=" * 100)
print(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"测试时间: {data['timestamp']}")
print()

# 总体结果
total = data['total_videos']
correct = data['correct_count']
accuracy = data['accuracy']

print("📊 总体结果")
print("-" * 100)
print(f"总视频数: {total}")
print(f"正确数: {correct}")
print(f"准确率: {accuracy:.1%}")
print()

# 判断是否达到目标
if accuracy == 1.0:
    print("🎉 恭喜！达到100%准确率！")
elif accuracy >= 0.95:
    print("✅ 准确率很高，接近目标")
elif accuracy >= 0.90:
    print("⚠️  准确率不错，但仍需优化")
else:
    print("❌ 准确率不够，需要重点优化")

print()

# 按项目统计
print("📋 各项目详细结果")
print("-" * 100)

# 按项目分组
projects = {}
for r in data['results']:
    project_name = r['project']
    if project_name not in projects:
        projects[project_name] = []
    projects[project_name].append(r)

for project_name in sorted(projects.keys()):
    project_results = projects[project_name]
    correct = sum(1 for r in project_results if r['correct'])
    total_episodes = len(project_results)
    acc = correct / total_episodes

    expected = project_results[0]['expected']

    status = "✅" if acc == 1.0 else "⚠️" if acc >= 0.8 else "❌"

    print(f"\n{status} {project_name}")
    print(f"   期望: {'有片尾' if expected else '无片尾'}")
    print(f"   准确率: {acc:.1%} ({correct}/{total_episodes})")

    # 列出错误案例
    if acc < 1.0:
        print(f"   错误案例:")
        for r in project_results:
            if not r['correct']:
                print(f"     第{r['episode']:2d}集: {'有片尾' if r['actual'] else '无片尾'} "
                      f"(期望: {'有片尾' if r['expected'] else '无片尾'}) "
                      f"方法: {r['method']} "
                      f"时长: {r['duration']:.2f}秒)")

# 错误详情
if data['errors']:
    print("\n" + "=" * 100)
    print("❌ 异常详情")
    print("-" * 100)
    for error in data['errors'][:10]:  # 只显示前10个
        print(f"  - {error}")
    if len(data['errors']) > 10:
        print(f"  ... 还有 {len(data['errors']) - 10} 个错误")

# 下一步建议
print("\n" + "=" * 100)
print("💡 下一步建议")
print("-" * 100)

if accuracy == 1.0:
    print("✅ 算法已达到100%准确率！")
    print("   建议：集成到渲染流程中")
    print("   建议：在新项目上验证算法")
elif accuracy >= 0.95:
    print("⚠️  准确率很高，但还有少量误判")
    print("   建议：查看错误案例，分析误判原因")
    print("   建议：针对性优化算法")
elif accuracy >= 0.90:
    print("⚠️  准确率尚可，但存在较多误判")
    print("   建议：重点分析错误案例")
    print("   建议：调整ASR分析阈值")
    print("   建议：优化判断逻辑")
else:
    print("❌ 准确率较低，需要大幅优化")
    print("   建议：重新审视算法设计")
    print("   建议：考虑引入更多特征")
    print("   建议：可能需要人工标注更多样本")

print("\n" + "=" * 100)
print(f"完整结果文件: {latest_result}")
print("=" * 100)

# 返回退出码
sys.exit(0 if accuracy == 1.0 else 1)
