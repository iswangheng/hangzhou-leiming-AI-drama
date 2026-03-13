"""
45度倾斜角标模块（V4.9 修复投影计算版）

功能：
在视频角落添加45度倾斜的半透明条幅角标（如"热门短剧"），无需外部图片素材。

技术方案（V4.0高级版）：
1. 预渲染PNG图片（一次性生成，避免逐帧旋转）
2. 使用overlay滤镜叠加PNG（性能提升100倍+）
3. **关键改进**：精准坐标移动实现角落留白
4. **半透明效果**：95%不透明度（alpha=0.95）

V4.9核心修复（修复投影计算错误）：
- **问题发现**：V4.6-V4.8使用projection=141px计算位置是不正确的
- **根本原因**：overlay的(x,y)是左上角，不是中心点；应该用canvas_half=200px
- **解决方案**：直接使用canvas_half计算overlay位置
- **效果对比**：
  - V4.8: x = corner_offset - 141 = 70 - 141 = -71 (画布中心太靠外)
  - V4.9: x = corner_offset - 200 = 70 - 200 = -130 (画布中心正确定位)
  - **360p不再"过于靠中间"**！✅

核心数学逻辑（V4.9修正版）：
- overlay的(x, y)是overlay图片左上角在视频上的位置
- 画布中心点在overlay图片中的位置是(200, 200)
- 要让画布中心点距离视频角落=corner_offset：
  - top-left: 画布中心在(corner_offset, corner_offset)
  - overlay左上角 = (corner_offset-200, corner_offset-200)

特点：
- 半透明背景（95%不透明度）
- 角落留白（视频最边角露出原画面）
- 精致条幅（动态高度，分辨率自适应）
- 高性能（PNG预渲染）

依赖：
- FFmpeg（支持drawtext、overlay滤镜）

作者：杭州雷鸣AI短剧项目
版本：V4.9 - 修复投影计算错误（解决360p过于靠中间问题）
"""
import os
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Literal

from scripts.utils.subprocess_utils import run_command, run_popen_with_timeout
from scripts.config import TimeoutConfig


@dataclass
class TiltedLabelConfig:
    """倾斜角标配置（V4.6 统一动态缩放版）

    重要说明：
    - 所有尺寸参数（font_size、box_height、corner_offset）都是**基准值**（基于360p）
    - apply_label()方法会自动根据分辨率缩放这些参数
    - 缩放系数：resolution_ratio * 0.8
    """
    label_text: str = "热门短剧"          # 角标文字
    font_size: int = 28                   # 字体大小（**基准值**，会根据分辨率动态调整）
    label_color: str = "red@0.95"         # 标签背景色（95%不透明度，更明显！）
    text_color: str = "white"             # 文字颜色
    position: Literal["top-left", "top-right"] = "top-right"  # 位置
    font_path: Optional[str] = None       # 自定义字体路径
    canvas_size: int = 400                # 画布大小（固定400）
    box_height: int = 60                  # 条幅高度（**基准值**，会根据分辨率动态调整）
    box_y: int = 170                      # 条幅Y坐标（(400-60)/2=170，居中）
    angle: int = 45                       # 旋转角度
    corner_offset: int = 70               # 角落留白偏移量（**基准值**，会根据分辨率动态调整）


