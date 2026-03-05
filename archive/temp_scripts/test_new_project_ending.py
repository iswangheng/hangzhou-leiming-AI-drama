#!/usr/bin/env python3
"""
测试新项目的片尾检测 - 不晚忘忧
"""
import sys
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from pathlib import Path
from scripts.detect_ending_credits import detect_project_endings

print("=" * 80)
print("🧪 测试新项目片尾检测: 不晚忘忧")
print("=" * 80)

# 测试配置
project_path = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧"
output_dir = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/ending_credits"

print(f"\n项目路径: {project_path}")
print(f"输出目录: {output_dir}")

# 批量检测
try:
    result = detect_project_endings(
        project_path=project_path,
        output_dir=output_dir
    )

    if result:
        print(f"\n✅ 检测完成")
        print(f"\n各集详情:")
        for ep in result.episodes:
            status = "✅" if ep.ending_info.has_ending else "❌"
            ending_type = ep.ending_info.method if ep.ending_info.has_ending else "无片尾"
            print(f"  第{ep.episode}集: {status} {ending_type} - {ep.ending_info.duration:.2f}秒")

        # 统计
        has_ending = sum(1 for ep in result.episodes if ep.ending_info.has_ending)
        no_ending = sum(1 for ep in result.episodes if not ep.ending_info.has_ending)

        print(f"\n📊 统计:")
        print(f"  总集数: {len(result.episodes)}")
        print(f"  有片尾: {has_ending}集")
        print(f"  无片尾: {no_ending}集")

        if has_ending > 0:
            avg_duration = sum(ep.ending_info.duration for ep in result.episodes if ep.ending_info.has_ending) / has_ending
            print(f"  平均片尾时长: {avg_duration:.2f}秒")

except Exception as e:
    print(f"❌ 检测失败: {e}")
    import traceback
    traceback.print_exc()
