#!/usr/bin/env python3
"""
测试剪辑渲染功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render_clips import ClipRenderer, Clip


def test_single_clip():
    """测试单个剪辑渲染"""
    print("=" * 80)
    print("测试1: 渲染单个剪辑")
    print("=" * 80)

    project_path = "data/hangzhou-leiming/analysis/百里将就"
    video_dir = "漫剧素材/百里将就"  # 视频文件目录
    project_name = "百里将就"  # 项目名称
    output_dir = f"clips/{project_name}"  # 新的输出目录

    # 创建渲染器
    renderer = ClipRenderer(
        project_path=project_path,
        output_dir=output_dir,
        video_dir=video_dir,  # 指定视频目录
        project_name=project_name  # 传递项目名称
    )

    # 打印基本信息
    print(f"\n项目信息:")
    print(f"  项目路径: {renderer.project_path}")
    print(f"  输出目录: {renderer.output_dir}")
    print(f"  视频目录: {renderer.video_dir}")
    print(f"  集数: {len(renderer.episode_durations)}")
    print(f"  视频文件: {len(renderer.video_files)}")

    print(f"\n各集时长:")
    for ep, duration in sorted(renderer.episode_durations.items()):
        print(f"  第{ep}集: {duration}秒 ({duration/60:.1f}分钟)")

    print(f"\n可用视频文件:")
    for ep, vf in sorted(renderer.video_files.items()):
        print(f"  第{ep}集: {vf.path}")

    # 加载剪辑数据
    clips_data = renderer.result.get('clips', [])
    print(f"\n剪辑总数: {len(clips_data)}")

    # 选择第一个剪辑进行测试
    if clips_data:
        clip_data = clips_data[0]
        clip = Clip(**clip_data)

        print(f"\n测试剪辑:")
        print(f"  类型: {clip.clip_type}")
        print(f"  起始集: 第{clip.episode}集")
        print(f"  结束集: 第{clip.hookEpisode}集")
        print(f"  起始时间: {clip.start}秒 (累积)")
        print(f"  结束时间: {clip.end}秒 (累积)")
        print(f"  时长: {clip.duration}秒")
        print(f"  跨集: {'是' if clip.is_cross_episode else '否'}")

        # 转换为片段
        print(f"\n转换为视频片段:")
        segments = renderer._clip_to_segments(clip)
        for i, seg in enumerate(segments, 1):
            print(f"  片段{i}: 第{seg.episode}集 {seg.start}-{seg.end}秒")
            print(f"    文件: {seg.video_path}")

        # 渲染剪辑
        print(f"\n开始渲染...")
        output_path = renderer.render_clip(clip)
        print(f"\n✅ 渲染成功: {output_path}")

        # 检查输出文件
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"  文件大小: {size/1024/1024:.2f} MB")
        else:
            print(f"  ❌ 文件不存在!")


def test_all_clips():
    """测试渲染所有剪辑"""
    print("\n" + "=" * 80)
    print("测试2: 渲染所有剪辑")
    print("=" * 80)

    project_path = "data/hangzhou-leiming/analysis/百里将就"
    video_dir = "漫剧素材/百里将就"  # 视频文件目录
    project_name = "百里将就"  # 项目名称
    output_dir = f"clips/{project_name}"  # 新的输出目录

    # 创建渲染器
    renderer = ClipRenderer(
        project_path=project_path,
        output_dir=output_dir,
        video_dir=video_dir,  # 指定视频目录
        project_name=project_name  # 传递项目名称
    )

    # 渲染所有剪辑
    def on_progress(current, total, progress):
        percent = progress * 100
        print(f"\r进度: [{current}/{total}] {percent:.1f}%", end='', flush=True)

    output_paths = renderer.render_all_clips(on_clip_progress=on_progress)

    print(f"\n\n完成！输出文件:")
    for path in output_paths:
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  - {path} ({size:.2f} MB)")
        else:
            print(f"  - {path} (不存在!)")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        test_all_clips()
    else:
        test_single_clip()

        print("\n" + "=" * 80)
        print("提示: 使用 'python test_render.py --all' 渲染所有剪辑")
        print("=" * 80)


if __name__ == "__main__":
    main()
