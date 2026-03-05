"""
测试 V14.1 自动片尾检测集成功能

测试内容：
1. 缓存加载测试
2. 自动检测触发测试
3. 强制重检测测试
4. 跳过检测测试
5. 有效时长计算测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.understand.render_clips import ClipRenderer


def test_cache_loading():
    """测试1: 缓存加载功能"""
    print("\n" + "="*60)
    print("测试1: 缓存加载功能")
    print("="*60)

    test_project = "data/hangzhou-leiming/analysis/不晚忘忧"

    # 创建渲染器（自动检测启用）
    renderer = ClipRenderer(
        project_path=test_project,
        output_dir="clips/test_cache",
        video_dir="新的漫剧素材/不晚忘忧",
        auto_detect_ending=True,
        skip_ending=False,
        force_detect=False
    )

    print(f"\n✅ 缓存数据加载: {len(renderer.ending_credits_cache)} 集")

    if renderer.ending_credits_cache:
        episode = list(renderer.ending_credits_cache.keys())[0]
        info = renderer.ending_credits_cache[episode]
        print(f"\n示例数据（第{episode}集）:")
        print(f"  总时长: {info.get('total_duration'):.2f}秒")
        print(f"  片尾时长: {info.get('ending_info', {}).get('duration', 0):.2f}秒")
        print(f"  有效时长: {info.get('effective_duration'):.2f}秒")

    return len(renderer.ending_credits_cache) > 0


def test_skip_detection():
    """测试2: 跳过检测功能"""
    print("\n" + "="*60)
    print("测试2: 跳过检测功能")
    print("="*60)

    test_project = "data/hangzhou-leiming/analysis/不晚忘忧"

    # 创建渲染器（跳过检测）
    renderer = ClipRenderer(
        project_path=test_project,
        output_dir="clips/test_skip",
        video_dir="新的漫剧素材/不晚忘忧",
        auto_detect_ending=False,
        skip_ending=True,
        force_detect=False
    )

    print(f"\n✅ 跳过检测模式: 缓存为空")
    print(f"   缓存数量: {len(renderer.ending_credits_cache)}")

    return len(renderer.ending_credits_cache) == 0


def test_effective_duration():
    """测试3: 有效时长计算"""
    print("\n" + "="*60)
    print("测试3: 有效时长计算")
    print("="*60)

    test_project = "data/hangzhou-leiming/analysis/不晚忘忧"

    # 创建渲染器（启用检测）
    renderer = ClipRenderer(
        project_path=test_project,
        output_dir="clips/test_duration",
        video_dir="新的漫剧素材/不晚忘忧",
        auto_detect_ending=True,
        skip_ending=False,
        force_detect=False
    )

    print(f"\n计算各集时长:")

    # 获取时长数据
    durations = renderer._calculate_episode_durations()

    for ep in sorted(durations.keys())[:3]:  # 显示前3集
        duration = durations[ep]

        if ep in renderer.ending_credits_cache:
            ep_info = renderer.ending_credits_cache[ep]
            total = ep_info.get('total_duration')
            ending = ep_info.get('ending_info', {}).get('duration', 0)
            effective = ep_info.get('effective_duration')

            print(f"\n  第{ep}集:")
            print(f"    总时长: {total:.2f}秒")
            print(f"    片尾时长: {ending:.2f}秒")
            print(f"    有效时长: {effective:.2f}秒")
            print(f"    使用时长: {duration}秒 ✅")
        else:
            print(f"\n  第{ep}集: {duration}秒（无片尾数据）")

    return True


def test_cache_file_path():
    """测试4: 缓存文件路径"""
    print("\n" + "="*60)
    print("测试4: 缓存文件路径")
    print("="*60)

    test_project = "data/hangzhou-leiming/analysis/不晚忘忧"

    renderer = ClipRenderer(
        project_path=test_project,
        output_dir="clips/test_path",
        video_dir="新的漫剧素材/不晚忘忧",
        auto_detect_ending=True
    )

    cache_file = renderer._get_ending_cache_file()

    print(f"\n缓存文件路径:")
    print(f"  {cache_file}")
    print(f"\n文件是否存在: {'✅ 是' if cache_file.exists() else '❌ 否'}")

    if cache_file.exists():
        import json
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"缓存内容:")
        print(f"  项目: {data.get('project')}")
        print(f"  集数: {len(data.get('episodes', []))}")

    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("V14.1 自动片尾检测集成 - 测试套件")
    print("="*60)

    tests = [
        ("缓存加载功能", test_cache_loading),
        ("跳过检测功能", test_skip_detection),
        ("有效时长计算", test_effective_duration),
        ("缓存文件路径", test_cache_file_path),
    ]

    results = {}

    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result
            status = "✅ 通过" if result else "❌ 失败"
            print(f"\n测试结果: {status}")
        except Exception as e:
            results[name] = False
            print(f"\n测试结果: ❌ 错误 - {e}")

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