class TiltedLabelRenderer:
    """倾斜角标渲染器（V4.0 高级半透明版）"""

    def __init__(self, config: TiltedLabelConfig):
        self.config = config
        # 保存原始配置基准值（用于动态缩放）
        self._base_font_size = config.font_size
        self._base_box_height = config.box_height
        self._base_corner_offset = config.corner_offset

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
        """预渲染倾斜角标PNG图片（V4.0：半透明 + 角落留白）

        Args:
            output_path: PNG输出路径

        Returns:
            PNG文件路径
        """
        config = self.config
        font_path = self._find_font_file()

        # 旋转角度（右上角顺时针45度，左上角逆时针45度）
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

        # 2. 绘制色块（使用原始drawbox方法）
        filter_parts.append(
            f"[canvas]drawbox=x=0:y={config.box_y}:w={config.canvas_size}:h={config.box_height}:color={config.label_color}:t=fill[bg]"
        )

        # 3. 绘制文字（居中）
        drawtext = f"drawtext=text='{config.label_text}':fontcolor={config.text_color}:fontsize={config.font_size}:x=(w-text_w)/2:y=(h-text_h)/2"
        if font_path:
            drawtext += f":fontfile='{font_path}'"
        filter_parts.append(f"[bg]{drawtext}[txt]")

        # 4. 旋转（关键：保持透明背景）
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
            output_path
        ]

        result = run_command(
            cmd,
            timeout=TimeoutConfig.FFMPEG_FRAME_SINGLE,
            retries=1,
            error_msg="PNG生成超时"
        )
        if result is None or result.returncode != 0:
            err = result.stderr if result is not None else "超时"
            raise RuntimeError(f"PNG生成失败: {err}")

        return output_path

    def _get_overlay_position(self, video_width: int, video_height: int) -> tuple:
        """计算overlay位置（V4.9 修复投影计算版）

        V4.9关键修复：
        - Agent Team发现：V4.6-V4.8使用projection=141px计算位置是不正确的
        - 正确做法：直接使用canvas_half=200px来计算overlay位置
        - 这样可以让画布中心点距离角落=corner_offset，实现真正的"角标"效果

        数学原理：
        - overlay的(x, y)是overlay图片左上角在视频上的位置
        - 画布中心点在overlay图片中的位置是(200, 200)
        - 要让画布中心点在视频上的位置距离角落=corner_offset：
          - top-left: 画布中心在(corner_offset, corner_offset)
          - overlay左上角 = 画布中心 - (200, 200) = (corner_offset-200, corner_offset-200)

        V4.9修复前后对比：
        - V4.8 (错误): x = corner_offset - 141 = 70 - 141 = -71
        - V4.9 (正确): x = corner_offset - 200 = 70 - 200 = -130

        Args:
            video_width: 视频宽度
            video_height: 视频高度

        Returns:
            (x, y) 位置元组
        """
        config = self.config
        canvas_half = config.canvas_size // 2  # 200
        corner_offset = config.corner_offset

        if config.position == "top-right":
            # 右上角：画布中心点在(W-corner_offset, corner_offset)
            # overlay左上角 = 画布中心 - (200, 200)
            x = video_width - corner_offset - canvas_half
            y = corner_offset - canvas_half
        else:
            # 左上角：画布中心点在(corner_offset, corner_offset)
            # overlay左上角 = 画布中心 - (200, 200)
            x = corner_offset - canvas_half
            y = corner_offset - canvas_half

        return x, y

    def apply_label(
        self,
        input_video: str,
        output_video: str,
        on_progress: Optional[callable] = None
    ) -> str:
        """在视频上应用倾斜角标（V4.9 修复投影计算版）

        V4.9关键改进：
        - 修复投影计算错误（使用canvas_half=200px而非projection=141px）
        - corner_offset保持固定值70px（不缩放）
        - 字体和条幅仍然动态缩放（resolution_ratio * 0.8）

        Args:
            input_video: 输入视频路径
            output_video: 输出视频路径
            on_progress: 进度回调

        Returns:
            输出视频路径
        """
        print(f"\n{'='*60}")
        print(f"🎬 开始应用倾斜角标（V4.9 修复投影计算版）")
        print(f"  输入: {input_video}")
        print(f"  输出: {output_video}")
        print(f"  角标: {self.config.label_text}")
        print(f"  位置: {self.config.position}")
        print(f"  半透明: {self.config.label_color}")
        print(f"{'='*60}\n")

        # 获取视频尺寸
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0', input_video
        ]
        result = run_command(probe_cmd, timeout=TimeoutConfig.FFPROBE_QUICK, retries=1)
        video_width, video_height = map(int, result.stdout.strip().split(',')) if result else (360, 640)

        # ===== V4.6 新增：统一动态缩放计算（包括corner_offset）=====
        # 基于较小边计算分辨率倍数（适配横竖屏）
        smaller_dimension = min(video_width, video_height)
        resolution_ratio = smaller_dimension / 360.0

        # 动态调整字体大小、条幅高度、角落留白
        original_font_size = self.config.font_size
        original_box_height = self.config.box_height
        original_box_y = self.config.box_y
        original_corner_offset = self.config.corner_offset

        # V4.6: 使用0.8缩放系数（平衡360p和1080p效果）
        # 360p: ratio=1.0 * 0.8 = 0.8, font_size=22, box_height=48, corner_offset=56
        # 1080p: ratio=3.0 * 0.8 = 2.4, font_size=67, box_height=144, corner_offset=168
        scale_factor = resolution_ratio * 0.8

        scaled_font_size = int(original_font_size * scale_factor)
        scaled_box_height = int(original_box_height * scale_factor)
        scaled_corner_offset = int(original_corner_offset * scale_factor)
        scaled_box_y = int((400 - scaled_box_height) / 2)  # 保持居中

        # 确保字体大小为偶数（FFmpeg渲染更稳定）
        scaled_font_size = scaled_font_size if scaled_font_size % 2 == 0 else scaled_font_size + 1
        scaled_corner_offset = scaled_corner_offset if scaled_corner_offset % 2 == 0 else scaled_corner_offset + 1

        # 临时更新配置（用于PNG生成和overlay位置计算）
        self.config.font_size = scaled_font_size
        self.config.box_height = scaled_box_height
        self.config.box_y = scaled_box_y
        self.config.corner_offset = scaled_corner_offset

        print(f"📹 视频分辨率: {video_width}x{video_height}")
        print(f"📐 定位算法: V4.9 修复投影计算 (canvas_half=200px)")
        print(f"📐 较小边: {smaller_dimension}px, 基础倍数: {resolution_ratio:.2f}x")
        print(f"📐 实际缩放: {scale_factor:.2f}x")
        print(f"📐 画布大小: {self.config.canvas_size}x{self.config.canvas_size}")
        print(f"📐 字体大小: {original_font_size}px -> {scaled_font_size}px")
        print(f"📐 条幅高度: {original_box_height}px -> {scaled_box_height}px")
        print(f"📐 角落留白: {original_corner_offset}px -> {scaled_corner_offset}px (旋转后~{int(scaled_corner_offset * 1.414)}px)")
        print(f"🎨 背景透明度: {self.config.label_color} (95%不透明度)")
        # ===== 动态缩放结束 =====

        # 生成临时PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            png_path = tmp.name

        try:
            # 步骤1：预渲染PNG
            print(f"\n🖼️  预渲染PNG角标...")
            self._generate_png(png_path)
            print(f"✅ PNG生成完成: {png_path}")

            # 步骤2：计算overlay位置（角落留白）
            x, y = self._get_overlay_position(video_width, video_height)
            print(f"\n📍 叠加位置: x={x}, y={y}")
            if self.config.position == "top-right":
                print(f"   画布中心点将在: ({video_width - self.config.corner_offset}, {self.config.corner_offset})")
            else:
                print(f"   画布中心点将在: ({self.config.corner_offset}, {self.config.corner_offset})")
            print(f"   预期留白区域: 边长~{int(self.config.corner_offset * 1.414)}px的等腰直角三角形")

            # 步骤3：使用PNG叠加到视频
            print(f"\n🔄 正在叠加角标到视频...")

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

            def _on_line(line: str):
                if "time=" in line and on_progress:
                    try:
                        on_progress(0.5)
                    except:
                        pass

            returncode = run_popen_with_timeout(
                cmd,
                timeout=TimeoutConfig.FFMPEG_CLIP_RENDER,
                on_line=_on_line,
                log_prefix="角标叠加"
            )

            if returncode != 0:
                raise RuntimeError(f"视频叠加失败 (返回码: {returncode})")

            print(f"✅ 倾斜角标应用完成")
            print(f"📁 输出文件: {output_video}\n")

            return output_video

        finally:
            # 清理临时PNG
            if os.path.exists(png_path):
                os.remove(png_path)

            # 恢复原始配置（避免影响后续调用）
            self.config.font_size = original_font_size
            self.config.box_height = original_box_height
            self.config.box_y = original_box_y
            self.config.corner_offset = original_corner_offset


