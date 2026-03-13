#!/usr/bin/env python3
"""
测试各种渲染场景
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.understand.render_clips import ClipRenderer


def test_scenario(name, clip_index, add_overlay, add_ending, parallel=False, max_workers=1):
    """测试单个场景"""
    output_dir = f"test_output/{name}"

    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"  剪辑索引: {clip_index}")
    print(f"  花字: {'有' if add_overlay else '无'}")
    print(f"  结尾: {'有' if add_ending else '无'}")
    print(f"  模式: {'并行' if parallel else '串行'}")
    print('='*60)

    renderer = ClipRenderer(
        project_path="data/analysis/上班不垫钱，账单甩脸就翻脸",
        video_dir="260306-待剪辑-漫剧网盘素材1/上班不垫钱，账单甩脸就翻脸",
        output_dir=output_dir,
        add_ending_clip=add_ending,
        add_overlay=add_overlay,
        auto_detect_ending=True,
        skip_ending=False,
    )

    if parallel:
        renderer.render_all_clips_parallel(
            max_workers=max_workers,
            clip_indices=[clip_index]
        )
    else:
        renderer.render_all_clips(clip_indices=[clip_index])

    print(f"\n✅ {name} 完成!")
    return output_dir


def main():
    # 场景1: 串行 + 有结尾 + 有花字（非跨集）
    test_scenario(
        name="串行_有结尾_有花字_非跨集",
        clip_index=3,  # 非跨集
        add_overlay=True,
        add_ending=True,
        parallel=False
    )

    # 场景2: 串行 + 有结尾 + 有花字（跨集）
    test_scenario(
        name="串行_有结尾_有花字_跨集",
        clip_index=0,  # 跨集
        add_overlay=True,
        add_ending=True,
        parallel=False
    )

    # 场景3: 串行 + 无结尾 + 有花字
    test_scenario(
        name="串行_无结尾_有花字",
        clip_index=3,
        add_overlay=True,
        add_ending=False,
        parallel=False
    )

    # 场景4: 串行 + 有结尾 + 无花字
    test_scenario(
        name="串行_有结尾_无花字",
        clip_index=3,
        add_overlay=False,
        add_ending=True,
        parallel=False
    )

    # 场景5: 并行 + 有结尾 + 有花字（非跨集）
    test_scenario(
        name="并行_有结尾_有花字_非跨集",
        clip_index=3,
        add_overlay=True,
        add_ending=True,
        parallel=True,
        max_workers=2
    )

    # 场景6: 并行 + 有结尾 + 有花字（跨集）
    test_scenario(
        name="并行_有结尾_有花字_跨集",
        clip_index=0,
        add_overlay=True,
        add_ending=True,
        parallel=True,
        max_workers=2
    )

    print("\n" + "="*60)
    print("✅ 所有测试完成!")
    print("="*60)
    print("\n生成的文件:")
    for d in Path("test_output").iterdir():
        if d.is_dir():
            print(f"  {d.name}:")
            for f in d.glob("*.mp4"):
                print(f"    - {f.name}")


if __name__ == "__main__":
    main()
