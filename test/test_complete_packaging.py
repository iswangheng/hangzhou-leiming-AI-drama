"""完整视频包装测试

包含三个元素：
1. 热门短剧（右上角倾斜角标）
2. 短剧名字（底部居中）
3. 免责声明（底部居中，剧名下方）

特点：
- 根据视频分辨率动态调整字体大小
- 基准：360x640分辨率下字体大小为 剧名18px、免责声明12px
- 字体大小按视频宽度比例缩放
"""
import sys
sys.path.insert(0, '.')

from scripts.understand.video_overlay.tilted_label import add_tilted_label
import subprocess
import os


def get_video_resolution(video_path: str) -> tuple:
    """获取视频分辨率 (width, height)"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    width, height = map(int, result.stdout.strip().split(','))
    return width, height


def calculate_font_sizes(video_width: int, video_height: int) -> tuple:
    """根据视频分辨率计算字体大小

    基准：360x640分辨率下
    - 剧名字体: 18px
    - 免责声明: 12px
    - 倾斜角标: 28px

    使用平方根缩放：字体大小变化更平缓
    - 360p: scale=1 -> font=基准值
    - 1080p: scale=3 -> font=基准值*sqrt(3)*0.8
    """
    # 以360为基准宽度
    base_width = 360
    scale_factor = video_width / base_width

    # 使用平方根缩放
    sqrt_scale = scale_factor ** 0.5

    # 动态计算字体大小（平方根缩放，再缩小20%）
    drama_title_size = int(18 * sqrt_scale * 0.8)   # 剧名
    disclaimer_size = int(12 * sqrt_scale * 0.8)    # 免责声明

    # 计算底部位置（按视频高度百分比固定）
    title_y = int(video_height * 0.05)              # 剧名距离底部5%
    disclaimer_y = int(video_height * 0.028)         # 免责声明距离底部2.8%

    print(f"  📐 视频分辨率: {video_width}x{video_height}")
    print(f"  📐 缩放比例: {scale_factor:.2f}x (sqrt: {sqrt_scale:.2f})")
    print(f"  📐 剧名字体: {drama_title_size}px, 位置y: h-{title_y}")
    print(f"  📐 免责声明: {disclaimer_size}px, 位置y: h-{disclaimer_y}")

    return {
        'drama_title_size': drama_title_size,
        'disclaimer_size': disclaimer_size,
        'label_size': int(28 * sqrt_scale * 0.8),  # 热门短剧角标
        'title_y': title_y,
        'disclaimer_y': disclaimer_y
    }


def complete_packaging(
    input_video: str,
    output_video: str,
    drama_title: str = "多子多福",
    disclaimer: str = "本故事纯属虚构请勿模仿"
) -> str:
    """添加完整包装（短剧名字 + 热门短剧 + 免责声明）"""

    print(f"\n{'='*60}")
    print(f"🎬 开始添加完整视频包装")
    print(f"  输入视频: {input_video}")
    print(f"  输出视频: {output_video}")
    print(f"  短剧名字: {drama_title}")
    print(f"  免责声明: {disclaimer}")
    print(f"{'='*60}\n")

    # 获取视频分辨率并计算字体大小
    video_width, video_height = get_video_resolution(input_video)
    font_config = calculate_font_sizes(video_width, video_height)

    # 步骤1：添加倾斜角标（热门短剧）
    temp_video = "/var/folders/q4/rjd2d4xn24z01l78hdpzwcrc0000gn/T/tmp_complete_step1.mp4"

    print("📍 步骤1: 添加倾斜角标（热门短剧）...")
    add_tilted_label(
        input_video=input_video,
        output_video=temp_video,
        label_text="热门短剧",
        position="top-right",
        label_color="red@0.9",
        font_size=font_config['label_size']
    )

    # 步骤2：添加底部文字（短剧名字 + 免责声明）
    print("📍 步骤2: 添加底部文字（短剧名字 + 免责声明）...")

    font_path = "/System/Library/Fonts/Supplemental/Songti.ttc"

    # 使用 drawtext 滤镜添加底部文字（动态字体大小）
    cmd = [
        'ffmpeg', '-y',
        '-i', temp_video,
        '-vf', f"drawtext=text='{drama_title}':fontcolor=white:fontsize={font_config['drama_title_size']}:x=(w-text_w)/2:y=h-{font_config['title_y']}:borderw=1:bordercolor=black:fontfile='{font_path}',drawtext=text='{disclaimer}':fontcolor=white@0.7:fontsize={font_config['disclaimer_size']}:x=(w-text_w)/2:y=h-{font_config['disclaimer_y']}:borderw=0.5:bordercolor=black@0.5:fontfile='{font_path}'",
        '-c:a', 'copy',
        '-preset', 'fast',
        '-movflags', '+faststart',
        output_video
    ]

    print(f"🔄 正在执行FFmpeg...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for line in process.stdout:
        print(line, end='')

    process.wait()

    # 清理临时文件
    if os.path.exists(temp_video):
        os.remove(temp_video)

    if process.returncode != 0:
        raise RuntimeError(f"视频叠加失败 (返回码: {process.returncode})")

    print(f"\n✅ 完整包装完成!")
    print(f"📁 输出文件: {output_video}\n")

    return output_video


if __name__ == "__main__":
    # 测试1：1080x1920 高清视频
    print("\n" + "="*60)
    print("🧪 测试1: 1080x1920 高清视频")
    print("="*60)

    input_video1 = "晓红姐-3.4剧目/多子多福，开局就送绝美老婆/1.mp4"
    output_video1 = "test/test/多子多福_1080p_完整包装.mp4"

    try:
        complete_packaging(
            input_video=input_video1,
            output_video=output_video1,
            drama_title="多子多福",
            disclaimer="本故事纯属虚构请勿模仿"
        )
    except Exception as e:
        print(f"❌ 错误: {e}")
