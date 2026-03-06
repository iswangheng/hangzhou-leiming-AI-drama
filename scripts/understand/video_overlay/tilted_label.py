"""
45度倾斜角标模块（V3.0优化版）

功能：
在视频角落添加45度倾斜的角标（如"热门短剧"），无需外部图片素材。

技术方案（V3.0优化）：
1. 预渲染PNG图片（一次性生成，避免逐帧旋转）
2. 使用overlay滤镜叠加PNG（性能提升100倍+）
3. 支持半透明、角落留白

特点：
- 半透明背景（90%不透明度）
- 角落留白（视频最边角露出原画面）
- 精致条幅（高度60px）
- 高性能（PNG预渲染）

依赖：
- FFmpeg（支持drawtext、overlay滤镜）

作者：杭州雷鸣AI短剧项目
版本：V3.0 - 使用PNG预渲染优化性能
"""
import os
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class TiltedLabelConfig:
    """倾斜角标配置"""
    label_text: str = "热门短剧"          # 角标文字
    font_size: int = 28                   # 字体大小（默认28）
    label_color: str = "red@0.9"          # 标签背景色（90%不透明度）
    text_color: str = "white"             # 文字颜色
    position: Literal["top-left", "top-right"] = "top-right"  # 位置
    font_path: Optional[str] = None       # 自定义字体路径
    canvas_size: int = 400                # 画布大小
    box_height: int = 60                  # 条幅高度
    box_y: int = 170                      # 条幅Y坐标
    angle: int = 45                       # 旋转角度


