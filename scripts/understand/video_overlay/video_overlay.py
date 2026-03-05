"""
视频花字叠加核心模块

基于FFmpeg实现视频花字叠加功能

技术方案：
- 使用FFmpeg的drawtext滤镜叠加文本
- 支持自定义字体、颜色、描边、阴影
- 支持多行文本独立配置
- 避免遮挡原字幕（位置可配置）
- 项目级样式统一（缓存项目样式选择）

依赖：
- FFmpeg（支持drawtext滤镜，需要启用--enable-libfreetype）
- 可选：中文字体文件（用于更好的中文显示）

作者：杭州雷鸣AI短剧项目
版本：V1.0
"""
import os
import json
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from .overlay_styles import (
    OverlayStyle,
    TextLayer,
    get_style,
    get_random_style,
    get_random_disclaimer,
    DISCLAIMER_TEXTS
)


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

        print(f"🎲 热门短剧显示模式: 左右交替显示（每10秒切换位置）")

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

    def _build_alternating_enable(self, left: bool) -> str:
        """构建热门短剧左右交替显示的enable表达式

        Args:
            left: True表示左上角层，False表示右上角层

        Returns:
            enable表达式字符串
        """
        enable_parts = []

        if left:
            # 左上角层：0-10秒, 40-50秒, 80-90秒...
            for cycle_start in range(0, 300, 40):  # 40秒一个完整周期
                enable_parts.append(f'between(t,{cycle_start},{cycle_start+10})')
        else:
            # 右上角层：20-30秒, 60-70秒, 100-110秒...
            for cycle_start in range(20, 300, 40):
                enable_parts.append(f'between(t,{cycle_start},{cycle_start+10})')

        return '+'.join(enable_parts)

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
        # 优先使用custom_enable（用于热门短剧左右交替）
        if custom_enable:
            params['enable'] = custom_enable
        # 特殊处理热门短剧：显示50%的时间（10秒显示+10秒隐藏循环）
        elif layer == self.style.hot_drama:
            # 构建循环显示表达式：显示10秒，隐藏10秒，循环往复
            # between(t,0,10)+between(t,20,30)+between(t,40,50)+between(t,60,70)+...
            enable_parts = []
            for cycle_start in range(0, 300, 20):  # 支持最长300秒的视频
                enable_parts.append(f'between(t,{cycle_start},{cycle_start+10})')
            enable_expr = '+'.join(enable_parts)
            params['enable'] = enable_expr  # format_param_value会自动添加单引号
            print(f"📺 热门短剧显示模式: 循环显示（10秒显示+10秒隐藏）")
        # 优先使用display_duration，如果没有则使用淡入动画
        elif hasattr(layer, 'display_duration') and layer.display_duration > 0:
            # 使用display_duration: 在指定时间段内显示
            params['enable'] = f'between(t,0,{layer.display_duration})'
        elif layer.enable_animation and layer.animation_type == "fade_in":
            params['enable'] = f'between(t,0,{self.style.fade_in_duration})'
            # 使用alpha表达式实现淡入
            # 注意：这里简化处理，实际淡入效果可能需要更复杂的表达式

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
        on_progress: Optional[callable] = None
    ) -> str:
        """在视频上应用花字叠加

        Args:
            input_video: 输入视频路径
            output_video: 输出视频路径
            on_progress: 进度回调函数

        Returns:
            输出视频路径
        """
        if not self.config.enabled:
            print("⚠️  花字叠加未启用，跳过处理")
            return input_video

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

        # 构建滤镜链（四个drawtext滤镜：热门短剧左+右，剧名，免责声明）
        filters = []

        # 创建两个热门短剧层，左右交替显示
        # 左上角层：0-10秒, 40-50秒, 80-90秒...显示
        hot_drama_left = self.style.hot_drama
        hot_drama_left.x = "20"
        left_enable = self._build_alternating_enable(left=True)
        filters.append(self._build_drawtext_filter(hot_drama_left, font_path, custom_enable=left_enable))

        # 右上角层：20-30秒, 60-70秒, 100-110秒...显示
        hot_drama_right = self.style.hot_drama
        hot_drama_right.x = "(w-tw)-20"
        right_enable = self._build_alternating_enable(left=False)
        filters.append(self._build_drawtext_filter(hot_drama_right, font_path, custom_enable=right_enable))

        filters.append(self._build_drawtext_filter(self.style.drama_title, font_path))
        filters.append(self._build_drawtext_filter(self.style.disclaimer, font_path))

        # 组合滤镜（使用逗号分隔多个滤镜）
        filter_complex = ','.join(filters)

        # FFmpeg命令
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', input_video,
            '-vf', filter_complex,
            '-c:a', 'copy',  # 音频直接复制，不重新编码
            '-movflags', '+faststart',  # 优化Web播放
            output_video
        ]

        print(f"📝 叠加内容:")
        print(f"  1. 热门短剧（左上角）- 奇数时段显示")
        print(f"  2. 热门短剧（右上角）- 偶数时段显示")
        print(f"  3. {self.style.drama_title.text}")
        print(f"  4. {self.style.disclaimer.text}")
        print(f"\n🔄 正在处理...\n")

        # 执行命令
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # 实时输出日志
            for line in process.stdout:
                # 解析进度（FFmpeg的time=字段）
                if "time=" in line and on_progress:
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        # 简单的进度估计
                        if on_progress:
                            on_progress(0.5)  # 简化处理
                    except:
                        pass

            process.wait()

            if process.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg花字叠加失败 (返回码: {process.returncode})\n"
                    f"命令: {' '.join(cmd)}\n"
                )

            print(f"✅ 花字叠加完成")
            print(f"📁 输出文件: {output_video}\n")

            return output_video

        except Exception as e:
            raise RuntimeError(f"花字叠加处理失败: {e}")


def apply_overlay_to_video(
    input_video: str,
    output_video: str,
    project_name: str,
    drama_title: str = "",
    style_id: Optional[str] = None,
    disclaimer: Optional[str] = None,
    enabled: bool = True,
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
        on_progress: 进度回调函数

    Returns:
        输出视频路径
    """
    config = OverlayConfig(
        enabled=enabled,
        style_id=style_id,
        project_name=project_name,
        drama_title=drama_title or project_name,
        disclaimer=disclaimer
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
