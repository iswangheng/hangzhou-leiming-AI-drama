"""
训练进度监控脚本 - 实时查看训练和数据提取进度
"""
import os
import sys
from pathlib import Path

def check_extraction_progress():
    """检查数据提取进度"""
    print("=" * 80)
    print("📊 数据提取进度检查")
    print("=" * 80)
    print()

    # 检查所有项目的缓存目录
    cache_base = Path("data/hangzhou-leiming/cache")

    if not cache_base.exists():
        print("缓存目录尚未创建")
        return

    keyframe_cache = cache_base / "keyframes"
    asr_cache = cache_base / "asr"

    # 获取所有项目
    if keyframe_cache.exists():
        projects = sorted([d for d in keyframe_cache.iterdir() if d.is_dir()])

        total_episodes = 0
        total_keyframes = 0
        total_asr = 0

        print(f"{'项目':<40} {'关键帧':<10} {'ASR':<10}")
        print("-" * 80)

        for project_dir in projects:
            project_name = project_dir.name

            # 统计关键帧
            keyframe_episodes = len([d for d in project_dir.iterdir() if d.is_dir()])

            # 统计ASR
            asr_dir = asr_cache / project_name
            asr_episodes = len([f for f in asr_dir.iterdir() if f.is_file()]) if asr_cache.exists() else 0

            total_episodes += max(keyframe_episodes, asr_episodes)
            total_keyframes += keyframe_episodes
            total_asr += asr_episodes

            print(f"{project_name:<40} {keyframe_episodes:<10} {asr_episodes:<10}")

        print("-" * 80)
        print(f"{'合计':<40} {total_keyframes:<10} {total_asr:<10}")
        print()

        # 计算进度
        target_episodes = 117  # 14个项目的总集数
        progress = (total_keyframes / target_episodes) * 100

        print(f"数据提取进度: {total_keyframes}/{target_episodes}集 ({progress:.1f}%)")
        print()

        if progress >= 100:
            print("✅ 所有数据提取完成！")
        else:
            print(f"⏳ 还需要提取 {target_episodes - total_keyframes}集数据...")

    print()
    print("=" * 80)


if __name__ == "__main__":
    check_extraction_progress()
