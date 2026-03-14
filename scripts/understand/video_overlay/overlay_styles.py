"""
花字叠加样式配置

定义了多种预制花字样式，包括：
- 字体大小、颜色、描边
- 位置配置
- 动画效果
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random


# ==================== BadgeStyle（放在此处以避免循环导入）====================

@dataclass
class BadgeStyle:
    """角标样式定义（20种多形态角标）"""
    id: str
    name: str
    shape: str          # tilted_banner / horizontal_banner / square_icon / triangle_corner / text_only / ink_stamp
    bg_color: str       # 背景色（HEX 或 "transparent"）
    text_color: str     # 文字色（HEX）
    border_color: str = ""
    border_width: int = 0
    position: str = ""   # "top-left" / "top-right" 固定；"" 表示每次随机
    extra: dict = field(default_factory=dict)


@dataclass
class TextLayer:
    """单行文本配置

    注意：V15.6中，部分属性会被video_overlay.py动态计算或覆盖：
    - font_size: 会被动态缩放算法覆盖
    - x: 会被硬编码为"(w-tw)/2"（居中）
    - y: 会被动态位置计算覆盖
    - font_color: drama_title会被随机化（白/淡紫）
    - border_color, border_width: drama_title会被强制覆盖

    V15.6更新：删除了animation相关字段（rotation、display_duration、enable_animation、animation_type）
    因为FFmpeg drawtext不支持这些功能。
    """
    text: str                    # 文本内容
    font_size: int = 28           # 字体大小（注意：会被动态缩放覆盖）
    font_color: str = "#FFFFFF"   # 字体颜色（FFmpeg格式：#RRGGBB）
    font_alpha: float = 1.0       # 字体透明度 (0.0-1.0)
    border_color: str = "#000000" # 描边颜色
    border_width: float = 1.0     # 描边宽度
    shadow_color: str = "#000000"  # 阴影颜色
    shadow_x: int = 1             # 阴影X偏移
    shadow_y: int = 1             # 阴影Y偏移
    x: str = "(w-tw)/2"           # X坐标位置（注意：会被硬编码覆盖）
    y: str = "30"                 # Y坐标位置（注意：会被动态计算覆盖）


@dataclass
class OverlayStyle:
    """花字叠加样式"""
    id: str                      # 样式ID
    name: str                    # 样式名称
    description: str             # 样式描述

    # 三行文本配置
    hot_drama: TextLayer         # "热门短剧"文本
    drama_title: TextLayer       # 剧名文本
    disclaimer: TextLayer        # 免责声明文本

    # 字体配置
    font_path: str = ""          # 字体文件路径（空字符串使用默认）

    # 附加配置
    z_index: int = 100           # 图层层级（越高越靠上）
    fade_in_duration: float = 0.5  # 淡入时长（秒）

    # 随机化配置
    randomize_hot_drama_position: bool = True  # 是否随机化"热门短剧"位置（左上/右上）
    randomize_display_duration: bool = True    # 是否随机化显示时长
    min_display_duration: float = 3.0         # 最小显示时长（秒）
    max_display_duration: float = 8.0         # 最大显示时长（秒）


# ==================== 免责声明文案库 ====================
DISCLAIMER_TEXTS = [
    "本故事纯属虚构 请勿模仿",
    "本剧情纯属虚构 如有雷同 纯属巧合",
    "影视效果无不良引导 请勿模仿",
    "纯属虚构 请勿模仿",
    "剧情纯属虚构  无不良导向",
    "本剧内容虚构 仅供娱乐参考",
    "故事情节虚构 切勿当真模仿",
    "纯属艺术创作 无不良导向"
]


# ==================== 预制样式定义 ====================

def _create_style_1_gold_luxury() -> OverlayStyle:
    """样式1：金色豪华风格"""
    return OverlayStyle(
        id="gold_luxury",
        name="金色豪华",
        description="金色渐变、粗体描边，适合高端短剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",  # 底部居中
            y="h-90",  # 距离底部90像素
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",  # 会被替换为随机免责声明
            font_size=18,  # V2.0: 基准字体调大
            font_color="#FFFF00",  # V2.0: 改为黄色，更明显
            font_alpha=0.9,  # V2.0: 提高透明度
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 适当增加描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",  # 底部居中
            y="h-50"
        )
    )


def _create_style_2_red_passion() -> OverlayStyle:
    """样式2：红色激情风格"""
    return OverlayStyle(
        id="red_passion",
        name="红色激情",
        description="鲜红色调、醒目突出，适合爱情/都市剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_3_blue_cool() -> OverlayStyle:
    """样式3：蓝色冷艳风格"""
    return OverlayStyle(
        id="blue_cool",
        name="蓝色冷艳",
        description="蓝色系、现代感强，适合悬疑/都市剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_4_purple_mystery() -> OverlayStyle:
    """样式4：紫色神秘风格"""
    return OverlayStyle(
        id="purple_mystery",
        name="紫色神秘",
        description="紫色调、神秘感强，适合玄幻/古装剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_5_green_fresh() -> OverlayStyle:
    """样式5：绿色清新风格"""
    return OverlayStyle(
        id="green_fresh",
        name="绿色清新",
        description="绿色系、清新自然，适合青春/校园剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_6_orange_vitality() -> OverlayStyle:
    """样式6：橙色活力风格"""
    return OverlayStyle(
        id="orange_vitality",
        name="橙色活力",
        description="橙色调、活力十足，适合喜剧/都市剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_7_pink_romantic() -> OverlayStyle:
    """样式7：粉色浪漫风格"""
    return OverlayStyle(
        id="pink_romantic",
        name="粉色浪漫",
        description="粉色调、浪漫温馨，适合爱情剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_8_silver_elegant() -> OverlayStyle:
    """样式8：银色优雅风格"""
    return OverlayStyle(
        id="silver_elegant",
        name="银色优雅",
        description="银色调、优雅大气，适合商务/都市剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_9_cyan_tech() -> OverlayStyle:
    """样式9：青色科技风格"""
    return OverlayStyle(
        id="cyan_tech",
        name="青色科技",
        description="青色调、科技感强，适合现代/都市剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


def _create_style_10_retro_brown() -> OverlayStyle:
    """样式10：复古棕色风格"""
    return OverlayStyle(
        id="retro_brown",
        name="复古棕色",
        description="棕色调、复古怀旧，适合年代/古装剧",

        hot_drama=TextLayer(text="热门短剧"),

        drama_title=TextLayer(
            text="《{title}》",
            font_size=28,  # V2.0: 基准字体调大
            font_color="#FFFFFF",  # V2.0: 改为白色，更清晰
            font_alpha=1.0,
            border_color="#000000",  # 黑色描边
            border_width=1.0,  # V2.0: 减少到1.0，不再太粗
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)/2",
            y="h-90"
        ),

        disclaimer=TextLayer(
            text="{disclaimer}",
            font_size=12,
            font_color="#FFFFFF",  # 白色（不显眼）
            font_alpha=0.7,  # 降低透明度使其更不显眼
            border_color="#808080",  # 灰色描边（确保可见）
            border_width=0.5,  # 很细的描边
            shadow_color="#000000",
            shadow_x=1,
            shadow_y=1,
            x="(w-tw)/2",
            y="h-50"
        )
    )


# ==================== 样式注册表 ====================

STYLE_REGISTRY: Dict[str, OverlayStyle] = {
    style.id: style
    for style in [
        _create_style_1_gold_luxury(),
        _create_style_2_red_passion(),
        _create_style_3_blue_cool(),
        _create_style_4_purple_mystery(),
        _create_style_5_green_fresh(),
        _create_style_6_orange_vitality(),
        _create_style_7_pink_romantic(),
        _create_style_8_silver_elegant(),
        _create_style_9_cyan_tech(),
        _create_style_10_retro_brown(),
    ]
}


def get_all_styles() -> List[OverlayStyle]:
    """获取所有可用样式"""
    return list(STYLE_REGISTRY.values())


def get_style(style_id: str) -> Optional[OverlayStyle]:
    """根据ID获取样式"""
    return STYLE_REGISTRY.get(style_id)


def get_random_style() -> OverlayStyle:
    """随机选择一个样式"""
    return random.choice(list(STYLE_REGISTRY.values()))


def get_random_disclaimer() -> str:
    """随机选择一条免责声明"""
    return random.choice(DISCLAIMER_TEXTS)


# ==================== 20种角标样式（BadgeStyle） ====================
# 需要 badge_renderer.py 中的 BadgeStyle dataclass
# 延迟导入避免循环

def _get_badge_styles():
    """返回15种 BadgeStyle 实例列表（删除了 ink/triangle 系列）

    位置规则：
    - banner 系列：固定 top-left（横幅形状只适合左上角）
    - square/text/tilted 系列：position 字段留空，由调用方随机选左/右
    """
    return [
        # ── A类：横向标签 (horizontal_banner) — 固定左上角 ─────────────────
        BadgeStyle(
            id="banner_red",
            name="红色横幅",
            shape="horizontal_banner",
            bg_color="#E84040",
            text_color="#FFFFFF",
            border_color="#FFFFFF",
            border_width=1,
            position="top-left",
        ),
        BadgeStyle(
            id="banner_orange",
            name="橙色横幅",
            shape="horizontal_banner",
            bg_color="#FF6B35",
            text_color="#FFFFFF",
            position="top-left",
        ),
        BadgeStyle(
            id="banner_gold",
            name="金色横幅",
            shape="horizontal_banner",
            bg_color="#FFD700",
            text_color="#1A1A1A",
            border_color="#1A1A1A",
            border_width=1,
            position="top-left",
        ),
        BadgeStyle(
            id="banner_dark",
            name="黑金横幅",
            shape="horizontal_banner",
            bg_color="#1A1A1A",
            text_color="#FFD700",
            border_color="#FFD700",
            border_width=1,
            position="top-left",
        ),
        BadgeStyle(
            id="banner_crimson",
            name="深红横幅",
            shape="horizontal_banner",
            bg_color="#CC0022",
            text_color="#FFFFFF",
            border_color="#FFFFFF",
            border_width=1,
            position="top-left",
        ),

        # ── B类：圆角方形 (square_icon) — 左右随机 ─────────────────────────
        BadgeStyle(
            id="square_redorange",
            name="橙红方块",
            shape="square_icon",
            bg_color="#E84040",
            text_color="#FFFFFF",
            border_color="#000000",
            border_width=2,
        ),
        BadgeStyle(
            id="square_darkred",
            name="深红方块",
            shape="square_icon",
            bg_color="#8B0000",
            text_color="#FFFFFF",
            border_color="#FFFFFF",
            border_width=2,
        ),
        BadgeStyle(
            id="square_gold",
            name="金色方块",
            shape="square_icon",
            bg_color="#FFD700",
            text_color="#1A1A1A",
            border_color="#000000",
            border_width=2,
        ),
        BadgeStyle(
            id="square_black",
            name="黑红方块",
            shape="square_icon",
            bg_color="#1A1A1A",
            text_color="#FF6666",   # 亮红色（更亮，提升对比度）
            border_color="#FF4444",
            border_width=2,
        ),

        # ── C类：纯文字描边 (text_only) — 左右随机 ─────────────────────────
        BadgeStyle(
            id="text_white_red",
            name="白字红边",
            shape="text_only",
            bg_color="transparent",
            text_color="#FFFFFF",
            border_color="#CC0000",
            border_width=4,
        ),
        BadgeStyle(
            id="text_red_black",
            name="红字黑边",
            shape="text_only",
            bg_color="transparent",
            text_color="#FF2222",
            border_color="#000000",
            border_width=4,
        ),
        BadgeStyle(
            id="text_gold_black",
            name="金字黑边",
            shape="text_only",
            bg_color="transparent",
            text_color="#FFD700",
            border_color="#000000",
            border_width=4,
        ),

        # ── D类：倾斜条幅有背景 (tilted_banner) — 固定左上角 ──────────────
        # 45度旋转方向决定只适合左上角；字体对齐原始 tilted_label.py（base 28px/60px）
        BadgeStyle(
            id="tilted_red",
            name="红色斜幅",
            shape="tilted_banner",
            bg_color="#CC0000",
            text_color="#FFFFFF",
            position="top-left",
        ),
        BadgeStyle(
            id="tilted_gold",
            name="金色斜幅",
            shape="tilted_banner",
            bg_color="#FFD700",
            text_color="#1A1A1A",
            position="top-left",
        ),
        BadgeStyle(
            id="tilted_black",
            name="黑橙斜幅",
            shape="tilted_banner",
            bg_color="#1A1A1A",
            text_color="#FF8C00",
            position="top-left",
        ),

        # ── E类：透明背景倾斜文字 (tilted_text) — 固定左上角 ──────────────
        # 无背景色条，只有文字＋厚描边斜45度；固定左上角
        BadgeStyle(
            id="tilted_text_white_red",
            name="白字红边斜字",
            shape="tilted_text",
            bg_color="transparent",
            text_color="#FFFFFF",
            border_color="#CC0000",
            border_width=6,
            position="top-left",
        ),
        BadgeStyle(
            id="tilted_text_red_black",
            name="红字黑边斜字",
            shape="tilted_text",
            bg_color="transparent",
            text_color="#FF2222",
            border_color="#000000",
            border_width=6,
            position="top-left",
        ),
        BadgeStyle(
            id="tilted_text_gold_black",
            name="金字黑边斜字",
            shape="tilted_text",
            bg_color="transparent",
            text_color="#FFD700",
            border_color="#000000",
            border_width=6,
            position="top-left",
        ),
        BadgeStyle(
            id="tilted_text_orange_dark",
            name="橙字深边斜字",
            shape="tilted_text",
            bg_color="transparent",
            text_color="#FF8C00",
            border_color="#1A1A1A",
            border_width=6,
            position="top-left",
        ),
    ]


# 角标文字候选
BADGE_TEXT_OPTIONS = ["热门短剧", "爆款短剧", "必看短剧"]


def get_all_badge_styles():
    """返回所有角标样式"""
    return _get_badge_styles()


def get_random_badge_style():
    """随机选择一种角标样式"""
    styles = _get_badge_styles()
    return random.choice(styles)


def get_random_badge_text() -> str:
    """随机选择角标文字"""
    return random.choice(BADGE_TEXT_OPTIONS)
