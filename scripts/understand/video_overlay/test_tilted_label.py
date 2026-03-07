"""
45度倾斜角标模块测试脚本（V2.0）

测试优化后的倾斜角标效果：
- 半透明背景（80%不透明度）
- 角落留白（视频最边角露出原画面）
- 精致条幅（高度60px）
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)

from scripts.understand.video_overlay.tilted_label import (
    TiltedLabelRenderer,
    TiltedLabelConfig,
    add_tilted_label
)


def test_top_right_label():
    """测试右上角倾斜角标（新模板）"""
    print("\n" + "="*60)
    print("测试1: 右上角45度倾斜角标（V2.0 - 半透明+留白）")
    print("="*60)

    input_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红-人工剪辑的用于参考的好视频素材/多子多福，开局就送绝美老婆 (1).mp4"
    output_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/test/多子多福_右上角_半透明.mp4"

    # 使用默认配置（新模板参数）
    config = TiltedLabelConfig(
        label_text="热门短剧",
        position="top-right"
    )

    renderer = TiltedLabelRenderer(config)
    result = renderer.apply_label(input_video, output_video)

    print(f"\n✅ 测试完成: {result}")
    return result


def test_top_left_label():
    """测试左上角倾斜角标（新模板）"""
    print("\n" + "="*60)
    print("测试2: 左上角45度倾斜角标（V2.0 - 半透明+留白）")
    print("="*60)

    input_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红-人工剪辑的用于参考的好视频素材/多子多福，开局就送绝美老婆 (2).mp4"
    output_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/test/多子多福_左上角_半透明.mp4"

    # 使用默认配置
    config = TiltedLabelConfig(
        label_text="热门短剧",
        label_color="orange@0.8",  # 橙色半透明
        position="top-left"
    )

    renderer = TiltedLabelRenderer(config)
    result = renderer.apply_label(input_video, output_video)

    print(f"\n✅ 测试完成: {result}")
    return result


def test_gold_style():
    """测试金色样式"""
    print("\n" + "="*60)
    print("测试3: 金色样式（爆款推荐）")
    print("="*60)

    input_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红-人工剪辑的用于参考的好视频素材/多子多福，开局就送绝美老婆 (1).mp4"
    output_video = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/test/多子多福_金色爆款.mp4"

    # 使用便捷函数
    result = add_tilted_label(
        input_video=input_video,
        output_video=output_video,
        label_text="爆款推荐",
        position="top-right",
        label_color="gold@0.8",
        text_color="black"
    )

    print(f"\n✅ 测试完成: {result}")
    return result


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("45度倾斜角标模块测试（V2.0）")
    print("特点：半透明 + 角落留白 + 精致条幅")
    print("="*60)

    # 确保测试目录存在
    test_dir = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/test"
    os.makedirs(test_dir, exist_ok=True)

    # 运行测试
    try:
        # 测试1: 右上角
        test_top_right_label()

        # 测试2: 左上角
        test_top_left_label()

        # 测试3: 金色样式
        test_gold_style()

        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
