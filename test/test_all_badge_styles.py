"""
测试：批量生成20种角标样式预览PNG

用法：
    python test/test_all_badge_styles.py

输出：
    test/output/badges/<style_id>.png   每种样式一张预览图
    test/output/badges/_all_preview.png  拼图：所有样式排列展示

依赖：Pillow
"""
import sys
import os
import random
import importlib.util

# ── 直接加载模块文件，完全绕开有问题的 scripts/understand/__init__.py ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module(name: str, rel_path: str):
    full = os.path.join(ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# 1. badge_renderer（无内部依赖）
br_mod = load_module(
    "scripts.understand.video_overlay.badge_renderer",
    "scripts/understand/video_overlay/badge_renderer.py",
)

# 2. overlay_styles（内部 _get_badge_styles 不再做相对导入）
os_mod = load_module(
    "scripts.understand.video_overlay.overlay_styles",
    "scripts/understand/video_overlay/overlay_styles.py",
)

BadgeRenderer       = br_mod.BadgeRenderer
get_all_badge_styles = os_mod.get_all_badge_styles
BADGE_TEXT_OPTIONS   = os_mod.BADGE_TEXT_OPTIONS

from pathlib import Path

OUTPUT_DIR   = Path(ROOT) / "test" / "output" / "badges"
VIDEO_WIDTH  = 360
VIDEO_HEIGHT = 640


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        renderer = BadgeRenderer()
    except ImportError as e:
        print(f"❌ 需要 Pillow: pip install Pillow\n{e}")
        sys.exit(1)

    styles = get_all_badge_styles()
    print(f"🎨 共 {len(styles)} 种角标样式，开始生成...\n")

    generated = []
    for style in styles:
        text = random.choice(BADGE_TEXT_OPTIONS)
        out  = str(OUTPUT_DIR / f"{style.id}.png")

        try:
            renderer.render(style, text, VIDEO_WIDTH, VIDEO_HEIGHT, output_path=out)
            size = os.path.getsize(out)
            print(f"  ✅ [{style.id}] {style.name} ({style.shape}) → {size} bytes")
            generated.append(out)
        except Exception as e:
            import traceback
            print(f"  ❌ [{style.id}] {style.name}: {e}")
            traceback.print_exc()

    print(f"\n🖼️  成功生成: {len(generated)}/{len(styles)}")

    _make_grid(generated, OUTPUT_DIR / "_all_preview.png")
    print(f"📋 总览图: {OUTPUT_DIR / '_all_preview.png'}")


def _make_grid(png_paths: list, output_path, cols: int = 5) -> None:
    """将所有角标 PNG 拼成网格图"""
    try:
        from PIL import Image
    except ImportError:
        return

    images = []
    for p in png_paths:
        try:
            images.append(Image.open(p).convert("RGBA"))
        except Exception:
            pass

    if not images:
        return

    cell_w = max(img.width  for img in images)
    cell_h = max(img.height for img in images)
    rows   = (len(images) + cols - 1) // cols

    grid = Image.new(
        "RGBA",
        (cols * cell_w + (cols + 1) * 4, rows * cell_h + (rows + 1) * 4),
        (40, 40, 40, 255)
    )

    for i, img in enumerate(images):
        col = i % cols
        row = i // cols
        x   = col * (cell_w + 4) + 4
        y   = row * (cell_h + 4) + 4
        # 居中粘贴（不同形态尺寸可能不同）
        cx  = x + (cell_w - img.width)  // 2
        cy  = y + (cell_h - img.height) // 2
        grid.paste(img, (cx, cy), img)

    grid.save(str(output_path), "PNG")


if __name__ == "__main__":
    main()
