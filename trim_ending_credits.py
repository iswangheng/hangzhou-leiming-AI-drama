#!/usr/bin/env python3
"""
剪掉片尾视频 - 使用检测结果去除每集的片尾
"""
import sys
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

import json
import subprocess
from pathlib import Path
from typing import Dict, List

print("=" * 70)
print("✂️  剪掉片尾视频")
print("=" * 70)

# 配置
project_name = "多子多福，开局就送绝美老婆"
json_file = Path(f"data/hangzhou-leiming/ending_credits/{project_name}_ending_credits.json")
source_dir = Path("/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆")
output_dir = Path("clips/多子多福，开局就送绝美老婆_去除片尾")

print(f"\n📁 项目名称: {project_name}")
print(f"📄 检测结果: {json_file}")
print(f"🎬 源视频目录: {source_dir}")
print(f"📤 输出目录: {output_dir}\n")

# 读取检测结果
if not json_file.exists():
    print(f"❌ 错误：未找到检测结果文件: {json_file}")
    sys.exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    detection_data = json.load(f)

# 创建输出目录
output_dir.mkdir(parents=True, exist_ok=True)

# 处理每一集
episodes = detection_data['episodes']
total = len(episodes)

print(f"准备处理 {total} 个视频文件\n")

success_count = 0
failed_episodes = []

for idx, ep_data in enumerate(episodes, 1):
    episode = ep_data['episode']
    total_duration = ep_data['total_duration']
    ending_duration = ep_data['ending_info']['duration']
    effective_duration = ep_data['effective_duration']
    
    # 源文件和目标文件
    source_file = source_dir / f"{episode}.mp4"
    output_file = output_dir / f"{episode}.mp4"
    
    print(f"\n[{idx}/{total}] 处理第{episode}集")
    print(f"  源文件: {source_file.name}")
    print(f"  原始时长: {total_duration:.2f}秒")
    print(f"  片尾时长: {ending_duration:.2f}秒")
    print(f"  保留时长: {effective_duration:.2f}秒")
    
    # 检查源文件是否存在
    if not source_file.exists():
        print(f"  ❌ 源文件不存在: {source_file}")
        failed_episodes.append(episode)
        continue
    
    # 使用 ffmpeg 裁剪视频
    # -t 参数指定裁剪后的时长
    try:
        cmd = [
            'ffmpeg',
            '-i', str(source_file),
            '-t', str(effective_duration),
            '-c', 'copy',  # 直接复制流，不重新编码（速度快）
            '-y',  # 覆盖输出文件
            str(output_file)
        ]
        
        print(f"  执行命令: ffmpeg -i \"{source_file.name}\" -t {effective_duration:.2f} -c copy")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            # 验证输出文件
            if output_file.exists():
                output_size = output_file.stat().st_size / (1024 * 1024)  # MB
                print(f"  ✅ 成功！输出文件: {output_file.name} ({output_size:.1f} MB)")
                success_count += 1
            else:
                print(f"  ❌ 输出文件未生成")
                failed_episodes.append(episode)
        else:
            print(f"  ❌ ffmpeg 处理失败")
            print(f"  错误信息: {result.stderr[:200]}")
            failed_episodes.append(episode)
            
    except Exception as e:
        print(f"  ❌ 处理出错: {e}")
        failed_episodes.append(episode)

# 输出汇总
print("\n" + "=" * 70)
print("📊 处理结果汇总")
print("=" * 70)

print(f"\n总数: {total}")
print(f"成功: {success_count}")
print(f"失败: {len(failed_episodes)}")

if failed_episodes:
    print(f"\n失败的集数: {', '.join(map(str, failed_episodes))}")

print(f"\n所有视频已保存到: {output_dir}")
print("=" * 70)

if success_count == total:
    print("\n✅ 全部完成！")
    sys.exit(0)
else:
    print(f"\n⚠️  部分失败 ({len(failed_episodes)}/{total})")
    sys.exit(1)
