#!/usr/bin/env python3
"""
生成"不晚忘忧"项目的验证视频（去除片尾后的最后5秒）
"""
import sys
import json
import subprocess
from pathlib import Path

# 读取检测结果
result_file = Path("data/hangzhou-leiming/ending_credits/不晚忘忧_ending_credits.json")
with open(result_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建输出目录
output_dir = Path("test/buwang_you_verification")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🎬 生成不晚忘忧项目的验证视频")
print("=" * 80)
print(f"\n输出目录: {output_dir.absolute()}\n")

# 选择几集来验证（选择片尾时长不同的集）
episodes_to_verify = [1, 3, 6, 10]  # 代表不同片尾时长

success_count = 0
fail_count = 0

for ep_data in data['episodes']:
    episode = ep_data['episode']
    if episode not in episodes_to_verify:
        continue

    video_path = ep_data['video_path']
    total_duration = ep_data['total_duration']
    ending_duration = ep_data['ending_info']['duration']
    effective_duration = ep_data['effective_duration']

    # 计算提取范围：有效时长的最后5秒
    extract_start = max(0, effective_duration - 5)
    extract_end = effective_duration
    extract_duration = extract_end - extract_start

    print("-" * 80)
    print(f"处理第{episode}集")
    print("-" * 80)
    print(f"  原视频总时长: {total_duration:.2f}秒")
    print(f"  片尾时长: {ending_duration:.2f}秒")
    print(f"  有效时长: {effective_duration:.2f}秒")
    print(f"  提取范围: {extract_start:.2f}秒 → {extract_end:.2f}秒 (共{extract_duration:.2f}秒)")

    # 输出文件名
    output_file = output_dir / f"第{episode}集_去除片尾后最后5秒.mp4"

    # 使用ffmpeg提取
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(extract_start),
        '-i', video_path,
        '-t', str(extract_duration),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        str(output_file)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            file_size = output_file.stat().st_size / 1024  # KB
            print(f"  ✅ 成功: {output_file.name} ({file_size:.1f}KB)")
            success_count += 1
        else:
            print(f"  ❌ 失败: {result.stderr}")
            fail_count += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        fail_count += 1

print("\n" + "=" * 80)
print("✅ 处理完成")
print("=" * 80)
print(f"\n成功: {success_count}个")
print(f"失败: {fail_count}个")
print(f"\n所有视频保存在: {output_dir.absolute()}")
