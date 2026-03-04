#!/usr/bin/env python3
"""
强制重新处理多子多福项目 - V14智能过滤版本
"""
import sys
import os
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

print("=" * 70)
print("🧪 重新处理多子多福项目 - V14智能关键帧过滤")
print("=" * 70)

from scripts.understand.video_understand import video_understand
import json

project_path = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆"

print(f"\n项目路径: {project_path}\n")

# 运行视频理解
result = video_understand(project_path=project_path)

# 保存结果
output_dir = f"/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/analysis/{result['projectName']}"
os.makedirs(output_dir, exist_ok=True)

with open(f"{output_dir}/result.json", 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 结果已保存到: {output_dir}/result.json")

# 显示结果统计
print("\n" + "=" * 70)
print("📊 处理结果统计")
print("=" * 70)

print(f"\n✅ 高光点：{len(result.get('highlights', []))} 个")
for i, hl in enumerate(result.get('highlights', [])[:10], 1):
    print(f"   {i:2d}. EP{hl.get('episode'):2d} {hl.get('timestamp'):6.1f}s - {hl.get('type')} (置信度: {hl.get('confidence', 0):.1f})")

if len(result.get('highlights', [])) > 10:
    print(f"   ... 还有 {len(result.get('highlights', [])) - 10} 个")

print(f"\n✅ 钩子点：{len(result.get('hooks', []))} 个")
for i, hook in enumerate(result.get('hooks', [])[:10], 1):
    print(f"   {i:2d}. EP{hook.get('episode'):2d} {hook.get('timestamp'):6.1f}s - {hook.get('type')} (置信度: {hook.get('confidence', 0):.1f})")

if len(result.get('hooks', [])) > 10:
    print(f"   ... 还有 {len(result.get('hooks', [])) - 10} 个")

print(f"\n✅ 剪辑组合：{len(result.get('clips', []))} 个")

# 剪辑时长统计
clips = result.get('clips', [])
if clips:
    durations = [c.get('duration', 0) for c in clips]
    print(f"\n📏 剪辑时长统计：")
    print(f"   最短：{min(durations):6.1f}秒 ({min(durations)/60:5.2f}分钟)")
    print(f"   最长：{max(durations):6.1f}秒 ({max(durations)/60:5.2f}分钟)")
    print(f"   平均：{sum(durations)/len(durations):6.1f}秒 ({sum(durations)/len(durations)/60:5.2f}分钟)")

    # 验证时长限制
    from scripts.understand.generate_clips import MIN_CLIP_DURATION, MAX_CLIP_DURATION

    print(f"\n📏 限制范围：{MIN_CLIP_DURATION/60:.0f} - {MAX_CLIP_DURATION/60:.0f} 分钟")

    # 检查是否符合
    valid_count = sum(1 for d in durations if MIN_CLIP_DURATION <= d <= MAX_CLIP_DURATION)
    too_short = [d for d in durations if d < MIN_CLIP_DURATION]
    too_long = [d for d in durations if d > MAX_CLIP_DURATION]

    if valid_count == len(durations):
        print(f"✅ 所有剪辑都符合时长要求")
    else:
        if too_short:
            print(f"⚠️  有 {len(too_short)} 个剪辑短于 {MIN_CLIP_DURATION/60:.0f} 分钟")
        if too_long:
            print(f"⚠️  有 {len(too_long)} 个剪辑长于 {MAX_CLIP_DURATION/60:.0f} 分钟")

    # 显示前10个剪辑
    print(f"\n前10个剪辑：")
    for i, clip in enumerate(clips[:10], 1):
        duration_min = clip.get('duration', 0) / 60
        print(f"   {i:2d}. EP{clip.get('episode'):2d}→{clip.get('hookEpisode'):2d} - {duration_min:5.2f}分钟 - {clip.get('type')}")

    if len(clips) > 10:
        print(f"   ... 还有 {len(clips) - 10} 个")

print("\n" + "=" * 70)
print("🎉 处理完成！")
print("=" * 70)

# 对比旧版本
print("\n" + "=" * 70)
print("📈 V13 vs V14 对比")
print("=" * 70)

backup_file = f"{output_dir}/result.json.backup"
if os.path.exists(backup_file):
    with open(backup_file, 'r', encoding='utf-8') as f:
        old_result = json.load(f)

    old_clips = old_result.get('clips', [])
    if old_clips:
        old_durations = [c['duration'] for c in old_clips]
        print(f"\nV13 (旧版本):")
        print(f"  高光点：{len(old_result.get('highlights', []))} 个")
        print(f"  钩子点：{len(old_result.get('hooks', []))} 个")
        print(f"  剪辑组合：{len(old_clips)} 个")
        print(f"  最短：{min(old_durations)/60:.2f} 分钟")
        print(f"  最长：{max(old_durations)/60:.2f} 分钟")
        print(f"  平均：{sum(old_durations)/len(old_durations)/60:.2f} 分钟")

print(f"\nV14 (新版本 - 智能过滤):")
print(f"  高光点：{len(result.get('highlights', []))} 个")
print(f"  钩子点：{len(result.get('hooks', []))} 个")
print(f"  剪辑组合：{len(clips)} 个")
print(f"  最短：{min(durations)/60:.2f} 分钟")
print(f"  最长：{max(durations)/60:.2f} 分钟")
print(f"  平均：{sum(durations)/len(durations)/60:.2f} 分钟")
