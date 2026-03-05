#!/usr/bin/env python3
"""
测试视频花字叠加功能

用于测试和展示花字叠加效果
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.understand.video_overlay.video_overlay import (
    apply_overlay_to_video,
    batch_apply_overlay,
    OverlayConfig,
    VideoOverlayRenderer
)
from scripts.understand.video_overlay.overlay_styles import (
    get_all_styles,
    get_random_style,
    get_random_disclaimer
)


def test_list_styles():
    """测试：列出所有可用样式"""
    print("="*70)
    print("📋 可用花字样式列表")
    print("="*70)

    styles = get_all_styles()
    for i, style in enumerate(styles, 1):
        print(f"\n{i}. {style.name} (ID: {style.id})")
        print(f"   描述: {style.description}")

    print(f"\n共 {len(styles)} 种样式")


def test_random_disclaimers():
    """测试：随机免责声明"""
    print("\n" + "="*70)
    print("📜 随机免责声明示例")
    print("="*70)

    for i in range(5):
        disclaimer = get_random_disclaimer()
        print(f"{i+1}. {disclaimer}")


def test_single_video(
    input_video: str,
    output_video: str,
    project_name: str,
    drama_title: str = "",
    style_id: str = None
):
    """测试：单个视频花字叠加"""
    print("\n" + "="*70)
    print("🎬 单个视频花字叠加测试")
    print("="*70)

    try:
        result = apply_overlay_to_video(
            input_video=input_video,
            output_video=output_video,
            project_name=project_name,
            drama_title=drama_title or project_name,
            style_id=style_id
        )

        print(f"\n✅ 测试成功！")
        print(f"📁 输出文件: {result}")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_overlay(
    input_dir: str,
    output_dir: str,
    project_name: str,
    drama_title: str = "",
    style_id: str = None
):
    """测试：批量花字叠加"""
    print("\n" + "="*70)
    print("🎬 批量花字叠加测试")
    print("="*70)

    # 查找所有视频文件
    input_path = Path(input_dir)
    video_files = list(input_path.glob("*.mp4"))

    if not video_files:
        print(f"❌ 错误: 在 {input_dir} 中未找到MP4视频文件")
        return False

    print(f"\n找到 {len(video_files)} 个视频文件")
    for i, video in enumerate(video_files, 1):
        print(f"  {i}. {video.name}")

    try:
        output_paths = batch_apply_overlay(
            input_videos=[str(v) for v in video_files],
            output_dir=output_dir,
            project_name=project_name,
            drama_title=drama_title or project_name,
            style_id=style_id
        )

        print(f"\n✅ 批量处理成功！")
        print(f"📊 成功: {len(output_paths)}/{len(video_files)} 个视频")
        print(f"📁 输出目录: {output_dir}")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='测试视频花字叠加功能',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 列出所有可用样式
  python test_overlay.py --list-styles

  # 显示随机免责声明
  python test_overlay.py --disclaimers

  # 单个视频叠加（自动选择样式）
  python test_overlay.py --single input.mp4 output.mp4 "项目名称" "剧名"

  # 单个视频叠加（指定样式）
  python test_overlay.py --single input.mp4 output.mp4 "项目名称" "剧名" --style gold_luxury

  # 批量叠加
  python test_overlay.py --batch ./input_dir ./output_dir "项目名称" "剧名"
        '''
    )

    parser.add_argument('--list-styles', action='store_true', help='列出所有可用样式')
    parser.add_argument('--disclaimers', action='store_true', help='显示随机免责声明')
    parser.add_argument('--single', nargs=4, metavar=('INPUT', 'OUTPUT', 'PROJECT', 'TITLE'),
                       help='单个视频叠加')
    parser.add_argument('--batch', nargs=4, metavar=('INPUT_DIR', 'OUTPUT_DIR', 'PROJECT', 'TITLE'),
                       help='批量叠加')
    parser.add_argument('--style', type=str, help='指定样式ID')

    args = parser.parse_args()

    # 执行相应的测试
    if args.list_styles:
        test_list_styles()
    elif args.disclaimers:
        test_random_disclaimers()
    elif args.single:
        input_video, output_video, project_name, drama_title = args.single
        test_single_video(
            input_video=input_video,
            output_video=output_video,
            project_name=project_name,
            drama_title=drama_title,
            style_id=args.style
        )
    elif args.batch:
        input_dir, output_dir, project_name, drama_title = args.batch
        test_batch_overlay(
            input_dir=input_dir,
            output_dir=output_dir,
            project_name=project_name,
            drama_title=drama_title,
            style_id=args.style
        )
    else:
        # 默认：显示基本信息
        print("🎨 视频花字叠加模块\n")
        print("请使用以下选项进行测试：")
        print("  --list-styles     列出所有可用样式")
        print("  --disclaimers     显示免责声明列表")
        print("  --single          单个视频叠加测试")
        print("  --batch           批量视频叠加测试")
        print("\n使用 --help 查看详细帮助信息")


if __name__ == "__main__":
    main()
