#!/usr/bin/env python3
"""
视频花字叠加使用示例

演示如何在不同场景下使用花字叠加功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.understand.video_overlay.video_overlay import (
    apply_overlay_to_video,
    batch_apply_overlay
)
from scripts.understand.video_overlay.overlay_styles import (
    get_all_styles,
    get_random_style
)


def example_1_single_video():
    """示例1：单个视频叠加（随机样式）"""
    print("\n" + "="*70)
    print("示例1：单个视频叠加（随机样式）")
    print("="*70)

    input_video = "test_input.mp4"
    output_video = "test_output.mp4"
    project_name = "多子多福，开局就送绝美老婆"
    drama_title = "多子多福"

    print(f"输入视频: {input_video}")
    print(f"输出视频: {output_video}")
    print(f"项目名称: {project_name}")
    print(f"剧名: {drama_title}")
    print("\n提示：系统将自动为该项目选择一个样式并缓存")
    print("同一项目的后续视频将使用相同样式\n")

    try:
        result = apply_overlay_to_video(
            input_video=input_video,
            output_video=output_video,
            project_name=project_name,
            drama_title=drama_title
        )
        print(f"✅ 成功！输出文件: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")


def example_2_specified_style():
    """示例2：指定样式"""
    print("\n" + "="*70)
    print("示例2：指定样式（金色豪华）")
    print("="*70)

    input_video = "test_input.mp4"
    output_video = "test_output_gold.mp4"

    print(f"输入视频: {input_video}")
    print(f"输出视频: {output_video}")
    print(f"样式: gold_luxury（金色豪华）\n")

    try:
        result = apply_overlay_to_video(
            input_video=input_video,
            output_video=output_video,
            project_name="测试项目",
            drama_title="测试剧名",
            style_id="gold_luxury"  # 指定样式
        )
        print(f"✅ 成功！输出文件: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")


def example_3_batch_processing():
    """示例3：批量处理"""
    print("\n" + "="*70)
    print("示例3：批量处理整个项目")
    print("="*70)

    input_dir = "./clips/多子多福，开局就送绝美老婆"
    output_dir = "./clips/多子多福，开局就送绝美老婆_带花字"
    project_name = "多子多福，开局就送绝美老婆"
    drama_title = "多子多福"

    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print(f"项目名称: {project_name}")
    print(f"剧名: {drama_title}")
    print("\n提示：所有视频将使用同一样式（项目级统一）\n")

    # 检查输入目录是否存在
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"⚠️  输入目录不存在: {input_dir}")
        print("请先运行渲染流程生成剪辑视频")
        return

    try:
        output_paths = batch_apply_overlay(
            input_videos=[str(f) for f in input_path.glob("*.mp4")],
            output_dir=output_dir,
            project_name=project_name,
            drama_title=drama_title
        )
        print(f"\n✅ 成功处理 {len(output_paths)} 个视频")
        print(f"📁 输出目录: {output_dir}")
    except Exception as e:
        print(f"❌ 失败: {e}")


def example_4_list_all_styles():
    """示例4：列出所有样式"""
    print("\n" + "="*70)
    print("示例4：列出所有可用样式")
    print("="*70 + "\n")

    styles = get_all_styles()
    print(f"共有 {len(styles)} 种预制样式：\n")

    for i, style in enumerate(styles, 1):
        print(f"{i}. {style.name}")
        print(f"   ID: {style.id}")
        print(f"   描述: {style.description}")
        print(f"   热门短剧: {style.hot_drama.text}")
        print(f"   免责声明: {style.disclaimer.text}")
        print()


def example_5_integration_with_render():
    """示例5：集成到渲染流程"""
    print("\n" + "="*70)
    print("示例5：集成到渲染流程（推荐方式）")
    print("="*70 + "\n")

    print("方法一：命令行")
    print("-" * 70)
    print("""
# 基础渲染（随机样式）
python -m scripts.understand.render_clips \\
  data/hangzhou-leiming/analysis/多子多福，开局就送绝美老婆 \\
  --add-overlay

# 指定样式
python -m scripts.understand.render_clips \\
  data/hangzhou-leiming/analysis/多子多福，开局就送绝美老婆 \\
  --add-overlay \\
  --overlay-style gold_luxury

# 完整功能（片尾检测 + 结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \\
  data/hangzhou-leiming/analysis/多子多福，开局就送绝美老婆 \\
  --add-ending \\
  --add-overlay
    """)

    print("\n方法二：Python API")
    print("-" * 70)
    print("""
from scripts.understand.render_clips import ClipRenderer

renderer = ClipRenderer(
    project_path="data/hangzhou-leiming/analysis/项目名",
    output_dir="clips/项目名",
    add_overlay=True,              # 启用花字叠加
    overlay_style_id="gold_luxury" # 可选：指定样式
)

output_paths = renderer.render_all_clips()
    """)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='视频花字叠加使用示例',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 示例1：单个视频（随机样式）
  python overlay_example.py --example 1

  # 示例2：指定样式
  python overlay_example.py --example 2

  # 示例3：批量处理
  python overlay_example.py --example 3

  # 示例4：列出所有样式
  python overlay_example.py --example 4

  # 示例5：集成说明
  python overlay_example.py --example 5

  # 运行所有示例
  python overlay_example.py --all
        '''
    )

    parser.add_argument('--example', type=int, choices=[1, 2, 3, 4, 5],
                       help='运行指定示例（1-5）')
    parser.add_argument('--all', action='store_true',
                       help='运行所有示例')

    args = parser.parse_args()

    # 运行示例
    if args.all:
        example_4_list_all_styles()
        example_5_integration_with_render()
        print("\n" + "="*70)
        print("提示：示例1-3需要实际的视频文件才能运行")
        print("请准备好测试视频后单独运行这些示例")
        print("="*70)
    elif args.example:
        if args.example == 1:
            example_1_single_video()
        elif args.example == 2:
            example_2_specified_style()
        elif args.example == 3:
            example_3_batch_processing()
        elif args.example == 4:
            example_4_list_all_styles()
        elif args.example == 5:
            example_5_integration_with_render()
    else:
        # 默认显示集成说明
        example_5_integration_with_render()
        print("\n" + "="*70)
        print("提示：使用 --example 1-5 查看具体示例")
        print("使用 --all 查看所有示例")
        print("="*70)


if __name__ == "__main__":
    main()