class TiltedLabelRenderer:
    """倾斜角标渲染器（V3.0 PNG预渲染版）"""

    def __init__(self, config: TiltedLabelConfig):
        self.config = config

    def _find_font_file(self) -> str:
        """查找中文字体文件"""
        if self.config.font_path and Path(self.config.font_path).exists():
            return self.config.font_path

        font_candidates = [
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]

        for font_path in font_candidates:
            if Path(font_path).exists():
                return font_path

        return ""

    def _generate_png(self, output_path: str) -> str:
        """预渲染倾斜角标PNG图片

        Args:
            output_path: PNG输出路径

        Returns:
            PNG文件路径
        """
        config = self.config
        font_path = self._find_font_file()

        # 旋转角度（右上角顺时针，左上角逆时针）
        if config.position == "top-right":
            rotation = f"{config.angle}*PI/180"
        else:
            rotation = f"-{config.angle}*PI/180"

        # 构建FFmpeg滤镜链生成PNG
        filter_parts = []

        # 1. 创建透明画布
        filter_parts.append(
            f"color=c=black@0:s={config.canvas_size}x{config.canvas_size},format=rgba[canvas]"
        )

        # 2. 绘制色块
        filter_parts.append(
            f"[canvas]drawbox=x=0:y={config.box_y}:w={config.canvas_size}:h={config.box_height}:color={config.label_color}:t=fill[bg]"
        )

        # 3. 绘制文字
        drawtext = f"drawtext=text='{config.label_text}':fontcolor={config.text_color}:fontsize={config.font_size}:x=(w-text_w)/2:y=(h-text_h)/2"
        if font_path:
            drawtext += f":fontfile='{font_path}'"
        filter_parts.append(f"[bg]{drawtext}[txt]")

        # 4. 旋转
        filter_parts.append(
            f"[txt]rotate={rotation}:c=black@0:ow={config.canvas_size}:oh={config.canvas_size}[rotated]"
        )

        filter_complex = ";".join(filter_parts)

        # 生成PNG（只处理1帧）
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black@0:s={config.canvas_size}x{config.canvas_size}:d=0.1',
            '-filter_complex', filter_complex,
            '-map', '[rotated]',
            '-frames:v', '1',
            '-y', output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"PNG生成失败: {result.stderr}")

        return output_path

    def _get_overlay_position(self, video_width: int, video_height: int) -> tuple:
        """计算overlay位置（平方根缩放版）

        策略：位置使用固定比例，而不是固定像素
        - X位置：视频宽度的75%处开始（右边留25%）
        - Y位置：视频高度的8%处（顶部留8%）

        Args:
            video_width: 视频宽度
            video_height: 视频高度

        Returns:
            (x, y) 位置元组
        """
        config = self.config

        # 按视频尺寸的百分比计算位置（固定比例）
        # X：视频宽度的25%处开始（即右边75%处）
        offset_x = int(video_width * 0.25)
        # Y：视频高度的8%（负值表示从顶部往下）
        offset_y = int(video_height * 0.08)

        if config.position == "top-right":
            # 右上角
            x = video_width - offset_x
            y = -offset_y
        else:
            # 左上角
            x = -offset_y
            y = -offset_y

        return x, y

    def apply_label(
        self,
        input_video: str,
        output_video: str,
        on_progress: Optional[callable] = None
    ) -> str:
        """在视频上应用倾斜角标（V6.0 平方根缩放版）

        使用平方根缩放：字体大小变化更平缓
        - 360p: scale=1 -> font=28
        - 1080p: scale=3 -> font=28*sqrt(3)=48 (不会太大)

        Args:
            input_video: 输入视频路径
            output_video: 输出视频路径
            on_progress: 进度回调

        Returns:
            输出视频路径
        """
        print(f"\n{'='*60}")
        print(f"🎬 开始应用倾斜角标（V6.0 平方根缩放版）")
        print(f"  输入: {input_video}")
        print(f"  输出: {output_video}")
        print(f"  角标: {self.config.label_text}")
        print(f"  位置: {self.config.position}")
        print(f"{'='*60}\n")

        # 获取视频尺寸（宽高都要获取）
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0', input_video
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_width, video_height = map(int, result.stdout.strip().split(','))

        # 计算缩放比例（基于360p基准）
        base_width = 360
        scale_factor = video_width / base_width

        # 使用平方根缩放（避免字体变化太剧烈）
        sqrt_scale = scale_factor ** 0.5

        # 动态调整配置参数
        original_canvas_size = self.config.canvas_size
        original_box_height = self.config.box_height
        original_box_y = self.config.box_y
        original_font_size = self.config.font_size

        # PNG画布按平方根缩放
        self.config.canvas_size = int(400 * sqrt_scale)
        # 条幅高度按平方根缩放
        self.config.box_height = int(60 * sqrt_scale)
        # 条幅Y坐标按平方根缩放
        self.config.box_y = int(170 * sqrt_scale)
        # 字体大小按平方根缩放，再缩小20%
        self.config.font_size = int(original_font_size * sqrt_scale * 0.8)

        print(f"📹 视频分辨率: {video_width}x{video_height}")
        print(f"📐 缩放比例: {scale_factor:.2f}x (sqrt: {sqrt_scale:.2f})")
        print(f"📐 画布大小: {original_canvas_size} -> {self.config.canvas_size}")
        print(f"📐 条幅高度: {original_box_height} -> {self.config.box_height}")
        print(f"📐 条幅Y坐标: {original_box_y} -> {self.config.box_y}")
        print(f"📐 字体大小: {original_font_size} -> {self.config.font_size} (sqrt*80%)")

        # 生成临时PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            png_path = tmp.name

        try:
            # 步骤1：预渲染PNG
            print(f"🖼️  预渲染PNG角标...")
            self._generate_png(png_path)
            print(f"✅ PNG生成完成: {png_path}")

            # 步骤2：计算overlay位置
            x, y = self._get_overlay_position(video_width, video_height)
            print(f"📍 叠加位置: x={x}, y={y}")

            # 步骤3：使用PNG叠加到视频
            print(f"🔄 正在叠加角标到视频...")

            cmd = [
                'ffmpeg', '-y',
                '-i', input_video,
                '-i', png_path,
                '-filter_complex',
                f'[0:v][1:v]overlay=x={x}:y={y}',
                '-c:a', 'copy',
                '-preset', 'fast',
                '-movflags', '+faststart',
                output_video
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            for line in process.stdout:
                if "time=" in line and on_progress:
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        on_progress(0.5)
                    except:
                        pass

            process.wait()

            if process.returncode != 0:
                raise RuntimeError(f"视频叠加失败 (返回码: {process.returncode})")

            print(f"✅ 倾斜角标应用完成")
            print(f"📁 输出文件: {output_video}\n")

            return output_video

        finally:
            # 清理临时PNG
            if os.path.exists(png_path):
                os.remove(png_path)


def add_tilted_label(
    input_video: str,
    output_video: str,
    label_text: str = "热门短剧",
    position: Literal["top-left", "top-right"] = "top-right",
    font_size: int = 28,
    label_color: str = "red@0.9",
    text_color: str = "white",
    font_path: Optional[str] = None,
    on_progress: Optional[callable] = None
) -> str:
    """便捷函数：为视频添加倾斜角标

    Args:
        input_video: 输入视频路径
        output_video: 输出视频路径
        label_text: 角标文字（固定为"热门短剧"）
        position: 位置（"top-left" 或 "top-right"）
        font_size: 字体大小（默认28）
        label_color: 标签背景色（格式：颜色@透明度，默认red@0.9）
        text_color: 文字颜色
        font_path: 自定义字体路径
        on_progress: 进度回调函数

    Returns:
        输出视频路径
    """
    config = TiltedLabelConfig(
        label_text=label_text,
        font_size=font_size,
        label_color=label_color,
        text_color=text_color,
        position=position,
        font_path=font_path
    )

    renderer = TiltedLabelRenderer(config)
    return renderer.apply_label(input_video, output_video, on_progress)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python tilted_label.py <输入视频> <输出视频> [角标文字] [位置]")
        print("位置选项: top-left, top-right")
        sys.exit(1)

    input_video = sys.argv[1]
    output_video = sys.argv[2]
    label_text = sys.argv[3] if len(sys.argv) > 3 else "热门短剧"
    position = sys.argv[4] if len(sys.argv) > 4 else "top-right"

    add_tilted_label(
        input_video=input_video,
        output_video=output_video,
        label_text=label_text,
        position=position
    )
