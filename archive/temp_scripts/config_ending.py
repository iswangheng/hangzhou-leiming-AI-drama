#!/usr/bin/env python3
"""
项目片尾配置工具

用于快速标记项目是否有片尾
"""
import sys
import json
from pathlib import Path
import argparse

sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from scripts.ending_credits_config import load_project_config, update_project_config


def config_project(project_path, has_ending, notes=""):
    """
    配置项目的片尾设置

    Args:
        project_path: 项目文件夹路径
        has_ending: 是否有片尾 (true/false)
        notes: 备注信息
    """
    project_path = Path(project_path)

    if not project_path.exists():
        print(f"❌ 错误：项目路径不存在: {project_path}")
        return False

    # 提取项目名称
    project_name = project_path.name

    # 检查是否有视频文件
    video_files = list(project_path.glob("*.mp4"))
    if not video_files:
        print(f"⚠️  警告：项目文件夹中没有找到mp4文件")

    # 准备配置
    config_updates = {
        "has_ending_credits": has_ending,
        "verified": True,  # 用户手动标记，视为已验证
        "notes": notes or ("用户手动标记：有片尾" if has_ending else "用户手动标记：无片尾")
    }

    # 更新配置
    try:
        update_project_config(project_name, config_updates)

        # 创建本地配置文件（可选，方便用户查看）
        local_config = project_path / "project_config.json"
        with open(local_config, 'w', encoding='utf-8') as f:
            json.dump({
                "has_ending_credits": has_ending,
                "notes": notes
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ 项目配置成功！")
        print(f"   项目: {project_name}")
        print(f"   片尾设置: {'有片尾' if has_ending else '无片尾'}")
        print(f"   本地配置文件: {local_config}")

        return True

    except Exception as e:
        print(f"❌ 配置失败: {e}")
        return False


def show_project_config(project_path):
    """显示项目的片尾配置"""
    project_path = Path(project_path)
    project_name = project_path.name

    config = load_project_config(project_name)

    print(f"\n{'='*60}")
    print(f"项目: {project_name}")
    print(f"{'='*60}")
    print(f"片尾设置: {'✅ 有片尾' if config.get('has_ending_credits') else '❌ 无片尾'}")
    print(f"已验证: {'✅' if config.get('verified') else '❌'}")
    print(f"备注: {config.get('notes', '无')}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="项目片尾配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 标记项目为无片尾
  python scripts/config_ending.py /path/to/project --no-ending "我的剧集没有片尾"

  # 标记项目为有片尾
  python scripts/config_ending.py /path/to/project --has-ending "有慢动作片尾"

  # 查看项目配置
  python scripts/config_ending.py /path/to/project --show
        """
    )

    parser.add_argument('project_path', help='项目文件夹路径')

    # 互斥选项
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--has-ending', action='store_true', help='标记为有片尾')
    group.add_argument('--no-ending', action='store_true', help='标记为无片尾')
    group.add_argument('--show', action='store_true', help='显示项目配置')

    parser.add_argument('--notes', default='', help='备注信息')

    args = parser.parse_args()

    # 显示配置
    if args.show:
        show_project_config(args.project_path)
        return

    # 配置项目
    if args.has_ending:
        config_project(args.project_path, True, args.notes)
    elif args.no_ending:
        config_project(args.project_path, False, args.notes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
