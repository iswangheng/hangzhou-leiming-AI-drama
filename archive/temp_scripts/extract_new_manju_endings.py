#!/usr/bin/env python3
"""
提取"新的漫剧素材"4个项目的片尾片段供人工检查
"""
import sys
import json
import subprocess
from pathlib import Path

# "新的漫剧素材"的4个项目
projects = [
    "雪烬梨香",
    "休书落纸",
    "不晚忘忧",
    "恋爱综艺，匹配到心动男友",
]

# 创建输出目录
output_dir = Path("test/new_manju_ending_clips")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 100)
print("🎬 提取新的漫剧素材项目的片尾片段")
print("=" * 100)
print(f"\n输出目录: {output_dir.absolute()}\n")

success_count = 0
fail_count = 0

for project_name in projects:
    # 读取检测结果
    result_file = Path(f"data/hangzhou-leiming/ending_credits/{project_name}_ending_credits.json")

    if not result_file.exists():
        print(f"⚠️  {project_name} - 检测结果文件不存在，跳过")
        continue

    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n{'=' * 100}")
    print(f"处理项目: {project_name}")
    print(f"{'=' * 100}")

    # 创建该项目的输出目录
    project_output_dir = output_dir / project_name
    project_output_dir.mkdir(parents=True, exist_ok=True)

    for ep in data['episodes']:
        episode = ep['episode']
        video_path = ep['video_path']
        total_duration = ep['total_duration']
        ending_duration = ep['ending_info']['duration']
        effective_duration = ep['effective_duration']

        # 如果没有片尾，跳过
        if ending_duration == 0 or not ep['ending_info']['has_ending']:
            print(f"  第{episode}集: 无片尾，跳过")
            continue

        # 计算片尾的开始和结束时间
        ending_start = effective_duration
        ending_end = total_duration

        print(f"  第{episode}集: 片尾 {ending_duration:.2f}秒 ({ending_start:.2f}s → {ending_end:.2f}s)")

        # 输出文件名
        output_file = project_output_dir / f"第{episode}集_片尾_{ending_duration:.2f}秒.mp4"

        # 使用ffmpeg提取片尾片段
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(ending_start),
            '-i', video_path,
            '-t', str(ending_duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            str(output_file)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                file_size = output_file.stat().st_size / 1024  # KB
                print(f"    ✅ 成功: {output_file.name} ({file_size:.1f}KB)")
                success_count += 1
            else:
                print(f"    ❌ 失败: {result.stderr}")
                fail_count += 1
        except Exception as e:
            print(f"    ❌ 异常: {e}")
            fail_count += 1

print(f"\n{'=' * 100}")
print("✅ 处理完成")
print(f"{'=' * 100}")
print(f"\n成功: {success_count}个")
print(f"失败: {fail_count}个")
print(f"\n所有片尾片段保存在: {output_dir.absolute()}")
print("\n请播放这些片尾片段，检查:")
print("  1. 这些片段是否真的是需要剪掉的片尾？")
print("  2. 还是正常剧情内容被误判为片尾？")
print("  3. 如果是正常内容，说明该项目的片尾特征与训练数据不同")
