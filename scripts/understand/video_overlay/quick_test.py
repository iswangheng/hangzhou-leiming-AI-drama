#!/usr/bin/env python3
"""
快速验证花字叠加模块是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试1：验证所有模块可以正常导入"""
    print("="*70)
    print("测试1：模块导入测试")
    print("="*70)

    try:
        print("导入 overlay_styles...", end=" ")
        from scripts.understand.video_overlay.overlay_styles import (
            get_all_styles,
            get_style,
            get_random_style,
            get_random_disclaimer
        )
        print("✅")

        print("导入 video_overlay...", end=" ")
        from scripts.understand.video_overlay.video_overlay import (
            VideoOverlayRenderer,
            OverlayConfig,
            apply_overlay_to_video
        )
        print("✅")

        print("\n✅ 所有模块导入成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_styles():
    """测试2：验证样式配置"""
    print("="*70)
    print("测试2：样式配置测试")
    print("="*70)

    try:
        from scripts.understand.video_overlay.overlay_styles import get_all_styles

        styles = get_all_styles()
        print(f"✅ 成功加载 {len(styles)} 种样式：\n")

        for style in styles[:3]:  # 只显示前3个
            print(f"  - {style.name} (ID: {style.id})")
            print(f"    描述: {style.description}")
            print(f"    热门短剧: {style.hot_drama.text}")
            print(f"    字体大小: {style.hot_drama.font_size}")
            print()

        if len(styles) > 3:
            print(f"  ... 还有 {len(styles) - 3} 种样式")

        print(f"\n✅ 样式配置验证成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ 样式配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_disclaimers():
    """测试3：验证免责声明"""
    print("="*70)
    print("测试3：免责声明测试")
    print("="*70)

    try:
        from scripts.understand.video_overlay.overlay_styles import (
            get_random_disclaimer,
            DISCLAIMER_TEXTS
        )

        print(f"免责声明库共有 {len(DISCLAIMER_TEXTS)} 条：\n")
        for i, text in enumerate(DISCLAIMER_TEXTS, 1):
            print(f"  {i}. {text}")

        print("\n随机选择测试：")
        for i in range(3):
            disclaimer = get_random_disclaimer()
            print(f"  {i+1}. {disclaimer}")

        print(f"\n✅ 免责声明验证成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ 免责声明测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试4：验证配置对象"""
    print("="*70)
    print("测试4：配置对象测试")
    print("="*70)

    try:
        from scripts.understand.video_overlay.video_overlay import OverlayConfig

        config = OverlayConfig(
            enabled=True,
            project_name="测试项目",
            drama_title="测试剧名"
        )

        print(f"✅ 成功创建配置对象")
        print(f"  - 启用: {config.enabled}")
        print(f"  - 项目名: {config.project_name}")
        print(f"  - 剧名: {config.drama_title}")
        print(f"  - 缓存目录: {config.cache_dir}")
        print(f"  - 字幕安全区: {config.subtitle_safe_zone}px")

        print(f"\n✅ 配置对象验证成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ 配置对象测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_renderer_creation():
    """测试5：验证渲染器创建"""
    print("="*70)
    print("测试5：渲染器创建测试")
    print("="*70)

    try:
        from scripts.understand.video_overlay.video_overlay import (
            VideoOverlayRenderer,
            OverlayConfig
        )

        config = OverlayConfig(
            enabled=True,
            project_name="测试项目",
            drama_title="测试剧名"
        )

        print("创建渲染器...", end=" ")
        renderer = VideoOverlayRenderer(config)
        print("✅")

        print(f"  - 样式: {renderer.style.name}")
        print(f"  - 热门短剧: {renderer.style.hot_drama.text}")
        print(f"  - 剧名: {renderer.style.drama_title.text}")
        print(f"  - 免责声明: {renderer.style.disclaimer.text}")

        print(f"\n✅ 渲染器创建成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ 渲染器创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ffmpeg_command():
    """测试6：验证FFmpeg命令生成"""
    print("="*70)
    print("测试6：FFmpeg命令生成测试")
    print("="*70)

    try:
        from scripts.understand.video_overlay.video_overlay import (
            VideoOverlayRenderer,
            OverlayConfig
        )

        config = OverlayConfig(
            enabled=True,
            project_name="测试项目",
            drama_title="测试剧名"
        )

        renderer = VideoOverlayRenderer(config)

        # 测试滤镜生成
        print("生成drawtext滤镜...", end=" ")
        filter1 = renderer._build_drawtext_filter(
            renderer.style.hot_drama,
            ""
        )
        print("✅")

        print(f"\n热门短剧滤镜预览：")
        print(f"  {filter1[:100]}...")

        print(f"\n✅ FFmpeg命令生成成功！\n")
        return True

    except Exception as e:
        print(f"\n❌ FFmpeg命令生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🎨 视频花字叠加模块 - 快速验证测试")
    print("="*70 + "\n")

    tests = [
        ("模块导入", test_imports),
        ("样式配置", test_styles),
        ("免责声明", test_disclaimers),
        ("配置对象", test_config),
        ("渲染器创建", test_renderer_creation),
        ("FFmpeg命令", test_ffmpeg_command),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 发生异常: {e}\n")
            results.append((name, False))

    # 显示测试总结
    print("="*70)
    print("测试总结")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！模块工作正常。")
        print("\n下一步：")
        print("  1. 准备测试视频文件")
        print("  2. 运行完整测试：python scripts/understand/video_overlay/test_overlay.py --help")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
