#!/usr/bin/env python3
"""
最终验证脚本：生成带花字叠加的测试视频
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from scripts.understand.video_overlay.video_overlay import apply_overlay_to_video


def create_test_video():
    """创建一个简单的测试视频"""
    import subprocess

    output_path = Path(tempfile.gettempdir()) / "overlay_test_input.mp4"

    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'color=c=darkgray:s=360x640:d=10:r=30',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_path)
    ]

    print("创建测试视频...")
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"✅ 测试视频: {output_path}")
    return output_path


def test_overlay():
    """测试花字叠加功能"""
    print("="*80)
    print("杭州雷鸣AI短剧 - 花字叠加修复验证")
    print("="*80)

    # 创建测试视频
    input_video = create_test_video()

    # 测试所有样式
    from scripts.understand.video_overlay.overlay_styles import STYLE_REGISTRY

    print(f"\n共有 {len(STYLE_REGISTRY)} 个样式需要测试")

    output_dir = Path(tempfile.gettempdir()) / 'overlay_test_outputs'
    output_dir.mkdir(exist_ok=True)

    test_results = []

    for style_id, style in STYLE_REGISTRY.items():
        print(f"\n{'='*80}")
        print(f"测试样式: {style.name}")
        print(f"描述: {style.description}")
        print(f"{'='*80}")

        output_video = output_dir / f'test_{style_id}.mp4'

        try:
            result = apply_overlay_to_video(
                input_video=str(input_video),
                output_video=str(output_video),
                project_name="测试项目",
                drama_title="霸道总裁爱上我",
                style_id=style_id,
                disclaimer="本故事纯属虚构请勿模仿"
            )

            print(f"✅ 成功: {result}")
            test_results.append({
                'style': style.name,
                'status': 'success',
                'output': str(result)
            })

        except Exception as e:
            print(f"❌ 失败: {e}")
            test_results.append({
                'style': style.name,
                'status': 'failed',
                'error': str(e)
            })

    # 输出总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")

    success_count = sum(1 for r in test_results if r['status'] == 'success')
    fail_count = sum(1 for r in test_results if r['status'] == 'failed')

    print(f"\n总样式数: {len(test_results)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")

    if success_count > 0:
        print(f"\n✅ 成功的样式:")
        for r in test_results:
            if r['status'] == 'success':
                print(f"   - {r['style']}")
                print(f"     视频: {r['output']}")

    if fail_count > 0:
        print(f"\n❌ 失败的样式:")
        for r in test_results:
            if r['status'] == 'failed':
                print(f"   - {r['style']}: {r['error']}")

    print(f"\n{'='*80}")
    print("手动验证步骤")
    print(f"{'='*80}")
    print(f"\n1. 打开输出目录:")
    print(f"   {output_dir}")
    print(f"\n2. 逐个播放测试视频，检查:")
    print(f"   ✅ 剧名是否在底部（距离底部45像素）")
    print(f"   ✅ '热门短剧'是否为金黄色（#FFD700）")
    print(f"   ✅ 免责声明是否在最底部")
    print(f"   ✅ 文字是否清晰可读")

    print(f"\n{'='*80}")
    print("修复内容确认")
    print(f"{'='*80}")
    print(f"\n✅ 剧名位置:")
    print(f"   修复前: y=120-130 (顶部)")
    print(f"   修复后: y=h-45 (底部，距底部45像素)")

    print(f"\n✅ 热门短剧颜色:")
    print(f"   修复前: 红色系 (#FF0000, #FF4500, #FF1493等)")
    print(f"   修复后: 金黄色 (#FFD700) + 各色描边")

    print(f"\n✅ FFmpeg坐标系统验证:")
    print(f"   原点(0,0)在左上角")
    print(f"   Y轴从上到下增加")
    print(f"   y='h-45' = 640-45 = 595 (距底部45像素)")


if __name__ == '__main__':
    test_overlay()
