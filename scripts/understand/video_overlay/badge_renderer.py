"""
角标渲染器 - 20种多形态角标样式

支持6种形态：
- tilted_banner: 45度倾斜条幅（现有样式扩展）
- horizontal_banner: 横向标签（带尖角/切角）
- square_icon: 圆角方形（类App图标）
- triangle_corner: 三角贴角
- text_only: 无背景纯文字（厚描边）
- ink_stamp: 水墨/印章风

全部用 PIL 预渲染 PNG，再由调用方用 FFmpeg overlay 叠加到视频。
动态缩放：基于视频较小边 / 360 的比例。

作者：杭州雷鸣AI短剧项目
"""
import os
import math
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

# PIL 可选依赖
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# BadgeStyle 定义在 overlay_styles 中（避免循环导入）
# 调用方传入 BadgeStyle 实例，badge_renderer 只负责渲染


# ==================== 全局常量 ====================

BADGE_TEXT_OPTIONS = ["热门短剧", "爆款短剧", "必看短剧"]

# 系统字体候选列表
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def _find_font(size: int) -> Optional["ImageFont.FreeTypeFont"]:
    """查找并加载中文字体"""
    if not PIL_AVAILABLE:
        return None
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _hex_to_rgb(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """将 '#RRGGBB' 转换为 (R,G,B,A)"""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b, alpha)
    return (200, 50, 50, alpha)


def _scale(value: int, ratio: float) -> int:
    """按分辨率比例缩放整数值"""
    return max(4, int(value * ratio))


# ==================== BadgeRenderer ====================

