#!/usr/bin/env python3
"""
渲染多子多福项目的剪辑组合
"""
import sys
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from pathlib import Path
from scripts.understand.render_clips import ClipRenderer

print("=" * 70)
print("🎬 渲染多子多福项目剪辑组合")
print("=" * 70)

# 配置
project_path = "data/hangzhou-leiming/analysis/多子多福，开局就送绝美老婆"
video_dir = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆"
output_dir = "clips/多子多福，开局就送绝美老婆"

print(f"\n📁 项目路径: {project_path}")
print(f"🎬 视频目录: {video_dir}")
print(f"📤 输出目录: {output_dir}\n")

# 读取result.json
import json
result_file = Path(project_path) / "result.json"

if not result_file.exists():
    print(f"❌ 错误：未找到result.json文件: {result_file}")
    sys.exit(1)

with open(result_file, 'r', encoding='utf-8') as f:
    result = json.load(f)

clips_data = result.get('clips', [])
print(f"📊 找到 {len(clips_data)} 个剪辑组合\n")

# 显示前几个剪辑信息
print("剪辑列表预览：\n")
for i, clip in enumerate(clips_data[:5], 1):
    duration_min = clip['duration'] / 60
    print(f"  {i}. EP{clip['episode']}→{clip['hookEpisode']}  {duration_min:.2f}分钟  {clip['type']}")

if len(clips_data) > 5:
    print(f"  ... 还有 {len(clips_data) - 5} 个")

print(f"\n开始渲染...\n")

# 创建渲染器
renderer = ClipRenderer(
    project_path=project_path,
    output_dir=output_dir,
    video_dir=video_dir,
    project_name="多子多福，开局就送绝美老婆"
)

# 渲染所有剪辑
def on_progress(current: int, total: int, progress: float):
    """进度回调"""
    percent = progress * 100
    print(f"\r进度: [{current}/{total}] {percent:.1f}%", end='', flush=True)

try:
    output_paths = renderer.render_all_clips(on_clip_progress=on_progress)

    print(f"\n\n✅ 渲染完成！")
    print(f"\n输出文件: {len(output_paths)} 个\n")

    for i, path in enumerate(output_paths, 1):
        file_size = Path(path).stat().st_size / (1024 * 1024)  # MB
        print(f"  {i}. {path} ({file_size:.1f} MB)")

    print(f"\n所有视频已保存到: {output_dir}")

except Exception as e:
    print(f"\n❌ 渲染失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
