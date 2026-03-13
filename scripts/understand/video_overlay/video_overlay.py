"""
视频花字叠加核心模块（V15.6 集成V4.9修复投影计算版）

基于FFmpeg实现视频花字叠加功能

技术方案（V15.6）：
- 热门短剧：使用倾斜角标（V4.9 修复投影计算）+ overlay滤镜
- 剧名、免责声明：使用drawtext滤镜
- 支持自定义字体、颜色、描边、阴影
- 支持多行文本独立配置
- 避免遮挡原字幕（位置可配置）
- 项目级样式统一（缓存项目样式选择）

V15.6关键更新：
- 集成V4.9倾斜角标模块（修复投影计算错误）
- 使用canvas_half=200px而非projection=141px计算overlay位置
- 解决360p视频"过于靠中间"的问题
- 确保360p和1080p的角标都真正靠近角落

依赖：
- FFmpeg（支持drawtext滤镜，需要启用--enable-libfreetype）
- 可选：中文字体文件（用于更好的中文显示）

作者：杭州雷鸣AI短剧项目
版本：V15.6 - 集成V4.9修复投影计算倾斜角标
"""
import os
import json
import subprocess
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from scripts.utils.subprocess_utils import run_command, run_popen_with_timeout
from scripts.config import TimeoutConfig

from .overlay_styles import (
    OverlayStyle,
    TextLayer,
    get_style,
    get_random_style,
    get_random_disclaimer,
    DISCLAIMER_TEXTS
)
from .tilted_label import TiltedLabelConfig, TiltedLabelRenderer


@dataclass
class OverlayConfig:
    """花字叠加配置"""
    enabled: bool = True                    # 是否启用花字叠加
    style_id: Optional[str] = None          # 指定样式ID（None表示随机）
    project_name: str = ""                  # 项目名称
    drama_title: str = ""                   # 剧名
    disclaimer: Optional[str] = None        # 免责声明（None表示随机）
    font_path: Optional[str] = None         # 自定义字体路径
    subtitle_safe_zone: int = 150           # 字幕安全区（底部像素）
    cache_dir: str = ".overlay_style_cache" # 样式缓存目录
    hot_drama_position: str = "top-right"   # 热门短剧角标位置（"top-left" 或 "top-right"）


