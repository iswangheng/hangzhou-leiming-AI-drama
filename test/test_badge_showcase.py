"""
test_badge_showcase.py — 22种角标样式截图汇总展示

用法：
    python test/test_badge_showcase.py

输出：
    test/output/showcase/<style_id>.jpg   每种样式单独截图（540px宽）
    test/output/showcase/_all_styles.jpg  4列汇总大图
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# 确保能 import 项目模块
# 把 scripts/understand/ 路径加入 sys.path，让 video_overlay 作为顶级包导入
# 这样绕开 scripts/understand/__init__.py 触发的其他模块的依赖问题
_root = Path(__file__).parent.parent
_vo_pkg_parent = _root / "scripts" / "understand"
sys.path.insert(0, str(_vo_pkg_parent))
sys.path.insert(0, str(_root))

# 现在 video_overlay 是顶级包，可以直接导入
from video_overlay.overlay_styles import (
    get_all_badge_styles,
    get_random_disclaimer,
)
from video_overlay.video_overlay import apply_overlay_to_video

# ── 配置 ──────────────────────────────────────────────────────────────────────
SRC_VIDEO_1080 = "test/output/overlay_test/烈日重生_1080p_input.mp4"
SRC_VIDEO_360  = "test/output/overlay_test/锦庭别后意_360p_input.mp4"
SHOWCASE_DIR   = Path("test/output/showcase")
DRAMA_TITLE    = "烈日重生"
PROJECT_NAME   = "烈日重生"
CAPTURE_SEC    = 3          # 截第几秒的帧
THUMB_WIDTH    = 540        # 缩略图宽度（px）
GRID_COLS      = 4          # 汇总图列数
LABEL_HEIGHT   = 40         # 每格标注文字区高度（px）
# ──────────────────────────────────────────────────────────────────────────────


def pick_source_video() -> str:
    """优先用1080p，备用360p；都不存在则报错。"""
    for path in [SRC_VIDEO_1080, SRC_VIDEO_360]:
        if Path(path).exists():
            print(f"✅ 使用源视频: {path}")
            return path
    raise FileNotFoundError(
        f"找不到源视频，请先准备以下任一文件:\n"
        f"  {SRC_VIDEO_1080}\n"
        f"  {SRC_VIDEO_360}"
    )


def capture_frame(video_path: str, output_jpg: str, sec: int = 3) -> bool:
    """用 ffmpeg 截取指定秒数的帧，缩放到 THUMB_WIDTH 宽。"""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(sec),
        "-i", video_path,
        "-frames:v", "1",
        "-vf", f"scale={THUMB_WIDTH}:-2",
        output_jpg
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def build_label_image(text: str, width: int, height: int, output_png: str) -> bool:
    """用 ffmpeg drawtext 生成深灰底白字标注图（label bar）。"""
    # 转义冒号和单引号
    safe_text = text.replace("'", "").replace(":", " ")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=#333333:s={width}x{height}",
        "-frames:v", "1",
        "-vf", f"drawtext=text='{safe_text}':fontsize=14:fontcolor=white:x=(w-tw)/2:y=(h-th)/2",
        output_png
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def stack_thumb_and_label(thumb_jpg: str, label_png: str, output_jpg: str) -> bool:
    """将截图和标注竖向拼接成一格。"""
    cmd = [
        "ffmpeg", "-y",
        "-i", thumb_jpg,
        "-i", label_png,
        "-filter_complex", "[0:v][1:v]vstack",
        output_jpg
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def build_grid(cell_paths: list, output_jpg: str, cols: int = 4) -> bool:
    """将多张图片拼成 cols 列的网格汇总图。"""
    # 填充到列数的整倍数
    while len(cell_paths) % cols != 0:
        cell_paths.append(cell_paths[-1])   # 复制最后一格填充空位

    rows = len(cell_paths) // cols

    # 构建 filter_complex：先每 cols 张 hstack，再全部 vstack
    inputs = "".join(f"-i {p} " for p in cell_paths)
    filter_parts = []
    row_labels = []
    for r in range(rows):
        row_inputs = "".join(f"[{r * cols + c}:v]" for c in range(cols))
        row_label  = f"row{r}"
        filter_parts.append(f"{row_inputs}hstack=inputs={cols}[{row_label}]")
        row_labels.append(f"[{row_label}]")

    all_rows = "".join(row_labels)
    filter_parts.append(f"{all_rows}vstack=inputs={rows}")
    filter_complex = ";".join(filter_parts)

    cmd = (
        ["ffmpeg", "-y"]
        + [item for p in cell_paths for item in ("-i", p)]
        + ["-filter_complex", filter_complex, output_jpg]
    )
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"  ⚠️  网格拼接stderr: {result.stderr.decode()[:500]}")
    return result.returncode == 0


def main():
    src_video = pick_source_video()
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)

    styles = get_all_badge_styles()
    print(f"\n📦 共 {len(styles)} 种角标样式，开始渲染...\n")

    cell_paths = []   # 每格（截图+标注）路径

    for i, style in enumerate(styles, 1):
        print(f"[{i:02d}/{len(styles)}] {style.id} — {style.name}")

        # 1. 渲染带花字的视频（临时文件）
        tmp_video = SHOWCASE_DIR / f"_tmp_{style.id}.mp4"
        try:
            apply_overlay_to_video(
                input_video=src_video,
                output_video=str(tmp_video),
                project_name=PROJECT_NAME,
                drama_title=DRAMA_TITLE,
                force_badge_style=style,
            )
        except Exception as e:
            print(f"  ❌ 渲染失败: {e}")
            continue

        # 2. 截帧 → 缩略图
        thumb_jpg = SHOWCASE_DIR / f"{style.id}_thumb.jpg"
        if not capture_frame(str(tmp_video), str(thumb_jpg), CAPTURE_SEC):
            print(f"  ❌ 截帧失败")
            tmp_video.unlink(missing_ok=True)
            continue

        # 3. 生成标注条（id + 中文名）
        label_text = f"{style.id}  {style.name}"
        label_png  = SHOWCASE_DIR / f"{style.id}_label.png"
        build_label_image(label_text, THUMB_WIDTH, LABEL_HEIGHT, str(label_png))

        # 4. 竖向拼接截图+标注
        cell_jpg = SHOWCASE_DIR / f"{style.id}.jpg"
        if label_png.exists():
            ok = stack_thumb_and_label(str(thumb_jpg), str(label_png), str(cell_jpg))
        else:
            # 如果标注生成失败，直接用截图
            shutil.copy(str(thumb_jpg), str(cell_jpg))
            ok = True

        if ok:
            cell_paths.append(str(cell_jpg))
            print(f"  ✅ 已保存: {cell_jpg}")
        else:
            print(f"  ⚠️  拼接失败，跳过")

        # 清理临时文件
        tmp_video.unlink(missing_ok=True)
        thumb_jpg.unlink(missing_ok=True)
        if label_png.exists():
            label_png.unlink()

    # 5. 拼汇总大图
    if cell_paths:
        grid_jpg = SHOWCASE_DIR / "_all_styles.jpg"
        print(f"\n🖼️  正在生成汇总图（{GRID_COLS}列 × {(len(cell_paths) + GRID_COLS - 1) // GRID_COLS}行）...")
        if build_grid(cell_paths, str(grid_jpg), cols=GRID_COLS):
            print(f"✅ 汇总图已生成: {grid_jpg}")
        else:
            print(f"❌ 汇总图生成失败")
    else:
        print("⚠️  没有成功的截图，跳过汇总图")

    print(f"\n完成！输出目录: {SHOWCASE_DIR.resolve()}")


if __name__ == "__main__":
    main()
