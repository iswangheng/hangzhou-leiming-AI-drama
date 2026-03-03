"""
测试脚本 - 自测视频理解流程的优化
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.understand.video_understand import video_understand


def test_video_understanding():
    """测试视频理解流程（使用百里将就项目）"""

    print("="*100)
    print("开始自测：视频理解V2（精确时间戳 + 质量筛选）")
    print("="*100)
    print()

    project_path = "./漫剧素材/百里将就"
    skill_file = "data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.1.md"

    # 检查路径
    if not os.path.exists(project_path):
        print(f"❌ 错误：项目路径不存在 - {project_path}")
        return False

    if not os.path.exists(skill_file):
        print(f"❌ 错误：技能文件不存在 - {skill_file}")
        return False

    try:
        # 运行视频理解
        result = video_understand(
            project_path=project_path,
            skill_file=skill_file,
            force_skill=False,
            output_dir="data/hangzhou-leiming/analysis/百里将就_v2"
        )

        print()
        print("="*100)
        print("✅ 测试成功！")
        print("="*100)
        print()
        print("结果统计：")
        print(f"  高光点: {result['statistics']['totalHighlights']} 个")
        print(f"  钩子点: {result['statistics']['totalHooks']} 个")
        print(f"  剪辑组合: {result['statistics']['totalClips']} 个")
        print(f"  平均置信度: {result['statistics']['averageConfidence']:.2f}")
        print()
        print("结果已保存到: data/hangzhou-leiming/analysis/百里将就_v2/result.json")
        print()

        # 显示一些示例
        print("高光点示例:")
        for i, hl in enumerate(result['highlights'][:5], 1):
            print(f"  {i}. 第{hl['episode']}集 {hl['timestamp']}秒 "
                  f"[{hl['type']}] 置信度:{hl['confidence']:.1f}")

        if len(result['highlights']) > 5:
            print(f"  ... 还有 {len(result['highlights'])-5} 个")

        print()
        print("钩子点示例:")
        for i, hook in enumerate(result['hooks'][:5], 1):
            print(f"  {i}. 第{hook['episode']}集 {hook['timestamp']}秒 "
                  f"[{hook['type']}] 置信度:{hook['confidence']:.1f}")

        if len(result['hooks']) > 5:
            print(f"  ... 还有 {len(result['hooks'])-5} 个")

        return True

    except Exception as e:
        print()
        print("="*100)
        print("❌ 测试失败！")
        print("="*100)
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """检查依赖项"""
    print("检查依赖项...")

    # 检查关键模块
    modules = [
        ("scripts.understand.video_understand", "视频理解主模块"),
        ("scripts.understand.analyze_segment", "片段分析模块"),
        ("scripts.understand.quality_filter", "质量筛选模块"),
        ("scripts.understand.generate_clips", "剪辑组合生成模块"),
    ]

    all_ok = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {description}")
        except ImportError as e:
            print(f"  ❌ {description} - {e}")
            all_ok = False

    return all_ok


if __name__ == "__main__":
    print()
    print("="*100)
    print("视频理解V2 - 自测脚本")
    print("="*100)
    print()

    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖项检查失败，请修复后重试")
        sys.exit(1)

    print("\n依赖项检查通过 ✅")
    print()

    # 运行测试
    success = test_video_understanding()

    sys.exit(0 if success else 1)