class VideoOverlayRenderer:
    """视频花字叠加渲染器"""

    def __init__(self, config: OverlayConfig):
        """初始化渲染器

        Args:
            config: 花字叠加配置
        """
        self.config = config

        # 确保缓存目录存在
        Path(config.cache_dir).mkdir(parents=True, exist_ok=True)

        # 获取或选择样式
        self.style = self._get_or_select_style()

        # 替换文本内容
        self._prepare_text_layers()

    def _apply_randomization(self):
        """应用随机化配置（位置、显示时长）"""
        import random

        # 随机化免责声明文案
        # 位置和显示时长由apply_overlay直接控制

        print(f"🎲 热门短剧显示模式: 倾斜角标（V4.1 PNG预渲染）")

    def _get_style_cache_file(self) -> Path:
        """获取样式缓存文件路径"""
        # 使用项目名称的hash作为缓存文件名
        project_hash = hashlib.md5(
            self.config.project_name.encode('utf-8')
        ).hexdigest()[:8]
        return Path(self.config.cache_dir) / f"style_{project_hash}.json"

    def _get_or_select_style(self) -> OverlayStyle:
        """获取或选择样式

        优先级：
        1. 配置中指定的样式
        2. 缓存中的样式（项目级统一）
        3. 随机选择新样式并缓存

        Returns:
            选择的样式
        """
        # 1. 如果配置中指定了样式ID，直接使用
        if self.config.style_id:
            style = get_style(self.config.style_id)
            if style:
                print(f"✅ 使用指定样式: {style.name}")
                return style
            else:
                print(f"⚠️  未找到样式ID '{self.config.style_id}'，将随机选择")

        # 2. 尝试从缓存加载样式
        cache_file = self._get_style_cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    style_id = cache_data.get('style_id')
                    if style_id:
                        style = get_style(style_id)
                        if style:
                            print(f"✅ 从缓存加载样式: {style.name}")
                            return style
            except Exception as e:
                print(f"⚠️  缓存文件损坏: {e}")

        # 3. 随机选择新样式并缓存
        style = get_random_style()
        self._cache_style(style.id)
        print(f"🎲 为项目 '{self.config.project_name}' 随机选择样式: {style.name}")
        return style

    def _cache_style(self, style_id: str) -> None:
        """缓存样式选择到文件

        Args:
            style_id: 样式ID
        """
        cache_file = self._get_style_cache_file()
        cache_data = {
            'project_name': self.config.project_name,
            'style_id': style_id
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def _prepare_text_layers(self) -> None:
        """准备文本图层，替换占位符

        将模板中的占位符替换为实际内容：
        - {title} -> 剧名
        - {disclaimer} -> 免责声明
        - 随机选择剧名颜色（白色或紫色）
        - 剧名使用黑色细描边，朴素清晰
        """
        import random

        # 随机选择剧名颜色：白色或紫色
        color_schemes = [
            {"font": "#FFFFFF", "border": "#000000", "name": "白色"},  # 白字黑边
            {"font": "#E6E6FA", "border": "#000000", "name": "淡紫色"},  # 淡紫色字黑边
        ]
        selected_color = random.choice(color_schemes)
        self.style.drama_title.font_color = selected_color["font"]
        self.style.drama_title.border_color = selected_color["border"]

        # 剧名文字完全不透明（清晰可见）
        self.style.drama_title.font_alpha = 1.0
        # 黑色细描边
        self.style.drama_title.border_width = 1.0
        # 轻阴影
        self.style.drama_title.shadow_x = 1
        self.style.drama_title.shadow_y = 1

        print(f"🎨 剧名颜色: {selected_color['name']} (朴素清晰)")

        # 替换剧名
        title = self.config.drama_title or self.config.project_name
        self.style.drama_title.text = self.style.drama_title.text.replace(
            "{title}", title
        )

        # 替换免责声明
        disclaimer = self.config.disclaimer or get_random_disclaimer()
        self.style.disclaimer.text = self.style.disclaimer.text.replace(
            "{disclaimer}", disclaimer
        )

    # V15.4: _build_alternating_enable方法已移除
    # 热门短剧现在使用tilted_label.py的倾斜角标（静态PNG预渲染）
    # 不再支持左右交替显示功能

    def _find_font_file(self) -> str:
        """查找中文字体文件

        优先级：
        1. 配置中指定的字体
        2. 系统常见中文字体位置

        Returns:
            字体文件路径（如果找不到返回空字符串）
        """
        # 1. 配置中指定的字体
        if self.config.font_path and Path(self.config.font_path).exists():
            return self.config.font_path

        # 2. 样式中指定的字体
        if self.style.font_path and Path(self.style.font_path).exists():
            return self.style.font_path

        # 3. 系统常见中文字体（按操作系统）
        font_candidates = []

        # macOS - 优先使用Songti（宋体，经典中文字体）
        if Path("/System/Library/Fonts/Supplemental/Songti.ttc").exists():
            font_candidates.append("/System/Library/Fonts/Supplemental/Songti.ttc")
        if Path("/System/Library/Fonts/STHeiti Medium.ttc").exists():
            font_candidates.append("/System/Library/Fonts/STHeiti Medium.ttc")
        if Path("/System/Library/Fonts/PingFang.ttc").exists():
            font_candidates.append("/System/Library/Fonts/PingFang.ttc")
        if Path("/Library/Fonts/Arial Unicode.ttf").exists():
            font_candidates.append("/Library/Fonts/Arial Unicode.ttf")

        # Linux
        if Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc").exists():
            font_candidates.append("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
        if Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf").exists():
            font_candidates.append("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf")

        # Windows
        if Path("C:/Windows/Fonts/msyh.ttc").exists():
            font_candidates.append("C:/Windows/Fonts/msyh.ttc")
        if Path("C:/Windows/Fonts/simhei.ttf").exists():
            font_candidates.append("C:/Windows/Fonts/simhei.ttf")

        # 返回第一个找到的字体
        for font_path in font_candidates:
            if Path(font_path).exists():
                print(f"📝 使用字体: {font_path}")
                return font_path

        # 如果都找不到，返回空字符串（FFmpeg将使用默认字体）
        print("⚠️  未找到中文字体，将使用FFmpeg默认字体")
        return ""

    def _build_drawtext_filter(self, layer: TextLayer, font_path: str, custom_enable: str = None) -> str:
        """构建FFmpeg drawtext滤镜字符串

        Args:
            layer: 文本图层配置
            font_path: 字体文件路径

        Returns:
            drawtext滤镜字符串
        """
        # 基础参数
        params = {
            'text': layer.text,
            'fontsize': layer.font_size,
            'fontcolor': layer.font_color,
            'alpha': layer.font_alpha,
            'x': layer.x,
            'y': layer.y,
        }

        # 添加字体（如果找到）
        # 注意：fontfile参数需要用单引号包裹，以支持包含空格的路径
        if font_path:
            # fontfile始终使用单引号包裹，不管路径是否包含空格
            # 这样可以确保字体正确加载
            params['fontfile'] = font_path

        # 添加描边
        if layer.border_width > 0:
            params['borderw'] = layer.border_width
            params['bordercolor'] = layer.border_color

        # 添加阴影
        if layer.shadow_x > 0 or layer.shadow_y > 0:
            params['shadowx'] = layer.shadow_x
            params['shadowy'] = layer.shadow_y
            params['shadowcolor'] = layer.shadow_color

        # 注意：FFmpeg drawtext不支持rotation参数
        # 如需倾斜效果，可以通过使用特殊的斜体字体实现

        # 添加显示时长控制
        # V15.6: 删除了animation相关功能（FFmpeg drawtext不支持）
        if custom_enable:
            params['enable'] = custom_enable

        # 构建参数字符串
        # 注意：FFmpeg drawtext滤镜参数格式化规则：
        # - fontfile: 用单引号包裹（路径可能包含空格）
        # - x, y: 表达式用单引号包裹
        # - enable: 表达式用单引号包裹
        # - 其他参数: 直接使用
        def format_param_value(key: str, value: str) -> str:
            """格式化参数值"""
            # fontfile参数：使用单引号
            if key == 'fontfile':
                return f"{key}='{value}'"

            # 表达式参数（x, y, enable）：用单引号包裹整个表达式
            if key in ['x', 'y', 'enable']:
                return f"{key}='{value}'"

            # 其他参数：直接使用
            return f"{key}={value}"

        param_str = ':'.join(format_param_value(k, v) for k, v in params.items())

        return f"drawtext={param_str}"

    def apply_overlay(
        self,
        input_video: str,
        output_video: str,
        on_progress: Optional[callable] = None,
        subtitle_bottom_y: Optional[int] = None,
    ) -> str:
        """在视频上应用花字叠加

        Args:
            input_video: 输入视频路径
            output_video: 输出视频路径
            on_progress: 进度回调函数
            subtitle_bottom_y: 原始字幕区域底部 Y 坐标（从顶部量起，像素单位）。
                               提供时，剧名定位于字幕下方；否则使用保守百分比。

        Returns:
            输出视频路径
        """
        if not self.config.enabled:
            print("⚠️  花字叠加未启用，跳过处理")
            return input_video

        # ===== V2.0: 动态分辨率自适应 =====
        # 获取视频分辨率，用于动态计算字体大小和位置
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0', input_video
        ]
        result = run_command(probe_cmd, timeout=TimeoutConfig.FFPROBE_QUICK, retries=1)
        video_width, video_height = map(int, result.stdout.strip().split(',')) if result else (360, 640)

        # 使用视频宽度计算缩放比例（基准：竖屏360宽度）
        base_width = 360  # 基准：竖屏视频的宽度
        scale_factor = video_width / base_width

        # V2.3 Final Ultimate v3: 精简优化版
        # 设计理念：简洁精致，避免字体过大
        # 热门短剧(×1.2), 剧名(×0.95), 免责(×0.85)

        # 判断是否为横屏
        is_landscape = video_width > video_height

        # 计算分辨率倍数（基于较小边）
        smaller_dimension = min(video_width, video_height)
        resolution_ratio = smaller_dimension / 360.0

        # 估算原始字幕大小（基于360p实测：18px，精简后）
        base_subtitle_size = int(18 * resolution_ratio)

        # 根据原始字幕大小计算花字大小（精简系数）
        hot_drama_font_size = int(base_subtitle_size * 1.2)  # 热门短剧略大
        drama_title_font_size = int(base_subtitle_size * 0.95)  # 剧名略小于字幕
        disclaimer_font_size = int(base_subtitle_size * 0.85)    # 免责声明精简

        # 确保字体大小为偶数（FFmpeg渲染更稳定）
        hot_drama_font_size = hot_drama_font_size if hot_drama_font_size % 2 == 0 else hot_drama_font_size + 1
        drama_title_font_size = drama_title_font_size if drama_title_font_size % 2 == 0 else drama_title_font_size + 1
        disclaimer_font_size = disclaimer_font_size if disclaimer_font_size % 2 == 0 else disclaimer_font_size + 1

        print(f"\n📹 视频分辨率: {video_width}x{video_height} {'横屏' if is_landscape else '竖屏'}")
        print(f"📐 缩放算法: V2.3 Final Ultimate v3 (精简优化版)")
        print(f"📐 较小边: {smaller_dimension}px, 分辨率倍数: {resolution_ratio:.1f}x")
        print(f"📝 设计逻辑: 简洁精致, 热门短剧×1.2, 剧名×0.95, 免责×0.85")
        print(f"📝 估算原始字幕: {base_subtitle_size}px (基于360p精简值18px×倍数)")
        print(f"📝 FFmpeg fontsize设置值:")
        print(f"   原始字幕(估算): {base_subtitle_size}px")
        print(f"   热门短剧: {hot_drama_font_size}px (原始×1.2)")
        print(f"   剧名: {drama_title_font_size}px (原始×0.95, 略小于字幕)")
        print(f"   免责声明: {disclaimer_font_size}px (原始×0.85, 精简)")

        # 动态计算剧名和免责声明 Y 坐标
        # 布局从底部往上：底部边缘 → 免责声明 → 间隙 → 剧名 → 间隙 → 原始字幕
        TITLE_GAP = 8        # 字幕底部 → 剧名顶部间隙（像素）
        DISCLAIMER_GAP = 4   # 剧名底部 → 免责声明顶部间隙（像素）
        BOTTOM_MARGIN = 4    # 免责声明底部 → 视频底部最小边距（像素）

        # 计算动态定位所需的总像素高度
        required_space = TITLE_GAP + drama_title_font_size + DISCLAIMER_GAP + disclaimer_font_size + BOTTOM_MARGIN
        available_space = (video_height - subtitle_bottom_y) if subtitle_bottom_y is not None else 0

        # use_single_row：空间不足时启用同行左右布局
        use_single_row = False
        drama_title_x_override = None
        disclaimer_x_override = None

        if subtitle_bottom_y is not None and subtitle_bottom_y < video_height * 0.95 and available_space >= required_space:
            # 动态定位：字幕下方空间足够，剧名紧跟字幕下方（两行）
            drama_title_top = subtitle_bottom_y + TITLE_GAP
            disclaimer_top = drama_title_top + drama_title_font_size + DISCLAIMER_GAP
            drama_title_y = str(drama_title_top)
            disclaimer_y = str(disclaimer_top)
            print(f"📍 动态位置（基于字幕检测 subtitle_bottom_y={subtitle_bottom_y}，可用={available_space}px≥需要={required_space}px）:")
        elif subtitle_bottom_y is not None and subtitle_bottom_y < video_height * 0.95:
            # 空间不足：剧名左对齐、免责声明右对齐，同行显示在字幕正下方
            common_y = str(subtitle_bottom_y + TITLE_GAP)
            drama_title_y = common_y
            disclaimer_y = common_y
            drama_title_x_override = "8"        # 左对齐
            disclaimer_x_override = "w-tw-8"   # 右对齐
            use_single_row = True
            print(f"📍 单行左右布局（字幕下方空间不足 {available_space}px < {required_space}px）:")
        else:
            # Fallback：保守百分比（距底部 12% 和 4%）
            # 用于：未检测到字幕、空间不足、或字幕过于靠下
            drama_title_y = f"h-{int(video_height * 0.12)}"
            disclaimer_y = f"h-{int(video_height * 0.04)}"
            reason = "未检测到字幕" if subtitle_bottom_y is None else f"空间不足({available_space}px < {required_space}px)"
            print(f"📍 动态位置（Fallback 保守百分比，原因: {reason}）:")

        print(f"   剧名: y={drama_title_y}")
        print(f"   免责声明: y={disclaimer_y}")
        print(f"   热门短剧: 由tilted_label模块自动计算（倾斜角标）")
        # ===== 动态分辨率自适应结束 =====

        print(f"\n{'='*60}")
        print(f"🎬 开始应用花字叠加")
        print(f"  输入: {input_video}")
        print(f"  输出: {output_video}")
        print(f"  样式: {self.style.name}")
        print(f"{'='*60}\n")

        # 应用随机化配置
        self._apply_randomization()

        # 查找字体
        font_path = self._find_font_file()

        # ===== V15.6 集成V4.9修复投影计算逻辑 =====
        # 获取视频尺寸
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0', input_video
        ]
        result = run_command(probe_cmd, timeout=TimeoutConfig.FFPROBE_QUICK, retries=1)
        video_width, video_height = map(int, result.stdout.strip().split(',')) if result else (360, 640)

        # 完全复制tilted_label.py的apply_label缩放逻辑（V4.9版本）
        smaller_dimension = min(video_width, video_height)
        resolution_ratio = smaller_dimension / 360.0

        # 基准值（360p）
        original_font_size = 28
        original_box_height = 60
        original_box_y = 170  # (400-60)/2
        original_corner_offset = 70

        # V4.9: 使用0.8缩放系数
        scale_factor = resolution_ratio * 0.8

        # 计算缩放后的值（完全复制tilted_label的逻辑）
        scaled_font_size = int(original_font_size * scale_factor)
        scaled_box_height = int(original_box_height * scale_factor)
        scaled_corner_offset = int(original_corner_offset * scale_factor)
        scaled_box_y = int((400 - scaled_box_height) / 2)  # 保持居中

        # 确保字体大小为偶数（FFmpeg渲染更稳定）
        scaled_font_size = scaled_font_size if scaled_font_size % 2 == 0 else scaled_font_size + 1
        scaled_corner_offset = scaled_corner_offset if scaled_corner_offset % 2 == 0 else scaled_corner_offset + 1

        print(f"\n🖼️  步骤1：生成倾斜角标PNG...")
        print(f"📹 视频分辨率: {video_width}x{video_height}")
        print(f"📐 V4.9定位算法: 修复投影计算 (canvas_half=200px)")
        print(f"📐 缩放系数: ratio={resolution_ratio:.2f}x, scale={scale_factor:.2f}x")
        print(f"📐 字体: {original_font_size}px -> {scaled_font_size}px")
        print(f"📐 条幅: {original_box_height}px -> {scaled_box_height}px")
        print(f"📐 留白: {original_corner_offset}px -> {scaled_corner_offset}px")

        tilted_png_path = None

        try:
            # 创建倾斜角标配置（传递已缩放的值，因为_generate_png不会自动缩放）
            tilted_config = TiltedLabelConfig(
                label_text=self.style.hot_drama.text,
                font_size=scaled_font_size,  # 已缩放
                label_color="red@0.95",
                text_color="white",
                position=self.config.hot_drama_position,  # 使用配置的位置
                box_height=scaled_box_height,  # 已缩放
                box_y=scaled_box_y,  # 已缩放
                corner_offset=scaled_corner_offset  # 已缩放
            )

            tilted_renderer = TiltedLabelRenderer(tilted_config)

            # 生成临时PNG
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tilted_png_path = tmp.name

            # 预渲染PNG
            tilted_renderer._generate_png(tilted_png_path)
            print(f"✅ 倾斜角标PNG生成完成")

            # 计算overlay位置
            x, y = tilted_renderer._get_overlay_position(video_width, video_height)
            print(f"📍 倾斜角标位置: x={x}, y={y}")

        except Exception as e:
            print(f"⚠️  倾斜角标生成失败: {e}")
            print(f"   将使用传统drawtext方式渲染热门短剧")
            tilted_png_path = None

        # ===== 构建滤镜链 =====
        print(f"\n🎨 步骤2：构建视频叠加滤镜链...")

        # 从overlay_styles导入TextLayer
        from .overlay_styles import TextLayer

        drawtext_filters = []

        # 剧名
        drama_title_layer = TextLayer(
            text=self.style.drama_title.text,
            font_size=drama_title_font_size,
            font_color=self.style.drama_title.font_color,
            font_alpha=self.style.drama_title.font_alpha,
            border_color=self.style.drama_title.border_color,
            border_width=self.style.drama_title.border_width,
            shadow_color=self.style.drama_title.shadow_color,
            shadow_x=self.style.drama_title.shadow_x,
            shadow_y=self.style.drama_title.shadow_y,
            x=drama_title_x_override if use_single_row else "(w-tw)/2",  # 单行左对齐，否则居中
            y=drama_title_y  # 动态Y位置
        )
        drawtext_filters.append(self._build_drawtext_filter(drama_title_layer, font_path))

        # 免责声明
        disclaimer_layer = TextLayer(
            text=self.style.disclaimer.text,
            font_size=disclaimer_font_size,
            font_color=self.style.disclaimer.font_color,
            font_alpha=self.style.disclaimer.font_alpha,
            border_color=self.style.disclaimer.border_color,
            border_width=self.style.disclaimer.border_width,
            shadow_color=self.style.disclaimer.shadow_color,
            shadow_x=self.style.disclaimer.shadow_x,
            shadow_y=self.style.disclaimer.shadow_y,
            x=disclaimer_x_override if use_single_row else "(w-tw)/2",  # 单行右对齐，否则居中
            y=disclaimer_y  # 动态Y位置
        )
        drawtext_filters.append(self._build_drawtext_filter(disclaimer_layer, font_path))

        # 组合drawtext滤镜
        if drawtext_filters:
            drawtext_filter_complex = ','.join(drawtext_filters)
        else:
            drawtext_filter_complex = None

        # FFmpeg命令
        if tilted_png_path and Path(tilted_png_path).exists():
            # 有倾斜角标PNG：两阶段叠加
            # 阶段1：overlay倾斜角标PNG
            # 阶段2：应用drawtext滤镜（剧名、免责声明）
            if drawtext_filter_complex:
                # 先overlay PNG，再应用drawtext滤镜
                filter_complex = f"[0:v][1:v]overlay=x={x}:y={y}[v1];[v1]{drawtext_filter_complex}"
                cmd = [
                    'ffmpeg',
                    '-y',  # 覆盖输出文件
                    '-i', input_video,
                    '-i', tilted_png_path,  # 第二个输入：PNG
                    '-filter_complex', filter_complex,
                    '-shortest',  # V17.5修复：确保输出时长以视频为准
                    '-c:a', 'copy',  # 音频直接复制，不重新编码
                    '-movflags', '+faststart',  # 优化Web播放
                    output_video
                ]
            else:
                # 只有overlay PNG
                filter_complex = f"[0:v][1:v]overlay=x={x}:y={y}"
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', input_video,
                    '-i', tilted_png_path,
                    '-filter_complex', filter_complex,
                    '-shortest',  # V17.5修复
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                    output_video
                ]
        elif drawtext_filter_complex:
            # 只有drawtext滤镜
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', input_video,
                '-vf', drawtext_filter_complex,
                '-shortest',  # V17.5修复：确保输出时长以视频为准
                '-c:a', 'copy',  # 音频直接复制，不重新编码
                '-movflags', '+faststart',  # 优化Web播放
                output_video
            ]
        else:
            # 没有滤镜，直接复制
            cmd = [
                'ffmpeg',
                '-y',
                '-i', input_video,
                '-shortest',  # V17.5修复
                '-c:a', 'copy',
                '-movflags', '+faststart',
                output_video
            ]

        print(f"📝 叠加内容:")
        if tilted_png_path and Path(tilted_png_path).exists():
            print(f"  1. 热门短剧（倾斜角标，右上角）- PNG预渲染，位置({x}, {y})")
        else:
            print(f"  1. 热门短剧（跳过，PNG生成失败或未启用）")
        print(f"  2. {self.style.drama_title.text}")
        print(f"  3. {self.style.disclaimer.text}")
        print(f"\n🔄 正在处理...\n")

        # 执行命令（带超时，超时 returncode=-1 → raise RuntimeError → 外层跳过该 clip）
        try:
            def _on_line(line: str):
                if "time=" in line and on_progress:
                    try:
                        on_progress(0.5)  # 简化处理
                    except:
                        pass

            returncode = run_popen_with_timeout(
                cmd,
                timeout=TimeoutConfig.FFMPEG_CLIP_RENDER,
                on_line=_on_line,
                log_prefix="花字叠加"
            )

            if returncode != 0:
                raise RuntimeError(
                    f"FFmpeg花字叠加失败 (返回码: {returncode})\n"
                    f"命令: {' '.join(cmd)}\n"
                )

            print(f"✅ 花字叠加完成")
            print(f"📁 输出文件: {output_video}\n")

            return output_video

        except Exception as e:
            raise RuntimeError(f"花字叠加处理失败: {e}")

        finally:
            # 清理临时PNG文件
            if tilted_png_path and Path(tilted_png_path).exists():
                try:
                    os.remove(tilted_png_path)
                    print(f"🗑️  已清理临时PNG: {tilted_png_path}")
                except Exception as e:
                    print(f"⚠️  清理临时PNG失败: {e}")


