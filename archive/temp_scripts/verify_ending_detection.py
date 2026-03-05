#!/usr/bin/env python3
"""
验证片尾检测准确性 - 提取关键帧供人工检查
"""
import sys
import json
import subprocess
from pathlib import Path

sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

# 读取检测结果
result_file = Path("data/hangzhou-leiming/ending_credits/多子多福，开局就送绝美老婆_ending_credits.json")
with open(result_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建输出目录
output_dir = Path("test/ending_frames_verification")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🔍 片尾检测准确性验证")
print("=" * 80)

# 选择要验证的集数（选择不同片尾时长的集）
episodes_to_verify = [
    1,   # 1.90秒
    2,   # 2.14秒
    5,   # 1.88秒
]

for ep_data in data['episodes']:
    episode = ep_data['episode']
    if episode not in episodes_to_verify:
        continue

    video_path = ep_data['video_path']
    total_duration = ep_data['total_duration']
    ending_duration = ep_data['ending_info']['duration']
    effective_duration = ep_data['effective_duration']

    print(f"\n" + "-" * 80)
    print(f"验证第{episode}集")
    print("-" * 80)
    print(f"视频路径: {video_path}")
    print(f"总时长: {total_duration:.2f}秒")
    print(f"检测到的片尾时长: {ending_duration:.2f}秒")
    print(f"片尾开始时间: {effective_duration:.2f}秒")

    # 创建该集的输出目录
    ep_output_dir = output_dir / f"第{episode}集"
    ep_output_dir.mkdir(parents=True, exist_ok=True)

    # 提取关键帧
    frames_to_extract = [
        ("片尾开始前1秒", effective_duration - 1.0),
        ("片尾开始时刻", effective_duration),
        ("片尾中间", effective_duration + ending_duration / 2),
        ("视频结束前0.5秒", total_duration - 0.5),
    ]

    print(f"\n提取关键帧:")
    for frame_name, timestamp in frames_to_extract:
        if timestamp < 0 or timestamp > total_duration:
            print(f"  ⚠️  跳过 '{frame_name}': 时间戳{timestamp:.2f}秒超出范围")
            continue

        output_file = ep_output_dir / f"{frame_name}_{timestamp:.2f}s.png"

        # 使用ffmpeg提取帧
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            str(output_file)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  ✅ '{frame_name}' ({timestamp:.2f}秒) -> {output_file}")
            else:
                print(f"  ❌ '{frame_name}' 提取失败: {result.stderr}")
        except Exception as e:
            print(f"  ❌ '{frame_name}' 提取异常: {e}")

    # 生成一个短视频片段（片尾部分）
    clip_output = ep_output_dir / f"片尾部分_{effective_duration:.2f}s-{total_duration:.2f}s.mp4"
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(effective_duration),
        '-i', video_path,
        '-t', str(ending_duration + 0.5),  # 多提取0.5秒
        '-c:v', 'libx264',
        '-c:a', 'aac',
        str(clip_output)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"\n  ✅ 片尾片段已保存: {clip_output}")
            print(f"     请播放此视频，检查:")
            print(f"     - 从{effective_duration:.2f}秒开始是否是慢动作片尾")
            print(f"     - 片尾时长约{ending_duration:.2f}秒是否准确")
        else:
            print(f"  ❌ 片尾片段提取失败: {result.stderr}")
    except Exception as e:
        print(f"  ❌ 片尾片段提取异常: {e}")

print("\n" + "=" * 80)
print("✅ 验证完成")
print("=" * 80)
print(f"\n所有输出文件保存在: {output_dir.absolute()}")
print("\n请查看:")
print("1. 关键帧图片 - 检查片尾开始时刻是否准确")
print("2. 片尾片段视频 - 播放查看片尾时长是否合理")
