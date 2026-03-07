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


@dataclass
class TextLayer:
    """单行文本配置"""
    text: str                    # 文本内容
    font_size: int               # 字体大小
    font_color: str              # 字体颜色（FFmpeg格式：#RRGGBB）
    font_alpha: float            # 字体透明度 (0.0-1.0)
    border_color: str            # 描边颜色
    border_width: float          # 描边宽度
    shadow_color: str            # 阴影颜色
    shadow_x: int                # 阴影X偏移
    shadow_y: int                # 阴影Y偏移
    x: str                       # X坐标位置（支持表达式，如"(w-tw)/2"）
    y: str                       # Y坐标位置（如"30"）
    rotation: float = 0.0        # 旋转角度（度数，正值为顺时针）
    display_duration: float = 0.0  # 显示时长（秒），0表示全程显示
    enable_animation: bool = False  # 是否启用动画
    animation_type: str = ""     # 动画类型："fade_in", "slide_in"


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
    "本故事纯属虚构请勿模仿",
    "本剧情纯属虚构如有雷同纯属巧合",
    "影视效果无不良引导请勿模仿",
    "纯属虚构请勿模仿"
]


# ==================== 预制样式定义 ====================

def _create_style_1_gold_luxury() -> OverlayStyle:
    """样式1：金色豪华风格"""
    return OverlayStyle(
        id="gold_luxury",
        name="金色豪华",
        description="金色渐变、粗体描边，适合高端短剧",

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=36,  # V2.0: 基准字体调大
            font_color="#FFD700",  # 金黄色
            font_alpha=1.0,
            border_color="#FF6600",  # V2.0: 调整为更明显的橙色
            border_width=1.5,  # V2.0: 减少描边宽度
            shadow_color="#000000",
            shadow_x=2,
            shadow_y=2,
            x="(w-tw)-20",  # 右上角
            y="50",
            rotation=-15,  # 向左倾斜15度，活泼效果
            enable_animation=True,
            animation_type="fade_in"
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#FF8C00",  # 深橙色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=4,
            shadow_y=4,
            x="30",  # 左上角
            y="50",
            enable_animation=True,
            animation_type="fade_in",
            display_duration=5.0
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#00BFFF",  # 深天蓝
            font_alpha=1.0,
            border_color="#00008B",  # 深蓝色
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="(w-tw)-30",
            y="45",
            enable_animation=True,
            animation_type="fade_in"
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#9400D3",  # 紫罗兰
            font_alpha=1.0,
            border_color="#4B0082",  # 靛青
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="30",
            y="48",
            enable_animation=True,
            animation_type="fade_in",
            display_duration=5.0
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#32CD32",  # 酸橙绿
            font_alpha=1.0,
            border_color="#006400",  # 深绿色
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="(w-tw)-30",
            y="52",
            enable_animation=True,
            animation_type="fade_in"
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#FFA500",  # 橙色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="30",
            y="50",
            enable_animation=True,
            animation_type="fade_in",
            display_duration=5.0
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#FFA500",  # 橙色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="(w-tw)-30",
            y="50",
            enable_animation=True,
            animation_type="fade_in"
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#C0C0C0",  # 银色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="30",
            y="48",
            enable_animation=True,
            animation_type="fade_in",
            display_duration=5.0
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#00CED1",  # 深青色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="(w-tw)-30",
            y="50",
            enable_animation=True,
            animation_type="fade_in"
        ),

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

        hot_drama=TextLayer(
            text="热门短剧",
            font_size=24,
            font_color="#FFD700",  # 金黄色（鲜艳活泼）
            font_alpha=1.0,
            border_color="#D2691E",  # 巧克力色描边
            border_width=2.0,
            shadow_color="#000000",
            shadow_x=3,
            shadow_y=3,
            x="30",
            y="50",
            enable_animation=True,
            animation_type="fade_in",
            display_duration=5.0
        ),

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