def apply_overlay_to_video(
    input_video: str,
    output_video: str,
    project_name: str,
    drama_title: str = "",
    style_id: Optional[str] = None,
    disclaimer: Optional[str] = None,
    enabled: bool = True,
    hot_drama_position: str = "top-right",
    on_progress: Optional[callable] = None
) -> str:
    """便捷函数：为单个视频应用花字叠加

    Args:
        input_video: 输入视频路径
        output_video: 输出视频路径
        project_name: 项目名称
        drama_title: 剧名（可选，默认使用project_name）
        style_id: 样式ID（可选，None表示自动选择）
        disclaimer: 免责声明（可选，None表示随机选择）
        enabled: 是否启用花字叠加
        hot_drama_position: 热门短剧角标位置（"top-left" 或 "top-right"）
        on_progress: 进度回调函数

    Returns:
        输出视频路径
    """
    config = OverlayConfig(
        enabled=enabled,
        style_id=style_id,
        project_name=project_name,
        drama_title=drama_title or project_name,
        disclaimer=disclaimer,
        hot_drama_position=hot_drama_position
    )

    renderer = VideoOverlayRenderer(config)
    return renderer.apply_overlay(input_video, output_video, on_progress)


def batch_apply_overlay(
    input_videos: List[str],
    output_dir: str,
    project_name: str,
    drama_title: str = "",
    style_id: Optional[str] = None,
    enabled: bool = True
) -> List[str]:
    """批量应用花字叠加

    Args:
        input_videos: 输入视频路径列表
        output_dir: 输出目录
        project_name: 项目名称
        drama_title: 剧名
        style_id: 样式ID（None表示自动选择）
        enabled: 是否启用花字叠加

    Returns:
        输出视频路径列表
    """
    output_paths = []

    # 创建渲染器（所有视频使用同一个样式）
    config = OverlayConfig(
        enabled=enabled,
        style_id=style_id,
        project_name=project_name,
        drama_title=drama_title or project_name
    )
    renderer = VideoOverlayRenderer(config)

    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 处理每个视频
    for i, input_video in enumerate(input_videos, 1):
        print(f"\n[{i}/{len(input_videos)}] 处理: {Path(input_video).name}")

        # 生成输出文件名（添加_带花字后缀）
        input_path = Path(input_video)
        output_filename = f"{input_path.stem}_带花字{input_path.suffix}"
        output_path = str(Path(output_dir) / output_filename)

        try:
            result_path = renderer.apply_overlay(input_video, output_path)
            output_paths.append(result_path)
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            continue

    print(f"\n✅ 批量处理完成: {len(output_paths)}/{len(input_videos)}个视频")
    return output_paths


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) < 3:
        print("用法: python video_overlay.py <输入视频> <输出视频> [项目名称] [剧名]")
        sys.exit(1)

    input_video = sys.argv[1]
    output_video = sys.argv[2]
    project_name = sys.argv[3] if len(sys.argv) > 3 else "测试项目"
    drama_title = sys.argv[4] if len(sys.argv) > 4 else project_name

    apply_overlay_to_video(
        input_video=input_video,
        output_video=output_video,
        project_name=project_name,
        drama_title=drama_title
    )
