#!/usr/bin/env python3
"""
分析实际的花字叠加代码，找出剧名位置问题的根源
"""
import sys
sys.path.insert(0, '/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from scripts.understand.video_overlay.overlay_styles import STYLE_REGISTRY

def analyze_all_styles():
    """分析所有样式的坐标配置"""
    print("="*80)
    print("杭州雷鸣AI短剧 - 花字叠加样式坐标分析")
    print("="*80)

    for style_id, style in STYLE_REGISTRY.items():
        print(f"\n{'='*80}")
        print(f"样式: {style.name} (ID: {style_id})")
        print(f"描述: {style.description}")
        print(f"{'='*80}")

        print(f"\n📍 剧名位置配置:")
        print(f"   Y坐标: {style.drama_title.y}")
        print(f"   X坐标: {style.drama_title.x}")

        # 解析Y坐标
        y_value = style.drama_title.y
        if y_value.startswith('h-'):
            offset = y_value.replace('h-', '')
            try:
                offset_val = int(offset)
                actual_y = 640 - offset_val
                print(f"   解析: y = h - {offset} = 640 - {offset} = {actual_y}")
                print(f"   位置: 距离底部{offset}像素（应该在底部）")
            except ValueError:
                print(f"   解析: 无法解析偏移量 '{offset}'")
        else:
            try:
                y_val = int(y_value)
                print(f"   解析: y = {y_val}")
                print(f"   位置: 距离顶部{y_val}像素（应该在顶部）")
            except ValueError:
                print(f"   解析: 表达式 '{y_value}'")

        print(f"\n🎨 文本样式:")
        print(f"   字体大小: {style.drama_title.font_size}")
        print(f"   字体颜色: {style.drama_title.font_color}")
        print(f"   描边: {style.drama_title.border_width}px - {style.drama_title.border_color}")

        print(f"\n🔥 热门短剧位置:")
        print(f"   X坐标: {style.hot_drama.x}")
        print(f"   Y坐标: {style.hot_drama.y}")
        if style.hot_drama.rotation != 0:
            print(f"   旋转: {style.hot_drama.rotation}度")

        print(f"\n⚠️  免责声明位置:")
        print(f"   Y坐标: {style.disclaimer.y}")
        print(f"   X坐标: {style.disclaimer.x}")

    print(f"\n{'='*80}")
    print("问题诊断")
    print(f"{'='*80}")

    # 检查所有样式的剧名位置
    bottom_titles = []
    top_titles = []

    for style_id, style in STYLE_REGISTRY.items():
        y_value = style.drama_title.y
        if y_value.startswith('h-'):
            bottom_titles.append((style.name, y_value))
        else:
            try:
                y_val = int(y_value)
                if y_val < 300:  # 中线以下
                    top_titles.append((style.name, y_value))
            except ValueError:
                top_titles.append((style.name, y_value))

    print(f"\n📊 统计结果:")
    print(f"   总样式数: {len(STYLE_REGISTRY)}")
    print(f"   底部显示: {len(bottom_titles)} 个")
    print(f"   顶部显示: {len(top_titles)} 个")

    if top_titles:
        print(f"\n⚠️  以下样式的剧名在顶部显示:")
        for name, y in top_titles:
            print(f"   - {name}: y={y}")

    if bottom_titles:
        print(f"\n✅ 以下样式的剧名在底部显示:")
        for name, y in bottom_titles:
            print(f"   - {name}: y={y}")

    print(f"\n{'='*80}")
    print("建议")
    print(f"{'='*80}")
    print(f"\n问题根源:")
    print(f"   所有样式的剧名都配置在顶部（y=120-130），")
    print(f"   而不是底部（y=h-45）！")
    print(f"\n修复方案:")
    print(f"   将所有样式的 drama_title.y 改为 'h-45' 或类似值")
    print(f"\n额外修复:")
    print(f"   同时修复 '热门短剧' 的颜色（当前红色系需更换）")


if __name__ == '__main__':
    analyze_all_styles()
