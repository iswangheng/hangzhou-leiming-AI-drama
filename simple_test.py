#!/usr/bin/env python3
"""简单测试"""
import sys
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

print("开始测试多子多福项目...")

from scripts.understand.video_understand import video_understand

project_path = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆"

print(f"项目路径: {project_path}")

result = video_understand(project_path=project_path)

print(f"\n处理完成!")
print(f"高光点: {len(result.get('highlights', []))} 个")
print(f"钩子点: {len(result.get('hooks', []))} 个")
print(f"剪辑组合: {len(result.get('clips', []))} 个")

# 检查剪辑时长
clips = result.get('clips', [])
if clips:
    durations = [c.get('duration', 0) for c in clips]
    print(f"\n时长统计:")
    print(f"  最短: {min(durations)/60:.1f} 分钟")
    print(f"  最长: {max(durations)/60:.1f} 分钟")
    print(f"  平均: {sum(durations)/len(durations)/60:.1f} 分钟")

print("\n测试完成!")