class BadgeRenderer:
    """
    角标 PNG 渲染器

    使用方式：
        renderer = BadgeRenderer()
        png_path = renderer.render(style, "热门短剧", 360, 640)
        # 返回临时 PNG 路径，由调用方 overlay 到视频后删除
    """

    def __init__(self):
        if not PIL_AVAILABLE:
            raise ImportError(
                "badge_renderer 需要 Pillow 库。请运行: pip install Pillow"
            )

    # ------------------------------------------------------------------ #
    #  公共入口
    # ------------------------------------------------------------------ #

    def render(
        self,
        style: Any,
        text: str,
        video_width: int,
        video_height: int,
        output_path: Optional[str] = None,
    ) -> str:
        """
        渲染角标为 PNG 文件。

        Args:
            style: 角标样式
            text:  显示文字（如"热门短剧"）
            video_width, video_height: 视频分辨率（用于动态缩放）
            output_path: 可选输出路径；不填则自动创建临时文件

        Returns:
            PNG 文件路径
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            output_path = tmp.name
            tmp.close()

        # 计算分辨率缩放比例（基于较小边 / 360）
        smaller = min(video_width, video_height)
        ratio = smaller / 360.0

        dispatch = {
            "tilted_banner":     self._render_tilted_banner,
            "tilted_text":       self._render_tilted_text,
            "horizontal_banner": self._render_horizontal_banner,
            "square_icon":       self._render_square_icon,
            "triangle_corner":   self._render_triangle_corner,
            "text_only":         self._render_text_only,
            "ink_stamp":         self._render_ink_stamp,
        }
        func = dispatch.get(style.shape, self._render_tilted_banner)
        func(style, text, ratio, output_path)
        return output_path

    # ------------------------------------------------------------------ #
    #  A. 倾斜条幅 (tilted_banner)
    # ------------------------------------------------------------------ #

    def _render_tilted_banner(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """45度倾斜条幅，对齐原始 tilted_label.py 的尺寸（base 28px字体/60px条幅）"""
        canvas = 400   # 固定画布，不随分辨率变化
        # 与原始 tilted_label.py 保持一致：base 28px，scale_factor = ratio * 0.8
        scale_factor = ratio * 0.8
        font_size = int(28 * scale_factor)
        font_size = font_size if font_size % 2 == 0 else font_size + 1
        box_h = int(60 * scale_factor)
        box_y = (canvas - box_h) // 2

        img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba   = _hex_to_rgb(style.bg_color, alpha=242)   # ~95% 透明度
        text_rgba = _hex_to_rgb(style.text_color)

        # 绘制横向色条
        draw.rectangle([0, box_y, canvas, box_y + box_h], fill=bg_rgba)

        # 描边（如果有）
        if style.border_width > 0 and style.border_color:
            bw = style.border_width
            bc = _hex_to_rgb(style.border_color)
            draw.rectangle([0, box_y - bw, canvas, box_y],           fill=bc)
            draw.rectangle([0, box_y + box_h, canvas, box_y + box_h + bw], fill=bc)

        # 文字
        font = _find_font(font_size)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        else:
            tw, th = font_size * len(text), font_size + 4
        tx = (canvas - tw) // 2
        ty = box_y + (box_h - th) // 2

        # 黑色阴影
        draw.text((tx + 1, ty + 1), text, font=font, fill=(0, 0, 0, 200))
        draw.text((tx, ty), text, font=font, fill=text_rgba)

        # 旋转 45 度（position 由调用方选择，这里统一不翻转）
        img_rot = img.rotate(45, expand=False, resample=Image.BICUBIC)
        img_rot.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  A2. 透明背景倾斜文字 (tilted_text)
    # ------------------------------------------------------------------ #

    def _render_tilted_text(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """透明背景 + 纯文字 + 厚描边，旋转45度。
        无色条背景，只有文字本身斜过来。
        使用与 tilted_banner 相同的 400x400 画布，overlay 定位逻辑共用。
        """
        canvas = 400
        scale_factor = ratio * 0.8
        font_size = int(32 * scale_factor)          # 比 tilted_banner 稍大（无背景需更显眼）
        font_size = font_size if font_size % 2 == 0 else font_size + 1
        bw = max(3, int(6 * scale_factor))          # 描边宽度

        font = _find_font(font_size)
        img  = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 测量文字
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        else:
            tw, th = font_size * len(text), font_size + 4

        tx = (canvas - tw) // 2
        ty = (canvas - th) // 2

        text_rgba = _hex_to_rgb(style.text_color)

        # 厚描边（圆形扩散）
        if style.border_color:
            bc = _hex_to_rgb(style.border_color)
            for dx in range(-bw, bw + 1):
                for dy in range(-bw, bw + 1):
                    if dx * dx + dy * dy <= bw * bw:
                        draw.text((tx + dx, ty + dy), text, font=font, fill=bc)

        # 主文字
        draw.text((tx, ty), text, font=font, fill=text_rgba)

        # 旋转45度，透明背景保持
        img_rot = img.rotate(45, expand=False, resample=Image.BICUBIC)
        img_rot.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  B. 横向标签 (horizontal_banner)
    # ------------------------------------------------------------------ #

    def _render_horizontal_banner(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """横向标签，右侧带斜切尖角"""
        font_size = _scale(18, ratio * 0.85)
        pad_x     = _scale(14, ratio)
        pad_y     = _scale(8, ratio)
        tip_w     = _scale(20, ratio)   # 尖角宽度

        font = _find_font(font_size)
        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        if font:
            bbox = dummy_draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        else:
            tw, th = font_size * len(text), font_size + 4

        w = tw + pad_x * 2 + tip_w
        h = th + pad_y * 2

        img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba   = _hex_to_rgb(style.bg_color, alpha=230)
        text_rgba = _hex_to_rgb(style.text_color)

        # 矩形主体（不含尖角区域）
        draw.rectangle([0, 0, w - tip_w, h], fill=bg_rgba)

        # 右侧斜切尖角（三角形）
        draw.polygon(
            [(w - tip_w, 0), (w, h // 2), (w - tip_w, h)],
            fill=bg_rgba
        )

        # 边框
        if style.border_width > 0 and style.border_color:
            bw = style.border_width
            bc = _hex_to_rgb(style.border_color, 220)
            draw.rectangle([0, 0, w - tip_w, h], outline=bc, width=bw)

        # 文字
        tx = pad_x
        ty = pad_y
        if style.border_width > 0 and style.border_color:
            bc = _hex_to_rgb(style.border_color)
            draw.text((tx + 1, ty + 1), text, font=font, fill=(0, 0, 0, 150))
        draw.text((tx, ty), text, font=font, fill=text_rgba)

        img.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  C. 圆角方形 (square_icon)
    # ------------------------------------------------------------------ #

    def _render_square_icon(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """圆角方形，上行大字 + 下行小字（类 App 图标）"""
        # 拆分文字（如"热门短剧" → "热门" + "短剧"）
        mid = len(text) // 2
        line1 = text[:mid]
        line2 = text[mid:]

        size     = _scale(80, ratio * 0.9)
        radius   = _scale(14, ratio * 0.9)
        font_big = _find_font(_scale(24, ratio * 0.9))
        font_sml = _find_font(_scale(14, ratio * 0.9))

        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba   = _hex_to_rgb(style.bg_color, alpha=235)
        text_rgba = _hex_to_rgb(style.text_color)

        # 圆角矩形
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=bg_rgba)

        # 描边
        if style.border_width > 0 and style.border_color:
            bc = _hex_to_rgb(style.border_color, 220)
            draw.rounded_rectangle(
                [0, 0, size - 1, size - 1],
                radius=radius, outline=bc, width=style.border_width
            )

        # 第一行大字
        if font_big:
            bb = draw.textbbox((0, 0), line1, font=font_big)
            tw1, th1 = bb[2] - bb[0], bb[3] - bb[1]
        else:
            tw1, th1 = len(line1) * 20, 22
        x1 = (size - tw1) // 2
        y1 = size // 2 - th1 - 2

        # 第二行小字
        if font_sml:
            bb = draw.textbbox((0, 0), line2, font=font_sml)
            tw2, th2 = bb[2] - bb[0], bb[3] - bb[1]
        else:
            tw2, th2 = len(line2) * 12, 14
        x2 = (size - tw2) // 2
        y2 = size // 2 + 2

        # 阴影 + 文字
        shadow = (0, 0, 0, 150)
        draw.text((x1 + 1, y1 + 1), line1, font=font_big, fill=shadow)
        draw.text((x1, y1), line1, font=font_big, fill=text_rgba)
        draw.text((x2 + 1, y2 + 1), line2, font=font_sml, fill=shadow)
        draw.text((x2, y2), line2, font=font_sml, fill=text_rgba)

        img.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  D. 三角贴角 (triangle_corner)
    # ------------------------------------------------------------------ #

    def _render_triangle_corner(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """等腰直角三角形贴在角落，文字沿斜边排列"""
        tri_size  = _scale(100, ratio * 0.9)
        font_size = _scale(14, ratio * 0.8)
        font      = _find_font(font_size)

        img  = Image.new("RGBA", (tri_size, tri_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba   = _hex_to_rgb(style.bg_color, alpha=230)
        text_rgba = _hex_to_rgb(style.text_color)

        # 上-左三角（左上贴角）
        draw.polygon([(0, 0), (tri_size, 0), (0, tri_size)], fill=bg_rgba)

        # 辅助底色（深色）
        if style.extra.get("aux_color"):
            aux = _hex_to_rgb(style.extra["aux_color"], 180)
            aux_size = _scale(20, ratio * 0.9)
            draw.polygon(
                [(0, 0), (aux_size, 0), (0, aux_size)],
                fill=aux
            )

        # 文字沿45度斜线排列
        if font:
            # 旋转 -45 度写文字
            txt_img = Image.new("RGBA", (tri_size * 2, tri_size * 2), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            bb = txt_draw.textbbox((0, 0), text, font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            cx = txt_img.width // 2 - tw // 2
            cy = txt_img.height // 2 - th // 2

            # 描边
            if style.border_color:
                bc = _hex_to_rgb(style.border_color)
                for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
                    txt_draw.text((cx+dx, cy+dy), text, font=font, fill=bc)
            txt_draw.text((cx, cy), text, font=font, fill=text_rgba)

            txt_rot = txt_img.rotate(-45, resample=Image.BICUBIC)
            # 粘贴到三角区域中部
            paste_x = -txt_img.width // 4
            paste_y = -txt_img.height // 4
            img.paste(txt_rot, (paste_x, paste_y), txt_rot)

        img.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  E. 纯文字描边 (text_only)
    # ------------------------------------------------------------------ #

    def _render_text_only(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """无背景，仅厚描边文字"""
        font_size = _scale(26, ratio * 0.9)
        bw        = max(2, _scale(style.border_width or 3, ratio * 0.7))
        font      = _find_font(font_size)

        dummy_img  = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        if font:
            bbox = dummy_draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        else:
            tw, th = font_size * len(text), font_size + 4

        pad = bw + 4
        w   = tw + pad * 2
        h   = th + pad * 2

        img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        text_rgba = _hex_to_rgb(style.text_color)

        # 厚描边：多偏移绘制
        if style.border_color:
            bc = _hex_to_rgb(style.border_color)
            for dx in range(-bw, bw + 1):
                for dy in range(-bw, bw + 1):
                    if dx * dx + dy * dy <= bw * bw:
                        draw.text((pad + dx, pad + dy), text, font=font, fill=bc)

        # 主文字
        draw.text((pad, pad), text, font=font, fill=text_rgba)

        img.save(output_path, "PNG")

    # ------------------------------------------------------------------ #
    #  F. 水墨印章 (ink_stamp)
    # ------------------------------------------------------------------ #

    def _render_ink_stamp(
        self, style: Any, text: str, ratio: float, output_path: str
    ) -> None:
        """水墨/印章风格 - 不规则方形背景 + 做旧文字"""
        size      = _scale(90, ratio * 0.9)
        font_size = _scale(16, ratio * 0.85)
        font      = _find_font(font_size)

        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba   = _hex_to_rgb(style.bg_color, alpha=220)
        text_rgba = _hex_to_rgb(style.text_color)

        # 不规则正方形（用多边形模拟笔刷感）
        jitter = max(2, _scale(4, ratio))
        corners = [
            (jitter,      jitter),
            (size - jitter * 2, jitter // 2),
            (size - jitter,     size - jitter),
            (jitter // 2, size - jitter * 2),
        ]
        draw.polygon(corners, fill=bg_rgba)

        # 内部文字（分两行）
        mid = len(text) // 2
        lines = [text[:mid], text[mid:]] if len(text) >= 3 else [text]

        line_h = font_size + 2
        total_h = line_h * len(lines)
        y_start = (size - total_h) // 2

        for i, line in enumerate(lines):
            if font:
                bb = draw.textbbox((0, 0), line, font=font)
                tw = bb[2] - bb[0]
            else:
                tw = font_size * len(line)
            tx = (size - tw) // 2
            ty = y_start + i * line_h
            # 轻微阴影制造做旧感
            draw.text((tx + 1, ty + 1), line, font=font, fill=(0, 0, 0, 100))
            draw.text((tx, ty), line, font=font, fill=text_rgba)

        # 轻微高斯模糊模拟油墨渗透
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        img.save(output_path, "PNG")


# ==================== 计算 overlay 位置 ====================

def get_badge_overlay_position(
    png_path: str,
    video_width: int,
    video_height: int,
    position: str,
    shape: str,
    ratio: float,
) -> Tuple[int, int]:
    """
    计算角标 PNG 在视频上的 overlay 位置 (x, y)。

    对于 tilted_banner：沿用 tilted_label.py 的 canvas_half 算法
    对于其他形态：直接贴在角落，留出少量边距
    """
    margin = max(8, int(12 * ratio))

    # 获取 PNG 实际尺寸
    try:
        with Image.open(png_path) as png:
            pw, ph = png.size
    except Exception:
        pw, ph = 80, 80

    if shape in ("tilted_banner", "tilted_text"):
        # tilted_banner / tilted_text 画布固定 400，用 canvas_half 定位
        canvas_half = 200
        corner_offset = max(8, int(70 * ratio * 0.8))
        corner_offset = corner_offset if corner_offset % 2 == 0 else corner_offset + 1
        if position == "top-right":
            x = video_width - corner_offset - canvas_half
            y = corner_offset - canvas_half
        else:
            x = corner_offset - canvas_half
            y = corner_offset - canvas_half
    else:
        if position == "top-right":
            x = video_width - pw - margin
            y = margin
        else:
            x = margin
            y = margin

    return x, y
