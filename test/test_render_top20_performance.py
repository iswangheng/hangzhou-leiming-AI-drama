#!/usr/bin/env python3
"""
渲染 Top 20 剪辑性能测试

目的：测试渲染一个短剧的 Top 20 个剪辑组合素材需要多久

测试方案：
1. 选择一个有分析结果的项目
2. 使用 --max-clips 20 参数渲染
3. 记录总耗时、每个剪辑平均耗时等性能数据

使用方式：
    python test/test_render_top20_performance.py "项目名"

    # 例如：
    python test/test_render_top20_performance.py "我是外星人"

作者: 杭州雷鸣AI短剧项目
日期: 2026-03-13
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_render_top20_performance(
    project_name: str,
    analysis_dir: str = "data/analysis",
    video_base_dir: str = "漫剧素材",
    add_overlay: bool = True,
    add_ending: bool = True,
    parallel: int = 4
) -> dict:
    """测试渲染 Top 20 剪辑的性能

    Args:
        project_name: 项目名称
        analysis_dir: 分析结果目录
        video_base_dir: 视频素材基础目录
        add_overlay: 是否添加花字
        add_ending: 是否添加结尾视频
        parallel: 并行worker数量

    Returns:
        性能测试结果
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

    # 检查分析结果文件
    result_file = Path(analysis_path) / "result.json"
    if not result_file.exists():
        return {
            'project': project_name,
            'success': False,
            'error': f"分析结果文件不存在: {result_file}"
        }

    print(f"\n{'='*70}")
    print(f"🎬 渲染 Top 20 剪辑性能测试")
    print(f"{'='*70}")
    print(f"项目名称: {project_name}")
    print(f"分析结果: {analysis_path}")
    print(f"视频素材: {video_path}")
    print(f"并行Worker: {parallel}")
    print(f"花字叠加: {'✅ 启用' if add_overlay else '❌ 禁用'}")
    print(f"结尾视频: {'✅ 启用' if add_ending else '❌ 禁用'}")
    print(f"{'='*70}\n")

    # 构建渲染命令
    cmd = [
        'python3', '-m', 'scripts.understand.render_clips',
        analysis_path,
        video_path,
        '--max-clips', '20',  # 只渲染 Top 20
        '--parallel', str(parallel),
    ]

    if add_overlay:
        cmd.append('--add-overlay')
    else:
        cmd.append('--no-overlay')

    if add_ending:
        cmd.append('--add-ending')
    else:
        cmd.append('--no-ending')

    print(f"执行命令:")
    print(f"  {' '.join(cmd)}")
    print(f"\n开始渲染...\n")

    start_time = time.time()
    start_datetime = datetime.now()

    try:
        # 运行渲染命令（实时输出）
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=False  # 实时输出到控制台
        )

        end_time = time.time()
        end_datetime = datetime.now()
        elapsed = end_time - start_time

        if result.returncode == 0:
            # 计算性能指标
            avg_time_per_clip = elapsed / 20

            print(f"\n\n{'='*70}")
            print(f"✅ 渲染完成！")
            print(f"{'='*70}")
            print(f"开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"总耗时: {elapsed:.1f} 秒 ({elapsed/60:.2f} 分钟)")
            print(f"渲染数量: 20 个剪辑")
            print(f"平均耗时: {avg_time_per_clip:.1f} 秒/剪辑")
            print(f"输出目录: clips/{project_name}")
            print(f"{'='*70}\n")

            return {
                'project': project_name,
                'success': True,
                'start_time': start_datetime.isoformat(),
                'end_time': end_datetime.isoformat(),
                'elapsed': elapsed,
                'elapsed_minutes': elapsed / 60,
                'clips_count': 20,
                'avg_time_per_clip': avg_time_per_clip,
                'output_dir': f"clips/{project_name}"
            }
        else:
            print(f"\n❌ 渲染失败")
            print(f"返回码: {result.returncode}")
            return {
                'project': project_name,
                'success': False,
                'error': f"渲染命令返回错误码: {result.returncode}",
                'elapsed': elapsed
            }

    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n❌ 渲染异常: {str(e)}")
        return {
            'project': project_name,
            'success': False,
            'error': str(e),
            'elapsed': elapsed
        }


def main():
    """主测试函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='渲染 Top 20 剪辑性能测试',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('project', help='项目名称')
    parser.add_argument('--analysis-dir', default='data/analysis',
                        help='分析结果目录（默认: data/analysis）')
    parser.add_argument('--video-base-dir', default='漫剧素材',
                        help='视频素材基础目录（默认: 漫剧素材）')
    parser.add_argument('--no-overlay', action='store_true',
                        help='禁用花字叠加')
    parser.add_argument('--no-ending', action='store_true',
                        help='禁用结尾视频')
    parser.add_argument('--parallel', type=int, default=4,
                        help='并行worker数量（默认: 4）')

    args = parser.parse_args()

    # 执行性能测试
    result = test_render_top20_performance(
        project_name=args.project,
        analysis_dir=args.analysis_dir,
        video_base_dir=args.video_base_dir,
        add_overlay=not args.no_overlay,
        add_ending=not args.no_ending,
        parallel=args.parallel
    )

    # 返回结果
    if result['success']:
        print(f"\n📊 性能测试结果:")
        print(f"  总耗时: {result['elapsed']:.1f}秒 ({result['elapsed_minutes']:.2f}分钟)")
        print(f"  平均耗时: {result['avg_time_per_clip']:.1f}秒/剪辑")
        sys.exit(0)
    else:
        print(f"\n❌ 性能测试失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
