#!/usr/bin/env python3
"""
测试时间戳优化模块（V13）
验证ASR辅助的毫秒级精度优化功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.understand.timestamp_optimizer import (
    adjust_hook_point,
    adjust_highlight_point,
    optimize_single_timestamp
)
from scripts.data_models import ASRSegment


def test_hook_optimization():
    """测试钩子点优化"""
    print("=" * 80)
    print("测试1: 钩子点优化（确保话已说完）")
    print("=" * 80)

    # 模拟ASR数据
    asr_segments = [
        ASRSegment(text="第一句话", start=0.0, end=2.5),
        ASRSegment(text="第二句话", start=2.8, end=5.2),
        ASRSegment(text="第三句话", start=5.5, end=8.0),
        ASRSegment(text="第四句话", start=8.3, end=11.7),
        ASRSegment(text="第五句话", start=12.0, end=15.5),
    ]

    # 测试场景1: 钩子点在第3句话开始时
    print("\n场景1: 钩子点 = 5.5秒（第三句话开始）")
    hook_ts = 5.5
    optimized = adjust_hook_point(hook_ts, asr_segments, buffer_ms=100.0)
    print(f"  原始: {hook_ts}秒")
    print(f"  优化: {optimized:.3f}秒")
    print(f"  策略: 等第三句话说完 (8.0秒) + 100ms缓冲")
    assert optimized == 8.1, f"期望 8.1, 实际 {optimized}"
    print("  ✅ 测试通过")

    # 测试场景2: 钩子点在最后
    print("\n场景2: 钩子点 = 20.0秒（所有ASR之后）")
    hook_ts = 20.0
    optimized = adjust_hook_point(hook_ts, asr_segments, buffer_ms=100.0)
    print(f"  原始: {hook_ts}秒")
    print(f"  优化: {optimized:.3f}秒")
    print(f"  策略: 未找到ASR数据，保持原时间")
    assert optimized == 20.0, f"期望 20.0, 实际 {optimized}"
    print("  ✅ 测试通过")


def test_highlight_optimization():
    """测试高光点优化"""
    print("\n" + "=" * 80)
    print("测试2: 高光点优化（确保话刚开始）")
    print("=" * 80)

    # 模拟ASR数据
    asr_segments = [
        ASRSegment(text="第一句话", start=0.0, end=2.5),
        ASRSegment(text="第二句话", start=2.8, end=5.2),
        ASRSegment(text="第三句话", start=5.5, end=8.0),
        ASRSegment(text="第四句话", start=8.3, end=11.7),
        ASRSegment(text="第五句话", start=12.0, end=15.5),
    ]

    # 测试场景1: 高光点在第三句话中间
    print("\n场景1: 高光点 = 7.0秒（第三句话中间）")
    hl_ts = 7.0
    optimized = adjust_highlight_point(hl_ts, asr_segments, buffer_ms=100.0)
    print(f"  原始: {hl_ts}秒")
    print(f"  优化: {optimized:.3f}秒")
    print(f"  策略: 从第三句话开始 (5.5秒) - 100ms缓冲")
    assert optimized == 5.4, f"期望 5.4, 实际 {optimized}"
    print("  ✅ 测试通过")

    # 测试场景2: 高光点在最开始
    print("\n场景2: 高光点 = 0.5秒（第一句话中间）")
    hl_ts = 0.5
    optimized = adjust_highlight_point(hl_ts, asr_segments, buffer_ms=100.0)
    print(f"  原始: {hl_ts}秒")
    print(f"  优化: {optimized:.3f}秒")
    print(f"  策略: 从第一句话开始 (0.0秒) - 100ms缓冲")
    assert optimized == 0.0, f"期望 0.0, 实际 {optimized}"  # 不会小于0
    print("  ✅ 测试通过")


def test_single_timestamp():
    """测试单个时间戳优化"""
    print("\n" + "=" * 80)
    print("测试3: 单个时间戳优化统一接口")
    print("=" * 80)

    asr_segments = [
        ASRSegment(text="测试", start=0.0, end=2.0),
    ]

    # 测试钩子点
    result = optimize_single_timestamp(1.5, 'hook', asr_segments)
    print(f"\n钩子点优化: 1.5秒 → {result:.3f}秒")
    assert result == 2.1, f"期望 2.1, 实际 {result}"
    print("  ✅ 测试通过")

    # 测试高光点
    result = optimize_single_timestamp(1.5, 'highlight', asr_segments)
    print(f"\n高光点优化: 1.5秒 → {result:.3f}秒")
    assert result == 0.0, f"期望 0.0, 实际 {result}"
    print("  ✅ 测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("V13 时间戳优化模块测试")
    print("=" * 80)

    try:
        test_hook_optimization()
        test_highlight_optimization()
        test_single_timestamp()

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        print("\n功能验证:")
        print("  ✓ 钩子点优化: 等话说完（对齐到ASR结束+100ms）")
        print("  ✓ 高光点优化: 从话开始（对齐到ASR开始-100ms）")
        print("  ✓ 毫秒级精度: 支持3位小数精度")
        print("  ✓ 边界保护: 不会小于0秒")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
