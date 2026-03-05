#!/usr/bin/env python3
"""
生成去除片尾后的最后5秒验证视频
用于人工检查去除片尾后的剪辑效果是否自然
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
output_dir = Path("test/ending_verification_trimmed")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🎬 生成去除片尾后的验证视频")
print("=" * 80)
print(f"\n输出目录: {output_dir.absolute()}\n")

success_count = 0
fail_count = 0

for ep_data in data['episodes']:
    episode = ep_data['episode']
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

    # 使用ffmpeg提取（使用流复制，速度快）
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(extract_start),
        '-i', video_path,
        '-t', str(extract_duration),
        '-c:v', 'libx264',  # 使用libx264编码确保兼容性
        '-c:a', 'aac',
        '-preset', 'fast',
        str(output_file)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # 获取文件大小
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
print("\n请播放这些视频，检查:")
print("  1. 最后画面是否自然？")
print("  2. 有没有突然截断的感觉？")
print("  3. 有没有剪到一半对话就没了？")
print("  4. 结束点选择是否合理？")
print("  5. 观感是否流畅？")
