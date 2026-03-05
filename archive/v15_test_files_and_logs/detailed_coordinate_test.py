#!/usr/bin/env python3
"""
详细的FFmpeg坐标系统测试
提取视频截图，验证文本实际位置
"""
import subprocess
import tempfile
from pathlib import Path


def create_test_video_with_text_overlay():
    """创建带有不同位置文本叠加的测试视频"""
    output_path = Path(tempfile.gettempdir()) / "coord_test_video.mp4"

    # 创建测试视频，同时添加多个文本，每个在不同位置
    filter_str = (
        "color=c=darkgray:s=360x640:d=10:r=30,"
        "drawtext=text='TOP_y=30':fontsize=24:fontcolor=#FF0000:x=10:y=30:borderw=2:bordercolor=white,"
        "drawtext=text='UPPER_y=120':fontsize=24:fontcolor=#00FF00:x=10:y=120:borderw=2:bordercolor=white,"
        "drawtext=text='LOWER_y=520':fontsize=24:fontcolor=#0000FF:x=10:y=520:borderw=2:bordercolor=white,"
        "drawtext=text='BOTTOM_h-45':fontsize=24:fontcolor=#FFFF00:x=(w-tw)/2:y=h-45:borderw=3:bordercolor=black,"
        "drawtext=text='ABS_BOTTOM_h-20':fontsize=24:fontcolor=#FF00FF:x=(w-tw)/2:y=h-20:borderw=3:bordercolor=white"
    )

    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=c=darkgray:s=360x640:d=10:r=30',
        '-filter_complex', filter_str,
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_path)
    ]

    print("创建测试视频...")
    print(f"命令: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 创建视频失败: {result.stderr}")
        return None

    print(f"✅ 测试视频创建成功: {output_path}")
    return output_path


def extract_screenshots(video_path):
    """从视频中提取多个时间点的截图"""
    output_dir = Path(tempfile.gettempdir()) / 'coord_test_screenshots'
    output_dir.mkdir(exist_ok=True)

    # 提取3个时间点的截图：开始、中间、结束
    timestamps = ['00:00:01', '00:00:05', '00:00:09']

    screenshots = []
    for ts in timestamps:
        output_path = output_dir / f'screenshot_{ts.replace(":", "_")}.png'

        cmd = [
            'ffmpeg',
            '-ss', ts,
            '-i', str(video_path),
            '-frames:v', '1',
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            screenshots.append(output_path)
            print(f"✅ 截图已保存: {output_path}")
        else:
            print(f"❌ 截图失败: {result.stderr}")

    return screenshots


def analyze_video_dimensions(video_path):
    """分析视频的尺寸信息"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"\n视频信息:")
    print(result.stdout)

    return result.stdout


def main():
    """主测试函数"""
    print("="*60)
    print("FFmpeg drawtext 坐标系统详细测试")
    print("="*60)

    print("\n测试目标:")
    print("- 验证 y='h-45' 是否真的在底部")
    print("- 验证 y='120' 是否在顶部")
    print("- 确认坐标系统的原点和方向")

    # 创建测试视频
    video_path = create_test_video_with_text_overlay()
    if not video_path:
        return

    # 分析视频信息
    analyze_video_dimensions(video_path)

    # 提取截图
    print("\n提取视频截图...")
    screenshots = extract_screenshots(video_path)

    print("\n" + "="*60)
    print("测试说明")
    print("="*60)
    print("\n请检查生成的视频和截图，观察以下文本的位置:")
    print("\n1. 红色文本 'TOP_y=30':")
    print("   - 预期: 距离顶部30像素")
    print("   - 如果在顶部，说明y坐标从上往下增加")

    print("\n2. 绿色文本 'UPPER_y=120':")
    print("   - 预期: 距离顶部120像素")
    print("   - 应该在红色文本下方")

    print("\n3. 蓝色文本 'LOWER_y=520':")
    print("   - 预期: 距离顶部520像素")
    print("   - 应该在视频中下部")

    print("\n4. 黄色文本 'BOTTOM_h-45' (居中):")
    print("   - 预期: 距离底部45像素")
    print("   - 计算公式: y = 640 - 45 = 595")
    print("   - 如果在顶部，说明坐标系统有问题！")

    print("\n5. 紫色文本 'ABS_BOTTOM_h-20' (居中):")
    print("   - 预期: 距离底部20像素")
    print("   - 计算公式: y = 640 - 20 = 620")
    print("   - 应该在视频最底部")

    print("\n" + "="*60)
    print("文件位置")
    print("="*60)
    print(f"\n测试视频: {video_path}")
    print(f"截图目录: {Path(tempfile.gettempdir()) / 'coord_test_screenshots'}")

    print("\n" + "="*60)
    print("关键结论")
    print("="*60)
    print("\n如果黄色文本 'BOTTOM_h-45' 显示在顶部而不是底部，")
    print("可能的原因:")
    print("\n1. ❌ 坐标系统理解错误:")
    print("     - FFmpeg的(0,0)可能不在左上角")
    print("     - y轴方向可能不是从上到下")
    print("\n2. ❌ 表达式解析错误:")
    print("     - 'h-45' 可能被错误解析")
    print("     - 可能需要转义或特殊格式")
    print("\n3. ❌ 代码逻辑错误:")
    print("     - y值可能被其他地方覆盖")
    print("     - 转义逻辑可能有问题")


if __name__ == '__main__':
    main()