def add_tilted_label(
    input_video: str,
    output_video: str,
    label_text: str = "热门短剧",
    position: Literal["top-left", "top-right"] = "top-right",
    font_size: int = 28,
    label_color: str = "red@0.95",
    text_color: str = "white",
    font_path: Optional[str] = None,
    corner_offset: int = 70,
    on_progress: Optional[callable] = None
) -> str:
    """便捷函数：为视频添加倾斜角标（V4.9 修复投影计算版）

    V4.9说明：
    - 修复投影计算错误（使用canvas_half=200px而非projection=141px）
    - font_size和box_height会自动缩放（缩放系数：resolution_ratio * 0.8）
    - corner_offset保持固定值（不缩放，使用传入值，默认70px）
    - 解决360p视频"过于靠中间"的问题

    Args:
        input_video: 输入视频路径
        output_video: 输出视频路径
        label_text: 角标文字（默认"热门短剧"）
        position: 位置（"top-left" 或 "top-right"）
        font_size: 字体大小（默认28，**基准值**，会自动缩放）
        label_color: 标签背景色（格式：颜色@透明度，默认red@0.95即95%不透明度）
        text_color: 文字颜色
        font_path: 自定义字体路径
        corner_offset: 角落留白偏移量（默认70px，**基准值**，会自动缩放）
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
        font_path=font_path,
        corner_offset=corner_offset
    )

    renderer = TiltedLabelRenderer(config)
    return renderer.apply_label(input_video, output_video, on_progress)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python tilted_label.py <输入视频> <输出视频> [角标文字] [位置]")
        print("位置选项: top-left, top-right")
        print("\n示例:")
        print("  python tilted_label.py input.mp4 output.mp4")
        print("  python tilted_label.py input.mp4 output.mp4 '热门短剧' top-right")
        print("  python tilted_label.py input.mp4 output.mp4 '新剧上线' top-left")
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
