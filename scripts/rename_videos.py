#!/usr/bin/env python3
"""
视频文件重命名工具 - 统一为纯数字格式
包含备份和回滚功能
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.filename_parser import parse_episode_number


def backup_videos(video_dir: str) -> str:
    """备份视频文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"{video_dir}_backup_{timestamp}"
    shutil.copytree(video_dir, backup_dir)
    print(f"💾 已备份到: {backup_dir}")
    return backup_dir


def rename_videos(video_dir: str, dry_run: bool = True) -> dict:
    """
    重命名视频文件为纯数字格式

    Args:
        video_dir: 视频目录
        dry_run: 是否为演习模式（只显示不执行）

    Returns:
        重命名记录
    """
    video_path = Path(video_dir)
    if not video_path.exists():
        print(f"⚠️  目录不存在: {video_dir}")
        return {}

    rename_map = {}
    skipped = 0
    errors = []

    # 获取所有mp4文件
    mp4_files = sorted(video_path.glob("*.mp4"))

    for mp4_file in mp4_files:
        # 解析集数
        episode = parse_episode_number(mp4_file.name)

        if episode is None:
            print(f"⚠️  跳过（无法解析）: {mp4_file.name}")
            errors.append(mp4_file.name)
            continue

        # 新文件名
        new_filename = f"{episode}.mp4"
        new_filepath = video_path / new_filename

        # 如果已经是目标格式，跳过
        if mp4_file.name == new_filename:
            skipped += 1
            continue

        # 检查目标文件是否已存在
        if new_filepath.exists():
            print(f"⚠️  跳过（目标已存在）: {mp4_file.name} → {new_filename}")
            errors.append(mp4_file.name)
            continue

        # 记录重命名
        rename_map[mp4_file.name] = new_filename

        if dry_run:
            print(f"📝 {mp4_file.name:30s} → {new_filename}")
        else:
            # 执行重命名
            mp4_file.rename(new_filepath)
            print(f"✅ {mp4_file.name:30s} → {new_filename}")

    # 汇总
    if not dry_run and rename_map:
        print(f"\n✅ 成功重命名 {len(rename_map)} 个文件")
    if skipped > 0:
        print(f"ℹ️  跳过 {skipped} 个已是标准格式的文件")
    if errors:
        print(f"⚠️  {len(errors)} 个文件处理失败")

    return {
        "renamed": rename_map,
        "skipped": skipped,
        "errors": errors,
        "total": len(mp4_files)
    }


def batch_rename(base_path: str, target_dir_name: str = "漫剧参考", dry_run: bool = True):
    """批量重命名目录"""
    base = Path(base_path)
    target_base = base / target_dir_name

    if not target_base.exists():
        print(f"⚠️  目标目录不存在: {target_base}")
        return

    print("=" * 80)
    print(f"模式: {'演习（不执行实际操作）' if dry_run else '正式执行'}")
    print(f"目标目录: {target_dir_name}/")
    print("=" * 80)
    print()

    all_rename_maps = []
    total_renamed = 0

    # 遍历所有子目录
    subdirs = sorted([d for d in target_base.iterdir() if d.is_dir()])

    if not subdirs:
        print("⚠️  没有找到子目录")
        return

    print(f"找到 {len(subdirs)} 个项目目录\n")

    for video_dir in subdirs:
        print(f"\n{'='*80}")
        print(f"📁 {video_dir.name}/")
        print("-" * 80)

        if not dry_run:
            # 备份
            print()
            backup_dir = backup_videos(str(video_dir))
            print()

        # 重命名
        result = rename_videos(str(video_dir), dry_run)
        all_rename_maps.append({
            "dir": video_dir.name,
            "result": result
        })

        if result.get("renamed"):
            total_renamed += len(result["renamed"])

    # 最终统计
    print("\n" + "=" * 80)
    print("统计信息")
    print("=" * 80)
    print(f"涉及项目: {len(subdirs)}")
    print(f"重命名文件: {total_renamed}")
    print()

    # 保存日志
    if not dry_run and all_rename_maps:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = base / f"rename_log_{timestamp}.txt"

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"视频文件重命名日志\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"模式: 正式执行\n")
            f.write("=" * 80 + "\n\n")

            for item in all_rename_maps:
                f.write(f"项目: {item['dir']}\n")
                f.write(f"重命名数量: {len(item['result'].get('renamed', {}))}\n")
                for old_name, new_name in item['result'].get('renamed', {}).items():
                    f.write(f"  {old_name} → {new_name}\n")
                f.write("\n")

        print(f"✅ 重命名日志已保存到: {log_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频文件重命名工具")
    parser.add_argument("--execute", action="store_true", help="正式执行（默认为演习模式）")
    parser.add_argument("--target", default="漫剧参考", help="目标目录名称")

    args = parser.parse_args()

    base_path = Path(__file__).parent.parent

    # 先运行演习模式
    print("第一步：演习模式\n")
    batch_rename(str(base_path), args.target, dry_run=True)

    # 如果指定了 --execute，询问确认
    if args.execute:
        print("\n" + "=" * 80)
        confirm = input("确认要执行重命名操作吗？(yes/no): ")

        if confirm.lower() == 'yes':
            print("\n第二步：正式执行\n")
            batch_rename(str(base_path), args.target, dry_run=False)
        else:
            print("已取消操作")
