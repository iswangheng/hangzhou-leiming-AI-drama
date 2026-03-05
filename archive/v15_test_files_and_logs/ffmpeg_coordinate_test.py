#!/usr/bin/env python3
"""
测试FFmpeg drawtext滤镜的坐标系统

用于验证：
1. y="h-45" 是否真的在底部
2. y="120" 是否在顶部
3. 坐标系统的原点在哪里
"""
import subprocess
import tempfile
from pathlib import Path


def create_test_video(width=360, height=640, duration=5):
    """创建测试视频（纯色背景）"""
    output_path = Path(tempfile.gettempdir()) / "test_video.mp4"

    # 创建纯色背景视频
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=c=blue:s={width}x{height}:d={duration}:r=30',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_path)
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def test_coordinate_system(video_path):
    """测试不同的y坐标值"""
    test_cases = [
        {
            'name': '顶部 (y=30)',
            'y': '30',
            'text': 'TOP_y=30',
            'color': '#FF0000',
            'expected': '顶部'
        },
        {
            'name': '中上部 (y=120)',
            'y': '120',
            'text': 'UPPER_y=120',
            'color': '#00FF00',
            'expected': '中上部'
        },
        {
            'name': '中部 (h/2)',
            'y': '(h/2)',
            'text': 'CENTER_h/2',
            'color': '#0000FF',
            'expected': '中部'
        },
        {
            'name': '底部 (h-45)',
            'y': 'h-45',
            'text': 'BOTTOM_h-45',
            'color': '#FFFF00',
            'expected': '底部'
        },
        {
            'name': '绝对底部 (h-30)',
            'y': 'h-30',
            'text': 'ABS_BOTTOM_h-30',
            'color': '#FF00FF',
            'expected': '绝对底部'
        },
    ]

    output_dir = Path(tempfile.gettempdir()) / 'ffmpeg_coord_tests'
    output_dir.mkdir(exist_ok=True)

    results = []

    for i, test_case in enumerate(test_cases):
        output_path = output_dir / f'test_{i}_{test_case["name"].replace(" ", "_")}.mp4'

        # 构建drawtext滤镜
        filter_str = (
            f"drawtext="
            f"text='{test_case['text']}':"
            f"fontsize=24:"
            f"fontcolor={test_case['color']}:"
            f"x='(w-tw)/2':"
            f"y={test_case['y']}:"
            f"borderw=3:bordercolor=white"
        )

        cmd = [
            'ffmpeg',
            '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:a', 'copy',
            str(output_path)
        ]

        print(f"\n测试 {i+1}: {test_case['name']}")
        print(f"  Y坐标: {test_case['y']}")
        print(f"  预期位置: {test_case['expected']}")
        print(f"  输出: {output_path}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"  ✅ 成功")
            results.append({
                'test': test_case['name'],
                'y_coord': test_case['y'],
                'expected': test_case['expected'],
                'output': str(output_path),
                'status': 'success'
            })
        else:
            print(f"  ❌ 失败")
            print(f"  错误: {result.stderr}")
            results.append({
                'test': test_case['name'],
                'y_coord': test_case['y'],
                'expected': test_case['expected'],
                'status': 'failed',
                'error': result.stderr
            })

    return results


def analyze_real_command():
    """分析实际的drawtext命令构建"""
    print("\n" + "="*60)
    print("分析实际的drawtext参数构建逻辑")
    print("="*60)

    # 模拟构建一个实际的drawtext滤镜
    y_value = "h-45"
    text = "测试剧名"

    print(f"\n目标Y坐标: {y_value}")
    print(f"文本: {text}")
    print(f"视频高度: 640")
    print(f"理论Y位置: {640 - 45} = 595 (应该是底部)")

    # 检查转义逻辑
    escaped_y = y_value.replace('\\', '\\\\').replace(':', '\\:').replace(',', '\\,').replace('(', '\\(').replace(')', '\\)')
    print(f"\n转义后的Y坐标: {escaped_y}")

    # 构建完整的滤镜字符串
    filter_str = f"drawtext=text={text}:fontsize=16:fontcolor=#FFA500:x=(w-tw)/2:y={escaped_y}"
    print(f"\n完整滤镜字符串:\n{filter_str}")

    print("\n" + "="*60)
    print("关键观察点:")
    print("="*60)
    print("1. y='h-45' 会被FFmpeg解释为: y = video_height - 45")
    print("2. 对于640px高的视频: y = 640 - 45 = 595")
    print("3. 这应该距离顶部595像素，即距离底部45像素")
    print("4. 如果显示在顶部，说明坐标系统理解有误")


def main():
    """主测试函数"""
    print("="*60)
    print("FFmpeg drawtext 坐标系统测试")
    print("="*60)

    # 分析实际命令
    analyze_real_command()

    print("\n" + "="*60)
    print("创建测试视频并测试不同坐标")
    print("="*60)

    # 创建测试视频
    print("\n创建测试视频...")
    test_video = create_test_video()
    print(f"测试视频: {test_video}")

    # 测试坐标系统
    print("\n开始测试坐标系统...")
    results = test_coordinate_system(test_video)

    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for result in results:
        if result['status'] == 'success':
            print(f"\n✅ {result['test']}")
            print(f"   Y坐标: {result['y_coord']}")
            print(f"   预期: {result['expected']}")
            print(f"   视频: {result['output']}")
            print(f"\n   请手动检查视频，确认文本位置是否符合预期！")
        else:
            print(f"\n❌ {result['test']}")
            print(f"   错误: {result.get('error', 'Unknown')}")

    print("\n" + "="*60)
    print("手动验证步骤:")
    print("="*60)
    print("1. 打开输出目录中的视频文件")
    print(f"   目录: {Path(tempfile.gettempdir()) / 'ffmpeg_coord_tests'}")
    print("2. 逐个检查视频，观察文本位置")
    print("3. 对比预期位置和实际位置")
    print("4. 如果 'h-45' 显示在顶部，说明坐标系统理解错误")


if __name__ == '__main__':
    main()
