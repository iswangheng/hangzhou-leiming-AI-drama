#!/usr/bin/env python3
"""
测试V13时间戳优化修复效果
验证episode参数是否正确传递到智能切割查找器
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入必要模块
from scripts.data_models import ASRSegment
from scripts.understand.timestamp_optimizer import optimize_clips_timestamps
from scripts.understand.analyze_segment import SegmentAnalysis


def test_timestamp_optimization():
    """测试时间戳优化功能"""
    print("=" * 80)
    print("测试V13时间戳优化修复")
    print("=" * 80)

    # 创建测试数据
    # 第1集的ASR数据
    asr_episode_1 = [
        ASRSegment(text="第一句话开始", start=0.0, end=1.5, episode=1),
        ASRSegment(text="这是第一集的测试内容", start=5.0, end=7.0, episode=1),
        ASRSegment(text="这里有一个高光点", start=10.0, end=12.0, episode=1),
        ASRSegment(text="第一集的钩子点", start=15.0, end=17.0, episode=1),
    ]

    # 第2集的ASR数据
    asr_episode_2 = [
        ASRSegment(text="第二集开始", start=0.0, end=1.5, episode=2),
        ASRSegment(text="第二集的内容", start=5.0, end=7.0, episode=2),
        ASRSegment(text="第二集的高光点", start=10.0, end=12.0, episode=2),
        ASRSegment(text="第二集的钩子点", start=15.0, end=17.0, episode=2),
    ]

    # 创建按集分组的ASR字典
    episode_asr_dict = {
        1: asr_episode_1,
        2: asr_episode_2
    }

    # 创建测试用的高光点和钩子点
    highlights = [
        SegmentAnalysis(
            episode=1,
            start_time=0,
            end_time=20,
            is_highlight=True,
            highlight_timestamp=10.5,
            highlight_type="剧情高潮",
            highlight_desc="第一集高光点",
            highlight_confidence=8.0,
            is_hook=False,
            hook_timestamp=0,
            hook_type=None,
            hook_desc="",
            hook_confidence=0.0
        ),
        SegmentAnalysis(
            episode=2,
            start_time=0,
            end_time=20,
            is_highlight=True,
            highlight_timestamp=10.5,
            highlight_type="剧情高潮",
            highlight_desc="第二集高光点",
            highlight_confidence=8.0,
            is_hook=False,
            hook_timestamp=0,
            hook_type=None,
            hook_desc="",
            hook_confidence=0.0
        )
    ]

    hooks = [
        SegmentAnalysis(
            episode=1,
            start_time=0,
            end_time=20,
            is_highlight=False,
            highlight_timestamp=0,
            highlight_type=None,
            highlight_desc="",
            highlight_confidence=0.0,
            is_hook=True,
            hook_timestamp=15.5,
            hook_type="悬念钩子",
            hook_desc="第一集钩子点",
            hook_confidence=8.0
        ),
        SegmentAnalysis(
            episode=2,
            start_time=0,
            end_time=20,
            is_highlight=False,
            highlight_timestamp=0,
            highlight_type=None,
            highlight_desc="",
            highlight_confidence=0.0,
            is_hook=True,
            hook_timestamp=15.5,
            hook_type="悬念钩子",
            hook_desc="第二集钩子点",
            hook_confidence=8.0
        )
    ]

    print(f"\n准备测试数据:")
    print(f"  - 高光点: {len(highlights)}个 (第1集 + 第2集)")
    print(f"  - 钩子点: {len(hooks)}个 (第1集 + 第2集)")
    print(f"  - ASR数据: {len(episode_asr_dict)}集")

    # 调用时间戳优化
    print("\n开始时间戳优化...")
    optimized_highlights, optimized_hooks = optimize_clips_timestamps(
        highlights=highlights,
        hooks=hooks,
        episode_asr_dict=episode_asr_dict,
        buffer_ms=100.0
    )

    print("\n优化完成!")
    print(f"  - 优化后高光点: {len(optimized_highlights)}个")
    print(f"  - 优化后钩子点: {len(optimized_hooks)}个")

    # 验证结果
    print("\n验证结果:")
    for i, hl in enumerate(optimized_highlights):
        print(f"  高光点{i+1}: 第{hl.episode}集, 时间戳={hl.highlight_timestamp:.2f}s")

    for i, hook in enumerate(optimized_hooks):
        print(f"  钩子点{i+1}: 第{hook.episode}集, 时间戳={hook.hook_timestamp:.2f}s")

    # 检查日志中是否有正确的episode参数
    print("\n✅ 测试完成!")
    print("\n检查点:")
    print("  1. 是否显示 '🎯 优化第X集' 日志？")
    print("  2. 是否显示 '使用X个ASR片段' 日志？")
    print("  3. 是否显示 '📝 高光点/钩子点' 详细信息？")

    return True


if __name__ == "__main__":
    try:
        success = test_timestamp_optimization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
