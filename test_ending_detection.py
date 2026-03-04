#!/usr/bin/env python3
"""
测试片尾检测模块 - 多子多福项目
"""
import sys
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from pathlib import Path
from scripts.detect_ending_credits import detect_project_endings, EndingCreditsDetector

print("=" * 70)
print("🧪 测试片尾检测模块")
print("=" * 70)

# 测试配置
project_path = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆"
output_dir = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/ending_credits"

print(f"\n项目路径: {project_path}")
print(f"输出目录: {output_dir}")

# 先测试单个视频（第1集）
print(f"\n" + "=" * 70)
print(f"测试1: 单个视频检测（第1集）")
print(f"=" * 70)

detector = EndingCreditsDetector()
video_path = f"{project_path}/1.mp4"

try:
    result = detector.detect_video_ending(
        video_path=video_path,
        episode=1,
        asr_segments=None  # 暂时不使用ASR
    )

    print(f"\n✅ 单个视频检测完成")
    print(f"   原始时长: {result.total_duration:.2f}秒")
    print(f"   片尾时长: {result.ending_info.duration:.2f}秒")
    print(f"   有效时长: {result.effective_duration:.2f}秒")
    print(f"   检测方法: {result.ending_info.method}")

except Exception as e:
    print(f"❌ 单个视频检测失败: {e}")
    import traceback
    traceback.print_exc()

# 测试批量检测（前3集）
print(f"\n" + "=" * 70)
print(f"测试2: 批量检测（前3集）")
print(f"=" * 70)

try:
    # 只处理前3集进行测试
    from scripts.detect_ending_credits import detect_project_endings

    result = detect_project_endings(
        project_path=project_path,
        output_dir=output_dir
    )

    if result:
        print(f"\n✅ 批量检测完成")
        print(f"\n各集详情:")
        for ep in result.episodes[:3]:
            print(f"\n  第{ep.episode}集:")
            print(f"    原始时长: {ep.total_duration:.2f}秒")
            print(f"    片尾时长: {ep.ending_info.duration:.2f}秒")
            print(f"    有效时长: {ep.effective_duration:.2f}秒")
            print(f"    检测方法: {ep.ending_info.method}")

except Exception as e:
    print(f"❌ 批量检测失败: {e}")
    import traceback
    traceback.print_exc()

print(f"\n" + "=" * 70)
print(f"测试完成")
print(f"=" * 70)
