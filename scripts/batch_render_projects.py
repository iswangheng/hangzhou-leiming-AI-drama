#!/usr/bin/env python3
"""
批量渲染多个项目（串行处理）- V16.2

使用方式:
    # 串行渲染多个项目（推荐）
    python -m scripts.batch_render_projects "项目1" "项目2" "项目3"

    # 带GPU加速
    python -m scripts.batch_render_projects "项目1" "项目2" --hwaccel

    # 带快速预设
    python -m scripts.batch_render_projects "项目1" "项目2" --fast-preset

    # 完整参数
    python -m scripts.batch_render_projects "项目1" "项目2" \
        --add-overlay --add-ending --parallel 4 --hwaccel --fast-preset

性能优化说明:
- 多项目串行处理（避免CPU竞争）
- 每个项目内部4个worker并行
- 可选GPU加速（macOS: videotoolbox）
- 可选快速预设（ultrafast）

作者: 杭州雷鸣AI短剧项目
版本: V16.2
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime


def render_single_project(
    project_name: str,
    analysis_dir: str = "data/analysis",
    video_base_dir: str = "260310-待剪辑-360 短剧素材",
    add_overlay: bool = True,
    add_ending: bool = True,
    parallel: int = 4,
    max_clips: int = 10,
    hwaccel: bool = False,
    fast_preset: bool = False
) -> dict:
    """渲染单个项目

    Args:
        project_name: 项目名称
        analysis_dir: 分析结果目录
        video_base_dir: 视频素材基础目录
        add_overlay: 是否添加花字
        add_ending: 是否添加结尾视频
        parallel: 并行worker数量
        max_clips: 最大剪辑数量
        hwaccel: 是否启用GPU加速
        fast_preset: 是否使用快速预设

    Returns:
        渲染结果字典
    """
    analysis_path = f"{analysis_dir}/{project_name}"
    video_path = f"{video_base_dir}/{project_name}"

    # 检查路径是否存在
    if not Path(analysis_path).exists():
        return {
            'project': project_name,
            'success': False,
            'error': f"分析结果不存在: {analysis_path}"
        }

    if not Path(video_path).exists():
        return {
            'project': project_name,
            'success': False,
            'error': f"视频素材不存在: {video_path}"
        }

    # 构建命令
    cmd = [
        'python', '-m', 'scripts.understand.render_clips',
        analysis_path,
        video_path,
        '--add-overlay' if add_overlay else '--no-overlay',
        '--add-ending' if add_ending else '--no-ending',
        '--parallel', str(parallel),
        '--max-clips', str(max_clips),
    ]

    if hwaccel:
        cmd.append('--hwaccel')

    if fast_preset:
        cmd.append('--fast-preset')

    start_time = time.time()

    try:
        # 运行渲染命令
        result = subprocess.run(cmd, capture_output=True, text=True)

        elapsed = time.time() - start_time

        if result.returncode == 0:
            return {
                'project': project_name,
                'success': True,
                'elapsed': elapsed,
                'output_dir': f"clips/{project_name}"
            }
        else:
            return {
                'project': project_name,
                'success': False,
                'error': result.stderr[-500:] if result.stderr else "未知错误",
                'elapsed': elapsed
            }

    except Exception as e:
        return {
            'project': project_name,
            'success': False,
            'error': str(e)
        }


def batch_render_projects(
    projects: list,
    add_overlay: bool = True,
    add_ending: bool = True,
    parallel: int = 4,
    max_clips: int = 10,
    hwaccel: bool = False,
    fast_preset: bool = False
) -> dict:
    """批量渲染多个项目（串行处理）

    Args:
        projects: 项目名称列表
        add_overlay: 是否添加花字
        add_ending: 是否添加结尾视频
        parallel: 并行worker数量
        max_clips: 最大剪辑数量
        hwaccel: 是否启用GPU加速
        fast_preset: 是否使用快速预设

    Returns:
        批量渲染结果
    """
    total_start = time.time()
    results = []

    print(f"\n{'='*60}")
    print(f"批量渲染 - V16.2 串行处理模式")
    print(f"{'='*60}")
    print(f"项目数量: {len(projects)}")
    print(f"每项目剪辑数: {max_clips}")
    print(f"并行worker: {parallel}")
    print(f"GPU加速: {'✅ 启用' if hwaccel else '❌ 禁用'}")
    print(f"快速预设: {'✅ ultrafast' if fast_preset else '❌ fast'}")
    print(f"{'='*60}\n")

    for i, project in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}] 开始渲染: {project}")
        print(f"{'='*40}")

        result = render_single_project(
            project_name=project,
            add_overlay=add_overlay,
            add_ending=add_ending,
            parallel=parallel,
            max_clips=max_clips,
            hwaccel=hwaccel,
            fast_preset=fast_preset
        )

        results.append(result)

        if result['success']:
            elapsed = result.get('elapsed', 0)
            print(f"\n✅ {project} 渲染完成")
            print(f"   耗时: {elapsed:.1f}秒")
            print(f"   输出: {result.get('output_dir', 'N/A')}")
        else:
            print(f"\n❌ {project} 渲染失败")
            print(f"   错误: {result.get('error', '未知错误')}")

    # 汇总统计
    total_elapsed = time.time() - total_start
    success_count = sum(1 for r in results if r['success'])

    print(f"\n\n{'='*60}")
    print(f"批量渲染完成")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{len(projects)}")
    print(f"总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")

    if success_count < len(projects):
        print(f"\n失败项目:")
        for r in results:
            if not r['success']:
                print(f"  - {r['project']}: {r.get('error', '未知错误')}")

    return {
        'total_projects': len(projects),
        'success_count': success_count,
        'total_elapsed': total_elapsed,
        'results': results
    }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='批量渲染多个项目（串行处理）- V16.2',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('projects', nargs='+', help='项目名称列表')
    parser.add_argument('--add-overlay', action='store_true', default=True,
                        help='添加花字叠加（默认启用）')
    parser.add_argument('--no-overlay', action='store_true',
                        help='禁用花字叠加')
    parser.add_argument('--add-ending', action='store_true', default=True,
                        help='添加结尾视频（默认启用）')
    parser.add_argument('--no-ending', action='store_true',
                        help='禁用结尾视频')
    parser.add_argument('--parallel', type=int, default=4,
                        help='每项目并行worker数量（默认4）')
    parser.add_argument('--max-clips', type=int, default=10,
                        help='每项目最大剪辑数量（默认10）')
    parser.add_argument('--hwaccel', action='store_true',
                        help='启用GPU硬件加速（macOS: videotoolbox）')
    parser.add_argument('--fast-preset', action='store_true',
                        help='使用ultrafast预设（速度提升30%%）')

    args = parser.parse_args()

    # 处理互斥参数
    add_overlay = not args.no_overlay
    add_ending = not args.no_ending

    # 执行批量渲染
    batch_render_projects(
        projects=args.projects,
        add_overlay=add_overlay,
        add_ending=add_ending,
        parallel=args.parallel,
        max_clips=args.max_clips,
        hwaccel=args.hwaccel,
        fast_preset=args.fast_preset
    )


if __name__ == "__main__":
    main()
