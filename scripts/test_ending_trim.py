#!/usr/bin/env python3
"""
V14.5 片尾剪裁测试脚本

单独测试片尾剪裁功能，不生成完整剪辑，只生成片尾片段。
"""

import sys
import json
import subprocess
from pathlib import Path


def test_ending_trim(project_name: str, video_dir: str, episode: int):
    """
    测试单集的片尾剪裁

    Args:
        project_name: 项目名称
        video_dir: 视频目录
        episode: 集数
    """
    print(f"\n{'=' * 70}")
    print(f"🎬 测试第{episode}集的片尾剪裁")
    print(f"{'=' * 70}\n")

    # 1. 加载片尾检测结果
    ending_cache_path = Path(f"data/hangzhou-leiming/ending_credits/{project_name}_ending_credits.json")

    if not ending_cache_path.exists():
        print(f"❌ 片尾缓存文件不存在: {ending_cache_path}")
        print("请先运行: python -m scripts.detect_ending_credits \"视频目录\"")
        return

    with open(ending_cache_path, 'r', encoding='utf-8') as f:
        ending_data = json.load(f)

    # 查找指定集
    episode_data = None
    for ep in ending_data['episodes']:
        if ep['episode'] == episode:
            episode_data = ep
            break

    if not episode_data:
        print(f"❌ 未找到第{episode}集的片尾数据")
        return

    # 2. 显示片尾检测信息
    total_duration = episode_data['total_duration']
    effective_duration = episode_data['effective_duration']
    ending_info = episode_data['ending_info']

    print(f"📊 片尾检测信息:")
    print(f"  总时长: {total_duration:.2f}秒 ({total_duration//60}分{total_duration%60:.0f}秒)")
    print(f"  有效时长: {effective_duration:.2f}秒 ({effective_duration//60}分{effective_duration%60:.0f}秒)")
    print(f"  剪掉时长: {total_duration - effective_duration:.2f}秒")
    print(f"  检测方法: {ending_info['method']}")
    print(f"  片尾时长: {ending_info['duration']:.2f}秒")
    print(f"  置信度: {ending_info['confidence']:.1%}")

    # 3. 找到视频文件
    video_path = Path(video_dir) / f"{episode}.mp4"
    if not video_path.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        return

    print(f"\n📹 视频文件: {video_path}")

    # 4. 测试剪裁：生成两个片段对比
    output_dir = Path("test_ending_trim") / project_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 片段1：完整视频的最后20秒（保留片尾）
    full_ending = output_dir / f"第{episode}集_完整片尾_最后20秒.mp4"
    start_time = max(0, total_duration - 20)

    print(f"\n🎬 生成对比片段...")
    print(f"\n片段1: 完整片尾（最后20秒）")
    print(f"  开始时间: {start_time:.2f}秒")

    cmd1 = [
        'ffmpeg',
        '-ss', f"{start_time:.3f}",
        '-i', str(video_path),
        '-t', '20.0',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y',
        str(full_ending)
    ]

    print(f"  命令: {' '.join(cmd1)}")
    result1 = subprocess.run(cmd1, capture_output=True, text=True)

    if result1.returncode == 0:
        print(f"  ✅ 生成成功: {full_ending}")
    else:
        print(f"  ❌ 生成失败: {result1.stderr}")
        return

    # 片段2：剪裁后的最后20秒（去除片尾）
    trim_ending = output_dir / f"第{episode}集_剪裁后_最后20秒.mp4"
    trim_start = max(0, effective_duration - 20)

    print(f"\n片段2: 剪裁后（最后20秒）")
    print(f"  开始时间: {trim_start:.2f}秒")
    print(f"  有效时长: {effective_duration:.2f}秒")

    cmd2 = [
        'ffmpeg',
        '-ss', f"{trim_start:.3f}",
        '-i', str(video_path),
        '-t', '20.0',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y',
        str(trim_ending)
    ]

    print(f"  命令: {' '.join(cmd2)}")
    result2 = subprocess.run(cmd2, capture_output=True, text=True)

    if result2.returncode == 0:
        print(f"  ✅ 生成成功: {trim_ending}")
    else:
        print(f"  ❌ 生成失败: {result2.stderr}")
        return

    # 5. 显示文件大小
    size1 = full_ending.stat().st_size / 1024 / 1024
    size2 = trim_ending.stat().st_size / 1024 / 1024

    print(f"\n📁 输出文件:")
    print(f"  完整片尾: {full_ending.name} ({size1:.1f}MB)")
    print(f"  剪裁后: {trim_ending.name} ({size2:.1f}MB)")

    # 6. 结论
    print(f"\n✅ 测试完成！")
    print(f"\n📝 对比说明:")
    print(f"  1. 播放「完整片尾」片段，看原始片尾内容")
    print(f"  2. 播放「剪裁后」片段，看去除片尾后的效果")
    print(f"  3. 对比两个片段，判断片尾剪裁是否正确")
    print(f"\n输出目录: {output_dir}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python scripts/test_ending_trim.py <项目名称> <视频目录> [集数]")
        print("\n示例:")
        print("  # 测试第1集")
        print("  python scripts/test_ending_trim.py \"多子多福，开局就送绝美老婆\" \"晓红姐-3.4剧目/多子多福，开局就送绝美老婆\" 1")
        print("\n  # 测试所有集")
        print("  python scripts/test_ending_trim.py \"多子多福，开局就送绝美老婆\" \"晓红姐-3.4剧目/多子多福，开局就送绝美老婆\"")
        sys.exit(1)

    project_name = sys.argv[1]
    video_dir = sys.argv[2]

    # 加载片尾数据
    ending_cache_path = Path(f"data/hangzhou-leiming/ending_credits/{project_name}_ending_credits.json")

    if not ending_cache_path.exists():
        print(f"❌ 片尾缓存不存在，请先运行片尾检测")
        sys.exit(1)

    with open(ending_cache_path, 'r', encoding='utf-8') as f:
        ending_data = json.load(f)

    # 如果指定了集数，只测试该集
    if len(sys.argv) >= 4:
        episode = int(sys.argv[3])
        test_ending_trim(project_name, video_dir, episode)
    else:
        # 测试所有集
        print(f"\n{'=' * 70}")
        print(f"🎬 测试所有集的片尾剪裁")
        print(f"{'=' * 70}\n")

        for ep in ending_data['episodes']:
            episode_num = ep['episode']
            print(f"\n--- 第{episode_num}集 ---")

            # 只测试有片尾的集
            if ep['ending_info']['has_ending']:
                test_ending_trim(project_name, video_dir, episode_num)
            else:
                print(f"第{episode_num}集: 无片尾")


if __name__ == "__main__":
    main()
